"""the whole model stage on a small synthetic panel, no network"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from esc import io
from esc.models import PAIR, explain, leakcheck, run

COUNTRIES = ["AUT", "SWE", "GRC", "CYP", "SRB", "WLD"]
YEARS = [2016, 2017, 2018]
LADDER = [12, 10, 8, 7, 6]


def synthetic_panel(seed: int = 0) -> pd.DataFrame:
    """greece and cyprus always swap top marks, the rest follows the entry"""
    rng = np.random.default_rng(seed)
    rows = []
    for year in YEARS:
        receivers = [c for c in COUNTRIES if c != "WLD"]
        quality = dict(zip(receivers, rng.permutation(len(receivers)), strict=True))
        for vote_type in ("jury", "televote"):
            for voter in COUNTRIES:
                if vote_type == "jury" and voter == "WLD":
                    continue
                ranked = sorted(
                    (r for r in receivers if r != voter),
                    key=lambda r: -quality[r] - rng.normal(0, 0.5),
                )
                friend = {"GRC": "CYP", "CYP": "GRC"}.get(voter)
                if friend:
                    ranked.remove(friend)
                    ranked.insert(0, friend)
                for slot, receiver in enumerate(ranked):
                    rows.append(
                        {
                            "year": year,
                            "round": "final",
                            "vote_type": vote_type,
                            "from_iso3": voter,
                            "to_iso3": receiver,
                            "points": LADDER[slot],
                        }
                    )
    panel = pd.DataFrame(rows)
    panel["points"] = panel["points"].astype("Int16")
    for column in PAIR:
        panel[column] = rng.normal(size=len(panel))
    panel["contig"] = (
        panel["from_iso3"].isin(["GRC", "CYP"]) & panel["to_iso3"].isin(["GRC", "CYP"])
    ).astype("float64")
    grouped = panel.groupby(["year", "vote_type", "to_iso3"])["points"]
    received = grouped.transform("sum").astype("float64")
    voters = grouped.transform("size")
    panel["receiver_effect"] = (received - panel["points"].astype("float64")) / (
        voters - 1
    )
    panel["web_interest"] = rng.uniform(0, 100, size=len(panel))
    panel["youtube_interest"] = rng.uniform(0, 100, size=len(panel))
    panel["running_position"] = rng.uniform(0, 1, size=len(panel))
    return panel


@pytest.fixture()
def processed(data_root):
    io.write_parquet(synthetic_panel(), "features", "processed")
    return data_root


def test_a_year_is_never_predicted_from_itself():
    panel = synthetic_panel()
    before = run.fit_predict(panel, PAIR, "ridge")
    changed = panel.copy()
    held = changed["year"] == 2017
    changed.loc[held, "points"] = pd.array([0] * held.sum(), dtype="Int16")
    after = run.fit_predict(changed, PAIR, "ridge")
    # the 2017 targets changed but the 2017 predictions must not
    assert np.allclose(before[held], after[held])
    assert not np.allclose(before[~held], after[~held])


@pytest.mark.parametrize("estimator", list(run.ESTIMATORS))
def test_every_estimator_gives_the_same_answer_twice(estimator):
    panel = synthetic_panel()
    first = run.fit_predict(panel, PAIR, estimator)
    second = run.fit_predict(panel, PAIR, estimator)
    assert first.notna().all()
    pd.testing.assert_series_equal(first, second)


# random pair features leave some synthetic rankings constant
@pytest.mark.filterwarnings("ignore::scipy.stats.ConstantInputWarning")
def test_the_model_stage_runs_end_to_end(processed):
    io.write_parquet(synthetic_panel(), "votes", "processed")
    run.main()
    explain.main()
    leakcheck.main()

    chance = io.read_parquet("chance", "processed")
    assert set(chance["vote_type"]) == {"jury", "televote"}
    assert (chance["low"] < chance["high"]).all()
    checked = io.read_parquet("leakcheck", "processed")
    assert set(checked["history"]) == {"all earlier years", "training years only"}

    summary = io.read_parquet("model_summary", "processed")
    assert set(summary["model"]) == set(run.ESTIMATORS)
    assert {"pair", "pair+order", "pair+attention+order"} <= set(summary["features"])

    parts = io.read_parquet("decomposition", "processed")
    assert set(parts["vote_type"]) == {"jury", "televote"}
    assert set(parts["model"]) == set(explain.ESTIMATORS)
    total = parts["entry_only"] + parts["pair_only"] + parts["overlap"] + parts["noise"]
    assert np.allclose(total, 1)

    pairs = io.read_parquet("pair_affinity", "processed")
    assert "WLD" not in set(pairs["from_iso3"])
    ranked = pairs[pairs["vote_type"] == "televote"].sort_values(
        "excess", ascending=False
    )
    # the planted friendship has to come out on top
    assert {tuple(r) for r in ranked[["from_iso3", "to_iso3"]].head(2).values} == {
        ("GRC", "CYP"),
        ("CYP", "GRC"),
    }


def test_the_folded_history_leaves_out_the_held_out_year():
    votes = synthetic_panel()
    panel = votes.copy()
    history = leakcheck.pair_history(votes)
    panel = panel.drop(columns=leakcheck.HISTORY).merge(
        history, on=leakcheck.KEYS, how="left"
    )
    folded = leakcheck.folded(panel, votes, 2017)
    held = panel["year"] == 2017
    pd.testing.assert_frame_equal(folded[held], panel[held])
    # 2018 saw 2016 and 2017 before, without 2017 its history is 2016 alone
    later = panel["year"] == 2018
    expected = (
        votes[votes["year"] == 2016]
        .groupby(["from_iso3", "to_iso3"])["points"]
        .mean()
        .astype("float64")
    )
    got = folded[later].groupby(["from_iso3", "to_iso3"])["past_points"].first()
    assert np.allclose(got.reindex(expected.index), expected)
