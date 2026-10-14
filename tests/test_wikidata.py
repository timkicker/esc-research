"""wikidata sparql results -> interim artists, no network"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from esc import config, io
from esc.fetch import wikidata as fetch_wikidata
from esc.parse import wikidata

WD = "http://www.wikidata.org/entity/"
FEMALE, MALE, NONBINARY = "Q6581072", "Q6581097", "Q48270"


def row(item, item_label, person, person_label, kind, birth=None, sex=None):
    out = {
        "item": {"value": WD + item},
        "itemLabel": {"value": item_label},
        "person": {"value": WD + person},
        "personLabel": {"value": person_label},
        "personType": {"value": WD + kind},
    }
    if birth:
        out["birth"] = {"value": f"{birth}T00:00:00Z"}
        out["birthPrecision"] = {"value": "11"}
    if sex:
        out["sex"] = {"value": WD + sex}
    return out


BINDINGS = [
    # a song with its performer, the accent differs from our title
    row("Q1", "Asteromata", "Q1", "Asteromata", "Q134556"),
    row("Q1", "Asteromata", "Q2", "Klavdia", "Q5", "2002-08-18", FEMALE),
    # a performer listed directly, under a longer name than ours
    row("Q3", "Agnete Saba", "Q3", "Agnete Saba", "Q5", "1994-05-17", FEMALE),
    # a band
    row("Q4", "Bird of Pray", "Q5", "Ziferblat", "Q215380"),
    # birthday one day after the final
    row("Q6", "Lighter", "Q7", "Kyle Alessandro", "Q5", "2006-05-18", MALE),
    row("Q8", "Voyage", "Q9", "Zoe Me", "Q5", "2000-10-06", NONBINARY),
    # an unknown birth date, 2000-01-01 at century precision
    {
        **row("Q11", "Tina", "Q11", "Tina", "Q5", "2000-01-01", FEMALE),
        "birthPrecision": {"value": "7"},
    },
    # a presenter, takes part but has no entry
    row("Q10", "Hazel Brugger", "Q10", "Hazel Brugger", "Q5", "1993-12-09", FEMALE),
]

ENTRIES = [
    ("2025-GRC", "Klavdia", "Asteromáta"),
    ("2025-NOR", "Agnete", "Icebreaker"),
    ("2025-UKR", "Ziferblat", "Bird of Pray"),
    ("2025-SWE", "Kyle Alessandro", "Lighter"),
    ("2025-CHE", "Zoë Më", "Voyage"),
    ("2025-ITA", "Ermal Meta & Fabrizio Moro", "Non mi avete fatto niente"),
    ("2025-NLD", "OG3NE", "Lights and Shadows"),
    ("2025-IRL", "Tina", "Cross Your Heart"),
]


@pytest.fixture()
def artists(data_root):
    folder = config.RAW / wikidata.RAW_ID
    folder.mkdir(parents=True)
    results = {"results": {"bindings": BINDINGS}}
    (folder / "2025.json").write_text(json.dumps(results), encoding="utf-8")
    births = [
        {key: r[key] for key in ("person", "birth", "birthPrecision")}
        for r in BINDINGS
        if "birth" in r
    ]
    births = json.dumps({"results": {"bindings": births}})
    (folder / "2025-births.json").write_text(births, encoding="utf-8")
    (folder / "editions.json").write_text("{}", encoding="utf-8")

    entries = pd.DataFrame(ENTRIES, columns=["entry_id", "artist", "song"])
    entries["year"] = pd.array([2025] * len(entries), dtype="int16")
    io.write_parquet(entries, "entries", "interim")
    dates = pd.DataFrame(
        {
            "year": pd.array([2025], dtype="int16"),
            "final_date": [pd.Timestamp("2025-05-17")],
        }
    )
    io.write_parquet(dates, "contest_dates", "interim")

    wikidata.parse()
    return io.read_parquet("artists", "interim").set_index("entry_id")


def test_song_title_matches_without_accents(artists):
    assert artists.loc["2025-GRC", "artist_age"] == 22
    assert artists.loc["2025-GRC", "artist_sex"] == "female"


def test_stage_name_matches_full_name(artists):
    assert artists.loc["2025-NOR", "artist_age"] == 31


def test_age_is_counted_at_the_final(artists):
    assert artists.loc["2025-SWE", "artist_age"] == 18


def test_a_birth_date_without_a_day_gives_no_age(artists):
    assert pd.isna(artists.loc["2025-IRL", "artist_age"])
    assert artists.loc["2025-IRL", "artist_sex"] == "female"


def test_sex_beyond_male_and_female_is_other(artists):
    assert artists.loc["2025-CHE", "artist_sex"] == "other"


@pytest.mark.parametrize("entry", ["2025-UKR", "2025-ITA", "2025-NLD"])
def test_groups_duos_and_misses_stay_missing(artists, entry):
    assert pd.isna(artists.loc[entry, "artist_age"])
    assert pd.isna(artists.loc[entry, "artist_sex"])


def test_one_row_per_entry_and_no_presenter(artists):
    assert sorted(artists.index) == sorted(e[0] for e in ENTRIES)


def test_editions_map_year_to_qid():
    text = json.dumps(
        {
            "results": {
                "bindings": [
                    {
                        "edition": {"value": WD + "Q1"},
                        "date": {"value": "2025-05-01T00:00:00Z"},
                    },
                    {
                        "edition": {"value": WD + "Q2"},
                        "date": {"value": "2026-05-01T00:00:00Z"},
                    },
                ]
            }
        }
    )
    assert fetch_wikidata.editions(text) == {2025: "Q1", 2026: "Q2"}
