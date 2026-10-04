"""teammate lyrics file -> lyric_features and song_language, no network"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from esc import config, io
from esc.models import design
from esc.parse import manual, team_dataset


def record(country, year, sentiment="sad", theme="heartbreak", main="no", chorus="yes"):
    return {
        "artist": "someone",
        "country": country,
        "year": str(year),
        "song": "a song",
        "language": "en",
        "sentiment": sentiment,
        "theme": theme,
        "repetition_main": main,
        "high_repetition_chorus": chorus,
    }


@pytest.fixture()
def lyrics_world(data_root):
    cmap = pd.DataFrame(
        {
            "label": ["Austria", "Sweden", "Bosnia and Herzegovina"],
            "iso3": ["AUT", "SWE", "BIH"],
            "kind": "name",
            "valid_from": pd.array([None] * 3, dtype="Int16"),
            "valid_to": pd.array([None] * 3, dtype="Int16"),
        }
    )
    io.write_parquet(cmap, "country_map", "interim")

    def write(records: dict) -> None:
        folder = config.RAW / team_dataset.RAW_ID
        folder.mkdir(parents=True, exist_ok=True)
        (folder / team_dataset.FILE).write_text(json.dumps(records))

    return write


def test_records_become_lyric_features_and_languages(lyrics_world):
    lyrics_world(
        {
            "Austria_2025": record("Austria", 2025, main="no", chorus="yes"),
            "Sweden_2025": record("Sweden", 2025, "funny", "festivity", "yes", "no"),
            "Bosnia_and_Herzegovina_2008": record("Bosnia and Herzegovina", 2008),
        }
    )
    team_dataset.parse()
    features = io.read_parquet("lyric_features", "interim").set_index("entry_id")
    assert set(features.index) == {"2025-AUT", "2025-SWE", "2008-BIH"}
    assert not features.loc["2025-AUT", "repetition_verse"]
    assert features.loc["2025-AUT", "repetition_chorus"]
    assert features.loc["2025-SWE", "theme"] == "festivity"
    languages = io.read_parquet("song_language", "interim")
    assert set(languages["language"]) == {"en"}


def test_an_unknown_label_raises(lyrics_world):
    lyrics_world({"Austria_2025": record("Austria", 2025, sentiment="angry")})
    with pytest.raises(ValueError, match="unknown value"):
        team_dataset.parse()


def test_a_country_missing_from_the_map_raises(lyrics_world):
    lyrics_world({"Narnia_2025": record("Narnia", 2025)})
    with pytest.raises(ValueError, match="country_map"):
        team_dataset.parse()


def test_the_committed_map_knows_the_lyrics_spelling():
    names = set(manual._read("country_map").query("kind == 'name'")["label"])
    assert "Bosnia and Herzegovina" in names


def test_one_hot_gives_the_same_columns_whatever_themes_occur():
    early = pd.DataFrame({"theme": pd.array(["romance", "romance"], dtype="string")})
    late = pd.DataFrame({"theme": pd.array(["nature", None], dtype="string")})
    a, b = design(early, ["theme"]), design(late, ["theme"])
    assert list(a.columns) == list(b.columns)
    assert len(a.columns) == len(team_dataset.THEMES)
    # a missing label stays missing, it is imputed later on the training years
    assert b.iloc[1].isna().all()
