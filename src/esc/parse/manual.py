"""hand curated csvs in data/manual/ -> interim tables

the only inputs we own so this one can actually be written, the headers are ours

pandas applies comment="#" anywhere on a line not just at the start, so no #
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
    df["valid_from"] = pd.to_numeric(df["valid_from"]).astype("int16")
    df["valid_to"] = pd.to_numeric(df["valid_to"]).astype("Int16")
    out = enforce(df, "country_map")
    print(f"[parse.manual] country_map: {len(df)} in -> {len(out)} out")
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
        f"[parse.manual] voting_regimes: {len(df)} in -> {len(out)} out, "
        f"{unverified} year(s) unverified or cancelled"
    )
    return io.write_parquet(out, "voting_regimes", "interim")


def parse_recent_entries() -> Path:
    df = _read("recent_entries")
    # drop the shipped example row so it cannot leak into the panel
    placeholders = int((df["country_iso3"] == PLACEHOLDER_ISO3).sum())
    df = df[df["country_iso3"] != PLACEHOLDER_ISO3].copy()

    df["year"] = pd.to_numeric(df["year"]).astype("int16")
    df["running_order"] = pd.to_numeric(df["running_order"]).astype("Int16")
    df["place"] = pd.to_numeric(df["place"]).astype("Int16")
    df["points_total"] = pd.to_numeric(df["points_total"]).astype("Int32")
    df["entry_id"] = entry_id(df["year"], df["country_iso3"]).values
    # not recorded by hand yet, missing not false
    df["qualified"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    df["selection_type"] = pd.Series(pd.NA, index=df.index, dtype="string")

    out = enforce(df, "entries")
    total = len(df) + placeholders
    print(
        f"[parse.manual] recent_entries: {total} in -> {len(out)} out, "
        f"{placeholders} placeholder row(s) dropped"
    )
    return io.write_parquet(out, "entries_manual", "interim")


def parse() -> list[Path]:
    return [parse_country_map(), parse_voting_regimes(), parse_recent_entries()]
