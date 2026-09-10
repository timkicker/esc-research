"""search interest per entry and voting country

not written yet, needs the anchor batching

pytrends works, tested on 2025. the catch is that interest_by_region normalises
per country over the queried terms to sum 100, so it is a share within the query
and five terms is the limit. every batch therefore carries a fixed anchor term,
"Eurovision" itself, and gets rescaled against it afterwards

the window ends the day before the final, the contest day spikes to 100 and is
the result, not an expectation
"""

from __future__ import annotations

from pathlib import Path

SOURCE_ID = "google_trends"
ANCHOR = "Eurovision"


def fetch() -> list[Path]:
    raise NotImplementedError("anchor batching not written, see module docstring")
