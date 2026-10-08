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


def _setup(tmp_path, monkeypatch):
    manifest = tmp_path / "sources.yml"
    manifest.write_text(SAMPLE)
    monkeypatch.setattr(config, "SOURCES_YML", manifest)
    monkeypatch.setattr(config, "PROVENANCE", tmp_path / "raw" / "provenance.yml")
    payload = tmp_path / "a.csv"
    payload.write_bytes(b"hello")
    return manifest, payload


def test_record_provenance_leaves_sources_yml_alone(tmp_path, monkeypatch):
    # a download that changes a tracked file breaks git pull for everyone else
    manifest, payload = _setup(tmp_path, monkeypatch)
    fetch.record_provenance("alpha", [payload])
    assert manifest.read_text() == SAMPLE

    log = yaml.safe_load(config.PROVENANCE.read_text())
    assert log["alpha"]["sha256"] == {"a.csv": fetch.checksum_file(payload)}
    assert log["alpha"]["retrieved_at"].endswith("Z")


def test_record_provenance_keeps_other_sources(tmp_path, monkeypatch):
    _, payload = _setup(tmp_path, monkeypatch)
    fetch.record_provenance("alpha", [payload])
    fetch.record_provenance("beta", [])
    fetch.record_provenance("alpha", [payload])
    log = yaml.safe_load(config.PROVENANCE.read_text())
    assert set(log) == {"alpha", "beta"}
    assert log["beta"]["sha256"] is None


def test_record_provenance_warns_when_upstream_changed(tmp_path, monkeypatch, capsys):
    manifest, payload = _setup(tmp_path, monkeypatch)
    manifest.write_text(
        SAMPLE.replace(
            "    sha256: null\n    notes: >-",
            "    sha256:\n      a.csv: 00\n    notes: >-",
            1,
        )
    )
    fetch.record_provenance("alpha", [payload])
    assert "differs from the checksum" in capsys.readouterr().out


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
