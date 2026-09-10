"""interim tables -> processed tables

offline, and everything logs what went in, what came out and what did not match
because most surprising numbers here turn out to be a bad merge
"""

from __future__ import annotations

import pandas as pd


def log(step: str, message: str) -> None:
    print(f"[build.{step}] {message}")


def log_counts(step: str, table: str, n_in: int, n_out: int) -> None:
    delta = n_out - n_in
    sign = "+" if delta >= 0 else ""
    log(step, f"{table}: {n_in} rows in -> {n_out} rows out ({sign}{delta})")


def left_join(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: list[str],
    label: str,
    step: str,
    validate: str = "m:1",
) -> pd.DataFrame:
    """left join and report the keys that found nothing

    validate defaults to m:1 so a non unique right side raises instead of
    quietly multiplying rows
    """
    before = len(left)
    merged = left.merge(right, on=on, how="left", validate=validate, indicator="_merge")
    unmatched = int((merged["_merge"] == "left_only").sum())
    merged = merged.drop(columns="_merge")

    if len(merged) != before:
        raise ValueError(
            f"{label}: row count changed {before} -> {len(merged)}, right side is "
            f"not unique on {on}"
        )
    share = unmatched / before if before else 0.0
    log(
        step,
        f"join {label} on {'+'.join(on)}: {before} rows, "
        f"{unmatched} without a match ({share:.1%})",
    )
    return merged


def require_non_empty(df: pd.DataFrame, table: str) -> pd.DataFrame:
    if df.empty:
        raise ValueError(
            f"{table} came out empty, that is a broken join or missing raw data "
            "and not a result, run `make data && make parse` first"
        )
    return df
