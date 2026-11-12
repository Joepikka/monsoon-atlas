"""T260 (child of T180): trusted Ask release export and the Worker route (D95)."""

import os
import re
import sqlite3
import subprocess
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest

from atlas.rag.corpus import Document
from atlas.rag.index import build_index
from atlas.rag.manifest import FIELDS, ManifestError, literal, load_sql, manifest

ROOT = Path(__file__).resolve().parents[2]
NODE = ROOT / ".tools/node/node-v22.16.0-win-x64"
SCHEMA = (ROOT / "worker/schema.sql").read_text("utf-8")
ROUTE = (ROOT / "worker/src/index.ts").read_text("utf-8")
BASE = Document(
    doc_id="m05",
    path="reports/models/m05.md",
    kind="project",
    states=("ka",),
    licence="project-mit",
    language="en",
    text="# M05\n\n## Limits\n\nSPI is meteorological drought only.\nIt's not groundwater.\n",
    sha256="0" * 64,
    available_at="2026-11-05T17:48:40Z",
    commit="f" * 40,
)


def built(tmp_path, *documents):
    index = tmp_path / "index.sqlite"
    build_index(list(documents or [BASE]), index)
    return index


def worker_db():
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    return db


def served(db, ids):
    """Run the Worker's own release and chunk queries from worker/src/index.ts."""
    pointer = re.search(r"prepare\('(SELECT release FROM ask_current[^']*)'\)", ROUTE).group(1)
    query = re.search(r"prepare\(`(SELECT chunk_id[^`]*)`\)", ROUTE).group(1)
    release = db.execute(pointer).fetchone()[0]
    sql = query.replace("${ids.map(() => '?').join(',')}", ",".join("?" * len(ids)))
    return release, db.execute(sql, (release, *ids)).fetchall()


def test_release_is_deterministic_and_hash_checked(tmp_path):
    index = built(tmp_path)
    first, second = manifest(index), manifest(index)
    assert first == second and re.fullmatch(r"[0-9a-f]{64}", first["release"])
    with closing(sqlite3.connect(index)) as db:
        assert len(first["chunks"]) == db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        db.execute("UPDATE chunks SET text = text || ' Tampered.'")
        db.commit()
    with pytest.raises(ManifestError, match="does not match its SHA-256"):
        manifest(index)
    other = manifest(built(tmp_path / "b", replace(BASE, available_at="2026-11-06T00:00:00Z")))
    assert other["release"] != first["release"]  # a recommit is a new release


def test_load_file_round_trips_text_and_swaps_releases(tmp_path):
    old = manifest(built(tmp_path / "old", replace(BASE, text="# M05\n\nOld text.\n")))
    new = manifest(built(tmp_path / "new"))
    sql = load_sql(new)
    assert len(sql.splitlines()) == len(new["chunks"]) + 2  # one line per statement
    db = worker_db()
    db.executescript(load_sql(old))
    db.executescript(sql)
    db.executescript(sql)  # reloading the same release is harmless
    ids = [item["chunk_id"] for item in new["chunks"]]
    release, rows = served(db, ids)
    assert release == new["release"]
    assert sorted(rows) == sorted(tuple(item[field] for field in FIELDS) for item in new["chunks"])
    assert any("It's" in row[4] for row in rows)
    sample = "a'b\nc\r\nd;"  # the chunker joins lines, so check the literal rule directly
    assert db.execute("SELECT " + literal(sample)).fetchone()[0] == sample
    count = db.execute("SELECT COUNT(*) FROM ask_chunks").fetchone()[0]
    assert count == len(new["chunks"])  # old rows deleted only after the pointer moved


def test_worker_has_no_generation_and_takes_no_client_evidence():
    assert "env.AI" not in ROUTE and "generate" not in ROUTE
    keys = re.search(r"\.includes\(key\)\)", ROUTE)
    assert keys and "'evidence'" not in ROUTE


def test_worker_ask_route_runs_under_pinned_node():
    if not (NODE / "node.exe").exists() or not (ROOT / "worker/node_modules").exists():
        pytest.skip("Optional pinned Worker toolchain is not installed in core-only CI")
    env = os.environ | {"TEMP": str(ROOT / ".cache/tmp"), "TMP": str(ROOT / ".cache/tmp")}
    result = subprocess.run(
        [
            str(NODE / "node.exe"),
            "--experimental-strip-types",
            "--test",
            "tests/ask-route.test.mjs",
        ],
        cwd=ROOT / "worker",
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# pass 4" in result.stdout and "# fail 0" in result.stdout
