"""estimation and evaluation

two modes, and the difference matters. the explanatory model may use the
receiver effect, which is what every other country gave the same entry, and is
how the song side is held constant. a forecasting model may not, because on the
morning of the final nobody knows it yet. running both and reporting the gap is
the honest version
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esc import io

SEED = 20260501

PAIR = [
    "log_dist",
    "contig",
    "comlang_off",
    "comlang_ethno",
    "colony",
    "comcol",
    "smctry",
    "past_points",
    "past_meetings",
]
ATTENTION = ["web_interest", "youtube_interest"]
RECEIVER = ["receiver_effect"]

TARGET = "points"
GROUP = "year"
ENTRY = ["year", "vote_type", "to_iso3"]


def feature_sets(panel: pd.DataFrame) -> dict[str, list[str]]:
    """the four comparisons the canvas promises, minus what nobody delivered"""
    have = [c for c in ATTENTION if c in panel.columns]
    sets = {"pair": PAIR, "pair+receiver": PAIR + RECEIVER}
    if have:
        sets["pair+attention"] = PAIR + have
        sets["all"] = PAIR + RECEIVER + have
    return {
        name: [c for c in cols if c in panel.columns] for name, cols in sets.items()
    }


def load(vote_type: str | None = None) -> pd.DataFrame:
    panel = io.read_parquet("features", "processed")
    panel = panel[panel["vote_type"].isin(["jury", "televote"])]
    if vote_type:
        panel = panel[panel["vote_type"] == vote_type]
    return panel.reset_index(drop=True)


def design(panel: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """numeric design matrix, booleans to 0/1, missing to the training median"""
    out = panel[columns].copy()
    for column in out.columns:
        if str(out[column].dtype) == "boolean":
            out[column] = out[column].astype("Float64")
    return out.astype("float64")


def totals(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """sum pair level points up to one row per entry and vote type"""
    return frame.groupby(ENTRY, as_index=False)[column].sum()


def rng() -> np.random.Generator:
    return np.random.default_rng(SEED)
