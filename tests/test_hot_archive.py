"""T044 acceptance: the daily export verifies every stored byte before archiving, writes immutable
Parquet plus a manifest in one commit, reads the commit back, and a restored archive reproduces
every exported snapshot ID. Tampered rows and a failed read-back stop the run; nothing is ever
deleted from the Worker (no purge exists, D184)."""

import base64
import gzip
import hashlib
import hmac
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from atlas.data.hot_export import (
    MANIFEST,
    ArchiveError,
    LocalArchive,
    forecast,
    run,
)

ROOT = Path(__file__).resolve().parents[1]
KEY = "k" * 40
ORIGIN = "https://monsoon-atlas-hot.monsoon-atlas.workers.dev"
CAP = json.loads((ROOT / "web/tests/fixtures/sachet-ka-point.json").read_text("utf-8"))
WEATHER = json.loads(
    (ROOT / "web/tests/fixtures/openmeteo-temperature-point.json").read_text("utf-8")
)


def stored(source_id: str, record: dict, ms: int) -> dict:
    snapshot = {
        "schema_version": 1,
        "state": "ka",
        "as_of": record["fetched_at"],
        "records": [record],
    }
    canonical = json.dumps({"source_id": source_id, "snapshot": snapshot}, sort_keys=True).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    return {
        "id": digest,
        "source_id": source_id,
        "as_of_ms": ms,
        "sha256": digest,
        "payload_gzip_base64": base64.b64encode(gzip.compress(canonical, mtime=0)).decode(),
    }


ROWS = [
    stored("S09", CAP, 1000),
    stored("S01", WEATHER, 2000),
    stored("S09", CAP | {"id": "x"}, 3000),
]


def worker(rows: list[dict], seen: list[dict], allocated: int = 1_000_000):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/export" and request.method == "POST"
        ts = request.headers["X-Atlas-Timestamp"]
        message = f"{ts}\nPOST\n/internal/export\n{hashlib.sha256(request.content).hexdigest()}"
        good = hmac.new(KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
        assert request.headers["X-Atlas-Signature"] == good
        cursor = json.loads(request.content)
        seen.append(cursor)
        after = [
            r for r in rows if (r["as_of_ms"], r["id"]) > (cursor["after_ms"], cursor["after_id"])
        ]
        page, more = after[:2], len(after) > 2
        last = page[-1] if page else None
        nxt = {"after_ms": last["as_of_ms"], "after_id": last["id"]} if last else cursor
        body = {
            "schema_version": 1,
            "state": "ka",
            "rows": page,
            "more": more,
            "next": nxt,
            "capacity": {"allocated_bytes": allocated, "size_after": 1, "cap_bytes": 400_000_000},
        }
        return httpx.Response(200, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def restored_ids(root: Path) -> set[str]:
    manifest = json.loads((root / MANIFEST).read_text("utf-8"))
    ids = set()
    for f in manifest["files"]:
        data = (root / f["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == f["sha256"]
        table = pq.read_table(io.BytesIO(data))
        for row in table.to_pylist():
            canonical = gzip.decompress(row["payload_gzip"])
            assert hashlib.sha256(canonical).hexdigest() == row["sha256"] == row["snapshot_id"]
            assert canonical.decode() == row["canonical_json"]
            ids.add(row["snapshot_id"])
    return ids


def test_export_pages_verifies_writes_and_restores_every_snapshot(tmp_path):
    seen = []
    result = run(LocalArchive(tmp_path), worker(ROWS, seen), ORIGIN, KEY)
    assert result["status"] == "archived" and result["snapshots"] == 3
    assert len(seen) == 2 and seen[0] == {"after_ms": -1, "after_id": ""}  # two pages
    assert restored_ids(tmp_path) == {r["id"] for r in ROWS}
    manifest = json.loads((tmp_path / MANIFEST).read_text("utf-8"))
    assert manifest["cursor"] == {"after_ms": 3000, "after_id": ROWS[2]["id"]}
    assert {f["source_id"] for f in manifest["files"]} == {"S01", "S09"}
    assert manifest["purge"].startswith("none")


def test_next_run_resumes_from_the_cursor_and_keeps_old_files(tmp_path):
    archive = LocalArchive(tmp_path)
    run(archive, worker(ROWS[:2], []), ORIGIN, KEY, now=datetime(2026, 11, 12, tzinfo=UTC))
    seen = []
    later = run(archive, worker(ROWS, seen), ORIGIN, KEY, now=datetime(2026, 11, 13, tzinfo=UTC))
    assert later["snapshots"] == 1 and seen[0]["after_ms"] == 2000
    assert restored_ids(tmp_path) == {r["id"] for r in ROWS}
    assert len(json.loads((tmp_path / MANIFEST).read_text("utf-8"))["files"]) == 3


def test_tampered_or_unknown_rows_stop_before_anything_is_written(tmp_path):
    bad = dict(ROWS[0])
    bad["payload_gzip_base64"] = base64.b64encode(gzip.compress(b'{"x":1}')).decode()
    with pytest.raises(ArchiveError, match="SHA-256"):
        run(LocalArchive(tmp_path), worker([bad], []), ORIGIN, KEY)
    other = dict(ROWS[0], source_id="S23")
    with pytest.raises(ArchiveError, match="unknown source"):
        run(LocalArchive(tmp_path), worker([other], []), ORIGIN, KEY)
    assert not any(tmp_path.iterdir())


def test_failed_read_back_fails_the_run(tmp_path):
    class Lossy(LocalArchive):
        def read_at(self, path, revision):
            return b"corrupted"

    with pytest.raises(ArchiveError, match="read-back"):
        run(Lossy(tmp_path), worker(ROWS, []), ORIGIN, KEY)


def test_capacity_forecast_uses_recorded_growth():
    history = [
        {
            "at": "2026-11-12T00:00:00+00:00",
            "allocated_bytes": 10_000_000,
            "cap_bytes": 400_000_000,
        },
        {
            "at": "2026-11-14T00:00:00+00:00",
            "allocated_bytes": 30_000_000,
            "cap_bytes": 400_000_000,
        },
    ]
    assert forecast(history) == {"bytes_per_day": 10_000_000, "days_to_cap": 37.0}
    assert forecast(history[:1]) == {"bytes_per_day": None, "days_to_cap": None}


def test_cli_refuses_an_untrusted_origin_without_network(monkeypatch, capsys, tmp_path):
    from atlas.data import hot_export

    monkeypatch.setenv("ATLAS_INGEST_HMAC_KEY", KEY)
    monkeypatch.setenv("ATLAS_HOT_ORIGIN", ORIGIN)
    code = hot_export.main(["--origin", "https://evil.example", "--local-dir", str(tmp_path)])
    assert code == 1 and json.loads(capsys.readouterr().out)["error_type"] == "ValueError"


def test_archive_workflow_is_daily_read_only_and_masks_the_repository():
    import yaml

    flow = yaml.safe_load((ROOT / ".github/workflows/archive.yml").read_text("utf-8"))
    assert flow[True]["schedule"] == [{"cron": "47 2 * * *"}] and "workflow_dispatch" in flow[True]
    assert flow["permissions"] == {"contents": "read"}
    job = flow["jobs"]["export"]
    (step,) = [s for s in job["steps"] if "secrets." in json.dumps(s)]
    assert step["run"].startswith('echo "::add-mask::$HF_ARCHIVE_REPO"')
    assert "atlas.data.hot_export" in step["run"] and "--hf-repo" in step["run"]
    install = next(s for s in job["steps"] if s.get("name", "").startswith("Install"))
    assert "--require-hashes" in install["run"] and "requirements/archive.txt" in install["run"]
