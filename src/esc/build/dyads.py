"""the directed dyad panel, (year, round, vote_type, from_iso3, to_iso3)

from_iso3 awards, to_iso3 receives, the pair is never collapsed

pairs that awarded nothing stay in with points = 0, only the top ten get points
so dropping the zeros would leave a panel of successes and turn every
coefficient into a selection artefact
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from esc import io
from esc.build import left_join, log, log_counts, require_non_empty
from esc.parse import entry_id

STEP = "dyads"

KEYS = ["year", "round", "vote_type", "from_iso3", "to_iso3"]


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
    migration = io.read_parquet("migration", "interim")
    pageviews = io.read_parquet("pageviews", "interim")
    regimes = io.read_parquet("voting_regimes", "interim")

    panel = _attach_points(_grid(votes, entries), votes)
    n_in = len(panel)

    panel = left_join(
        panel,
        dyad_static.rename(columns={"iso_o": "from_iso3", "iso_d": "to_iso3"}),
        ["from_iso3", "to_iso3"],
        "dyad_static",
        STEP,
    )

    # geo is the reporting country and citizen the citizenship, so this is the
    # stock of to_iso3 citizens living in from_iso3, the diaspora that votes
    panel = left_join(
        panel,
        migration.rename(
            columns={
                "geo_iso3": "from_iso3",
                "citizen_iso3": "to_iso3",
                "population": "migrant_stock",
            }
        ),
        ["year", "from_iso3", "to_iso3"],
        "migration",
        STEP,
    )

    # which dates this sum covers is decided by what fetch/pageviews.py asks for
    attention = (
        pageviews.groupby("entry_id", as_index=False)["views"]
        .sum()
        .rename(columns={"views": "views_total"})
    )
    panel["entry_id"] = entry_id(panel["year"], panel["to_iso3"]).values
    panel = left_join(panel, attention, ["entry_id"], "pageviews", STEP)

    panel = left_join(panel, regimes, ["year"], "voting_regimes", STEP)

    no_views = int(panel["views_total"].isna().sum())
    log_counts(STEP, "dyads", n_in, len(panel))
    log(STEP, f"years {panel['year'].min()}-{panel['year'].max()}")
    log(STEP, f"rows without pageviews: {no_views}")
    return io.write_parquet(require_non_empty(panel, "dyads"), "dyads", "processed")
