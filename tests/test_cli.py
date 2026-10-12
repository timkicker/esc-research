"""the one entry point that also works on windows"""

from __future__ import annotations

from esc import cli


def test_help_lists_every_command(capsys):
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    for name in cli.COMMANDS:
        assert name in out


def test_an_unknown_command_fails(capsys):
    assert cli.main(["nonsense"]) == 2


def test_clean_removes_only_interim(tmp_path, monkeypatch):
    for name in ("raw", "interim"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(cli.config, "ROOT", tmp_path)
    monkeypatch.setattr(cli.config, "INTERIM", tmp_path / "interim")
    cli.main(["clean"])
    assert not (tmp_path / "interim").exists()
    assert (tmp_path / "raw").exists()
