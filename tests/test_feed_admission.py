"""T242 exercises the Worker claim boundary before real collector fixtures."""

import hashlib
import hmac
import importlib
import json
import sys
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from atlas.config import load_state
from atlas.ingest.s09 import FEED
from atlas.ingest.schedule import defer, open_control

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
ORIGIN = "http://127.0.0.1:8787"
NOW = datetime(2026, 11, 5, 14, tzinfo=UTC)
KEY = "local-test-signing-key-for-feed-admission"


@pytest.fixture
def admission(monkeypatch):
    monkeypatch.setenv("ATLAS_INGEST_HMAC_KEY", KEY)
    return importlib.import_module("atlas.ingest.admission")


def reply(source, admitted):
    body = {"state": "ka", "source_id": source, "admitted": admitted}
    if not admitted:
        body["reason"] = "not_due"
    return httpx.Response(201 if admitted else 200, json=body)


def no_request(request):
    pytest.fail(f"Unexpected request to {request.url.host}")


def run(admission, root, worker, *, source="S09", provider=no_request, now=NOW):
    return admission.capture_admitted(
        root,
        source_id=source,
        origin=ORIGIN,
        max_documents=1,
        admission_transport=httpx.MockTransport(worker),
        provider_transport=httpx.MockTransport(provider),
        clock=lambda: now,
        sleep=lambda _: None,
    )


@pytest.mark.parametrize("source", ["S09", "S01"])
def test_signed_claim_precedes_real_capture_and_duplicate_has_no_provider(
    admission, tmp_path, source
):
    calls = []

    def worker(request):
        assert request.url == ORIGIN + "/internal/feed-check"
        assert request.method == "POST"
        assert request.headers["content-type"] == "application/json"
        assert request.headers["accept-encoding"] == "identity"
        assert json.loads(request.content) == {"state": "ka", "source_id": source}
        body_hash = hashlib.sha256(request.content).hexdigest()
        timestamp = request.headers["x-atlas-timestamp"]
        signed = f"{timestamp}\nPOST\n/internal/feed-check\n{body_hash}"
        assert (
            request.headers["x-atlas-signature"]
            == hmac.new(KEY.encode(), signed.encode(), hashlib.sha256).hexdigest()
        )
        first = "worker" not in calls
        calls.append("worker")
        return reply(source, first)

    def provider(request):
        assert calls[0] == "worker"
        calls.append("provider")
        if source == "S09":
            if str(request.url) == FEED:
                feed = ET.fromstring(
                    (FIXTURES / "s09_sachet_rss_india_2026-11-05.xml").read_bytes()
                )
                channel = feed.find("channel")
                for item in channel.findall("item"):
                    if not item.findtext("link").endswith("1793881986295019"):
                        channel.remove(item)
                body = ET.tostring(feed)
            else:
                name = f"s09_sachet_cap_{request.url.params['identifier']}.xml"
                body = (FIXTURES / name).read_bytes()
            media = "application/xml"
        else:
            name = (
                "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
                if request.url.path.endswith("meta.json")
                else "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
            )
            body = (FIXTURES / name).read_bytes()
            media = "application/json"
        return httpx.Response(200, content=body, headers={"content-type": media})

    root = tmp_path / "feeds"
    captured = run(admission, root, worker, source=source, provider=provider)
    assert captured["status"] == "captured", captured
    if source == "S09":
        assert captured["validated"] == 1
    assert calls == ["worker"] + ["provider"] * (2 if source == "S09" else 3)
    before = (root / "control.sqlite").read_bytes()
    assert run(admission, root, worker, source=source)["status"] == "not_due"
    assert calls.count("worker") == 2
    assert (root / "control.sqlite").read_bytes() == before


