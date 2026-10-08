"""the metrics, on frames small enough to check by hand"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from esc import models
from esc.models import evaluate


def entries(points: list[int], guesses: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": 2016,
            "vote_type": "jury",
            "to_iso3": [f"C{i:02d}" for i in range(len(points))],
            "actual": pd.array(points, dtype="Int16"),
            "guess": guesses,
        }
    )


def test_a_perfect_ranking_scores_one():
    frame = entries([10, 8, 6, 4], [100.0, 80.0, 60.0, 40.0])
    row = evaluate.ranking_metrics(frame, "actual", "guess").iloc[0]
    assert row["spearman"] == pytest.approx(1.0)
    assert row["kendall"] == pytest.approx(1.0)
    assert row["rank_error"] == 0


def test_a_reversed_ranking_scores_minus_one():
    frame = entries([10, 8, 6, 4], [40.0, 60.0, 80.0, 100.0])
    row = evaluate.ranking_metrics(frame, "actual", "guess").iloc[0]
    assert row["spearman"] == pytest.approx(-1.0)
    assert row["rank_error"] > 0


def test_rank_error_does_not_underflow_on_nullable_ints():
    # .rank() on a nullable Int returns UInt64 and a plain subtraction wraps
    frame = entries([1, 2, 3, 4], [4.0, 3.0, 2.0, 1.0])
    row = evaluate.ranking_metrics(frame, "actual", "guess").iloc[0]
    assert 0 < row["rank_error"] < len(frame)


def test_chance_sits_near_a_third_of_the_field():
    frame = entries(list(range(26, 0, -1)), [float(i) for i in range(26)])
    chance = evaluate.random_baseline(frame, "actual", draws=200)
    assert chance["low"] < chance["rank_error"] < chance["high"]
    assert 6 < chance["rank_error"] < 12


def test_win_probabilities_sum_to_one_per_contest():
    pairs = pd.DataFrame(
        {
            "year": [2016] * 6 + [2017] * 6,
            "vote_type": "jury",
            "to_iso3": ["AUT", "AUT", "SWE", "SWE", "ITA", "ITA"] * 2,
            "predicted": [6.0, 6.0, 3.0, 3.0, 1.0, 1.0] * 2,
        }
    )
    out = evaluate.win_probabilities(
        pairs, "predicted", np.array([-0.5, 0.0, 0.5]), draws=100
    )
    per_contest = out.groupby(["year", "vote_type"])["win_probability"].sum()
    assert per_contest.round(6).eq(1.0).all()
    best = out[out["year"] == 2016].set_index("to_iso3")["win_probability"]
    assert best["AUT"] > best["ITA"]


def test_calibration_uses_fixed_bins_not_quantiles():
    # almost every entry sits near zero so quantile bins would collapse to one
    frame = pd.DataFrame(
        {
            "won": [False] * 18 + [True, True],
            "win_probability": [0.0] * 18 + [0.6, 0.9],
        }
    )
    curve = evaluate.calibration_curve(frame, "won", "win_probability")
    assert len(curve) >= 2
    assert curve["n"].sum() == 20


def test_every_set_with_the_receiver_effect_counts_as_explanatory():
    # "all" does not say receiver in its name and once got picked as a forecast
    panel = pd.DataFrame(
        columns=[*models.PAIR, *models.RECEIVER, "web_interest", "youtube_interest"]
    )
    sets = models.feature_sets(panel)
    assert models.explanatory(sets) == {"pair+receiver", "all"}
