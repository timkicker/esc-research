from __future__ import annotations

import importlib
import os

import pytest

from esc import config


def test_paths_are_inside_the_repository():
    assert config.ROOT.is_dir()
    assert (config.ROOT / "pyproject.toml").is_file()
    for path in (config.RAW, config.INTERIM, config.PROCESSED, config.MANUAL):
        assert path.is_relative_to(config.DATA)
    assert config.CACHE.parent == config.ROOT


def test_user_agent_carries_the_contact_address():
    agent = config.build_user_agent("someone@example.org")
    assert agent == "esc-research/0.1 (mailto:someone@example.org)"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_user_agent_refuses_a_missing_contact_address(value):
    with pytest.raises(config.MissingContactEmail) as excinfo:
        config.build_user_agent(value)
    assert ".env.example" in str(excinfo.value)


def test_import_fails_without_contact_email(monkeypatch):
    # patch dotenv itself because the reload re-imports load_dotenv and a local .env
    # would put the value straight back
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: False)
    monkeypatch.delenv("CONTACT_EMAIL", raising=False)
    try:
        # the reload redefines the class so match the base and the message
        with pytest.raises(RuntimeError, match="CONTACT_EMAIL is not set"):
            importlib.reload(config)
    finally:
        os.environ["CONTACT_EMAIL"] = "pytest@example.org"
        importlib.reload(config)


def test_layer_dir_rejects_an_unknown_layer():
    with pytest.raises(ValueError, match="unknown layer"):
        config.layer_dir("nonsense")
