"""wikidata sparql, performer birth date P569 and sex P21

not written yet. a plain name match is not enough because "Sergey Lazarev"
alone returns six different people, so the query has to constrain to eurovision
participants. bands have neither property and they make up roughly a third of
entries
"""

from __future__ import annotations

from pathlib import Path

SOURCE_ID = "wikidata"


def fetch() -> list[Path]:
    raise NotImplementedError("no sparql query yet, see module docstring")