@pytest.mark.parametrize(
    ("status", "content", "headers"),
    [
        (201, b'{"admitted":true,"state":"ka","source_id":"S01"}', {}),
        (201, b'{"admitted":1,"state":"ka","source_id":"S09"}', {}),
        (201, b'{"admitted":false,"state":"ka","source_id":"S09"}', {}),
        (201, b'{"admitted":false,"admitted":true,"state":"ka","source_id":"S09"}', {}),
        (200, b'{"admitted":true,"state":"ka","source_id":"S09"}', {}),
        (201, b"x" * 4097, {}),
        (201, b"", {"content-encoding": "gzip"}),
        (307, b"private response", {"location": "https://example.invalid/"}),
        (401, b"private response", {}),
        (429, b"private response", {}),
        (503, b"private response", {}),
        (507, b"private response", {}),
    ],
)
def test_untrusted_reply_fails_once_before_local_state(
    admission, tmp_path, status, content, headers
):
    attempts = []

    def worker(request):
        attempts.append(request)
        return httpx.Response(status, content=content, headers=headers)

    root = tmp_path / "feeds"
    result = run(admission, root, worker)
    assert result["status"] == "failed"
    assert result["stage"] == "admission"
    assert len(attempts) == 1
    assert "private response" not in repr(result)
    assert not root.exists()


def test_deny_and_lost_acknowledgement_leave_feed_unopened(admission, tmp_path):
    root = tmp_path / "feeds"
    assert run(admission, root, lambda _: reply("S09", False))["status"] == "not_due"

    def timeout(request):
        raise httpx.ReadTimeout("private response", request=request)

    assert run(admission, root, timeout)["error_type"] == "ReadTimeout"
    assert not root.exists()


@pytest.mark.parametrize(
    "origin", ["https://127.0.0.1:8787", "http://localhost:8787", ORIGIN + "/"]
)
def test_invalid_origin_fails_before_worker_or_provider(admission, tmp_path, origin):
    result = admission.capture_admitted(
        tmp_path / "feeds",
        source_id="S09",
        origin=origin,
        admission_transport=httpx.MockTransport(no_request),
        provider_transport=httpx.MockTransport(no_request),
    )
    assert result == {"status": "failed", "stage": "admission", "error_type": "ValueError"}
    assert not (tmp_path / "feeds").exists()


def test_missing_key_fails_before_worker_or_provider(admission, tmp_path, monkeypatch):
    monkeypatch.delenv("ATLAS_INGEST_HMAC_KEY")
    assert run(admission, tmp_path / "feeds", no_request)["error_type"] == "ValueError"
    assert not (tmp_path / "feeds").exists()


def test_local_cooldown_still_applies_after_worker_admits(admission, tmp_path):
    root = tmp_path / "feeds"
    with closing(open_control(root / "control.sqlite")) as db:
        defer(db, "S09", (NOW + timedelta(hours=1)).timestamp())
    result = run(admission, root, lambda _: reply("S09", True))
    assert result["status"] == "deferred"
    assert not (root / "raw").exists()


def test_disabled_source_never_contacts_worker(admission, tmp_path, monkeypatch):
    state = load_state(ROOT / "configs/states/ka.yaml")
    state = state.model_copy(
        update={
            "sources": tuple(
                source.model_copy(update={"enabled": False})
                if source.source_id == "S09"
                else source
                for source in state.sources
            )
        }
    )
    monkeypatch.setattr(admission, "load_state", lambda _: state)
    root = tmp_path / "feeds"
    assert run(admission, root, no_request)["error_type"] == "SourceUnavailable"
    assert not root.exists()


def test_parent_runs_one_child_with_hard_deadline(admission, tmp_path, monkeypatch, capsys):
    command = []

    def child(args, *, timeout):
        command.extend(args)
        assert timeout == 150
        return {"status": "deadline", "coverage": "partial"}

    monkeypatch.setattr(admission, "run_bounded", child)
    monkeypatch.setattr(
        sys, "argv", ["admission", "--origin", ORIGIN, "--source", "S09", "--root", str(tmp_path)]
    )
    with pytest.raises(SystemExit, match="1"):
        admission.main()
    assert command[:4] == [sys.executable, "-m", "atlas.ingest.admission", "--child"]
    assert KEY not in repr(command)
    assert json.loads(capsys.readouterr().out)["status"] == "deadline"
