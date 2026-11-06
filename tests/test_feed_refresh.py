"""T236: bounded local orchestration using genuine source fixtures."""

import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

import atlas.ingest.refresh as refresh_module
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.raw_store import RawStore
from atlas.ingest.refresh import refresh
from atlas.ingest.s09 import FEED
from atlas.ingest.s09_collect import run_bounded

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
IDENT = "1793881986295019"
NOW = datetime(2026, 11, 5, 14, tzinfo=UTC)


def feed():
    root = ET.fromstring((FIXTURES / "s09_sachet_rss_india_2026-11-05.xml").read_bytes())
    channel = root.find("channel")
    for item in channel.findall("item"):
        if not item.findtext("link", "").endswith(IDENT):
            channel.remove(item)
    return ET.tostring(root)


def run(root, *, now=NOW, handler=None):
    calls = []

    def response(request):
        calls.append(request)
        if handler:
            special = handler(request)
            if special is not None:
                return special
        body = (
            feed()
            if str(request.url) == FEED
            else (FIXTURES / f"s09_sachet_cap_{IDENT}.xml").read_bytes()
        )
        return httpx.Response(200, content=body, headers={"etag": '"test-validator"'})

    result = refresh(
        root,
        max_documents=1,
        clock=lambda: now,
        sleep=lambda _: None,
        transport=httpx.MockTransport(response),
    )
    return result, calls


def test_local_refresh_captures_and_prepares_actual_warning(tmp_path):
    result, calls = run(tmp_path)
    assert result["status"] == "prepared" and result["coverage"] == "partial"
    assert result["collection"]["validated"] == 1 and len(calls) == 2
    prepared = json.loads(Path(result["prepared"]["payload_path"]).read_text("utf-8"))
    assert len(prepared["snapshot"]["records"]) == 1
    assert prepared["snapshot"]["sources"][0]["status"] == "partial"
    assert not list(tmp_path.rglob("*.approval.json"))


def test_duplicate_admission_recovers_existing_preparation_without_provider_calls(tmp_path):
    first, _ = run(tmp_path)
    again, calls = run(tmp_path)
    assert not calls and again["collection"]["status"] == "not_due"
    assert again["prepared"]["sha256"] == first["prepared"]["sha256"]


