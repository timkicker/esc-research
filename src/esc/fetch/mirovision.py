"""mirovision csvs, pinned to a commit since there are no releases"""

from __future__ import annotations

from pathlib import Path

from esc.fetch import fetch_download_source

SOURCE_ID = "mirovision"


def fetch() -> list[Path]:
    return fetch_download_source(SOURCE_ID)
