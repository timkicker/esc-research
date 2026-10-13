"""does the pair history leak the held out year

python -m esc.models.leakcheck

past_points is the mean over every earlier final. when 2018 is held out, the
training rows of 2019 onwards still carry the 2018 points in that feature.
this reruns the split and the forecast with the history rebuilt per fold from
the training years only and writes both numbers side by side
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esc import io
from esc.build.features import pair_history
from esc.models import TARGET, design, feature_sets, load, totals
from esc.models.evaluate import ranking_metrics
from esc.models.explain import ESTIMATORS as EXPLAIN_ESTIMATORS
from esc.models.explain import PARTS, decompose
from esc.models.run import ESTIMATORS, VOTE_TYPES, fit_predict

HISTORY = ["past_points", "past_meetings"]
KEYS = ["from_iso3", "to_iso3", "year"]
FORECAST_SETS = ("pair", "pair+attention")


def folded(panel: pd.DataFrame, votes: pd.DataFrame, year: int) -> pd.DataFrame:
    """the panel with the pair history rebuilt without the held out year"""
    history = pair_history(votes, skip_year=year)
    out = panel.drop(columns=HISTORY).merge(history, on=KEYS, how="left")
    out.index = panel.index
    # the held out year keeps its own history, which never contains itself
    test = panel["year"] == year
    out.loc[test, HISTORY] = panel.loc[test, HISTORY]
    return out


def fit_predict_folded(
    panel: pd.DataFrame, votes: pd.DataFrame, columns, factory
) -> pd.Series:
    out = pd.Series(np.nan, index=panel.index, dtype="float64")
    target = panel[TARGET].astype("float64")
    for year in sorted(panel["year"].unique()):
        frame = folded(panel, votes, year) if set(HISTORY) & set(columns) else panel
        matrix = design(frame, columns)
        test = panel["year"] == year
        medians = matrix[~test].median()
        model = factory()
        model.fit(matrix[~test].fillna(medians), target[~test])
        out[test] = model.predict(matrix[test].fillna(medians))
    return out


def rank_error(panel: pd.DataFrame, predicted: pd.Series) -> float:
    frame = panel.assign(predicted=predicted)
    actual = totals(frame, TARGET).rename(columns={TARGET: "actual"})
    guess = totals(frame, "predicted").rename(columns={"predicted": "guess"})
    entries = actual.merge(guess, on=list(actual.columns[:-1]))
    return float(ranking_metrics(entries, "actual", "guess")["rank_error"].mean())


def main() -> None:
    votes = io.read_parquet("votes", "processed")
    rows = []
    for vote_type in VOTE_TYPES:
        panel = load(vote_type)
        for history, fit in (
            ("all earlier years", lambda p, c, f: fit_predict(p, c, "m", {"m": f})),
            ("training years only", lambda p, c, f: fit_predict_folded(p, votes, c, f)),
        ):
            predictions = {
                part: fit(panel, columns, EXPLAIN_ESTIMATORS["ridge"])
                for part, columns in PARTS.items()
            }
            pooled = decompose(panel, predictions).iloc[0]
            for share in ("entry_only", "pair_only", "overlap", "noise"):
                rows.append(_row(vote_type, history, "split", "ridge", share, pooled))
            sets = feature_sets(panel)
            for name in FORECAST_SETS:
                for estimator in ("ridge", "boosting"):
                    predicted = fit(panel, sets[name], ESTIMATORS[estimator])
                    rows.append(
                        {
                            "vote_type": vote_type,
                            "history": history,
                            "analysis": "forecast",
                            "model": estimator,
                            "measure": f"rank_error {name}",
                            "value": rank_error(panel, predicted),
                        }
                    )

    table = pd.DataFrame(rows)
    io.write_parquet(table, "leakcheck", "processed")
    wide = table.pivot_table(
        index=["vote_type", "analysis", "model", "measure"],
        columns="history",
        values="value",
    )
    print("\npair history from all earlier years against training years only")
    print(wide.round(4).to_string())


def _row(vote_type, history, analysis, model, share, pooled) -> dict:
    return {
        "vote_type": vote_type,
        "history": history,
        "analysis": analysis,
        "model": model,
        "measure": share,
        "value": float(pooled[share]),
    }


if __name__ == "__main__":
    main()
