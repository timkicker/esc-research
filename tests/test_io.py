from __future__ import annotations

import pandas as pd
import pytest

from esc import io


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": pd.Series([2016, 2015, 2016], dtype="int16"),
            "to_iso3": pd.Series(["SWE", "ITA", "AUT"], dtype="string"),
            "points": pd.Series([12.0, 8.0, None], dtype="float64"),
            "qualified": pd.Series([True, False, True], dtype="bool"),
        }
    )


def test_parquet_round_trip_preserves_dtypes_and_values(data_root):
    df = sample_frame()
    io.write_parquet(df, "entries", "interim")
    back = io.read_parquet("entries", "interim")

    expected = io.canonicalise(df)
    pd.testing.assert_frame_equal(back, expected)
    assert back.dtypes.to_dict() == expected.dtypes.to_dict()


def test_write_sorts_columns_and_rows(data_root):
    df = sample_frame()
    io.write_parquet(df, "entries", "interim")
    back = io.read_parquet("entries", "interim")

    assert list(back.columns) == sorted(df.columns)
    assert back["year"].is_monotonic_increasing


def test_rewriting_the_same_frame_is_byte_identical(data_root):
    df = sample_frame()
    path = io.write_parquet(df, "entries", "interim")
    first = path.read_bytes()
    io.write_parquet(df.iloc[::-1], "entries", "interim")
    assert path.read_bytes() == first


def test_read_parquet_points_at_the_make_target(data_root):
    with pytest.raises(FileNotFoundError, match="make parse"):
        io.read_parquet("entries", "interim")
    with pytest.raises(FileNotFoundError, match="make build"):
        io.read_parquet("dyads", "processed")


def test_duck_registers_processed_tables_as_views(data_root):
    io.write_parquet(sample_frame(), "entries", "processed")
    con = io.duck()
    try:
        rows = con.execute("SELECT count(*) FROM entries").fetchone()[0]
    finally:
        con.close()
    assert rows == 3
