"""estimation and evaluation

two modes with different rules. the explanatory model may use the receiver
effect (what every other country gave the same entry) and that is how the song
side is held constant. a forecasting model may not, because on the morning of
the final nobody knows it yet. we run both and report the gap
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esc import io
from esc.parse.team_dataset import SENTIMENTS, THEMES

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
LYRICS = ["sentiment", "theme", "repetition_verse", "repetition_chorus"]
ORDER = ["running_position"]

# fixed categories, so a test year with a theme missing still gets every column
CATEGORIES = {"sentiment": SENTIMENTS, "theme": THEMES}

TARGET = "points"
GROUP = "year"
ENTRY = ["year", "vote_type", "to_iso3"]


def feature_sets(panel: pd.DataFrame) -> dict[str, list[str]]:
    """the comparisons the canvas promises, minus what nobody delivered"""
    have = [c for c in ATTENTION if c in panel.columns]
    order = [c for c in ORDER if c in panel.columns]
    sets = {"pair": PAIR, "pair+receiver": PAIR + RECEIVER}
    if "sentiment" in panel.columns:
        sets["pair+lyrics"] = PAIR + LYRICS
    if order:
        sets["pair+order"] = PAIR + order
    if have:
        sets["pair+attention"] = PAIR + have
        sets["all"] = PAIR + RECEIVER + have
    if have and order:
        sets["pair+attention+order"] = PAIR + have + order
    return {
        name: [c for c in cols if c in panel.columns] for name, cols in sets.items()
    }


def explanatory(sets: dict[str, list[str]]) -> set[str]:
    """sets that use the receiver effect explain a result but cannot forecast it"""
    return {name for name, columns in sets.items() if set(RECEIVER) & set(columns)}


def load(vote_type: str | None = None) -> pd.DataFrame:
    panel = io.read_parquet("features", "processed")
    panel = panel[panel["vote_type"].isin(["jury", "televote"])]
    if vote_type:
        panel = panel[panel["vote_type"] == vote_type]
    return panel.reset_index(drop=True)


def design(panel: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """numeric design matrix, categories one-hot, booleans 0/1, missing stays NaN"""
    parts = []
    for column in columns:
        if column in CATEGORIES:
            values = panel[column].astype("string")
            for level in CATEGORIES[column]:
                dummy = (values == level).astype("Float64")
                dummy[values.isna()] = pd.NA
                parts.append(dummy.rename(f"{column}={level}"))
        elif str(panel[column].dtype) == "boolean":
            parts.append(panel[column].astype("Float64"))
        else:
            parts.append(panel[column])
    return pd.concat(parts, axis=1).astype("float64")


def totals(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """sum pair level points up to one row per entry and vote type"""
    return frame.groupby(ENTRY, as_index=False)[column].sum()


def rng() -> np.random.Generator:
    return np.random.default_rng(SEED)
