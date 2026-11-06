"""T234: real CAP fixture replay; edited copies exercise failure paths only."""

import json
import sqlite3
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from atlas.ingest.s09 import FEED
from atlas.ingest.s09_collect import collect, run_bounded

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
IDS = ["1793881986295019", "1793880856139008", "1793871793334006"]
NOW = datetime(2026, 11, 6, 16, tzinfo=UTC)


def rss(ids=IDS):
    root = ET.fromstring((FIXTURES / "s09_sachet_rss_india_2026-11-05.xml").read_bytes())
    channel = root.find("channel")
    for item in channel.findall("item"):
        if not any(item.findtext("link", "").endswith(i) for i in ids):
            channel.remove(item)
    return ET.tostring(root)


def replay(root, *, now=NOW, limit=2, handler=None, ids=IDS):
    calls = []

    def response(request):
        calls.append(request)
        if handler:
            special = handler(request)
            if special is not None:
                return special
        body = (
            rss(ids)
            if str(request.url) == FEED
            else (FIXTURES / f"s09_sachet_cap_{request.url.params['identifier']}.xml").read_bytes()
        )
        return httpx.Response(200, content=body, headers={"etag": '"fixture-validator"'})

    result = collect(
        root,
        max_documents=limit,
        clock=lambda: now,
        sleep=lambda _: None,
        transport=httpx.MockTransport(response),
    )
    return result, calls


def documents(root):
    with sqlite3.connect(root / "control.sqlite") as db:
        db.row_factory = sqlite3.Row
        return {r["identifier"]: dict(r) for r in db.execute("SELECT * FROM cap_documents")}


def test_bounded_capture_retains_actual_bytes_and_never_publishes(tmp_path):
    result, calls = replay(tmp_path)
    assert result["coverage"] == "partial" and result["validated"] == 2
    assert result["pending"] == 1 and len(calls) == 3
    assert all("Polygon" not in str(r.url) for r in calls)
    for row in documents(tmp_path).values():
        if row["artifact_json"]:
            artifact = json.loads(row["artifact_json"])
            assert (
                Path(artifact["path"]).read_bytes()
                == (FIXTURES / f"s09_sachet_cap_{row['identifier']}.xml").read_bytes()
            )
    assert not list(tmp_path.rglob("*.approval.json"))
    assert not list(tmp_path.rglob("*.parquet"))


def test_shared_local_admission_survives_new_collector_and_utc_boundary(tmp_path):
    first = NOW.replace(hour=23, minute=59)
    assert replay(tmp_path, now=first)[1]
    result, calls = replay(tmp_path, now=first + timedelta(minutes=8))
    assert result["status"] == "not_due" and not calls
    assert replay(tmp_path, now=first - timedelta(hours=1))[1] == []
    assert replay(tmp_path, now=first + timedelta(minutes=15))[1]


def test_competing_process_connections_share_one_admission(tmp_path):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: replay(tmp_path, limit=1), range(2)))
    assert sum(bool(calls) for _, calls in results) == 1
    assert sorted(result["status"] for result, _ in results) == ["captured", "not_due"]


def test_not_due_result_still_reports_retained_pending_work(tmp_path):
    replay(tmp_path, limit=1)
    result, calls = replay(tmp_path)
    assert result["pending"] == 2 and not calls


def test_feed_304_does_not_refresh_unchecked_documents_or_content_clock(tmp_path):
    replay(tmp_path, limit=3)
    before = documents(tmp_path)

    def unchanged(request):
        assert request.headers["if-none-match"] == '"fixture-validator"'
        return httpx.Response(304)

    result, calls = replay(tmp_path, now=NOW + timedelta(minutes=15), limit=1, handler=unchanged)
    after = documents(tmp_path)
    checked = calls[1].url.params["identifier"]
    assert result["validated"] == 1 and len(calls) == 2
    assert after[checked]["checked_at"] != before[checked]["checked_at"]
    assert all(after[i]["content_fetched_at"] == before[i]["content_fetched_at"] for i in IDS)
    assert all(after[i]["checked_at"] == before[i]["checked_at"] for i in IDS if i != checked)


