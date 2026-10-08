"""rendered eurovisionworld scoreboards -> interim votes_recent and entries_recent

the scoreboard is a matrix where header cells carry data-from and rows carry
id="tr_<iso2>". output matches the spijkervet tables so build can concatenate
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from esc import config, io
from esc.parse import enforce, entry_id

RAW_ID = "eurovisionworld"
VOTE_TYPE = {"jury": "jury", "tele": "televote"}
# rank, flag, name and total sit in front of the first point column
LEAD_CELLS = 3
FILENAME = re.compile(r"^(\d{4})-(jury|tele)\.html$")


def _scoreboard(path: Path) -> list[tuple[str, str, int]]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table", class_="scoreboard_table")
    if table is None:
        raise ValueError(f"{path.name} has no scoreboard table, the layout changed")

    rows = table.find_all("tr")
    voters = [
        (i, cell["data-from"])
        for i, cell in enumerate(rows[0].find_all(["th", "td"]))
        if cell.has_attr("data-from")
    ]
    if not voters:
        raise ValueError(f"{path.name} header has no data-from cells")

    out = []
    for row in rows[1:]:
        row_id = row.get("id", "")
        if not row_id.startswith("tr_"):
            continue
        receiver = row_id.removeprefix("tr_")
        cells = row.find_all(["th", "td"])
        for index, voter in voters:
            position = index + LEAD_CELLS
            if position >= len(cells):
                continue
            text = cells[position].get_text(strip=True)
            out.append((voter, receiver, int(text) if text.isdigit() else 0))
    return out


def _lookup() -> dict[str, str]:
    cmap = io.read_parquet("country_map", "interim")
    codes = cmap[cmap["kind"] == "iso2"]
    return dict(zip(codes["label"], codes["iso3"], strict=True))


def _results(path: Path) -> list[dict]:
    """the finalist table next to the scoreboard with artist, song and running order"""
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table", class_="v_table_main")
    if table is None:
        raise ValueError(f"{path.name} has no results table, the layout changed")

    out = []
    for row in table.find_all("tr"):
        row_id = row.get("id", "")
        if not row_id.startswith("v_tr_"):
            continue
        cells = row.find_all(["th", "td"])
        artist_tag = cells[2].find("span", class_="v_artist")
        artist = artist_tag.get_text(strip=True) if artist_tag else ""
        if artist_tag:
            artist_tag.extract()
        order = cells[6].get_text(strip=True) if len(cells) > 6 else ""
        out.append(
            {
                "iso2": row_id.removeprefix("v_tr_"),
                "place": cells[0].get_text(strip=True),
                "song": cells[2].get_text(" ", strip=True),
                "artist": artist,
                "points_total": cells[3].get_text(strip=True),
                "running_order": order,
            }
        )
    return out


def parse_entries() -> Path:
    source = config.RAW / RAW_ID
    mapping = _lookup()
    records = []
    # the jury page carries the same finalist table as the televote page
    for path in sorted(source.glob("*-jury.html")):
        match = FILENAME.match(path.name)
        if not match:
            continue
        year = int(match.group(1))
        for item in _results(path):
            if item["iso2"] not in mapping:
                continue
            iso3 = mapping[item["iso2"]]
            records.append({**item, "year": year, "country_iso3": iso3})

    df = pd.DataFrame.from_records(records).drop(columns=["iso2"])
    df["year"] = df["year"].astype("int16")
    for column in ("place", "running_order"):
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int16")
    totals = pd.to_numeric(df["points_total"], errors="coerce")
    df["points_total"] = totals.astype("Int32")
    for column in ("artist", "song", "country_iso3"):
        df[column] = df[column].astype("string")
    df["round"] = pd.Series("final", index=df.index, dtype="string")
    df["entry_id"] = entry_id(df["year"], df["country_iso3"]).values
    for column, dtype in (
        ("qualified", "boolean"),
        ("artist_age", "Int16"),
        ("artist_sex", "string"),
        ("song_language", "string"),
    ):
        df[column] = pd.Series(pd.NA, index=df.index, dtype=dtype)

    out = enforce(df, "entries")
    years = sorted(out["year"].unique())
    print(
        f"[parse.eurovisionworld] entries_recent: {len(out)} finalists, years {years}"
    )
    return io.write_parquet(out, "entries_recent", "interim")


def parse_votes() -> Path:
    source = config.RAW / RAW_ID
    files = sorted(source.glob("*.html"))
    if not files:
        raise FileNotFoundError(f"{source} is empty, run `make data` first")

    mapping = _lookup()
    records, unmapped = [], set()
    for path in files:
        match = FILENAME.match(path.name)
        if not match:
            continue
        year, view = int(match.group(1)), match.group(2)
        for voter, receiver, points in _scoreboard(path):
            if voter not in mapping or receiver not in mapping:
                unmapped.update({voter, receiver} - set(mapping))
                continue
            records.append(
                {
                    "year": year,
                    "round": "final",
                    "from_iso3": mapping[voter],
                    "to_iso3": mapping[receiver],
                    "vote_type": VOTE_TYPE[view],
                    "points": points,
                }
            )

    df = pd.DataFrame.from_records(records)
    df["year"] = df["year"].astype("int16")
    df["points"] = df["points"].astype("Int16")
    for column in ("round", "from_iso3", "to_iso3", "vote_type"):
        df[column] = df[column].astype("string")
    df = df[df["from_iso3"] != df["to_iso3"]]

    out = enforce(df, "votes")
    years = sorted(out["year"].unique())
    print(
        f"[parse.eurovisionworld] votes_recent: {len(out)} rows, years {years}, "
        f"{out['from_iso3'].nunique()} voters"
    )
    if unmapped:
        print(f"[parse.eurovisionworld] no country_map row for {sorted(unmapped)}")
    return io.write_parquet(out, "votes_recent", "interim")


def parse() -> list[Path]:
    return [parse_entries(), parse_votes()]
