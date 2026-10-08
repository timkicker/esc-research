"""cepii dist_cepii, only downloaded here since the parse step unpacks the zip"""

from __future__ import annotations

from pathlib import Path

from esc.fetch import fetch_download_source

SOURCE_ID = "cepii_geodist"


def fetch() -> list[Path]:
    return fetch_download_source(SOURCE_ID)
