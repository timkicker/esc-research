"""raw bytes -> typed interim tables

the schema is fixed here instead of per source so two sources cannot disagree
about dtypes. it is the one from README.md as pandas dtypes

entry_id is year-iso3 and since there is one entry per country per contest
that is a real key
"""

from __future__ import annotations

import pandas as pd

# nullable dtypes throughout because a missing running order is not a zero one
SCHEMA: dict[str, dict[str, str]] = {
    "entries": {
        "entry_id": "string",
        "year": "int16",
        "country_iso3": "string",
        "artist": "string",
        "song": "string",
        "running_order": "Int16",
        "round": "string",
        "place": "Int16",
        "points_total": "Int32",
        "qualified": "boolean",
        "artist_age": "Int16",
        "artist_sex": "string",
        "song_language": "string",
    },
    "votes": {
        "year": "int16",
        "round": "string",
        "from_iso3": "string",
        "to_iso3": "string",
        "vote_type": "string",
        "points": "Int16",
    },
    "dyad_static": {
        "iso_o": "string",
        "iso_d": "string",
        "dist": "float64",
        "distw": "float64",
        "contig": "boolean",
        "comlang_off": "boolean",
        "comlang_ethno": "boolean",
        "colony": "boolean",
        "comcol": "boolean",
        "smctry": "boolean",
    },
    "voting_regimes": {
        "year": "int16",
        "jury_share": "float64",
        "televote_share": "float64",
        "separately_reported": "boolean",
        "row_vote": "boolean",
    },
    "country_map": {
        "label": "string",
        "iso3": "string",
        "kind": "string",
        "valid_from": "Int16",
        "valid_to": "Int16",
    },
    "contest_dates": {
        "year": "int16",
        "final_date": "datetime64[ns]",
    },
    "artists": {
        "entry_id": "string",
        "artist_age": "Int16",
        "artist_sex": "string",
    },
    "song_language": {
        "entry_id": "string",
        "language": "string",
    },
    # one row per voting country and entry since that is the whole point of using trends
    "trends": {
        "year": "int16",
        "from_iso3": "string",
        "entry_id": "string",
        "web_interest": "float64",
        "youtube_interest": "float64",
        "censored": "boolean",
    },
    "lyric_features": {
        "entry_id": "string",
        "sentiment": "string",
        "repetition_verse": "boolean",
        "repetition_chorus": "boolean",
        "theme": "string",
    },
}

ROUNDS = ("semi1", "semi2", "final")
VOTE_TYPES = ("jury", "televote", "combined")


def entry_id(year, country_iso3) -> pd.Series:
    left = pd.Series(year).astype("string")
    right = pd.Series(country_iso3).astype("string")
    return (left + "-" + right).astype("string")


def enforce(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """cast to the interim schema and fail on a missing or unexpected column"""
    try:
        dtypes = SCHEMA[table]
    except KeyError:
        known = ", ".join(sorted(SCHEMA))
        raise ValueError(f"unknown table {table!r}, expected one of {known}") from None

    missing = sorted(set(dtypes) - set(df.columns))
    extra = sorted(set(df.columns) - set(dtypes))
    if missing or extra:
        raise ValueError(
            f"{table}: column mismatch. missing={missing or 'none'}, "
            f"unexpected={extra or 'none'}"
        )

    out = df.loc[:, list(dtypes)].copy()
    for column, dtype in dtypes.items():
        out[column] = out[column].astype(dtype)
    return out
