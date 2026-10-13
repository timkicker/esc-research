"""dyad panel -> model ready features

the receiver effect is the important one. a country's points are partly the song
and partly the relationship, so without controlling for what everyone else gave
the same entry, a pair coefficient is just measuring a good song. it is also
what carries the song side now that there are no audio features
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from esc import io
from esc.build import log, log_counts, require_non_empty

STEP = "features"
FIRST_HISTORY_YEAR = 1957

SHOW_KEYS = ["year", "round", "vote_type"]
ENTRY_KEYS = [*SHOW_KEYS, "to_iso3"]


def pair_history(votes: pd.DataFrame, skip_year: int | None = None) -> pd.DataFrame:
    """mean points and meetings of each ordered pair in strictly earlier finals

    skip_year drops one contest from the history, so a check can rebuild the
    feature from the training years of a fold only
    """
    history = votes[votes["round"] == "final"]
    if skip_year is not None:
        history = history[history["year"] != skip_year]
    per_year = (
        history.groupby(["from_iso3", "to_iso3", "year"], as_index=False)["points"]
        .mean()
        .sort_values("year")
    )
    grouped = per_year.groupby(["from_iso3", "to_iso3"])["points"]
    per_year["past_points"] = grouped.transform(lambda s: s.shift().expanding().mean())
    per_year["past_meetings"] = grouped.transform(
        lambda s: s.shift().expanding().count()
    )
    return per_year[["from_iso3", "to_iso3", "year", "past_points", "past_meetings"]]


def _past_points(panel: pd.DataFrame) -> pd.DataFrame:
    """mean points this ordered pair exchanged in earlier contests

    uses the whole vote history including the years before the panel. only
    strictly earlier years count so it cannot leak the year it predicts
    """
    per_year = pair_history(io.read_parquet("votes", "processed"))
    out = panel.merge(
        per_year,
        on=["from_iso3", "to_iso3", "year"],
        how="left",
        validate="m:1",
    )
    never = int(out["past_points"].isna().sum())
    log(STEP, f"{never} of {len(out)} rows are a pair meeting for the first time")
    return out


def _running_position(panel: pd.DataFrame) -> pd.DataFrame:
    """slot in the final scaled to 0..1 because finals differ in size

    the order is out two to three days before the final and may go into a
    forecast. the semi final result may not because it stays secret until
    after the final
    """
    entries = io.read_parquet("entries", "processed")
    finals = entries[entries["round"] == "final"]
    slots = finals.groupby("year")["running_order"].transform("max")
    # 2020 has one placeholder row and no final
    order = finals["running_order"].astype("float64")
    span = (slots - 1).astype("float64").where(slots > 1)
    lookup = finals.assign(running_position=(order - 1) / span)
    out = panel.merge(
        lookup[["entry_id", "running_position"]],
        on="entry_id",
        how="left",
        validate="m:1",
    )
    missing = int(out["running_position"].isna().sum())
    log(STEP, f"{missing} of {len(out)} rows without a running order")
    return out


def build() -> Path:
    panel = io.read_parquet("dyads", "processed")
    n_in = len(panel)
    points = panel["points"].astype("float64")

    # share of the pool because that is the only way years and vote types compare
    pool = points.groupby([panel[k] for k in SHOW_KEYS]).transform("sum")
    panel["points_share"] = np.where(pool > 0, points / pool, np.nan)

    grouped = points.groupby([panel[k] for k in ENTRY_KEYS])
    received = grouped.transform("sum")
    voters = grouped.transform("size")

    # leave one out (what the rest of the field gave this entry)
    others = voters - 1
    panel["points_received_total"] = received
    leave_one_out = (received - points) / others
    panel["receiver_effect"] = np.where(others > 0, leave_one_out, np.nan)

    panel["log_dist"] = np.log(panel["dist"].astype("float64"))
    panel = _past_points(panel)
    panel = _running_position(panel)

    thin = int(np.isnan(panel["receiver_effect"]).sum())
    if thin:
        log(STEP, f"{thin} rows in a show with a single voter, receiver effect is NA")
    for vote_type, count in panel["vote_type"].value_counts().items():
        log(STEP, f"vote_type {vote_type}: {count} rows")

    log_counts(STEP, "features", n_in, len(panel))
    return io.write_parquet(
        require_non_empty(panel, "features"), "features", "processed"
    )
