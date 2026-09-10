"""raw trends responses -> trends

not written yet, depends on fetch/google_trends.py

rescale every batch against the anchor, then one row per (year, voting country,
entry_id) with the web and the youtube series side by side. a zero stays a zero
but gets a censored flag, it means below one percent of the anchor
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "google_trends"


def parse() -> list[Path]:
    raise NotImplementedError("nothing fetched yet, see fetch/google_trends.py")
