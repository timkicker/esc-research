"""un ideal points from harvard dataverse

not written yet, the file choice is open and dataverse ids move with every
version

version 39.0 read on 2026-09-10:
  13642051  IdealPointDyads1946-2025.tab   73mb dyadic
  11824371  IdealpointsJuly2025.tab        2.4mb country year
  11837234  AgreementScores.csv            145mb dyadic

deriving a distance from the small country year file is probably enough and 30x
cheaper, nobody has decided yet, sources.yml points at 13642051 as a placeholder

recheck the id against
https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/LEJUQZ
"""

from __future__ import annotations

from pathlib import Path

SOURCE_ID = "unga_ideal_points"


def fetch() -> list[Path]:
    raise NotImplementedError("file choice open and the dataverse id needs a recheck")
