"""csv and site json, no network"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from esc import export


def features():
    return pd.DataFrame(
        {
            "year": [2016, 2016, 2016, 2016, 2016],
            "vote_type": ["jury", "jury", "televote", "televote", "combined"],
            "from_iso3": ["AUT", "SWE", "AUT", "SWE", "AUT"],
            "to_iso3": ["SWE", "AUT", "SWE", "AUT", "SWE"],
            "points": pd.array([12, 0, 8, 10, 5], dtype="Int16"),
        }
    )


def entry_table():
    return pd.DataFrame(
        {
            "year": [2016, 2016, 2015],
            "round": ["final", "final", "final"],
            "country_iso3": ["SWE", "AUT", "AUT"],
            "artist": ["Frans", "Zoë", "old"],
            "song": ["If I Were Sorry", "Loin d'ici", "old"],
            "place": [1, 2, 1],
            "running_order": [2, 1, 1],
        }
    )


def test_votes_keep_only_awards_and_drop_the_combined_rows():
    payload = export.votes(features())
    assert payload["columns"] == ["year", "type", "from", "to", "points"]
    assert payload["rows"] == [
        [2016, "j", "AUT", "SWE", 12],
        [2016, "t", "AUT", "SWE", 8],
        [2016, "t", "SWE", "AUT", 10],
    ]


def test_entries_sum_each_half_and_skip_years_without_a_split():
    payload = export.entries(features(), entry_table())
    rows = [dict(zip(payload["columns"], r, strict=True)) for r in payload["rows"]]
    assert [r["country"] for r in rows] == ["SWE", "AUT"]
    assert rows[0]["jury"] == 12 and rows[0]["televote"] == 8
    assert rows[1]["jury"] == 0 and rows[1]["televote"] == 10


def test_split_takes_the_headline_model_and_every_year():
    rows = []
    for model in ("ridge", "boosting"):
        for scope in ("all", "2016", "2017"):
            rows.append(
                {
                    "vote_type": "televote",
                    "model": model,
                    "scope": scope,
                    "entry_only": 0.4 if model == "ridge" else 0.9,
                    "pair_only": 0.1,
                    "overlap": 0.0,
                    "noise": 0.5,
                }
            )
    payload = export.split(pd.DataFrame(rows))
    assert payload["model"] == "ridge"
    assert payload["split"]["televote"]["entry_only"] == 0.4
    assert set(payload["split"]["televote"]["per_year"]) == {"2016", "2017"}


def test_affinity_keeps_only_pairs_that_met_often_enough():
    pairs = pd.DataFrame(
        {
            "vote_type": ["televote", "televote"],
            "from_iso3": ["GRC", "AUT"],
            "to_iso3": ["CYP", "DEU"],
            "excess": [10.5, 2.0],
            "points": [12.0, 3.0],
            "meetings": [8, 2],
        }
    )
    payload = export.affinity(pairs)
    assert payload["rows"] == [["t", "GRC", "CYP", 10.5, 12.0, 8]]


def test_meta_refuses_a_country_without_a_display_name():
    names = pd.DataFrame({"iso3": ["AUT"], "name": ["Austria"]})
    with pytest.raises(ValueError, match="SWE"):
        export.meta(features(), names)


def test_latex_tables_name_the_far_entries_and_keep_the_public_top():
    shares = {"entry_only": 0.25, "pair_only": 0.03, "overlap": 0.02, "noise": 0.7}
    rows = [[2016 + i, "GRC", "a", "b", 1, 1, 10 * i, 300 - 40 * i] for i in range(8)]
    columns = ["year", "country", "artist", "song", "place", "order", "jury"]
    affinity = [["t", "GRC", "CYP", 10.5, 12.0, 8], ["j", "CYP", "GRC", 9.4, 11.0, 7]]
    payloads = {
        "split": {"split": {"jury": shares, "televote": shares}},
        "entries": {"columns": [*columns, "televote"], "rows": rows},
        "affinity": {
            "columns": ["type", "from", "to", "excess", "points", "meetings"],
            "rows": affinity,
        },
    }
    names = {"GRC": "Greece", "CYP": "Cyprus"}
    tables = export.latex_tables(payloads, names)
    assert list(tables["split"]["jury"]) == [25.0, 3.0, 2.0, 70.0]
    assert len(tables["scatter"]) == 8
    assert len(tables["scatter-named"]) == 5
    assert list(tables["favourites-public"]["label"]) == ["Greece $\\to$ Cyprus"]


def test_json_is_written_as_utf8_without_escapes(tmp_path, monkeypatch):
    monkeypatch.setattr(export, "EXPORT", tmp_path)
    path = export._write_json("probe", {"artist": "Zoë"})
    text = path.read_text(encoding="utf-8")
    assert "Zoë" in text
    assert json.loads(text) == {"artist": "Zoë"}
    assert path == tmp_path / "site" / "probe.json"


def test_forecast_table_shows_chance_and_only_the_main_model():
    rows = []
    for model in ("ridge", "boosting"):
        for vote_type in ("jury", "televote"):
            for name in ("pair", "pair+attention", "pair+receiver"):
                rows.append(
                    {
                        "model": model,
                        "vote_type": vote_type,
                        "features": name,
                        "rank_error": 6.0 if model == "boosting" else 7.0,
                        "spearman": 0.4,
                    }
                )
    chance = pd.DataFrame(
        {
            "vote_type": ["jury", "televote"],
            "rank_error": [8.5, 8.4],
            "low": [8.3, 8.2],
            "high": [8.7, 8.6],
        }
    )
    table = export.forecast_table(pd.DataFrame(rows), chance)
    assert list(table["label"]) == [
        "chance",
        "country pair",
        "country pair + search interest",
    ]
    assert table.loc[0, "televote_low"] == 8.2
    assert set(table.loc[1:, "jury_rank_error"]) == {6.0}
