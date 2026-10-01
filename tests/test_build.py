from __future__ import annotations

import pandas as pd
import pytest

from esc import io
from esc.build import dyads, entries, features, votes

LADDER_SUM = 58
PANEL_YEAR = 2016


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


def test_the_panel_starts_in_2016(built):
    table = io.read_parquet("dyads", "processed")
    # 2015 is in the fixtures and reports combined points only, so it is out
    assert set(table["year"]) == {PANEL_YEAR}
    assert set(table["vote_type"]) == {"jury", "televote"}
    assert set(table["round"]) == {"final"}


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


def test_a_missing_optional_table_does_not_stop_the_build(built):
    table = io.read_parquet("dyads", "processed")
    # nobody has delivered trends or the lyric features yet
    assert "web_interest" not in table.columns
    assert "sentiment" not in table.columns
    assert len(table) > 0


def test_an_optional_table_is_joined_once_it_exists(interim):
    panel_entries = io.read_parquet("entries", "interim")
    final = panel_entries[panel_entries["round"] == "final"]
    lyrics = pd.DataFrame(
        {
            "entry_id": final["entry_id"].unique(),
            "sentiment": "sad",
            "repetition_verse": True,
            "repetition_chorus": False,
            "theme": "heartbreak",
        }
    )
    io.write_parquet(lyrics, "lyric_features", "interim")
    entries.build()
    votes.build()
    dyads.build()
    table = io.read_parquet("dyads", "processed")
    assert set(table["sentiment"].dropna()) == {"sad"}


def test_points_share_sums_to_one_per_show(built):
    table = io.read_parquet("features", "processed")
    shares = table.groupby(["year", "round", "vote_type"])["points_share"].sum()
    assert shares.round(6).eq(1.0).all()


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
