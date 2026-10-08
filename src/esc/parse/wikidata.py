"""sparql results -> interim artists

not written yet and without a query there is no result shape. target is the
artists table with entry_id, artist_age and artist_sex
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "wikidata"


def parse() -> list[Path]:
    raise NotImplementedError("no query so no result shape, see fetch/wikidata.py")
