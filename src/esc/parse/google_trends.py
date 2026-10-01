"""raw trends responses -> interim trends

not written yet. rescale each batch against the anchor, one row per year, voting
country and entry. a zero keeps a censored flag, it means below one percent
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "google_trends"


def parse() -> list[Path]:
    raise NotImplementedError("nothing fetched yet, see fetch/google_trends.py")
