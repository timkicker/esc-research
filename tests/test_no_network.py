"""network belongs in src/esc/fetch/ only"""

from __future__ import annotations

import ast

from esc import config

BANNED = {"requests", "requests_cache", "urllib", "urllib3", "http", "socket"}

# io.py holds the cached client that fetch/ uses, that is the one exception
ALLOWED = {"esc/io.py"}


def imported_names(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module.split(".")[0]


def test_only_fetch_and_io_import_http_libraries():
    src = config.ROOT / "src"
    offenders = {}
    for path in sorted(src.rglob("*.py")):
        relative = path.relative_to(src).as_posix()
        if relative.startswith("esc/fetch/") or relative in ALLOWED:
            continue
        found = BANNED & set(imported_names(ast.parse(path.read_text())))
        if found:
            offenders[relative] = sorted(found)
    assert offenders == {}


def test_the_scan_would_notice(tmp_path):
    tree = ast.parse("import requests\nfrom requests_cache import CachedSession\n")
    assert BANNED & set(imported_names(tree)) == {"requests", "requests_cache"}
