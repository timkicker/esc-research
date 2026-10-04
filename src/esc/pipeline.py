"""stage runners behind the make targets

python -m esc.pipeline data|parse|build
"""

from __future__ import annotations

import importlib
import sys

FETCH = [
    "eurovision_dataset",
    "cepii_geodist",
    "eurovisionworld",
    "wikidata",
    "google_trends",
    "team_dataset",
]

PARSE = [
    "manual",
    "eurovision_dataset",
    "cepii_geodist",
    "eurovisionworld",
    "wikidata",
    "google_trends",
    "team_dataset",
]

BUILD = ["entries", "votes", "dyads", "features"]


def _run(package: str, modules: list[str], func: str) -> list[str]:
    """run every stage module, remember the ones that are still stubs"""
    skipped = []
    for name in modules:
        module = importlib.import_module(f"esc.{package}.{name}")
        try:
            getattr(module, func)()
        except NotImplementedError as exc:
            print(f"[{package}] {name}: not implemented, {exc}")
            skipped.append(name)
    return skipped


def _report(stage: str, skipped: list[str]) -> None:
    if skipped:
        print(f"[{stage}] skipped {len(skipped)} stub(s): {', '.join(skipped)}")
    else:
        print(f"[{stage}] done")


def data() -> None:
    _report("data", _run("fetch", FETCH, "fetch"))


def parse() -> None:
    _report("parse", _run("parse", PARSE, "parse"))


def build() -> None:
    # no stubs here, a build that cannot read its inputs must fail
    for name in BUILD:
        try:
            importlib.import_module(f"esc.build.{name}").build()
        except FileNotFoundError as exc:
            raise SystemExit(f"[build] {name}: {exc}") from None
    print("[build] done")


STAGES = {"data": data, "parse": parse, "build": build}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in STAGES:
        print(f"usage: python -m esc.pipeline {'|'.join(STAGES)}", file=sys.stderr)
        return 2
    STAGES[argv[0]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
