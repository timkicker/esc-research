"""un ideal points -> interim table

not written yet, which dataverse file we take decides both the schema and the
parse, see fetch/unga.py

dyadic file -> (year, iso_o, iso_d, ideal_point_distance), filter and rename
country year file -> (year, iso3, ideal_point), distance computed in build/dyads

add whichever one wins to parse.SCHEMA, not both

country codes here are correlates of war codes not iso3, that is a third
vocabulary and needs its own column in country_map.csv
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "unga_ideal_points"


def parse() -> list[Path]:
    raise NotImplementedError("file choice open so the target schema is undecided")
