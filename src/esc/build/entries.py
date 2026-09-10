"""interim entry tables -> processed entries

mirovision up to the year its dataset ends, recent_entries.csv after that, and
where both cover a year the manual row wins since it was typed from the
official results on purpose
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from esc import io
from esc.build import log, log_counts, require_non_empty
from esc.parse import enforce

STEP = "entries"


def build() -> Path:
    upstream = io.read_parquet("entries", "interim")
    manual = io.read_parquet("entries_manual", "interim")
    country_map = io.read_parquet("country_map", "interim")
    log(STEP, f"upstream {len(upstream)} rows, manual {len(manual)} rows")

    overlap = sorted(set(manual["year"]) & set(upstream["year"]))
    if overlap:
        log(STEP, f"manual overrides upstream for {overlap}")
        upstream = upstream[~upstream["year"].isin(overlap)]

    combined = pd.concat([upstream, manual], ignore_index=True)
    n_in = len(combined)

    known = set(country_map["iso3"].dropna())
    unknown = sorted(set(combined["country_iso3"].dropna()) - known)
    if unknown:
        raise ValueError(
            f"{len(unknown)} code(s) missing from country_map.csv: {unknown}, add "
            "them by hand instead of dropping them"
        )

    duplicates = combined.duplicated(subset=["entry_id", "round"]).sum()
    if duplicates:
        raise ValueError(f"{duplicates} duplicate (entry_id, round) rows, bad concat")

    out = enforce(combined, "entries")
    log_counts(STEP, "entries", n_in, len(out))
    log(STEP, f"years {out['year'].min()}-{out['year'].max()}")
    return io.write_parquet(require_non_empty(out, "entries"), "entries", "processed")
