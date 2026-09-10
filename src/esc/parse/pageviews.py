"""pageview responses -> pageviews

not written yet, depends on parse/wikidata.py for the entry_id join

the response shape is not the problem, it is
{"items": [{"project", "article", "timestamp", "views", ...}]} with timestamps
as YYYYMMDDHH, the blocker is mapping article back to entry_id

the series starts 2015-07-01 so an earlier date in the interim table is a bug
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "wikimedia_pageviews"


def parse() -> list[Path]:
    raise NotImplementedError("needs the article mapping from parse/wikidata.py")
