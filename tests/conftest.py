"""shared test setup, nothing here touches the network"""

from __future__ import annotations

import os

# esc.config refuses to import without this
os.environ.setdefault("CONTACT_EMAIL", "pytest@example.org")

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from esc import config, io  # noqa: E402
from esc.parse import SCHEMA, enforce  # noqa: E402

FIXTURES = config.ROOT / "tests" / "fixtures"

# fixture file -> interim schema it follows
TABLES = {
    "country_map": "country_map",
    "voting_regimes": "voting_regimes",
    "entries": "entries",
    "entries_manual": "entries",
    "votes": "votes",
    "dyad_static": "dyad_static",
}


def _cast(df: pd.DataFrame, table: str) -> pd.DataFrame:
    for column, dtype in SCHEMA[table].items():
        series = df[column]
        if dtype == "boolean":
            series = series.map({"true": True, "false": False})
        elif dtype.startswith("datetime"):
            series = pd.to_datetime(series)
        elif dtype != "string":
            series = pd.to_numeric(series)
        df[column] = series
    return enforce(df, table)


def load_fixture(name: str) -> pd.DataFrame:
    df = pd.read_csv(FIXTURES / f"{name}.csv", dtype="string", na_values=[""])
    return _cast(df, TABLES[name])


@pytest.fixture()
def data_root(tmp_path, monkeypatch):
    """point every layer at a throwaway directory"""
    layers = {}
    for layer in config.LAYERS:
        path = tmp_path / layer
        path.mkdir(parents=True)
        layers[layer] = path
    monkeypatch.setattr(config, "LAYERS", layers)
    for layer, path in layers.items():
        monkeypatch.setattr(config, layer.upper(), path)
    monkeypatch.setattr(config, "CACHE", tmp_path / "cache")
    return tmp_path


@pytest.fixture()
def interim(data_root):
    """the fixture world loaded into the tmp interim layer"""
    for name in TABLES:
        io.write_parquet(load_fixture(name), name, "interim")
    return data_root
