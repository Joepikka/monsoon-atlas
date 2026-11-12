"""T229/T042 local contract: actual source samples, SQLite caps and signed uploads."""

import gzip
import hashlib
import json
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def database(tmp_path):
    connection = sqlite3.connect(tmp_path / "hot.sqlite")
    connection.executescript((ROOT / "worker/schema.sql").read_text("utf-8"))
    yield connection
    connection.close()


def insert(connection, source="S09", database_bytes=0):
    name = "sachet-ka-point" if source == "S09" else "openmeteo-temperature-point"
    record = json.loads((ROOT / f"web/tests/fixtures/{name}.json").read_text("utf-8"))
    payload = gzip.compress(json.dumps(record).encode())
    ident = hashlib.sha256(payload).hexdigest()
    with connection:
        connection.execute(
            "INSERT OR IGNORE INTO daily_usage(day,writes_reserved) VALUES ('2026-11-06',0)"
        )
        connection.execute(
            "INSERT INTO hot_snapshots(id,state,source_id,as_of_ms,payload,sha256,"
            "budget_day,database_bytes) "
            "VALUES (?,'ka',?,1,?,?, '2026-11-06',?)",
            (ident, source, payload, hashlib.sha256(payload).hexdigest(), database_bytes),
        )
    return ident


def test_storage_reservation_and_head_are_atomic(database):
    ident = insert(database)
    assert database.execute("SELECT snapshot_id FROM hot_current").fetchone() == (ident,)
    before = database.execute("SELECT allocated_bytes FROM capacity").fetchone()
    with pytest.raises(sqlite3.IntegrityError, match="storage_cap"):
        insert(database, "S01", database_bytes=400_000_000 - 64)
    assert database.execute("SELECT COUNT(*) FROM hot_snapshots").fetchone() == (1,)
    assert database.execute("SELECT allocated_bytes FROM capacity").fetchone() == before
    assert database.execute("SELECT snapshot_id FROM hot_current").fetchone() == (ident,)


def test_write_cap_rollback_preserves_previous_snapshot(database):
    ident = insert(database)
    database.execute("UPDATE daily_usage SET writes_reserved=10000")
    database.commit()
    with pytest.raises(sqlite3.IntegrityError, match="write_cap"):
        insert(database, "S01")
    assert database.execute("SELECT COUNT(*) FROM hot_snapshots").fetchone() == (1,)
    assert database.execute("SELECT snapshot_id FROM hot_current").fetchone() == (ident,)
    assert database.execute("SELECT writes_reserved FROM daily_usage").fetchone() == (10000,)


def test_worker_pins_and_disabled_deployment_configuration():
    package = json.loads((ROOT / "worker/package.json").read_text("utf-8"))
    lock = json.loads((ROOT / "worker/package-lock.json").read_text("utf-8"))
    assert package["engines"]["node"] == "22.16.0"
    for name, version in package["devDependencies"].items():
        assert lock["packages"][f"node_modules/{name}"]["version"] == version
    config = (ROOT / "worker/wrangler.toml").read_text("utf-8")
    assert 'CAPABILITY_GATE = "blocked"' in config
    assert "workers_dev = false" in config
    assert "database_id =" not in config


def test_worker_pure_logic_and_type_check():
    node_dir = ROOT / ".tools/node/node-v22.16.0-win-x64"
    if not (node_dir / "node.exe").exists() or not (ROOT / "worker/node_modules").exists():
        pytest.skip("Optional pinned Worker toolchain is not installed in core-only CI")
    env = os.environ.copy()
    env.update(
        {
            "TEMP": str(ROOT / ".cache/tmp"),
            "TMP": str(ROOT / ".cache/tmp"),
            "PATH": str(node_dir) + os.pathsep + env.get("PATH", ""),
        }
    )
    for action in ("check", "test"):
        result = subprocess.run(
            [
                str(node_dir / "node.exe"),
                str(node_dir / "node_modules/npm/bin/npm-cli.js"),
                "run",
                action,
            ],
            cwd=ROOT / "worker",
            env=env,
            capture_output=True,
            encoding="utf-8",
            timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
