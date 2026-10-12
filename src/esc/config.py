"""paths and the http identity"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
MANUAL = DATA / "manual"
EXPORT = DATA / "export"
CACHE = ROOT / "cache"

SOURCES_YML = ROOT / "sources.yml"
PROVENANCE = RAW / "provenance.yml"

LAYERS: dict[str, Path] = {
    "raw": RAW,
    "interim": INTERIM,
    "processed": PROCESSED,
    "manual": MANUAL,
}

PROJECT = "esc-research"
VERSION = "0.1"

HTTP_TIMEOUT = 30
HTTP_RETRIES = 5
HTTP_BACKOFF = 1.0
HTTP_RETRY_STATUS = (429, 500, 502, 503, 504)


class MissingContactEmail(RuntimeError):
    pass


def build_user_agent(email: str | None) -> str:
    email = (email or "").strip()
    if not email:
        raise MissingContactEmail(
            "CONTACT_EMAIL is not set, wikimedia needs a contact address in the "
            f"user agent, copy .env.example to {ROOT / '.env'}"
        )
    return f"{PROJECT}/{VERSION} (mailto:{email})"


def user_agent() -> str:
    """only the download stage needs it, parse, build and model run without"""
    return build_user_agent(os.environ.get("CONTACT_EMAIL"))


def layer_dir(layer: str) -> Path:
    try:
        return LAYERS[layer]
    except KeyError:
        known = ", ".join(sorted(LAYERS))
        raise ValueError(f"unknown layer {layer!r}, expected one of {known}") from None
