"""mirovision csvs -> entries, votes, jurors, odds

not written yet, nothing is downloaded so the headers are unknown

this is the authority for entries and votes, it is a superset of
eurovision_dataset and the one the ismir paper describes

  contestants.csv -> entries
  votes.csv       -> votes
  jurors.csv      -> jurors
  bookmakers.csv  -> odds
  countries.csv   -> feeds country_map.csv by hand, not the pipeline

still to check: country spelling per table, whether juror_letter really is a
letter per country per year or a global id, whether votes.csv has a vote_type
column or separate columns to melt, and the timezone of the odds date

do not fill entries past 2023 from here, those come from recent_entries.csv
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "mirovision"


def parse() -> list[Path]:
    raise NotImplementedError("csv headers unknown, nothing downloaded yet")
