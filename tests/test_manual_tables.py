"""the committed csvs in data/manual/ have to stay usable"""

from __future__ import annotations

from esc.parse import manual


def test_country_map_parses_and_has_unique_names_per_period():
    df = manual._read("country_map")
    assert not df.duplicated(subset=["esc_name", "valid_from"]).any()
    assert df["iso3"].str.len().eq(3).all()


def test_greece_and_the_uk_keep_their_eurostat_quirks():
    df = manual._read("country_map").set_index("esc_name")
    assert df.loc["Greece", "eurostat_geo"] == "EL"
    assert df.loc["United Kingdom", "eurostat_geo"] == "UK"


def test_voting_regimes_have_one_row_per_year():
    df = manual._read("voting_regimes")
    years = df["year"].astype(int)
    assert not years.duplicated().any()
    assert years.tolist() == sorted(years.tolist())


def test_2020_is_present_but_empty():
    df = manual._read("voting_regimes").set_index("year")
    row = df.loc["2020"]
    assert row[["jury_share", "televote_share"]].isna().all()
    assert "cancelled" in row["notes"]


def test_jury_only_years_are_marked_as_such():
    df = manual._read("voting_regimes").set_index("year")
    assert df.loc["1975", "jury_share"] == "1.0"
    assert df.loc["1975", "separately_reported"] == "false"
    assert df.loc["2016", "separately_reported"] == "true"


def test_recent_entries_only_ships_the_placeholder():
    df = manual._read("recent_entries")
    assert (df["country_iso3"] == manual.PLACEHOLDER_ISO3).all()
