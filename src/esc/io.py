"""paths, parquet helpers, cached http client"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import requests_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from esc import config

PARQUET_COMPRESSION = "zstd"


class _TimeoutCachedSession(requests_cache.CachedSession):
    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", config.HTTP_TIMEOUT)
        return super().request(method, url, **kwargs)


def get_session() -> requests_cache.CachedSession:
    """cached session that only fetch/ may call"""
    config.CACHE.mkdir(parents=True, exist_ok=True)
    session = _TimeoutCachedSession(
        cache_name=str(config.CACHE / "http"),
        backend="sqlite",
        allowable_codes=(200,),  # never cache an error response
        stale_if_error=False,
    )
    session.headers["User-Agent"] = config.user_agent()

    retry = Retry(
        total=config.HTTP_RETRIES,
        backoff_factor=config.HTTP_BACKOFF,
        status_forcelist=config.HTTP_RETRY_STATUS,
        allowed_methods=frozenset({"GET", "HEAD"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def parquet_path(name: str, layer: str) -> Path:
    return config.layer_dir(layer) / f"{name}.parquet"


def canonicalise(df: pd.DataFrame) -> pd.DataFrame:
    """sorted columns, sorted rows, fresh index, so reruns are byte identical"""
    out = df[sorted(df.columns)]
    if len(out.columns):
        out = out.sort_values(by=list(out.columns), kind="stable", na_position="last")
    return out.reset_index(drop=True)


def write_parquet(df: pd.DataFrame, name: str, layer: str) -> Path:
    path = parquet_path(name, layer)
    path.parent.mkdir(parents=True, exist_ok=True)
    canonicalise(df).to_parquet(
        path,
        engine="pyarrow",
        index=False,
        compression=PARQUET_COMPRESSION,
    )
    return path


def read_parquet(name: str, layer: str) -> pd.DataFrame:
    path = parquet_path(name, layer)
    if not path.exists():
        target = "parse" if layer == "interim" else "build"
        raise FileNotFoundError(
            f"{path} is missing, run `make {target}` first or `make data` if the "
            "downloads are missing too"
        )
    return canonicalise(pd.read_parquet(path, engine="pyarrow"))


def duck() -> duckdb.DuckDBPyConnection:
    """in memory connection with every processed parquet as a view"""
    con = duckdb.connect()
    for path in sorted(config.PROCESSED.glob("*.parquet")):
        # duckdb refuses bound parameters in ddl
        view = path.stem.replace('"', '""')
        literal = str(path).replace("'", "''")
        con.execute(
            f'CREATE OR REPLACE VIEW "{view}" AS '
            f"SELECT * FROM read_parquet('{literal}')"
        )
    return con
