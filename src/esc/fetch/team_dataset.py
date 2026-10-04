"""lyrics analysis from the teammate repo, pinned to a commit"""

from __future__ import annotations

from pathlib import Path

from esc.fetch import fetch_download_source

SOURCE_ID = "team_dataset"


def fetch() -> list[Path]:
    return fetch_download_source(SOURCE_ID)
