"""wikimedia rest pageviews per article per day

not written yet, needs the title mapping from fetch/wikidata.py which is also
a stub

settled already: data starts 2015-07-01 so an earlier start is a bug not an
empty result, agent=user, titles percent encoded with underscores, a redirect
counts against whichever title was asked for
"""

from __future__ import annotations

from pathlib import Path

SOURCE_ID = "wikimedia_pageviews"


def fetch() -> list[Path]:
    raise NotImplementedError("needs the article titles from fetch/wikidata.py")
