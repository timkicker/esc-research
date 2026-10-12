"""one command on every system, make does not exist on windows

uv run esc data|parse|build|model|all|test|lint|clean|clean-all
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from esc import config, pipeline


def _model() -> None:
    from esc.models import explain, run

    run.main()
    explain.main()


def _all() -> None:
    for step in (pipeline.data, pipeline.parse, pipeline.build, _model):
        step()


def _export() -> None:
    from esc import export

    export.main()


def _tool(*args: str) -> None:
    code = subprocess.call([sys.executable, "-m", *args], cwd=config.ROOT)
    if code:
        raise SystemExit(code)


def _test() -> None:
    _tool("pytest", "-q")


def _lint() -> None:
    _tool("ruff", "check", "src", "tests")
    _tool("ruff", "format", "--check", "src", "tests")


def _remove(*paths) -> None:
    for path in paths:
        print(f">> removing {path.relative_to(config.ROOT).as_posix()}")
        shutil.rmtree(path, ignore_errors=True)


COMMANDS = {
    "data": (pipeline.data, "download and scrape into data/raw"),
    "parse": (pipeline.parse, "raw files into typed tables in data/interim"),
    "build": (pipeline.build, "the pair table in data/processed"),
    "model": (_model, "forecast and explain, every year tested unseen"),
    "all": (_all, "data, parse, build and model in a row"),
    "export": (_export, "csv and site json into data/export"),
    "test": (_test, "run the tests"),
    "lint": (_lint, "ruff check and format check"),
    "clean": (lambda: _remove(config.INTERIM), "delete data/interim"),
    "clean-all": (
        lambda: _remove(
            config.RAW, config.INTERIM, config.PROCESSED, config.CACHE, config.EXPORT
        ),
        "delete everything that was downloaded or built",
    ),
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in COMMANDS:
        print("usage: uv run esc <command>\n")
        for name, (_, help_text) in COMMANDS.items():
            print(f"  {name:<10} {help_text}")
        return 0 if argv in ([], ["help"], ["-h"], ["--help"]) else 2
    COMMANDS[argv[0]][0]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
