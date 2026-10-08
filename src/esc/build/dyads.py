"""the directed dyad panel, (year, round, vote_type, from_iso3, to_iso3)

finals from 2016 only. semi-finals have a different voter set and no jury from
2023, while before 2016 the split was never reported. the semi-final result
still enters as a column on the entry rather than its own row
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from esc import io
from esc.build import left_join, log, log_counts, optional_join, require_non_empty

STEP = "dyads"

KEYS = ["year", "round", "vote_type", "from_iso3", "to_iso3"]
FIRST_YEAR = 2016


def _grid(votes: pd.DataFrame, entries: pd.DataFrame) -> pd.DataFrame:
    voters = votes[["year", "round", "vote_type", "from_iso3"]].drop_duplicates()
    competitors = (
        entries[["year", "round", "country_iso3"]]
        .drop_duplicates()
        .rename(columns={"country_iso3": "to_iso3"})
    )
    log(STEP, f"{len(voters)} voter-show rows, {len(competitors)} entry-show rows")

    grid = voters.merge(competitors, on=["year", "round"], how="inner")
    self_pairs = int((grid["from_iso3"] == grid["to_iso3"]).sum())
    grid = grid[grid["from_iso3"] != grid["to_iso3"]]
    log(STEP, f"grid {len(grid) + self_pairs} pairs, {self_pairs} self-pairs removed")
    return grid.reset_index(drop=True)


def _attach_points(grid: pd.DataFrame, votes: pd.DataFrame) -> pd.DataFrame:
    panel = left_join(grid, votes, KEYS, "votes", STEP, validate="1:1")
    zeros = int(panel["points"].isna().sum())
    panel["points"] = panel["points"].fillna(0).astype("Int16")
    log(STEP, f"{zeros} pairs awarded nothing, filled with 0")

    orphans = len(votes) - (len(panel) - zeros)
    if orphans:
        raise ValueError(
            f"{orphans} vote rows found no place in the grid, entries and votes "
            "disagree about who took part"
        )
    return panel


def build() -> Path:
    votes = io.read_parquet("votes", "processed")
    entries = io.read_parquet("entries", "processed")
    dyad_static = io.read_parquet("dyad_static", "interim")
    regimes = io.read_parquet("voting_regimes", "interim")

    votes = votes[(votes["round"] == "final") & (votes["year"] >= FIRST_YEAR)]
    entries = entries[(entries["round"] == "final") & (entries["year"] >= FIRST_YEAR)]
    log(STEP, f"finals from {FIRST_YEAR}: {len(votes)} votes, {len(entries)} entries")

    panel = _attach_points(_grid(votes, entries), votes)
    n_in = len(panel)

    panel = left_join(
        panel,
        dyad_static.rename(columns={"iso_o": "from_iso3", "iso_d": "to_iso3"}),
        ["from_iso3", "to_iso3"],
        "dyad_static",
        STEP,
    )
    panel["entry_id"] = (
        panel["year"].astype("string") + "-" + panel["to_iso3"].astype("string")
    ).astype("string")

    panel = optional_join(
        panel, "trends", "interim", ["year", "from_iso3", "entry_id"], STEP
    )
    panel = optional_join(panel, "lyric_features", "interim", ["entry_id"], STEP)
    panel = left_join(panel, regimes, ["year"], "voting_regimes", STEP)

    log_counts(STEP, "dyads", n_in, len(panel))
    log(STEP, f"years {panel['year'].min()}-{panel['year'].max()}")
    return io.write_parquet(require_non_empty(panel, "dyads"), "dyads", "processed")
