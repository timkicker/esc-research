"""spijkervet release csvs"""

from __future__ import annotations

from pathlib import Path

from esc.fetch import fetch_download_source

SOURCE_ID = "eurovision_dataset"


def fetch() -> list[Path]:
    return fetch_download_source(SOURCE_ID)
