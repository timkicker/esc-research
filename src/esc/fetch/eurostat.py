"""eurostat migr_pop1ctz

not written yet, missing the dimension codes

the endpoint works, a probe with geo=AT&time=2020 returns json-stat, what is
missing is the code list for unit, age, sex, citizen, geo, freq and whether
citizenship uses the same geo vocabulary as the reporting country

get them from
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/datastructure/ESTAT/migr_pop1ctz
"""

from __future__ import annotations

from pathlib import Path

SOURCE_ID = "eurostat_migration"


def fetch() -> list[Path]:
    raise NotImplementedError(
        "missing the dimension codes for migr_pop1ctz, see module docstring"
    )
