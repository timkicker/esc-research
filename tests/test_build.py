from __future__ import annotations

import pandas as pd
import pytest

from esc import io
from esc.build import dyads, entries, features, votes

LADDER_SUM = 58


@pytest.fixture()
def built(interim):
    entries.build()
    votes.build()
    dyads.build()
    features.build()
    return interim


def test_entries_rejects_a_country_missing_from_the_map(interim):
    table = io.read_parquet("entries", "interim")
    table.loc[0, "country_iso3"] = "ZZZ"
    io.write_parquet(table, "entries", "interim")
    with pytest.raises(ValueError, match="country_map.csv"):
        entries.build()


def test_votes_rejects_a_country_voting_for_itself(interim):
    table = io.read_parquet("votes", "interim")
    table.loc[0, "to_iso3"] = table.loc[0, "from_iso3"]
    io.write_parquet(table, "votes", "interim")
    with pytest.raises(ValueError, match="votes for itself"):
        votes.build()


def test_votes_rejects_a_jury_series_before_it_existed(interim):
    table = io.read_parquet("votes", "interim")
    table.loc[table["year"] == 2015, "vote_type"] = "jury"
    io.write_parquet(table, "votes", "interim")
    with pytest.raises(ValueError, match="separately_reported"):
        votes.build()


def test_every_voter_awards_the_full_ladder(built):
    table = io.read_parquet("votes", "processed")
    totals = table.groupby(["year", "round", "from_iso3", "vote_type"])["points"].sum()
    assert set(totals.unique()) == {LADDER_SUM}


def test_row_counts_per_year_are_non_zero(built):
    table = io.read_parquet("dyads", "processed")
    counts = table.groupby("year").size()
    assert (counts > 0).all()
    assert 2020 not in counts.index


def test_country_map_covers_every_country_in_the_panel(built):
    table = io.read_parquet("dyads", "processed")
    known = set(io.read_parquet("country_map", "interim")["iso3"])
    assert set(table["from_iso3"]) <= known
    assert set(table["to_iso3"]) <= known


def test_dyads_have_no_orphan_entry_ids(built):
    table = io.read_parquet("dyads", "processed")
    known = set(io.read_parquet("entries", "processed")["entry_id"])
    assert set(table["entry_id"]) <= known


def test_dyads_keep_the_pairs_that_scored_nothing(built):
    table = io.read_parquet("dyads", "processed")
    # twelve countries and only ten score, so every voter leaves one pair at zero
    assert (table["points"] == 0).sum() > 0
    assert table["points"].min() == 0


def test_dyads_stay_directed(built):
    table = io.read_parquet("dyads", "processed")
    pairs = set(zip(table["from_iso3"], table["to_iso3"], strict=True))
    assert ("AUT", "SWE") in pairs
    assert ("SWE", "AUT") in pairs
    assert not (table["from_iso3"] == table["to_iso3"]).any()


def test_pageviews_are_missing_before_they_existed(built):
    table = io.read_parquet("dyads", "processed")
    assert table.loc[table["year"] == 2015, "views_total"].isna().all()
    assert table.loc[table["year"] == 2016, "views_total"].notna().all()


def test_receiver_effect_leaves_the_focal_voter_out(built):
    table = io.read_parquet("features", "processed")
    row = table.iloc[0]
    same_entry = table[
        (table["year"] == row["year"])
        & (table["round"] == row["round"])
        & (table["vote_type"] == row["vote_type"])
        & (table["to_iso3"] == row["to_iso3"])
    ]
    others = same_entry[same_entry["from_iso3"] != row["from_iso3"]]
    assert row["receiver_effect"] == pytest.approx(others["points"].mean())


def test_a_duplicated_join_key_is_caught(interim):
    static = io.read_parquet("dyad_static", "interim")
    io.write_parquet(
        pd.concat([static, static.iloc[[0]]], ignore_index=True),
        "dyad_static",
        "interim",
    )
    entries.build()
    votes.build()
    with pytest.raises(ValueError, match="not unique"):
        dyads.build()
