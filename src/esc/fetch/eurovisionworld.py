"""eurovisionworld results for the years after the spijkervet release

the results page loads its data from a plain script under scripts/js/voting/
that holds the songs, the final table and every jury and televote point as
json. we read the script number off the year page and keep the script, so no
browser is needed and parse works offline from data/raw
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from esc import config, io
from esc.fetch import record_provenance

SOURCE_ID = "eurovisionworld"
YEARS = (2024, 2025, 2026)
PAGE = "https://eurovisionworld.com/eurovision/{year}"
SCRIPT = "https://eurovisionworld.com/scripts/js/voting/{event}.js"
EVENT = re.compile(r"/scripts/js/voting/(\d+)\.js")
BETWEEN = 2


def _event(session, year: int) -> str:
    page = session.get(PAGE.format(year=year))
    page.raise_for_status()
    events = sorted(set(EVENT.findall(page.text)))
    if len(events) != 1:
        raise ValueError(
            f"[{SOURCE_ID}] {year}: expected one voting script, found {events}, "
            "the page layout changed"
        )
    return events[0]


def fetch() -> list[Path]:
    target = config.RAW / SOURCE_ID
    target.mkdir(parents=True, exist_ok=True)
    missing = [y for y in YEARS if not (target / f"{y}.js").exists()]
    print(f"[{SOURCE_ID}] {len(YEARS)} year(s), {len(missing)} still to fetch")

    session = io.get_session()
    for year in missing:
        event = _event(session, year)
        script = session.get(SCRIPT.format(event=event))
        script.raise_for_status()
        path = target / f"{year}.js"
        path.write_text(script.text, encoding="utf-8")
        print(f"  {path.name}: voting script {event}, {len(script.text)} chars")
        time.sleep(BETWEEN)

    paths = sorted(target.glob("*.js"))
    record_provenance(SOURCE_ID, paths)
    return paths
