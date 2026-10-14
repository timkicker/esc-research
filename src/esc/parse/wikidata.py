"""sparql results -> interim artists

an entry is matched by its song title and else by its artist name, both only
against what took part in the same edition. age is counted at the final.
groups and duos stay missing, they have neither a birth date nor a sex
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

from esc import config, io
from esc.parse import enforce

RAW_ID = "wikidata"
HUMAN = "Q5"
DAY = "11"
SEX = {
    "Q6581097": "male",
    "Q6581072": "female",
    "Q2449503": "male",
    "Q1052281": "female",
}
# two names in the artist field are a duo even if one of them is found alone
SEVERAL = re.compile(r"\s(&|and|feat\.?|ft\.?|x|with)\s", re.IGNORECASE)


def normalise(name) -> str:
    """casefold and drop accents and punctuation, Asteromáta meets Asteromata"""
    if name is None or pd.isna(name):
        return ""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]", "", text.casefold())


def _qid(row: dict, key: str) -> str | None:
    value = row.get(key, {}).get("value")
    return value.rsplit("/", 1)[-1] if value else None


def _label(row: dict, key: str) -> str:
    return row.get(key, {}).get("value", "")


def _births(path: Path) -> dict[str, set[str]]:
    """person -> birth dates known to the day"""
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing, run `esc data` again")
    rows = json.loads(path.read_text(encoding="utf-8"))["results"]["bindings"]
    out: dict[str, set[str]] = {}
    for row in rows:
        # an unknown birth date is stored as 2000-01-01 at century precision
        if row["birthPrecision"]["value"] == DAY:
            out.setdefault(_qid(row, "person"), set()).add(row["birth"]["value"][:10])
    return out


def _participants(path: Path) -> tuple[dict, dict, dict]:
    """people with their facts, song title -> performers, name -> people"""
    rows = json.loads(path.read_text(encoding="utf-8"))["results"]["bindings"]
    births = _births(path.with_name(f"{path.stem}-births.json"))
    people: dict[str, dict] = {}
    by_song: dict[str, set[str]] = {}
    by_name: dict[str, set[str]] = {}
    for row in rows:
        item, person = _qid(row, "item"), _qid(row, "person")
        facts = people.setdefault(
            person, {"types": set(), "births": set(), "sex": set()}
        )
        if kind := _qid(row, "personType"):
            facts["types"].add(kind)
        facts["births"] |= births.get(person, set())
        if sex := _qid(row, "sex"):
            facts["sex"].add(sex)
        if person == item:
            by_name.setdefault(normalise(_label(row, "personLabel")), set()).add(person)
        else:
            by_song.setdefault(normalise(_label(row, "itemLabel")), set()).add(person)
    return people, by_song, by_name


def _age(births: set[str], final: date) -> int | None:
    """years at the final, one birth date or nothing"""
    if len(births) != 1:
        return None
    try:
        born = date.fromisoformat(next(iter(births)))
    except ValueError:
        return None
    return final.year - born.year - ((final.month, final.day) < (born.month, born.day))


def _by_prefix(artist: str, by_name: dict[str, set[str]]) -> set[str]:
    """stage name against full name, Agnete meets Agnete Saba, only if unique"""
    key = normalise(artist)
    if len(key) < 4:
        return set()
    hits = [
        qids
        for name, qids in by_name.items()
        if name and (name.startswith(key) or key.startswith(name))
    ]
    return hits[0] if len(hits) == 1 else set()


def _resolve(performers: set[str], people: dict, final: date) -> tuple:
    """(age, sex, kind) for a single human, nothing for a group or a duo"""
    if not performers:
        return None, None, "unmatched"
    humans = [p for p in performers if HUMAN in people[p]["types"]]
    if len(performers) != 1 or len(humans) != 1:
        return None, None, "group"
    facts = people[humans[0]]
    sex = SEX.get(next(iter(facts["sex"])), "other") if len(facts["sex"]) == 1 else None
    return _age(facts["births"], final), sex, "solo"


def _entries() -> pd.DataFrame:
    frames = [io.read_parquet("entries", "interim")]
    if io.parquet_path("entries_recent", "interim").exists():
        frames.append(io.read_parquet("entries_recent", "interim"))
    entries = pd.concat(frames, ignore_index=True)
    columns = ["entry_id", "year", "artist", "song"]
    return entries[columns].drop_duplicates("entry_id").sort_values("entry_id")


def parse() -> list[Path]:
    folder = config.RAW / RAW_ID
    files = {int(p.stem): p for p in folder.glob("*.json") if p.stem.isdigit()}
    if not files:
        raise FileNotFoundError(f"no {RAW_ID} results in {folder}, run `esc data`")

    finals = io.read_parquet("contest_dates", "interim")
    finals = dict(zip(finals["year"].astype(int), finals["final_date"], strict=True))
    entries = _entries()
    entries = entries[entries["year"].astype(int).isin(files)]

    rows, kinds, unmatched = [], {"solo": 0, "group": 0, "unmatched": 0}, []
    for year, group in entries.groupby("year"):
        people, by_song, by_name = _participants(files[int(year)])
        final = pd.Timestamp(finals[int(year)]).date()
        for entry in group.itertuples():
            performers = (
                by_song.get(normalise(entry.song))
                or by_name.get(normalise(entry.artist))
                or _by_prefix(entry.artist, by_name)
            )
            if SEVERAL.search(str(entry.artist)):
                age, sex, kind = None, None, "group"
            else:
                age, sex, kind = _resolve(performers, people, final)
            kinds[kind] += 1
            if kind == "unmatched":
                unmatched.append(entry.entry_id)
            rows.append(
                {"entry_id": entry.entry_id, "artist_age": age, "artist_sex": sex}
            )

    print(
        f"[parse.{RAW_ID}] {len(entries)} entries in {len(files)} year(s): "
        f"{kinds['solo']} solo, {kinds['group']} group or duo, "
        f"{kinds['unmatched']} not found"
    )
    if unmatched:
        print(f"[parse.{RAW_ID}] not found: {', '.join(unmatched)}")

    artists = pd.DataFrame(rows, columns=["entry_id", "artist_age", "artist_sex"])
    return [io.write_parquet(enforce(artists, "artists"), "artists", "interim")]
