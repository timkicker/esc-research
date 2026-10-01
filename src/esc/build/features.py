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


def _past_points(panel: pd.DataFrame) -> pd.DataFrame:
    """mean points this ordered pair exchanged in earlier contests

    uses the whole vote history, not just the panel years, because the point of
    the pair features is the long memory. strictly earlier years only, so it
    cannot leak the year it is predicting
    """
    history = io.read_parquet("votes", "processed")
    history = history[history["round"] == "final"]
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

    out = panel.merge(
        per_year[["from_iso3", "to_iso3", "year", "past_points", "past_meetings"]],
        on=["from_iso3", "to_iso3", "year"],
        how="left",
        validate="m:1",
    )
    never = int(out["past_points"].isna().sum())
    log(STEP, f"{never} of {len(out)} rows are a pair meeting for the first time")
    return out


def build() -> Path:
    panel = io.read_parquet("dyads", "processed")
    n_in = len(panel)
    points = panel["points"].astype("float64")

    # share of the pool handed out in that show, so years and vote types are
    # comparable. the pool doubled in 2016 when the split was introduced
    pool = points.groupby([panel[k] for k in SHOW_KEYS]).transform("sum")
    panel["points_share"] = np.where(pool > 0, points / pool, np.nan)

    grouped = points.groupby([panel[k] for k in ENTRY_KEYS])
    received = grouped.transform("sum")
    voters = grouped.transform("size")

    # leave one out, what the rest of the field gave this entry
    others = voters - 1
    panel["points_received_total"] = received
    leave_one_out = (received - points) / others
    panel["receiver_effect"] = np.where(others > 0, leave_one_out, np.nan)

    panel["log_dist"] = np.log(panel["dist"].astype("float64"))
    panel = _past_points(panel)

    thin = int(np.isnan(panel["receiver_effect"]).sum())
    if thin:
        log(STEP, f"{thin} rows in a show with a single voter, receiver effect is NA")
    for vote_type, count in panel["vote_type"].value_counts().items():
        log(STEP, f"vote_type {vote_type}: {count} rows")

    log_counts(STEP, "features", n_in, len(panel))
    return io.write_parquet(
        require_non_empty(panel, "features"), "features", "processed"
    )