def test_provider_cooldown_still_allows_dated_preparation_and_retains_real_clock(tmp_path):
    first, _ = run(tmp_path)

    def throttled(request):
        return httpx.Response(429, headers={"retry-after": "3600"})

    later = NOW + timedelta(minutes=15)
    deferred, calls = run(tmp_path, now=later, handler=throttled)
    assert deferred["status"] == "prepared" and deferred["collection"]["status"] == "deferred"
    assert len(calls) == 1
    snapshot = json.loads(Path(deferred["prepared"]["payload_path"]).read_text("utf-8"))["snapshot"]
    assert snapshot["sources"][0]["last_success_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert snapshot["records"][0]["fetched_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert Path(first["prepared"]["payload_path"]).exists()
    assert run(tmp_path, now=later + timedelta(minutes=15))[1] == []


def test_initial_throttle_cannot_create_a_fake_empty_snapshot(tmp_path):
    def throttled(request):
        return httpx.Response(429, headers={"retry-after": "3600"})

    result, calls = run(tmp_path, handler=throttled)
    assert result["status"] == "failed" and result["stage"] == "prepare"
    assert len(calls) == 1 and not (tmp_path / "prepared/prepared.json").exists()


def test_invalid_new_document_keeps_dated_last_good_warning(tmp_path):
    run(tmp_path)

    def malformed(request):
        if str(request.url) != FEED:
            return httpx.Response(200, content=b"<broken")

    result, _ = run(tmp_path, now=NOW + timedelta(minutes=15), handler=malformed)
    assert result["status"] == "prepared" and result["collection"]["failed"] == 1
    snapshot = json.loads(Path(result["prepared"]["payload_path"]).read_text("utf-8"))["snapshot"]
    assert len(snapshot["records"]) == 1 and snapshot["sources"][0]["status"] == "partial"
    assert snapshot["sources"][0]["last_success_at"] == NOW.isoformat().replace("+00:00", "Z")


def test_corrupt_retained_evidence_cannot_replace_prepared_head(tmp_path):
    first, _ = run(tmp_path)
    pointer = (tmp_path / "prepared/prepared.json").read_bytes()
    with sqlite3.connect(tmp_path / "control.sqlite") as db:
        raw = json.loads(db.execute("SELECT artifact_json FROM cap_documents").fetchone()[0])
    Path(raw["path"]).write_bytes(b"corrupt-test-copy")
    result, calls = run(tmp_path)
    assert result["status"] == "failed" and result["stage"] == "prepare" and not calls
    assert (tmp_path / "prepared/prepared.json").read_bytes() == pointer
    assert Path(first["prepared"]["payload_path"]).exists()


def test_parent_deadline_includes_preparation_and_keeps_completed_capture(tmp_path):
    script = tmp_path / "blocked_prepare.py"
    marker = tmp_path / "preparation-started"
    capture_root = tmp_path / "capture"
    script.write_text(
        "import time\nfrom pathlib import Path\nfrom datetime import UTC,datetime\n"
        "import httpx\nimport atlas.ingest.refresh as module\n"
        "from atlas.ingest.s09 import FEED\n"
        f"rss={feed()!r}\n"
        f"cap=Path({str(FIXTURES / f's09_sachet_cap_{IDENT}.xml')!r}).read_bytes()\n"
        "def blocked(*args,**kwargs):\n"
        f"    Path({str(marker)!r}).write_text('started')\n"
        "    time.sleep(30)\n"
        "module.prepare=blocked\n"
        "def response(request):\n"
        "    return httpx.Response(200,content=rss if str(request.url)==FEED else cap)\n"
        f"module.refresh(Path({str(capture_root)!r}),max_documents=1,"
        "clock=lambda:datetime(2026,11,5,14,tzinfo=UTC),sleep=lambda _:None,"
        "transport=httpx.MockTransport(response))\n",
        encoding="utf-8",
    )
    result = run_bounded([sys.executable, str(script)], timeout=5)
    assert result["status"] == "deadline" and marker.exists()
    with sqlite3.connect(capture_root / "control.sqlite") as db:
        assert db.execute(
            "SELECT COUNT(*) FROM cap_documents WHERE checked_at IS NOT NULL"
        ).fetchone() == (1,)
    recovered, calls = run(capture_root)
    assert recovered["status"] == "prepared" and not calls


def test_capture_io_failure_still_prepares_retained_data_without_new_validation_clock(
    tmp_path, monkeypatch
):
    run(tmp_path)

    def unavailable_ledger(*args, **kwargs):
        raise PermissionError("test-only ledger append failure")

    monkeypatch.setattr(RawStore, "record", unavailable_ledger)
    result, calls = run(tmp_path, now=NOW + timedelta(minutes=15))
    assert result["status"] == "prepared" and len(calls) == 1
    assert result["collection"]["status"] == "failed"
    assert result["collection"]["error_type"] == "PermissionError"
    snapshot = json.loads(Path(result["prepared"]["payload_path"]).read_text("utf-8"))["snapshot"]
    assert snapshot["sources"][0]["last_success_at"] == NOW.isoformat().replace("+00:00", "Z")


def test_disabled_capture_cannot_prepare_retained_source_data(tmp_path, monkeypatch):
    def disabled(*args, **kwargs):
        raise SourceUnavailable("source disabled in test configuration")

    def must_not_prepare(*args, **kwargs):
        raise AssertionError("Disabled source must stop before preparation")

    monkeypatch.setattr(refresh_module, "collect", disabled)
    monkeypatch.setattr(refresh_module, "prepare", must_not_prepare)
    result = refresh_module.refresh(tmp_path)
    assert result["status"] == "failed" and result["stage"] == "capture"
