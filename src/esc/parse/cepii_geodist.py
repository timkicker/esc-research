"""dist_cepii -> dyad_static

not written yet, unclear what is inside the zip and in which format, the member
names and the stata version are unconfirmed and read_stata does not read all of
them

the target columns are already named the same upstream so the mapping should be
the identity, what needs checking is whether the dummies come as 0/1 ints which
have to become nullable booleans not floats, whether the file is symmetric since
the panel is directed and needs both directions, and which codes fall out when
they go through country_map.csv
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "cepii_geodist"


def parse() -> list[Path]:
    raise NotImplementedError("zip contents and stata version unconfirmed")
