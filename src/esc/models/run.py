"""leave-one-year-out fit and evaluation

python -m esc.models.run

one contest is one group. a random split would put rows from the same final in
train and test and leak the answer, so every year is held out whole. the median
used for imputation and the scaler are fitted on the training years only
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import RidgeCV

from esc import io
from esc.models import TARGET, design, explanatory, feature_sets, load, totals
from esc.models.evaluate import (
    brier_and_log_loss,
    calibration_curve,
    random_baseline,
    ranking_metrics,
    win_probabilities,
)

VOTE_TYPES = ("jury", "televote")
ESTIMATORS = {
    "ridge": lambda: RidgeCV(alphas=np.logspace(-3, 3, 13)),
    "boosting": lambda: HistGradientBoostingRegressor(
        max_depth=4, learning_rate=0.06, max_iter=300, random_state=0
    ),
    # two cores keep a laptop usable and do not change the results
    "forest": lambda: RandomForestRegressor(
        n_estimators=200,
        min_samples_leaf=20,
        max_features=0.5,
        n_jobs=2,
        random_state=0,
    ),
}


def fit_predict(
    panel: pd.DataFrame, columns: list[str], estimator: str, factories=None
) -> pd.Series:
    """one prediction per row, each produced by a model that never saw its year"""
    factories = factories or ESTIMATORS
    out = pd.Series(np.nan, index=panel.index, dtype="float64")
    matrix = design(panel, columns)
    target = panel[TARGET].astype("float64")

    for year in sorted(panel["year"].unique()):
        test = panel["year"] == year
        train = ~test
        medians = matrix[train].median()
        model = factories[estimator]()
        model.fit(matrix[train].fillna(medians), target[train])
        out[test] = model.predict(matrix[test].fillna(medians))
    return out


def evaluate(panel: pd.DataFrame, columns: list[str], estimator: str) -> dict:
    predicted = fit_predict(panel, columns, estimator)
    frame = panel.assign(predicted=predicted)

    actual = totals(frame, TARGET).rename(columns={TARGET: "actual"})
    guess = totals(frame, "predicted").rename(columns={"predicted": "guess"})
    entries = actual.merge(guess, on=list(actual.columns[:-1]))
    ranks = ranking_metrics(entries, "actual", "guess")

    residuals = (frame[TARGET].astype("float64") - frame["predicted"]).to_numpy()
    probabilities = win_probabilities(frame, "predicted", residuals)
    entries = entries.merge(probabilities, on=list(probabilities.columns[:-1]))
    entries["won"] = entries.groupby(["year", "vote_type"])["actual"].transform(
        lambda s: s == s.max()
    )
    scores = brier_and_log_loss(entries, "won", "win_probability")

    return {
        "spearman": float(ranks["spearman"].mean()),
        "kendall": float(ranks["kendall"].mean()),
        "rank_error": float(ranks["rank_error"].mean()),
        **scores,
        "entries": entries,
    }


def main() -> None:
    rows = []
    kept = {}
    explain_only = set()
    for vote_type in VOTE_TYPES:
        panel = load(vote_type)
        sets = feature_sets(panel)
        chance = random_baseline(
            totals(panel, TARGET).rename(columns={TARGET: "actual"}), "actual"
        )
        print(
            f"\n== {vote_type}: {len(panel)} pair rows, "
            f"{panel['year'].nunique()} contests"
        )
        print(
            f"   chance rank error {chance['rank_error']:.2f} "
            f"(95% {chance['low']:.2f} to {chance['high']:.2f})"
        )
        explain_only |= explanatory(sets)
        for name, columns in sets.items():
            for estimator in ESTIMATORS:
                result = evaluate(panel, columns, estimator)
                kept[(vote_type, name, estimator)] = result.pop("entries")
                rows.append(
                    {
                        "vote_type": vote_type,
                        "features": name,
                        "model": estimator,
                        "n_features": len(columns),
                        **result,
                    }
                )
                last = rows[-1]
                print(
                    f"   {name:16s} {estimator:9s} "
                    f"rho {last['spearman']:+.3f}  tau {last['kendall']:+.3f}  "
                    f"rank err {last['rank_error']:5.2f}  "
                    f"brier {last['brier']:.4f}  logloss {last['log_loss']:.3f}"
                )

    summary = pd.DataFrame(rows)
    io.write_parquet(summary, "model_summary", "processed")
    # the receiver effect explains a result but does not forecast one
    forecasting = {k: v for k, v in kept.items() if k[1] not in explain_only}
    scored = summary.set_index(["vote_type", "features", "model"])
    best = max(forecasting, key=lambda k: scored.loc[k, "spearman"])
    io.write_parquet(forecasting[best], "model_entries", "processed")
    curve = calibration_curve(forecasting[best], "won", "win_probability")
    print(f"\ncalibration of {best}:")
    print(curve.to_string(index=False))


if __name__ == "__main__":
    main()
