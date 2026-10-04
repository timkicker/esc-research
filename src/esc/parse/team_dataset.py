"""teammate lyrics analysis -> interim lyric_features and song_language

country and year come from the record, not the key, the key glues them with
underscores. unknown labels raise, a typo in the llm output should not become a
new category
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from esc import config, io
from esc.parse import enforce, entry_id

RAW_ID = "team_dataset"
FILE = "lyrics_analysis.json"

SENTIMENTS = ("neutral", "sad", "funny")
THEMES = (
    "romance",
    "heartbreak",
    "kinship",
    "society",
    "nature",
    "folklore",
    "festivity",
    "other",
)
YES_NO = {"yes": True, "no": False}


def _check(series: pd.Series, allowed, what: str) -> None:
    bad = sorted(set(series.dropna()) - set(allowed))
    if bad:
        raise ValueError(f"{what}: unknown value(s) {bad}, allowed {list(allowed)}")


def _records() -> pd.DataFrame:
    path = config.RAW / RAW_ID / FILE
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing, run `make data` first")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return pd.DataFrame.from_records(list(raw.values()))


def parse() -> list[Path]:
    df = _records()
    cmap = io.read_parquet("country_map", "interim")
    names = cmap[cmap["kind"] == "name"]
    lookup = dict(zip(names["label"], names["iso3"], strict=True))

    iso3 = df["country"].map(lookup)
    missing = sorted(set(df.loc[iso3.isna(), "country"]))
    if missing:
        raise ValueError(f"{FILE}: country name(s) missing from country_map {missing}")

    year = pd.to_numeric(df["year"]).astype("int16")
    df["entry_id"] = entry_id(year, iso3.astype("string")).values

    for column, allowed in (
        ("sentiment", SENTIMENTS),
        ("theme", THEMES),
        ("repetition_main", YES_NO),
        ("high_repetition_chorus", YES_NO),
    ):
        _check(df[column], allowed, column)

    features = pd.DataFrame(
        {
            "entry_id": df["entry_id"],
            "sentiment": df["sentiment"],
            "repetition_verse": df["repetition_main"].map(YES_NO),
            "repetition_chorus": df["high_repetition_chorus"].map(YES_NO),
            "theme": df["theme"],
        }
    )
    for column in ("entry_id", "sentiment", "theme"):
        features[column] = features[column].astype("string")
    for column in ("repetition_verse", "repetition_chorus"):
        features[column] = features[column].astype("boolean")

    language = pd.DataFrame(
        {
            "entry_id": df["entry_id"].astype("string"),
            "language": df["language"].astype("string"),
        }
    )

    if features["entry_id"].duplicated().any():
        raise ValueError(f"{FILE}: duplicate entries after mapping to entry_id")

    out_features = enforce(features, "lyric_features")
    out_language = enforce(language, "song_language")
    span = f"{year.min()}-{year.max()}"
    print(f"[parse.team_dataset] {len(out_features)} entries, years {span}")
    return [
        io.write_parquet(out_features, "lyric_features", "interim"),
        io.write_parquet(out_language, "song_language", "interim"),
    ]
