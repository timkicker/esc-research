"""wikidata sparql, performer birth date P569 and sex P21

a plain name match is not enough because "Sergey Lazarev" alone returns six
different people, so the query only asks for what took part in one edition
(P1344) and the performers of those songs (P175). parse matches the names to
our entries offline, inside one year they are unique. one query for the
edition per year and one per edition, the combined query times out
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from esc import config, io
from esc.fetch import record_provenance

SOURCE_ID = "wikidata"
ENDPOINT = "https://query.wikidata.org/sparql"
YEARS = tuple(y for y in range(2016, 2027) if y != 2020)
EDITIONS_FILE = "editions.json"
BETWEEN = 1

# Q110288240 is "Eurovision Song Contest edition", P585 its date
EDITIONS = """
SELECT ?edition ?date WHERE {
  ?edition wdt:P31 wd:Q110288240 ; wdt:P585 ?date .
}
"""

# the edition has to sit inside both branches, a bare BIND scans everything
PARTICIPANTS = """
SELECT ?item ?itemLabel ?person ?personLabel ?personType ?birth ?sex WHERE {
  VALUES ?edition { wd:%s }
  { ?item wdt:P1344 ?edition . BIND(?item AS ?person) }
  UNION
  { ?item wdt:P1344 ?edition ; wdt:P175 ?person . }
  OPTIONAL { ?person wdt:P31 ?personType }
  OPTIONAL { ?person wdt:P569 ?birth }
  OPTIONAL { ?person wdt:P21 ?sex }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }
}
"""


def _query(session, sparql: str) -> str:
    response = session.get(
        ENDPOINT,
        params={"query": sparql},
        headers={"Accept": "application/sparql-results+json"},
    )
    response.raise_for_status()
    json.loads(response.text)
    return response.text


def editions(text: str) -> dict[int, str]:
    """year -> edition qid, fails on a year with two editions"""
    out: dict[int, str] = {}
    for row in json.loads(text)["results"]["bindings"]:
        year = int(row["date"]["value"][:4])
        qid = row["edition"]["value"].rsplit("/", 1)[-1]
        if out.get(year, qid) != qid:
            raise ValueError(f"[{SOURCE_ID}] {year}: two editions {out[year]}, {qid}")
        out[year] = qid
    return out


def fetch() -> list[Path]:
    target = config.RAW / SOURCE_ID
    target.mkdir(parents=True, exist_ok=True)
    missing = [y for y in YEARS if not (target / f"{y}.json").exists()]
    print(f"[{SOURCE_ID}] {len(YEARS)} year(s), {len(missing)} still to fetch")

    if missing:
        session = io.get_session()
        index = target / EDITIONS_FILE
        if not index.exists():
            index.write_text(_query(session, EDITIONS), encoding="utf-8")
        known = editions(index.read_text(encoding="utf-8"))
        for year in missing:
            if year not in known:
                raise ValueError(f"[{SOURCE_ID}] no edition item for {year}")
            text = _query(session, PARTICIPANTS % known[year])
            path = target / f"{year}.json"
            path.write_text(text, encoding="utf-8")
            rows = len(json.loads(text)["results"]["bindings"])
            print(f"  {path.name}: edition {known[year]}, {rows} rows")
            time.sleep(BETWEEN)

    paths = sorted(target.glob("*.json"))
    record_provenance(SOURCE_ID, paths)
    return paths
