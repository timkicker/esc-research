"""teammate repo -> interim lyric_features, song_language and trends

lyrics: country and year come from the record and not from the key. unknown
labels raise because a typo in the llm output should not become a new category
trends: target_iso is the voting country, song_country the entry
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from esc import config, io
from esc.parse import enforce, entry_id

RAW_ID = "team_dataset"
FILE = "lyrics_analysis.json"
TRENDS_FILE = "trends_results.csv"

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


def _lookup(kind: str) -> dict[str, str]:
    cmap = io.read_parquet("country_map", "interim")
    rows = cmap[cmap["kind"] == kind]
    return dict(zip(rows["label"], rows["iso3"], strict=True))


def _records() -> pd.DataFrame:
    path = config.RAW / RAW_ID / FILE
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing, run `make data` first")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return pd.DataFrame.from_records(list(raw.values()))


def parse_lyrics() -> list[Path]:
    df = _records()
    lookup = _lookup("name")

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


def parse_trends() -> Path:
    path = config.RAW / RAW_ID / TRENDS_FILE
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing, run `make data` first")
    df = pd.read_csv(path, dtype="string", keep_default_na=False, na_values=[""])

    names, codes = _lookup("name"), _lookup("iso2")
    entry_iso3 = df["song_country"].map(names)
    voter_iso3 = df["target_iso"].str.lower().map(codes)
    for series, source, what in (
        (entry_iso3, df["song_country"], "song_country"),
        (voter_iso3, df["target_iso"], "target_iso"),
    ):
        missing = sorted(set(source[series.isna()]))
        if missing:
            raise ValueError(f"{TRENDS_FILE}: {what} not in country_map {missing}")

    year = pd.to_numeric(df["year"]).astype("int16")
    web = pd.to_numeric(df["trend_score"]).astype("float64")
    youtube = pd.to_numeric(df["youtube_score"]).astype("float64")
    out = pd.DataFrame(
        {
            "year": year,
            "from_iso3": voter_iso3.astype("string"),
            "entry_id": entry_id(year, entry_iso3.astype("string")).values,
            "web_interest": web,
            "youtube_interest": youtube,
            # below the trends threshold so neither source measured anything
            "censored": ((web == 0) & (youtube == 0)).astype("boolean"),
        }
    )
    out = enforce(out, "trends")
    print(
        f"[parse.team_dataset] trends: {len(out)} rows, "
        f"{out['censored'].mean():.0%} censored, years "
        f"{out['year'].min()}-{out['year'].max()}"
    )
    return io.write_parquet(out, "trends", "interim")


def parse() -> list[Path]:
    return [*parse_lyrics(), parse_trends()]
