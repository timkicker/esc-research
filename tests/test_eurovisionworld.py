"""eurovisionworld voting script -> votes_recent and entries_recent, no network"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from esc import config, io
from esc.parse import eurovisionworld

# a two country final where at gives se jury points only
SCRIPT = {
    "voting_data": {"year": 2025, "jury": True, "tele": True},
    "voting_songs": {"at": ["JJ", "Wasted Love", 1], "se": ["KAJ", "Bara", 1]},
    "voting_table_main": {"at": [9, 1, 20, 8, 12, True, 2], "se": [4, 2, 10, 0, 10]},
    "voting_point": [["at", "se", 1, 10, 0], ["se", "at", 1, 12, 8]],
}


def write_script(folder, year, data):
    lines = [f"{name} = {json.dumps(value)};" for name, value in data.items()]
    (folder / f"{year}.js").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture()
def world(data_root):
    cmap = pd.DataFrame(
        {
            "label": ["at", "se"],
            "iso3": ["AUT", "SWE"],
            "kind": ["iso2", "iso2"],
            "valid_from": pd.array([None, None], dtype="Int16"),
            "valid_to": pd.array([None, None], dtype="Int16"),
        }
    )
    io.write_parquet(cmap, "country_map", "interim")
    folder = config.RAW / eurovisionworld.RAW_ID
    folder.mkdir(parents=True)
    write_script(folder, 2025, SCRIPT)
    return folder


def test_votes_split_jury_and_televote(world):
    eurovisionworld.parse_votes()
    votes = io.read_parquet("votes_recent", "interim")
    got = {
        (r.vote_type, r.from_iso3, r.to_iso3): int(r.points) for r in votes.itertuples()
    }
    assert got == {
        ("jury", "AUT", "SWE"): 10,
        ("jury", "SWE", "AUT"): 12,
        ("televote", "SWE", "AUT"): 8,
    }


def test_entries_carry_order_place_and_names(world):
    eurovisionworld.parse_entries()
    entries = io.read_parquet("entries_recent", "interim").set_index("country_iso3")
    assert entries.loc["AUT", "artist"] == "JJ"
    assert entries.loc["AUT", "running_order"] == 9
    assert entries.loc["AUT", "place"] == 1
    assert entries.loc["SWE", "points_total"] == 10


def test_a_changed_script_format_fails_loudly(world):
    write_script(world, 2025, {"voting_data": {}})
    with pytest.raises(ValueError, match="format changed"):
        eurovisionworld.parse_votes()
