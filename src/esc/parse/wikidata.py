"""sparql results -> interim artists

not written yet, no query so no result shape. target is the artists table,
entry_id with artist_age and artist_sex
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "wikidata"


def parse() -> list[Path]:
    raise NotImplementedError("no query so no result shape, see fetch/wikidata.py")
