"""network lives here and nowhere else

every module exposes fetch() -> list[Path], writes into data/raw/<source_id>/
and records what it got in data/raw/provenance.yml. sources.yml is only read
here, a download must not leave a diff in git
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import yaml

from esc import config, io

CHUNK = 1 << 20


def load_sources() -> dict:
    with config.SOURCES_YML.open(encoding="utf-8") as fh:
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
    """write date and checksums to data/raw/provenance.yml

    for downloads the checksums in sources.yml are the files our results are
    based on, a different file upstream gets a warning
    """
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    checksums = {p.name: checksum_file(p) for p in sorted(paths)}

    source = get_source(source_id)
    if source["kind"] == "download":
        expected = source.get("sha256") or {}
        for name, digest in checksums.items():
            if expected.get(name) not in (None, digest):
                print(
                    f"[{source_id}] WARNING {name} differs from the checksum in "
                    "sources.yml, upstream changed and results may differ"
                )

    log = config.PROVENANCE
    entries = {}
    if log.exists():
        entries = yaml.safe_load(log.read_text(encoding="utf-8")) or {}
    entries[source_id] = {"retrieved_at": stamp, "sha256": checksums or None}
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(yaml.safe_dump(entries, sort_keys=True), encoding="utf-8")
    print(f"[{source_id}] provenance recorded for {len(checksums)} file(s)")


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
