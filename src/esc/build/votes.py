"""interim votes -> processed votes

stays directed, never collapsed into unordered pairs
"""

from __future__ import annotations

from pathlib import Path

from esc import io
from esc.build import left_join, log, log_counts, require_non_empty
from esc.parse import VOTE_TYPES, enforce

STEP = "votes"


def build() -> Path:
    votes = io.read_parquet("votes", "interim")
    regimes = io.read_parquet("voting_regimes", "interim")
    n_in = len(votes)

    bad = sorted(set(votes["vote_type"].dropna()) - set(VOTE_TYPES))
    if bad:
        raise ValueError(f"unknown vote_type {bad}, expected one of {VOTE_TYPES}")

    self_votes = int((votes["from_iso3"] == votes["to_iso3"]).sum())
    if self_votes:
        raise ValueError(
            f"{self_votes} rows where a country votes for itself, from and to are "
            "probably swapped"
        )

    # attached only to check the year against the regime then thrown away again
    checked = left_join(votes, regimes, ["year"], "voting_regimes", STEP)
    missing_regime = sorted(checked.loc[checked["jury_share"].isna(), "year"].unique())
    if missing_regime:
        log(STEP, f"no verified regime for {missing_regime}, splits will drop them")

    separate = checked["separately_reported"].fillna(False)
    early_jury = checked[(checked["vote_type"] == "jury") & ~separate]
    if len(early_jury):
        years = sorted(early_jury["year"].unique())
        raise ValueError(
            f"vote_type 'jury' in {years} which are not separately_reported, before "
            "2016 the components are not public so this is 'combined' mislabelled"
        )

    out = enforce(votes, "votes")
    log_counts(STEP, "votes", n_in, len(out))
    for vote_type, count in out["vote_type"].value_counts().items():
        log(STEP, f"vote_type {vote_type}: {count} rows")
    return io.write_parquet(require_non_empty(out, "votes"), "votes", "processed")
