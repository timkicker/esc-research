"""spijkervet csvs -> entries_esc, votes_esc, odds_esc

not written yet, nothing is downloaded so the headers are unknown and guessing
them is how you silently drop a column

run make data, look at the first line of each file, then map
  contestants.csv     -> entries_esc
  votes.csv           -> votes_esc
  betting_offices.csv -> odds_esc

still to check against the real files: how country is spelled since it is a
name not a code, how the round is encoded and whether semis are there at all,
which vote_type the votes file claims per year, and whether the odds are one
row per bookmaker per day or a single snapshot

this is the cross check not the authority, mirovision covers the same tables
plus jurors, where they disagree that is a finding for notes/
"""

from __future__ import annotations

from pathlib import Path

RAW_ID = "eurovision_dataset"


def parse() -> list[Path]:
    raise NotImplementedError("csv headers unknown, nothing downloaded yet")
