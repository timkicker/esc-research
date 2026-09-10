"""network lives here and nowhere else

every module exposes fetch() -> list[Path], writes into data/raw/<source_id>/
and records provenance back into sources.yml
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

from esc import config, io

CHUNK = 1 << 20


def load_sources() -> dict:
    with config.SOURCES_YML.open() as fh:
        return yaml.safe_load(fh)


def get_source(source_id: str) -> dict:
    sources = load_sources()["sources"]
    for source in sources:
        if source["id"] == source_id:
            return source
    known = ", ".join(s["id"] for s in sources)
    raise KeyError(f"{source_id!r} is not in {config.SOURCES_YML}, known: {known}")


def checksum_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def record_provenance(source_id: str, paths: list[Path]) -> None:
    """patch retrieved_at and sha256 in place

    a yaml round trip would drop every comment and note in the file
    """
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    checksums = {p.name: checksum_file(p) for p in sorted(paths)}

    lines = config.SOURCES_YML.read_text().splitlines(keepends=True)
    start = _entry_start(lines, source_id)
    first, last = _provenance_span(lines, start, source_id)

    block = [f"    retrieved_at: '{stamp}'\n"]
    if checksums:
        block.append("    sha256:\n")
        block += [f"      {name}: {digest}\n" for name, digest in checksums.items()]
    else:
        block.append("    sha256: null\n")

    config.SOURCES_YML.write_text("".join(lines[:first] + block + lines[last:]))
    print(f"[{source_id}] provenance recorded for {len(checksums)} file(s)")


def _entry_start(lines: list[str], source_id: str) -> int:
    pattern = re.compile(rf"^  - id:\s*{re.escape(source_id)}\s*$")
    for i, line in enumerate(lines):
        if pattern.match(line.rstrip("\n")):
            return i
    raise KeyError(f"no entry for {source_id!r} in {config.SOURCES_YML}")


def _provenance_span(lines: list[str], start: int, source_id: str) -> tuple[int, int]:
    first = last = None
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("  - id:") or (
            lines[i].strip() and not lines[i].startswith(" ")
        ):
            break
        if lines[i].startswith("    retrieved_at:"):
            first = i
        elif lines[i].startswith("    notes:"):
            last = i
            break
    if first is None or last is None:
        raise ValueError(
            f"entry {source_id!r} needs retrieved_at and sha256 right before "
            "notes, that is the block we rewrite"
        )
    return first, last


def download(session, url: str, dest: Path, expected_sha256: str | None = None) -> Path:
    if dest.exists() and expected_sha256 and checksum_file(dest) == expected_sha256:
        print(f"  {dest.name}: present and matching, skipped")
        return dest

    print(f"  {dest.name}: GET {url}")
    response = session.get(url, stream=True)
    response.raise_for_status()

    # .part first so an interrupted run leaves nothing that looks finished
    part = dest.with_name(dest.name + ".part")
    with part.open("wb") as fh:
        for chunk in response.iter_content(CHUNK):
            fh.write(chunk)
    part.replace(dest)
    print(f"  {dest.name}: {dest.stat().st_size} bytes")
    return dest


def fetch_download_source(source_id: str) -> list[Path]:
    source = get_source(source_id)
    if source["kind"] != "download":
        raise ValueError(f"{source_id} is kind {source['kind']}, not download")

    urls = source["url"]
    if not isinstance(urls, dict):
        raise TypeError(f"{source_id}: url must map filename to url, see sources.yml")
    known = source.get("sha256") or {}

    target = config.RAW / source_id
    target.mkdir(parents=True, exist_ok=True)
    print(f"[{source_id}] fetching {len(urls)} file(s) into {target}")

    session = io.get_session()
    paths = [
        download(session, url, target / name, known.get(name))
        for name, url in sorted(urls.items())
    ]
    record_provenance(source_id, paths)
    return sorted(paths)
