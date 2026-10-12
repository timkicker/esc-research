"""the committed csvs in data/manual/ have to stay usable"""

from __future__ import annotations

from esc.parse import manual


def test_country_map_has_no_duplicate_labels():
    df = manual._read("country_map")
    assert not df.duplicated(subset=["label", "kind"]).any()
    assert df["iso3"].str.len().eq(3).all()
    assert set(df["kind"]) == {"name", "iso2"}


def test_country_map_covers_both_vocabularies():
    df = manual._read("country_map")
    names = df[df["kind"] == "name"]
    codes = df[df["kind"] == "iso2"]
    assert len(names) > 40 and len(codes) > 40
    # the labels the two source files disagree about
    assert "Czechia" in set(names["label"])
    assert "Czech Republic" in set(names["label"])
    assert codes.set_index("label").loc["wld", "iso3"] == "WLD"


def test_the_states_that_changed_keep_their_own_rows():
    df = manual._read("country_map").set_index(["kind", "label"])
    assert df.loc[("iso2", "yu"), "iso3"] == "YUG"
    assert df.loc[("iso2", "cs"), "iso3"] == "SCG"
    assert df.loc[("name", "Yugoslavia"), "valid_to"] == "1992"


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


def test_contest_dates_cover_the_panel_years():
    df = manual._read("contest_dates")
    years = set(df["year"].astype(int))
    assert {2016, 2017, 2018, 2019, 2021, 2022, 2023} <= years
    assert 2020 not in years


def test_country_names_have_one_name_per_country():
    names = manual._read("country_names")
    assert not names["iso3"].duplicated().any()
    assert names["iso3"].str.len().eq(3).all()
    assert names["name"].notna().all()
    assert not names["name"].duplicated().any()


def test_recent_entries_only_ships_the_placeholder():
    df = manual._read("recent_entries")
    assert (df["country_iso3"] == manual.PLACEHOLDER_ISO3).all()
