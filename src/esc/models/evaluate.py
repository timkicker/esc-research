"""metrics for a predicted ranking and for a predicted win probability

ranking quality is scored per contest and then averaged without pooling across
years, because a contest is the unit people care about
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from esc.models import rng


def ranking_metrics(entries: pd.DataFrame, truth: str, predicted: str) -> pd.DataFrame:
    """spearman, kendall and mean rank error per year and vote type"""
    rows = []
    for (year, vote_type), group in entries.groupby(["year", "vote_type"]):
        if len(group) < 3:
            continue
        actual = group[truth].rank(ascending=False, method="min").astype("float64")
        guess = group[predicted].rank(ascending=False, method="min").astype("float64")
        rows.append(
            {
                "year": year,
                "vote_type": vote_type,
                "n": len(group),
                "spearman": stats.spearmanr(group[truth], group[predicted]).statistic,
                "kendall": stats.kendalltau(group[truth], group[predicted]).statistic,
                "rank_error": float((actual - guess).abs().mean()),
            }
        )
    return pd.DataFrame(rows)


def random_baseline(entries: pd.DataFrame, truth: str, draws: int = 1000) -> dict:
    """what chance looks like (with an interval) so a rank error can be placed"""
    generator = rng()
    errors = []
    for (_year, _vote_type), group in entries.groupby(["year", "vote_type"]):
        if len(group) < 3:
            continue
        actual = (
            group[truth]
            .rank(ascending=False, method="min")
            .astype("float64")
            .to_numpy()
        )
        for _ in range(draws):
            shuffled = generator.permutation(actual)
            errors.append(np.abs(actual - shuffled).mean())
    errors = np.asarray(errors)
    low, high = np.percentile(errors, [2.5, 97.5])
    return {"rank_error": float(errors.mean()), "low": float(low), "high": float(high)}


def win_probabilities(
    pairs: pd.DataFrame, predicted: str, residuals: np.ndarray, draws: int = 2000
) -> pd.DataFrame:
    """simulate each contest and count how often an entry comes first

    resamples the model's own residuals onto the pair predictions
    """
    generator = rng()
    out = []
    for (year, vote_type), group in pairs.groupby(["year", "vote_type"]):
        receivers = group["to_iso3"].drop_duplicates().reset_index(drop=True)
        index = group.groupby("to_iso3").ngroup().to_numpy()
        base = group[predicted].to_numpy()
        wins = np.zeros(len(receivers))
        for _ in range(draws):
            noisy = base + generator.choice(residuals, size=len(base), replace=True)
            scored = np.bincount(index, weights=noisy, minlength=len(receivers))
            wins[int(np.argmax(scored))] += 1
        out.append(
            pd.DataFrame(
                {
                    "year": year,
                    "vote_type": vote_type,
                    "to_iso3": sorted(group["to_iso3"].unique()),
                    "win_probability": wins / draws,
                }
            )
        )
    return pd.concat(out, ignore_index=True)


def brier_and_log_loss(entries: pd.DataFrame, won: str, probability: str) -> dict:
    p = entries[probability].to_numpy().clip(1e-9, 1 - 1e-9)
    y = entries[won].to_numpy().astype(float)
    return {
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
    }


CALIBRATION_BINS = (0.0, 0.01, 0.05, 0.10, 0.25, 0.50, 1.0)


def calibration_curve(entries: pd.DataFrame, won: str, probability: str):
    """predicted probability against observed frequency

    fixed bins instead of quantiles because almost every entry sits near zero
    """
    frame = entries[[probability, won]].copy()
    frame["bucket"] = pd.cut(
        frame[probability], bins=CALIBRATION_BINS, include_lowest=True
    )
    grouped = frame.groupby("bucket", observed=True)
    return pd.DataFrame(
        {
            "predicted": grouped[probability].mean(),
            "observed": grouped[won].mean().astype("float64"),
            "n": grouped.size(),
        }
    ).reset_index()
