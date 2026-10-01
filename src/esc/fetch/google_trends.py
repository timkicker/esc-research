"""search interest per entry and voting country

not written yet. pytrends works, tested on 2025. the catch is that
interest_by_region returns a share within the query and takes five terms, so
batches carry a fixed anchor and get rescaled. the window ends the day before
the final, the contest day spikes to 100 and is the result
"""

from __future__ import annotations

from pathlib import Path

SOURCE_ID = "google_trends"
ANCHOR = "Eurovision"


def fetch() -> list[Path]:
    raise NotImplementedError("anchor batching not written, see module docstring")
