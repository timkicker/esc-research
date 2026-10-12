"""entry against relationship split and pair affinity, no network"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from esc.models import explain


def test_r2_is_one_for_a_perfect_fit_and_nan_without_spread():
    actual = pd.Series([0, 4, 12])
    assert explain.r2(actual, actual.astype("float64")) == 1
    assert math.isnan(explain.r2(pd.Series([5, 5]), pd.Series([5.0, 5.0])))


def test_shares_add_up_to_one():
    parts = explain.shares(r2_entry=0.4, r2_pair=0.15, r2_both=0.5)
    assert parts["entry_only"] == pytest.approx(0.35)
    assert parts["pair_only"] == pytest.approx(0.10)
    assert parts["overlap"] == pytest.approx(0.05)
    total = parts["entry_only"] + parts["pair_only"] + parts["overlap"]
    assert total + parts["noise"] == pytest.approx(1)


def panel():
    return pd.DataFrame(
        {
            "year": [2016, 2016, 2017, 2017, 2018, 2018],
            "vote_type": ["televote"] * 6,
            "from_iso3": ["GRC", "WLD", "GRC", "WLD", "GRC", "AUT"],
            "to_iso3": ["CYP"] * 6,
            "points": pd.array([12, 12, 10, 10, 12, 0], dtype="Int16"),
        }
    )


def test_decompose_reports_all_years_and_each_year():
    frame = panel()
    exact = frame["points"].astype("float64")
    flat = pd.Series(exact.mean(), index=frame.index)
    table = explain.decompose(frame, {"entry": flat, "pair": exact, "both": exact})
    assert list(table["scope"]) == ["all", "2016", "2017", "2018"]
    pooled = table.iloc[0]
    # the relationship alone explains everything, the entry adds nothing
    assert pooled["pair_only"] == pytest.approx(1)
    assert pooled["entry_only"] == pytest.approx(0)


def test_affinity_skips_the_pooled_voter_and_counts_meetings():
    frame = panel()
    earned = pd.Series(6.0, index=frame.index)
    table = explain.affinity(frame, earned)
    assert "WLD" not in set(table["from_iso3"])
    greece = table[table["from_iso3"] == "GRC"].iloc[0]
    assert greece["meetings"] == 3
    assert greece["excess"] == pytest.approx((6 + 4 + 6) / 3)
    assert bool(greece["reliable"])
    austria = table[table["from_iso3"] == "AUT"].iloc[0]
    assert not bool(austria["reliable"])
    # strongest first
    assert table.iloc[0]["from_iso3"] == "GRC"
