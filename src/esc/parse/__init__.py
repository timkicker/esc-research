"""raw bytes -> typed interim tables

the schema is fixed here instead of per source so two sources cannot disagree
about dtypes, it is the one from README.md as pandas dtypes

entry_id is year-iso3, one entry per country per contest so that is a real key
"""

from __future__ import annotations

import pandas as pd

# nullable dtypes throughout, a missing running order and a running order of
# zero are not the same thing
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
        "selection_type": "string",
    },
    "votes": {
        "year": "int16",
        "round": "string",
        "from_iso3": "string",
        "to_iso3": "string",
        "vote_type": "string",
        "points": "Int16",
    },
    "jurors": {
        "year": "int16",
        "country_iso3": "string",
        "juror_letter": "string",
        "entry_id": "string",
        "rank": "Int16",
    },
    "odds": {
        "year": "int16",
        "entry_id": "string",
        "bookmaker": "string",
        "date": "datetime64[ns]",
        "decimal_odds": "float64",
    },
    "pageviews": {
        "entry_id": "string",
        "wiki_lang": "string",
        "date": "datetime64[ns]",
        "views": "Int64",
    },
    "migration": {
        "year": "int16",
        "geo_iso3": "string",
        "citizen_iso3": "string",
        "population": "Int64",
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
    "audio_features": {
        "entry_id": "string",
        "feature_name": "string",
        "value": "float64",
    },
    "voting_regimes": {
        "year": "int16",
        "jury_share": "float64",
        "televote_share": "float64",
        "separately_reported": "boolean",
        "row_vote": "boolean",
    },
    "country_map": {
        "esc_name": "string",
        "iso3": "string",
        "eurostat_geo": "string",
        "wikidata_qid": "string",
        "valid_from": "int16",
        "valid_to": "Int16",
    },
}

ROUNDS = ("semi1", "semi2", "final")
VOTE_TYPES = ("jury", "televote", "combined")


def entry_id(year, country_iso3) -> pd.Series:
    left = pd.Series(year).astype("string")
    right = pd.Series(country_iso3).astype("string")
    return (left + "-" + right).astype("string")


def enforce(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """cast to the interim schema, a missing or unexpected column is an error"""
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
