"""interim entry tables -> processed entries

mirovision up to the year its dataset ends and recent_entries.csv after that.
where both cover a year the manual row wins since it was typed from the
official results on purpose
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from esc import io
from esc.build import log, log_counts, require_non_empty
from esc.parse import enforce


def _optional(name: str) -> pd.DataFrame | None:
    path = io.parquet_path(name, "interim")
    return io.read_parquet(name, "interim") if path.exists() else None


def _fill_from(frame: pd.DataFrame, name: str, columns: dict[str, str]) -> None:
    """fill columns from an optional interim table

    mapped by entry_id rather than merged (no _x and _y suffixes)
    """
    path = io.parquet_path(name, "interim")
    if not path.exists():
        log(STEP, f"{name}: file not there yet, {', '.join(columns)} stay empty")
        return
    source = io.read_parquet(name, "interim").set_index("entry_id")
    for target, column in columns.items():
        mapped = frame["entry_id"].map(source[column])
        frame[target] = mapped.astype(frame[target].dtype)
        log(STEP, f"{name}: {int(mapped.notna().sum())} of {len(frame)} rows filled")


STEP = "entries"


def build() -> Path:
    upstream = io.read_parquet("entries", "interim")
    manual = io.read_parquet("entries_manual", "interim")
    country_map = io.read_parquet("country_map", "interim")

    scraped = _optional("entries_recent")
    if scraped is None:
        log(STEP, "entries_recent: file not there yet, years after 2023 are missing")
    else:
        log(STEP, f"entries_recent: {len(scraped)} scraped finalists")
        upstream = pd.concat([upstream, scraped], ignore_index=True)
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

    _fill_from(
        combined,
        "artists",
        {"artist_age": "artist_age", "artist_sex": "artist_sex"},
    )
    _fill_from(combined, "song_language", {"song_language": "language"})

    out = enforce(combined, "entries")
    log_counts(STEP, "entries", n_in, len(out))
    log(STEP, f"years {out['year'].min()}-{out['year'].max()}")
    return io.write_parquet(require_non_empty(out, "entries"), "entries", "processed")
