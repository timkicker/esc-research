"""how much of a vote is the entry and how much is the relationship

python -m esc.models.explain

three fits per vote type (entry only, pair only, both) scored on years they
never saw. ridge is the headline and boosting only a check, see the pitfall on
entry level features in README.md

the residual of the ridge entry fit is what a voter gave beyond what the entry
earned and its mean per directed pair says who favours whom
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV

from esc import io
from esc.models import PAIR, RECEIVER, TARGET, load
from esc.models.run import VOTE_TYPES, fit_predict

ESTIMATORS = {
    "ridge": lambda: RidgeCV(alphas=np.logspace(-3, 3, 13)),
    "boosting": lambda: HistGradientBoostingRegressor(
        max_depth=4,
        learning_rate=0.06,
        max_iter=300,
        min_samples_leaf=200,
        random_state=0,
    ),
}
PARTS = {"entry": RECEIVER, "pair": PAIR, "both": RECEIVER + PAIR}
# televote from the rest of the world is one pooled voter with no geography
POOLED_VOTERS = {"WLD"}
MIN_MEETINGS = 3


def r2(actual: pd.Series, predicted: pd.Series) -> float:
    actual = actual.astype("float64")
    total = float(((actual - actual.mean()) ** 2).sum())
    if total == 0:
        return float("nan")
    return 1 - float(((actual - predicted) ** 2).sum()) / total


def shares(r2_entry: float, r2_pair: float, r2_both: float) -> dict[str, float]:
    """split explained variance, the overlap can come out negative out of sample"""
    return {
        "r2_entry": r2_entry,
        "r2_pair": r2_pair,
        "r2_both": r2_both,
        "entry_only": r2_both - r2_pair,
        "pair_only": r2_both - r2_entry,
        "overlap": r2_entry + r2_pair - r2_both,
        "noise": 1 - r2_both,
    }


def decompose(panel: pd.DataFrame, predictions: dict[str, pd.Series]) -> pd.DataFrame:
    """one row for all years pooled and one per held out year"""
    actual = panel[TARGET]
    rows = [
        {
            "scope": "all",
            **shares(*(r2(actual, predictions[part]) for part in PARTS)),
        }
    ]
    for year in sorted(panel["year"].unique()):
        mask = panel["year"] == year
        values = (r2(actual[mask], predictions[part][mask]) for part in PARTS)
        rows.append({"scope": str(year), **shares(*values)})
    return pd.DataFrame(rows)


def affinity(panel: pd.DataFrame, entry_only: pd.Series) -> pd.DataFrame:
    """mean points a country gave beyond what the entry earned, per directed pair"""
    frame = panel.assign(excess=panel[TARGET].astype("float64") - entry_only)
    frame = frame[~frame["from_iso3"].isin(POOLED_VOTERS)]
    out = frame.groupby(["vote_type", "from_iso3", "to_iso3"], as_index=False).agg(
        excess=("excess", "mean"),
        points=(TARGET, "mean"),
        meetings=("year", "nunique"),
    )
    out["points"] = out["points"].astype("float64")
    out["reliable"] = out["meetings"] >= MIN_MEETINGS
    return out.sort_values(
        ["vote_type", "excess"], ascending=[True, False], ignore_index=True
    )


def main() -> None:
    parts_out, pairs_out = [], []
    for vote_type in VOTE_TYPES:
        panel = load(vote_type)
        for estimator in ESTIMATORS:
            predictions = {
                part: fit_predict(panel, columns, estimator, ESTIMATORS)
                for part, columns in PARTS.items()
            }
            table = decompose(panel, predictions)
            table.insert(0, "model", estimator)
            table.insert(0, "vote_type", vote_type)
            parts_out.append(table)
            if estimator == "ridge":
                pairs_out.append(affinity(panel, predictions["entry"]))

    parts = pd.concat(parts_out, ignore_index=True)
    pairs = pd.concat(pairs_out, ignore_index=True)
    io.write_parquet(parts, "decomposition", "processed")
    io.write_parquet(pairs, "pair_affinity", "processed")

    print("\nshare of the points explained, years never seen, all years pooled")
    pooled = parts[parts["scope"] == "all"]
    for row in pooled.itertuples():
        spread = parts[
            (parts["vote_type"] == row.vote_type)
            & (parts["model"] == row.model)
            & (parts["scope"] != "all")
        ]
        print(
            f"   {row.vote_type:9s} {row.model:9s} entry only {row.entry_only:6.1%}  "
            f"pair only {row.pair_only:6.1%}  overlap {row.overlap:6.1%}  "
            f"noise {row.noise:6.1%}  "
            f"(pair only per year {spread['pair_only'].min():.1%} "
            f"to {spread['pair_only'].max():.1%})"
        )

    reliable = pairs[pairs["reliable"]]
    for vote_type in VOTE_TYPES:
        top = reliable[reliable["vote_type"] == vote_type].head(10)
        print(f"\nstrongest {vote_type} affinity, {MIN_MEETINGS}+ meetings")
        for row in top.itertuples():
            print(
                f"   {row.from_iso3} -> {row.to_iso3}  {row.excess:+5.2f} points "
                f"over the entry, {row.meetings} meetings"
            )


if __name__ == "__main__":
    main()
