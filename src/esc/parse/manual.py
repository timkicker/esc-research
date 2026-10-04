"""hand curated csvs in data/manual/ -> typed interim tables

the only inputs we own, so unlike the other parse modules this one can be
written without looking at a download first

pandas applies comment="#" anywhere on a line, not only at the start, so no #
inside a field
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from esc import config, io
from esc.parse import enforce, entry_id

PLACEHOLDER_ISO3 = "XXX"

BOOLEANS = {"true": True, "false": False, "TRUE": True, "FALSE": False}


def _read(name: str) -> pd.DataFrame:
    path = config.MANUAL / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing, it is committed so this is odd")
    return pd.read_csv(
        path,
        comment="#",
        dtype="string",
        keep_default_na=False,
        na_values=[""],
    )


def _to_boolean(series: pd.Series) -> pd.Series:
    return series.map(BOOLEANS).astype("boolean")


def parse_country_map() -> Path:
    df = _read("country_map").drop(columns=["notes"])
    for column in ("valid_from", "valid_to"):
        df[column] = pd.to_numeric(df[column]).astype("Int16")
    out = enforce(df, "country_map")
    kinds = out["kind"].value_counts().to_dict()
    print(f"[parse.manual] country_map: {len(out)} labels, {kinds}")
    return io.write_parquet(out, "country_map", "interim")


def parse_voting_regimes() -> Path:
    df = _read("voting_regimes").drop(columns=["notes"])
    df["year"] = pd.to_numeric(df["year"]).astype("int16")
    for column in ("jury_share", "televote_share"):
        df[column] = pd.to_numeric(df[column]).astype("float64")
    for column in ("separately_reported", "row_vote"):
        df[column] = _to_boolean(df[column])
    out = enforce(df, "voting_regimes")
    unverified = int(out["separately_reported"].isna().sum())
    print(
        f"[parse.manual] voting_regimes: {len(out)} rows, "
        f"{unverified} year(s) unverified or cancelled"
    )
    return io.write_parquet(out, "voting_regimes", "interim")


def parse_contest_dates() -> Path:
    df = _read("contest_dates")
    df["year"] = pd.to_numeric(df["year"]).astype("int16")
    df["final_date"] = pd.to_datetime(df["final_date"])
    out = enforce(df, "contest_dates")
    print(f"[parse.manual] contest_dates: {len(out)} years")
    return io.write_parquet(out, "contest_dates", "interim")


def parse_recent_entries() -> Path:
    """entries for the years after the upstream release, typed in by hand"""
    df = _read("recent_entries")
    placeholders = int((df["country_iso3"] == PLACEHOLDER_ISO3).sum())
    df = df[df["country_iso3"] != PLACEHOLDER_ISO3].copy()

    df["year"] = pd.to_numeric(df["year"]).astype("int16")
    df["running_order"] = pd.to_numeric(df["running_order"]).astype("Int16")
    df["place"] = pd.to_numeric(df["place"]).astype("Int16")
    df["points_total"] = pd.to_numeric(df["points_total"]).astype("Int32")
    df["entry_id"] = entry_id(df["year"], df["country_iso3"]).values
    # filled later by build/entries.py from the artists and song_language tables
    for column, dtype in (
        ("qualified", "boolean"),
        ("artist_age", "Int16"),
        ("artist_sex", "string"),
        ("song_language", "string"),
    ):
        df[column] = pd.Series(pd.NA, index=df.index, dtype=dtype)

    out = enforce(df, "entries")
    total = len(df) + placeholders
    print(
        f"[parse.manual] recent_entries: {total} in -> {len(out)} out, "
        f"{placeholders} placeholder row(s) dropped"
    )
    return io.write_parquet(out, "entries_manual", "interim")


def parse() -> list[Path]:
    return [
        parse_country_map(),
        parse_voting_regimes(),
        parse_contest_dates(),
        parse_recent_entries(),
    ]