def test_malformed_changed_cap_preserves_last_good_checkpoint(tmp_path):
    replay(tmp_path, limit=3)
    before = documents(tmp_path)

    def broken(request):
        if request.url.params.get("identifier") == IDS[0]:
            return httpx.Response(200, content=b"<broken", headers={"etag": '"broken-copy"'})

    result, _ = replay(tmp_path, now=NOW + timedelta(minutes=15), limit=3, handler=broken)
    after = documents(tmp_path)
    assert result["failed"] == 1
    for key in ("checked_at", "artifact_json", "content_fetched_at", "validated_version"):
        assert after[IDS[0]][key] == before[IDS[0]][key]
    assert any(p.read_bytes() == b"<broken" for p in (tmp_path / "raw").rglob("*.bin"))


def test_mutable_cap_url_is_rechecked_even_with_unchanged_rss_item(tmp_path):
    replay(tmp_path, ids=[IDS[0]], limit=1)
    before = documents(tmp_path)[IDS[0]]

    def changed(request):
        if str(request.url) == FEED:
            return httpx.Response(304)
        assert request.headers["if-none-match"] == '"fixture-validator"'
        # Whitespace-only test copy changes actual bytes, not analytical observations.
        body = (FIXTURES / f"s09_sachet_cap_{IDS[0]}.xml").read_bytes() + b"\n"
        return httpx.Response(200, content=body, headers={"etag": '"changed-test-copy"'})

    result, _ = replay(tmp_path, now=NOW + timedelta(minutes=15), ids=[IDS[0]], handler=changed)
    after = documents(tmp_path)[IDS[0]]
    assert result["validated"] == 1 and after["version"] == before["version"]
    assert after["artifact_json"] != before["artifact_json"]
    assert after["content_fetched_at"] != before["content_fetched_at"]
    assert Path(json.loads(before["artifact_json"])["path"]).exists()


def test_feed_bytes_are_hash_checked_before_queue_changes(tmp_path):
    replay(tmp_path, limit=1)
    entry = next(
        json.loads(line)
        for line in (tmp_path / "raw/ledger.jsonl").read_text().splitlines()
        if json.loads(line)["artifact"]["source_url"] == FEED
    )
    Path(entry["artifact"]["path"]).write_bytes(rss([]))  # Simulated local corruption only.

    def unchanged(request):
        return httpx.Response(304)

    result, calls = replay(tmp_path, now=NOW + timedelta(minutes=15), handler=unchanged)
    assert result["status"] == "failed" and len(calls) == 1
    assert all(row["in_feed"] for row in documents(tmp_path).values())


def test_old_pending_document_is_not_starved_and_disappearing_items_are_retained(tmp_path):
    replay(tmp_path, limit=1)
    for n in range(1, 4):
        replay(tmp_path, now=NOW + timedelta(minutes=15 * n), limit=1)
    assert all(r["checked_at"] for r in documents(tmp_path).values())
    replay(tmp_path, now=NOW + timedelta(hours=1), ids=[])
    assert len(documents(tmp_path)) == 3


@pytest.mark.parametrize("retry_after", ["3600", "Fri, 06 Nov 2026 17:00:00 GMT"])
def test_retry_after_survives_process_restart_without_another_provider_call(tmp_path, retry_after):
    def throttled(request):
        return httpx.Response(429, headers={"retry-after": retry_after})

    result, calls = replay(tmp_path, handler=throttled)
    assert result["status"] == "deferred" and len(calls) == 1
    result, calls = replay(tmp_path, now=NOW + timedelta(minutes=30))
    assert result["status"] == "deferred" and not calls
    assert replay(tmp_path, now=NOW + timedelta(hours=1))[1]


def test_terminal_retry_after_is_persisted_even_when_no_retry_remains(tmp_path):
    responses = iter([503, 503, 503, 429])

    def terminal(request):
        status = next(responses)
        return httpx.Response(status, headers={"retry-after": "3600"} if status == 429 else {})

    result, calls = replay(tmp_path, limit=4, handler=terminal)
    assert result["status"] == "deferred" and len(calls) == 4
    result, calls = replay(tmp_path, now=NOW + timedelta(minutes=30))
    assert result["status"] == "deferred" and not calls
    assert replay(tmp_path, now=NOW + timedelta(hours=1))[1]


def test_cooldown_is_saved_from_headers_before_a_response_body_can_block(tmp_path):
    class UnreadBody(httpx.SyncByteStream):
        def __iter__(self):
            raise AssertionError("A retry response body must not delay saving Retry-After")
            yield b""  # Make this a stream; never reached.

    def throttled(request):
        return httpx.Response(429, headers={"retry-after": "3600"}, stream=UnreadBody())

    result, _ = replay(tmp_path, handler=throttled)
    assert result["status"] == "deferred"
    assert replay(tmp_path, now=NOW + timedelta(minutes=30))[1] == []


