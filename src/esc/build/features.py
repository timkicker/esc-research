"""dyad panel -> model ready features

the receiver effect is the important one, a country's points are partly the
song and partly the relationship, so without controlling for what everyone else
gave the same entry a pair coefficient is just measuring a good song
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from esc import io
from esc.build import log, log_counts, require_non_empty

STEP = "features"

ENTRY_KEYS = ["year", "round", "vote_type", "to_iso3"]


def build() -> Path:
    panel = io.read_parquet("dyads", "processed")
    n_in = len(panel)

    grouped = panel.groupby(ENTRY_KEYS)["points"]
    received = grouped.transform("sum").astype("float64")
    voters = grouped.transform("size").astype("float64")

    # leave one out, what the rest of the field gave this entry
    others = voters - 1
    panel["points_received_total"] = received
    panel["receiver_effect"] = np.where(
        others > 0, (received - panel["points"]) / others, np.nan
    )

    panel["log_dist"] = np.log(panel["dist"].astype("float64"))
    panel["log_migrant_stock"] = np.log1p(panel["migrant_stock"].astype("float64"))
    panel["has_pageviews"] = panel["views_total"].notna()

    thin = int(panel["receiver_effect"].isna().sum())
    if thin:
        log(STEP, f"{thin} rows in a show with a single voter, receiver effect is NA")
    with_views = int(panel["has_pageviews"].sum())
    log(STEP, f"{with_views} of {len(panel)} rows have pageviews")

    log_counts(STEP, "features", n_in, len(panel))
    return io.write_parquet(
        require_non_empty(panel, "features"), "features", "processed"
    )
