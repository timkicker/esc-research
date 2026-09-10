"""migr_pop1ctz json-stat -> migration

not written yet, same blocker as fetch/eurostat.py, the dimension codes

json-stat keeps values in a flat array indexed by the cartesian product of the
dimensions so this cannot be written before the dimension order is known

once fetch works: expand to long form, map geo and citizen through
country_map.csv with EL -> GRC and UK -> GBR, drop unmatched with a logged count

reporting countries outside eu and efta have no rows at all, drop them with a
count, a suppressed value is NA and never 0
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "eurostat_migration"


def parse() -> list[Path]:
    raise NotImplementedError("dimension order unknown, see fetch/eurostat.py")
