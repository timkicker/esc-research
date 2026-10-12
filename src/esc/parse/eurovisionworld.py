"""eurovisionworld voting scripts -> interim votes_recent and entries_recent

each data/raw/eurovisionworld/<year>.js assigns json to a few variables.
voting_songs maps iso2 to artist and song, voting_table_main holds the finalists
as [running order, place, total, televote, jury, ...] and voting_point every
award as [from, to, _, jury points, televote points]. output matches the
spijkervet tables so build can concatenate
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from esc import config, io
from esc.parse import enforce, entry_id

RAW_ID = "eurovisionworld"
FILENAME = re.compile(r"^(\d{4})\.js$")
VARIABLE = re.compile(r"^(\w+) = (.*?);\s*$", re.MULTILINE)
NEEDED = ("voting_songs", "voting_table_main", "voting_point")


def _load(path: Path) -> dict:
    found = {
        name: json.loads(value)
        for name, value in VARIABLE.findall(path.read_text(encoding="utf-8"))
    }
    missing = [name for name in NEEDED if name not in found]
    if missing:
        raise ValueError(f"{path.name} lacks {missing}, the script format changed")
    return found


def _years() -> list[tuple[int, dict]]:
    source = config.RAW / RAW_ID
    out = []
    for path in sorted(source.glob("*.js")):
        if match := FILENAME.match(path.name):
            out.append((int(match.group(1)), _load(path)))
    if not out:
        raise FileNotFoundError(f"{source} has no voting scripts, run data first")
    return out


def _lookup() -> dict[str, str]:
    cmap = io.read_parquet("country_map", "interim")
    codes = cmap[cmap["kind"] == "iso2"]
    return dict(zip(codes["label"], codes["iso3"], strict=True))


def parse_entries() -> Path:
    mapping = _lookup()
    records = []
    for year, data in _years():
        for iso2, row in data["voting_table_main"].items():
            artist, song, *_ = data["voting_songs"][iso2]
            records.append(
                {
                    "year": year,
                    "country_iso3": mapping[iso2],
                    "running_order": row[0],
                    "place": row[1],
                    "points_total": row[2],
                    "artist": artist,
                    "song": song,
                }
            )

    df = pd.DataFrame.from_records(records)
    df["year"] = df["year"].astype("int16")
    for column in ("place", "running_order"):
        df[column] = df[column].astype("Int16")
    df["points_total"] = df["points_total"].astype("Int32")
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
    mapping = _lookup()
    records, unmapped = [], set()
    for year, data in _years():
        finalists = list(data["voting_table_main"])
        given = {}
        for voter, receiver, _, jury, tele in data["voting_point"]:
            given[("jury", voter, receiver)] = jury
            given[("televote", voter, receiver)] = tele
        # every voter against every finalist, the awards only list who got points
        for vote_type in ("jury", "televote"):
            voters = {v for (t, v, _), p in given.items() if t == vote_type and p}
            for voter in sorted(voters):
                for receiver in finalists:
                    if voter == receiver:
                        continue
                    if voter not in mapping or receiver not in mapping:
                        unmapped.update({voter, receiver} - set(mapping))
                        continue
                    records.append(
                        {
                            "year": year,
                            "round": "final",
                            "from_iso3": mapping[voter],
                            "to_iso3": mapping[receiver],
                            "vote_type": vote_type,
                            "points": given.get((vote_type, voter, receiver), 0),
                        }
                    )

    df = pd.DataFrame.from_records(records)
    df["year"] = df["year"].astype("int16")
    df["points"] = df["points"].astype("Int16")
    for column in ("round", "from_iso3", "to_iso3", "vote_type"):
        df[column] = df[column].astype("string")

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
