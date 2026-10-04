"""provenance bookkeeping, no network"""

from __future__ import annotations

import yaml

from esc import config, fetch

SAMPLE = """\
# a comment that must survive
sources:
  - id: alpha
    name: Alpha
    url:
      a.csv: https://example.org/a.csv
    kind: download
    license: CC0 1.0
    citation: nobody
    retrieved_at: null
    sha256: null
    notes: >-
      keep me
  - id: beta
    name: Beta
    url: https://example.org
    kind: api
    license: CC0 1.0
    citation: nobody
    retrieved_at: null
    sha256: null
    notes: keep me too
"""


def test_checksum_file(tmp_path):
    path = tmp_path / "a.csv"
    path.write_bytes(b"year,points\n2016,12\n")
    digest = fetch.checksum_file(path)
    assert len(digest) == 64
    assert digest == fetch.checksum_file(path)


def test_record_provenance_keeps_comments_and_notes(tmp_path, monkeypatch):
    manifest = tmp_path / "sources.yml"
    manifest.write_text(SAMPLE)
    monkeypatch.setattr(config, "SOURCES_YML", manifest)

    payload = tmp_path / "a.csv"
    payload.write_bytes(b"hello")
    fetch.record_provenance("alpha", [payload])

    text = manifest.read_text()
    assert text.startswith("# a comment that must survive")
    assert "keep me too" in text

    parsed = yaml.safe_load(text)
    alpha, beta = parsed["sources"]
    assert alpha["sha256"] == {"a.csv": fetch.checksum_file(payload)}
    assert alpha["retrieved_at"].endswith("Z")
    assert alpha["notes"].strip() == "keep me"
    assert beta["retrieved_at"] is None


def test_record_provenance_is_idempotent(tmp_path, monkeypatch):
    manifest = tmp_path / "sources.yml"
    manifest.write_text(SAMPLE)
    monkeypatch.setattr(config, "SOURCES_YML", manifest)
    payload = tmp_path / "a.csv"
    payload.write_bytes(b"hello")

    fetch.record_provenance("alpha", [payload])
    once = manifest.read_text()
    fetch.record_provenance("alpha", [payload])
    twice = manifest.read_text()
    # only the timestamp may differ
    assert once.count("sha256:") == twice.count("sha256:")
    assert len(once.splitlines()) == len(twice.splitlines())


def test_get_source_lists_the_known_ids(tmp_path, monkeypatch):
    manifest = tmp_path / "sources.yml"
    manifest.write_text(SAMPLE)
    monkeypatch.setattr(config, "SOURCES_YML", manifest)
    assert fetch.get_source("beta")["kind"] == "api"
    try:
        fetch.get_source("gamma")
    except KeyError as exc:
        assert "alpha, beta" in str(exc)
    else:
        raise AssertionError("expected a KeyError")


def test_every_source_in_the_real_manifest_has_a_module():
    import importlib

    modules = {
        "eurovision_dataset": "eurovision_dataset",
        "eurovisionworld": "eurovisionworld",
        "cepii_geodist": "cepii_geodist",
        "wikidata": "wikidata",
        "team_dataset": "team_dataset",
    }
    for source in fetch.load_sources()["sources"]:
        if source["kind"] == "manual":
            continue
        module = importlib.import_module(f"esc.fetch.{modules[source['id']]}")
        assert module.SOURCE_ID == source["id"]