@pytest.mark.parametrize("message_type", ["Cancel", "Update"])
def test_header_only_control_is_retained_without_invented_row(tmp_path, message_type):
    def cancellation(request):
        if str(request.url) == FEED:
            return None
        # Test-only mutation of the actual captured CAP; no synthetic observation.
        root = ET.fromstring((FIXTURES / f"s09_sachet_cap_{IDS[0]}.xml").read_bytes())
        ns = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
        root.find("cap:msgType", ns).text = message_type
        for info in root.findall("cap:info", ns):
            root.remove(info)
        return httpx.Response(200, content=ET.tostring(root))

    result, _ = replay(tmp_path, ids=[IDS[0]], handler=cancellation)
    row = documents(tmp_path)[IDS[0]]
    assert result["validated"] == 1
    header = json.loads(row["header_json"])
    assert header["msg_type"] == message_type and header["references"]
    assert "event" not in header and "severity" not in header


def test_invalid_sent_time_fails_even_for_non_karnataka_cap(tmp_path):
    def naive(request):
        if str(request.url) == FEED:
            return None
        root = ET.fromstring((FIXTURES / f"s09_sachet_cap_{IDS[1]}.xml").read_bytes())
        root.find("{urn:oasis:names:tc:emergency:cap:1.2}sent").text = "2026-11-05T12:00:00"
        return httpx.Response(200, content=ET.tostring(root))

    result, _ = replay(tmp_path, ids=[IDS[1]], handler=naive)
    assert result["failed"] == 1 and documents(tmp_path)[IDS[1]]["checked_at"] is None


def test_hard_deadline_kills_and_reaps_http_only_child():
    started = time.monotonic()
    result = run_bounded([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.15)
    assert result["status"] == "deadline" and time.monotonic() - started < 5


def test_killed_child_keeps_completed_checkpoint_and_raw_evidence(tmp_path):
    # A real child validates one captured document, then blocks on a second HTTP
    # attempt. The parent timeout must preserve the committed first checkpoint.
    script = tmp_path / "interrupted.py"
    script.write_text(
        "import time\nfrom pathlib import Path\nimport httpx\n"
        "from datetime import UTC, datetime\n"
        "from atlas.ingest.s09_collect import collect\n"
        "from atlas.ingest.s09 import FEED\n"
        f"rss = {rss()!r}\nfixtures = Path({str(FIXTURES)!r})\n"
        "count = 0\n"
        "def handler(request):\n"
        "    global count\n"
        "    if str(request.url) == FEED: return httpx.Response(200, content=rss)\n"
        "    count += 1\n"
        "    if count == 2: time.sleep(30)\n"
        "    name = 's09_sachet_cap_' + request.url.params['identifier'] + '.xml'\n"
        "    return httpx.Response(200, content=(fixtures / name).read_bytes())\n"
        f"collect(Path({str(tmp_path / 'capture')!r}), max_documents=3, "
        "clock=lambda:datetime(2026,11,6,16,tzinfo=UTC), sleep=lambda _:None, "
        "transport=httpx.MockTransport(handler))\n",
        encoding="utf-8",
    )
    result = run_bounded([sys.executable, str(script)], timeout=5)
    rows = documents(tmp_path / "capture")
    assert result["status"] == "deadline"
    completed = [row for row in rows.values() if row["checked_at"]]
    assert len(completed) == 1
    assert Path(json.loads(completed[0]["artifact_json"])["path"]).is_file()
    assert replay(tmp_path / "capture")[1] == []


def test_bounded_launcher_uses_argument_list_and_no_shell(monkeypatch):
    def done(command, **kwargs):
        assert isinstance(command, list) and kwargs["shell"] is False
        assert kwargs["timeout"] == 120
        return subprocess.CompletedProcess(command, 0, stdout='{"status":"captured"}', stderr="")

    monkeypatch.setattr(subprocess, "run", done)
    assert run_bounded([sys.executable, "-m", "atlas.ingest.s09_collect"], timeout=120) == {
        "status": "captured"
    }


@pytest.mark.parametrize("limit", [0, 31])
def test_invalid_admission_limit_fails_before_network(tmp_path, limit):
    with pytest.raises(ValueError, match="1.*30"):
        replay(tmp_path, limit=limit)
