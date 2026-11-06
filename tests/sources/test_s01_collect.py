"""T237 paired acquisition; genuine S01 fixtures and explicitly edited failure copies."""

import hashlib
import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

import atlas.ingest.s01_collect as module
from atlas.config import load_state
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s01_collect import collect_weather
from atlas.ingest.schedule import run_bounded

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests/fixtures"
META = FIX / "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
FORECAST = FIX / "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
NOW = datetime(2026, 11, 5, 14, tzinfo=UTC)


def capture(root, *, now=NOW, handler=None):
    calls, sleeps = [], []

    def response(request):
        calls.append(request)
        if handler:
            special = handler(request)
            if special is not None:
                return special
        meta = request.url.path.endswith("meta.json")
        if request.headers.get("if-none-match"):
            return httpx.Response(304)
        return httpx.Response(
            200,
            content=(META if meta else FORECAST).read_bytes(),
            headers={
                "content-type": "application/json",
                "etag": '"meta-fixture"' if meta else '"forecast-fixture"',
            },
        )

    result = collect_weather(
        root, clock=lambda: now, sleep=sleeps.append, transport=httpx.MockTransport(response)
    )
    return result, calls, sleeps


def receipt(result):
    path = Path(result["receipt_path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == result["receipt_sha256"]
    return json.loads(path.read_text("utf-8"))


def test_capture_keeps_verified_profile_and_all_three_actual_artifacts(tmp_path):
    result, calls, sleeps = capture(tmp_path)
    assert result["status"] == "captured" and result["coverage"] == "partial"
    assert len(calls) == 3 and sleeps == [5.0, 5.0, 5.0]
    assert calls[0].url.path.endswith("meta.json") and calls[2].url.path.endswith("meta.json")
    assert calls[1].url.params["models"] == "ecmwf_ifs025"
    assert calls[1].url.params["latitude"] == "12.97"
    pair = receipt(result)
    assert pair["requested_points"] == [[12.97, 77.59]]
    assert pair["returned_points"] == [[13.0, 77.5]]
    assert [item["role"] for item in pair["requests"]] == [
        "metadata_before",
        "forecast",
        "metadata_after",
    ]
    assert [item["artifact"]["response_status"] for item in pair["requests"]] == [200, 200, 304]
    assert pair["model_initialization"] == "2026-11-05T00:00:00Z"
    for item in pair["requests"]:
        artifact = item["artifact"]
        assert hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest() == artifact["sha256"]
    assert not list(tmp_path.rglob("*.approval.json"))


def test_four_admitted_runs_in_24_hours_use_twelve_nominal_requests(tmp_path):
    total = 0
    for hour in range(24):
        result, calls, _ = capture(tmp_path, now=NOW + timedelta(hours=hour))
        total += len(calls)
        assert result["status"] == ("captured" if hour % 6 == 0 else "not_due")
    assert total == 12


def test_attempt_budget_stops_at_five_and_keeps_prior_pair(tmp_path):
    capture(tmp_path)
    head = (tmp_path / "weather/latest-pair.json").read_bytes()
    seen = 0

    def limited(request):
        nonlocal seen
        seen += 1
        # Complete before/forecast, then exhaust the remaining attempt budget on after metadata.
        if seen >= 3:
            return httpx.Response(503)

    result, calls, _ = capture(tmp_path, now=NOW + timedelta(hours=6), handler=limited)
    assert result["status"] == "failed" and len(calls) == 5
    assert (tmp_path / "weather/latest-pair.json").read_bytes() == head
    assert len(receipt(result)["requests"]) == 2


@pytest.mark.parametrize("failure", ["run_changed", "unsettled", "missing", "bad_grid", "expired"])
def test_unusable_pair_cannot_replace_last_validated_head(tmp_path, failure):
    capture(tmp_path)
    head = (tmp_path / "weather/latest-pair.json").read_bytes()
    later = NOW + timedelta(hours=6)
    meta_count = 0

    def changed(request):
        nonlocal meta_count
        is_meta = request.url.path.endswith("meta.json")
        if is_meta:
            meta_count += 1
        if failure == "run_changed" and is_meta and meta_count == 2:
            body = json.loads(META.read_bytes())
            body["last_run_initialisation_time"] += 21600
        elif failure == "unsettled" and is_meta:
            body = json.loads(META.read_bytes())
            body["last_run_availability_time"] = int(later.timestamp())
        elif failure == "missing" and not is_meta:
            body = json.loads(FORECAST.read_bytes())
            body["hourly"]["temperature_2m"] = [None] * len(body["hourly"]["time"])
        elif failure == "bad_grid" and not is_meta:
            body = json.loads(FORECAST.read_bytes())
            body["latitude"] = 13.25
        else:
            return None
        return httpx.Response(200, json=body)  # Edited failure copy; not an observation.

    at = NOW + timedelta(days=30) if failure == "expired" else later
    result, _, _ = capture(tmp_path, now=at, handler=changed)
    assert result["status"] in {"failed", "unavailable"}
    assert (tmp_path / "weather/latest-pair.json").read_bytes() == head
    assert receipt(result)["outcome"] != "validated"


def test_source_specific_retry_after_does_not_throttle_s09(tmp_path):
    def throttled(request):
        return httpx.Response(429, headers={"retry-after": "3600"})

    result, calls, _ = capture(tmp_path, handler=throttled)
    assert result["status"] == "deferred" and len(calls) == 1
    assert capture(tmp_path, now=NOW + timedelta(minutes=30))[1] == []
    with sqlite3.connect(tmp_path / "control.sqlite") as db:
        retry = db.execute("SELECT retry_at FROM local_admission WHERE source='S01'").fetchone()[0]
        assert retry == (NOW + timedelta(hours=1)).timestamp()
        assert db.execute("SELECT * FROM local_admission WHERE source='S09'").fetchone() is None


def test_disabled_weather_source_fails_before_any_request(tmp_path, monkeypatch):
    state = load_state(ROOT / "configs/states/ka.yaml")
    disabled = state.model_copy(
        update={
            "sources": tuple(
                source.model_copy(update={"enabled": False})
                if source.source_id == "S01"
                else source
                for source in state.sources
            )
        }
    )
    monkeypatch.setattr(module, "load_state", lambda _: disabled)
    with pytest.raises(SourceUnavailable):
        capture(tmp_path)
    assert not (tmp_path / "control.sqlite").exists()


def test_revalidation_keeps_original_receipt_and_exact_source_bytes(tmp_path):
    first, _, _ = capture(tmp_path)
    first_bytes = Path(first["receipt_path"]).read_bytes()
    later, _, _ = capture(tmp_path, now=NOW + timedelta(hours=6))
    old = receipt(first)["requests"][1]["artifact"]
    checked = receipt(later)["requests"][1]["artifact"]
    assert checked["response_status"] == 304
    assert (checked["sha256"], checked["path"]) == (old["sha256"], old["path"])
    assert checked["fetched_at"] != old["fetched_at"]
    assert Path(first["receipt_path"]).read_bytes() == first_bytes
    assert receipt(later)["model_initialization"] == receipt(first)["model_initialization"]


def test_older_model_response_cannot_roll_latest_pair_back(tmp_path):
    capture(tmp_path)
    original = (tmp_path / "weather/latest-pair.json").read_bytes()

    def older(request):
        if request.url.path.endswith("meta.json"):
            body = json.loads(META.read_bytes())
            body["last_run_initialisation_time"] -= 21600
            return httpx.Response(200, json=body)  # Metadata-only rollback test copy.

    result, _, _ = capture(tmp_path, now=NOW + timedelta(hours=6), handler=older)
    assert result["status"] == "older_run"
    assert (tmp_path / "weather/latest-pair.json").read_bytes() == original
    assert receipt(result)["outcome"] == "validated"


def test_killed_incomplete_fetch_preserves_metadata_without_fabricating_a_pair(tmp_path):
    script = tmp_path / "interrupted_weather.py"
    capture_root = tmp_path / "capture"
    script.write_text(
        "import time\nfrom pathlib import Path\nfrom datetime import UTC,datetime\n"
        "import httpx\nfrom atlas.ingest.s01_collect import collect_weather\n"
        f"meta=Path({str(META)!r}).read_bytes()\n"
        "def response(request):\n"
        "    if not request.url.path.endswith('meta.json'): time.sleep(30)\n"
        "    return httpx.Response(200,content=meta,headers={'content-type':'application/json'})\n"
        f"collect_weather(Path({str(capture_root)!r}),clock=lambda:datetime(2026,11,5,14,tzinfo=UTC),"
        "sleep=lambda _:None,transport=httpx.MockTransport(response))\n",
        encoding="utf-8",
    )
    result = run_bounded([sys.executable, str(script)], timeout=5)
    assert result["status"] == "deadline"
    assert not (capture_root / "weather/latest-pair.json").exists()
    assert (capture_root / "weather/raw/ledger.jsonl").is_file()
    assert capture(capture_root)[1] == []  # The admission survives interruption.


@pytest.mark.parametrize("damage", ["pointer", "previous_receipt"])
def test_bad_prior_head_does_not_lose_new_completed_pairing(tmp_path, damage):
    first, _, _ = capture(tmp_path)
    head = tmp_path / "weather/latest-pair.json"
    if damage == "pointer":
        head.write_bytes(b"{damaged-pointer")
    else:
        Path(first["receipt_path"]).write_bytes(b"damaged-receipt")
    previous_head = head.read_bytes()
    old_count = len(list((tmp_path / "weather/pairs").rglob("*.json")))
    result, calls, _ = capture(tmp_path, now=NOW + timedelta(hours=6))
    assert result["status"] == "failed" and len(calls) == 3
    assert len(list((tmp_path / "weather/pairs").rglob("*.json"))) == old_count + 1
    assert head.read_bytes() == previous_head
    pair = receipt(result)
    assert pair["outcome"] == "validated" and len(pair["requests"]) == 3
