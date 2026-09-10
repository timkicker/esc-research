"""wikidata sparql, article titles per entry

not written yet, missing the query

open before it can be written: which item an entry actually is, the song, the
performance or the country participation, they are not all present in every
year, the property path from there to year and country, and which sitelinks to
take per country

endpoint is https://query.wikidata.org/sparql with
Accept: application/sparql-results+json, it times out after 60s so slice by year
"""

from __future__ import annotations

from pathlib import Path

SOURCE_ID = "wikidata"


def fetch() -> list[Path]:
    raise NotImplementedError("no sparql query yet, see module docstring")
