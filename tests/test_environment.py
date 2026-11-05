"""T002 environment checks: Python 3.12, DuckDB 1.x, Parquet roundtrip, DB reopen integrity."""

import sys

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

import atlas


def test_python_is_312():
    assert sys.version_info[:2] == (3, 12)


def test_duckdb_major_is_1():
    assert duckdb.__version__.split(".")[0] == "1"


def test_package_importable():
    assert atlas.__version__


def test_parquet_roundtrip(tmp_path):
    table = pa.table(
        {
            "station_id": pa.array(["KA-001", "KA-002"]),
            "rain_mm": pa.array([12.5, None], type=pa.float64()),
            "observed_at": pa.array(
                [1_730_000_000_000, 1_730_086_400_000], type=pa.timestamp("ms", tz="UTC")
            ),
        }
    )
    path = tmp_path / "sample.parquet"
    pq.write_table(table, path)
    back = pq.read_table(path)
    assert back.schema == table.schema
    assert back.equals(table)


def test_duckdb_reopen_integrity(tmp_path):
    db = tmp_path / "cache.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE t AS SELECT range AS i, range * 0.5 AS v FROM range(10000)")
    expected = con.execute("SELECT count(*), sum(i), sum(v) FROM t").fetchone()
    con.execute("CHECKPOINT")
    con.close()

    # Reopen read-only: the file must load and return identical aggregates.
    con = duckdb.connect(str(db), read_only=True)
    assert con.execute("SELECT count(*), sum(i), sum(v) FROM t").fetchone() == expected
    con.close()
