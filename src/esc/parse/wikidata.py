"""sparql results -> entry_articles

not written yet, there is no query so there is no result shape either

target is (entry_id, wiki_lang, article_title), plumbing rather than analysis
which is why it is not in the README.md schema, add it to parse.SCHEMA once the
query is settled so it gets the same dtype enforcement as everything else

titles have to be canonical, a redirect gives pageviews for the redirect only
which is a quiet undercount not an error
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "wikidata"


def parse() -> list[Path]:
    raise NotImplementedError("no query so no result shape, see fetch/wikidata.py")
