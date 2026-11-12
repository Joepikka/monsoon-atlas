"""T004 acceptance: 304 makes no duplicate; 429 waits per header; interrupted write leaves prior
data intact; secrets absent from logs. All tests are offline (mock or fixture transports)."""

import hashlib
import logging
import os
import random
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from atlas.contracts import Budget, FetchContext
from atlas.ingest import raw_store
from atlas.ingest.base import (
    BudgetExceeded,
    CircuitOpen,
    FetchError,
    HostNotAllowed,
    SourceUnavailable,
    TooLarge,
)
from atlas.ingest.http import TIMEOUT_S, Fetcher, FixtureTransport
from atlas.ingest.raw_store import RawStore

HOST = "api.open-meteo.com"
URL = f"https://{HOST}/v1/forecast"
NOW = datetime(2026, 11, 5, 6, 0, tzinfo=UTC)
SECRET = "sk-live-DO-NOT-LEAK-1234"


def ctx(tmp_path, source="S01", max_requests=50, max_bytes=1_000_000, secrets=None, run="run-1"):
    return FetchContext(
        source_id=source,
        state="ka",
        run_id=run,
        requested_at=NOW,
        budget=Budget(max_requests=max_requests, max_bytes=max_bytes),
        raw_root=tmp_path,
        secrets=secrets or {},
    )


def make(tmp_path, handler, sleeps=None, hosts=(HOST,)):
    store = RawStore(tmp_path / "raw")
    sleeps = [] if sleeps is None else sleeps
    fetcher = Fetcher(
        store,
        set(hosts),
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        rng=random.Random(42),
        clock=lambda: NOW,
    )
    return fetcher, store, sleeps


def stored_files(store):
    return [p for p in store.root.rglob("*") if p.is_file() and p.name != "ledger.jsonl"]


def test_timeout_and_user_agent():
    f, _, _ = make(Path("."), lambda r: httpx.Response(200))
    assert f.client.timeout.read == TIMEOUT_S
    assert f.client.headers["User-Agent"].startswith("MonsoonAtlas/")


def test_200_is_content_addressed_and_ledgered(tmp_path):
    body = b'{"rain_mm": 3.2}'
    f, store, _ = make(
        tmp_path,
        lambda r: httpx.Response(
            200, content=body, headers={"ETag": '"v1"', "Content-Type": "application/json"}
        ),
    )
    art = f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1", params={"latitude": "12.97"})
    assert art.sha256 == hashlib.sha256(body).hexdigest()
    assert art.path == store.root / "S01" / "2026-11-05" / f"{art.sha256}.json"
    assert art.path.read_bytes() == body
    assert art.source_url == f"{URL}?latitude=12.97"
    (entry,) = store.entries()
    assert entry["http"]["etag"] == '"v1"'


def test_304_makes_no_duplicate(tmp_path):
    seen = []

    def handler(request):
        seen.append(request.headers.get("If-None-Match"))
        if request.headers.get("If-None-Match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, content=b"data-v1", headers={"ETag": '"v1"'})

    f, store, _ = make(tmp_path, handler)
    first = f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    second = f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    assert seen == [None, '"v1"']
    assert second.response_status == 304
    assert (second.sha256, second.path) == (first.sha256, first.path)
    assert len(stored_files(store)) == 1
    assert [e["artifact"]["response_status"] for e in store.entries()] == [200, 304]


def test_identical_content_is_not_written_twice(tmp_path):
    f, store, _ = make(tmp_path, lambda r: httpx.Response(200, content=b"same"))
    a = f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    b = f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    assert a.path == b.path and len(stored_files(store)) == 1


def test_429_waits_per_retry_after_header(tmp_path):
    responses = iter(
        [httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, content=b"ok")]
    )
    f, _, sleeps = make(tmp_path, lambda r: next(responses))
    art = f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    assert sleeps == [7.0]
    assert art.response_status == 200


def test_no_retry_fetcher_stops_on_the_first_error(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    store = RawStore(tmp_path / "raw")
    f = Fetcher(store, {HOST}, transport=httpx.MockTransport(handler), retry_delays=())
    with pytest.raises(FetchError, match="HTTP 503"):
        f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    assert calls == [1]  # D109: providers that forbid retries get exactly one request


def test_retry_after_above_cap_fails(tmp_path):
    f, _, sleeps = make(tmp_path, lambda r: httpx.Response(429, headers={"Retry-After": "3600"}))
    with pytest.raises(FetchError, match="exceeds cap"):
        f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    assert sleeps == []


def test_retries_2_8_30_with_jitter_then_fails(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    f, _, sleeps = make(tmp_path, handler)
    with pytest.raises(FetchError, match="HTTP 503"):
        f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    assert len(calls) == 4  # 1 try + 3 retries
    for got, base in zip(sleeps, (2, 8, 30), strict=True):
        assert base <= got < base + 1


def test_interrupted_write_leaves_prior_data_intact(tmp_path, monkeypatch):
    store = RawStore(tmp_path / "raw")
    prior_path, _ = store.put(b"prior", "S01", NOW, "json")
    ledger_before = store.entries()

    def crash(src, dst):
        raise OSError("disk full / power cut during rename")

    monkeypatch.setattr(raw_store.os, "replace", crash)
    with pytest.raises(OSError):
        store.put(b"new-content", "S01", NOW, "json")
    monkeypatch.setattr(raw_store.os, "replace", os.replace)

    assert prior_path.read_bytes() == b"prior"
    assert [p.name for p in prior_path.parent.iterdir()] == [prior_path.name]  # no temp leftovers
    assert store.entries() == ledger_before


def test_torn_ledger_line_is_ignored(tmp_path):
    f, store, _ = make(tmp_path, lambda r: httpx.Response(200, content=b"x"))
    f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    with open(store.root / "ledger.jsonl", "a", encoding="utf-8") as fh:
        fh.write('{"artifact": {"sha')  # crash mid-append
    assert len(store.entries()) == 1


def test_secrets_absent_from_logs_ledger_and_urls(tmp_path, caplog):
    seen = []

    def handler(request):
        seen.append(request.url.params.get("MAP_KEY"))
        return httpx.Response(200, content=b"fires")

    f, store, _ = make(tmp_path, handler, hosts=("firms.modaps.eosdis.nasa.gov",))
    c = ctx(tmp_path, source="S25", secrets={"NASA_FIRMS_MAP_KEY": SECRET})
    url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    with caplog.at_level(logging.DEBUG):
        art = f.fetch_bytes(
            c,
            url,
            mapping_version="m1",
            params={"area": "KA"},
            secret_params={"MAP_KEY": "NASA_FIRMS_MAP_KEY"},
        )
    assert seen == [SECRET]  # the provider receives the key
    assert SECRET not in art.source_url
    assert SECRET not in art.model_dump_json()
    assert SECRET not in (store.root / "ledger.jsonl").read_text(encoding="utf-8")
    assert SECRET not in caplog.text


def test_secrets_absent_from_error_messages(tmp_path, caplog):
    def handler(request):
        raise httpx.ConnectError(f"cannot reach {request.url}", request=request)

    f, _, _ = make(tmp_path, handler, hosts=("firms.modaps.eosdis.nasa.gov",))
    c = ctx(tmp_path, source="S25", secrets={"NASA_FIRMS_MAP_KEY": SECRET})
    with caplog.at_level(logging.DEBUG), pytest.raises(FetchError) as err:
        f.fetch_bytes(
            c,
            "https://firms.modaps.eosdis.nasa.gov/api/area/csv",
            mapping_version="m1",
            secret_params={"MAP_KEY": "NASA_FIRMS_MAP_KEY"},
        )
    assert SECRET not in str(err.value) and err.value.__cause__ is None
    assert SECRET not in caplog.text


def test_missing_secret_is_source_unavailable(tmp_path):
    f, _, _ = make(tmp_path, lambda r: httpx.Response(200))
    with pytest.raises(SourceUnavailable):
        f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1", secret_params={"k": "MISSING_KEY"})


@pytest.mark.parametrize("url", ["https://evil.example.com/x", f"http://{HOST}/v1/forecast"])
def test_host_and_scheme_allowlist(tmp_path, url):
    calls = []
    f, _, _ = make(tmp_path, lambda r: calls.append(1) or httpx.Response(200))
    with pytest.raises(HostNotAllowed):
        f.fetch_bytes(ctx(tmp_path), url, mapping_version="m1")
    assert calls == []


def test_redirects_must_stay_on_allowlist(tmp_path):
    def handler(request):
        if request.url.host == HOST and request.url.path == "/old":
            return httpx.Response(302, headers={"Location": "https://evil.example.com/steal"})
        if request.url.path == "/moved":
            return httpx.Response(301, headers={"Location": f"https://{HOST}/new"})
        return httpx.Response(200, content=b"new")

    f, _, _ = make(tmp_path, handler)
    with pytest.raises(HostNotAllowed):
        f.fetch_bytes(ctx(tmp_path), f"https://{HOST}/old", mapping_version="m1")
    art = f.fetch_bytes(ctx(tmp_path, run="run-2"), f"https://{HOST}/moved", mapping_version="m1")
    assert art.path.read_bytes() == b"new"


def test_byte_budget(tmp_path):
    f, store, _ = make(tmp_path, lambda r: httpx.Response(200, content=b"x" * 2000))
    with pytest.raises(TooLarge):
        f.fetch_bytes(ctx(tmp_path, max_bytes=1000), URL, mapping_version="m1")
    assert stored_files(store) == []


def test_request_budget(tmp_path):
    f, _, _ = make(tmp_path, lambda r: httpx.Response(503))
    with pytest.raises(BudgetExceeded):
        f.fetch_bytes(ctx(tmp_path, max_requests=2), URL, mapping_version="m1")


def test_circuit_breaker_after_3_consecutive_failures(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404)

    f, _, _ = make(tmp_path, handler)
    for _ in range(3):
        with pytest.raises(FetchError):
            f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    with pytest.raises(CircuitOpen):
        f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    assert len(calls) == 3  # the open breaker sent nothing


def test_success_resets_breaker(tmp_path):
    responses = iter([httpx.Response(404), httpx.Response(404), httpx.Response(200, content=b"ok")])
    f, _, _ = make(tmp_path, lambda r: next(responses))
    for _ in range(2):
        with pytest.raises(FetchError):
            f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    assert f._failures["S01"] == 0


def test_offline_fixture_replay(tmp_path):
    fixtures = tmp_path / "fixtures"
    public = "https://firms.modaps.eosdis.nasa.gov/api/area/csv?area=KA"
    FixtureTransport.record(
        fixtures, public, b"lat,lon\n12.9,77.6\n", headers={"Content-Type": "text/csv"}
    )
    store = RawStore(tmp_path / "raw")
    f = Fetcher(
        store,
        {"firms.modaps.eosdis.nasa.gov"},
        transport=FixtureTransport(fixtures, secret_names=("MAP_KEY",)),
        sleep=lambda s: None,
        clock=lambda: NOW,
    )
    c = ctx(tmp_path, source="S25", secrets={"NASA_FIRMS_MAP_KEY": SECRET})
    art = f.fetch_bytes(
        c,
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv",
        mapping_version="m1",
        params={"area": "KA"},
        secret_params={"MAP_KEY": "NASA_FIRMS_MAP_KEY"},
    )
    assert art.media_type == "text/csv" and art.path.suffix == ".csv"
    with pytest.raises(FetchError):  # no fixture -> no network fallback
        f.fetch_bytes(c, "https://firms.modaps.eosdis.nasa.gov/other", mapping_version="m1")


def test_httpx_debug_logging_is_still_redacted(tmp_path, caplog):
    f, _, _ = make(
        tmp_path,
        lambda r: httpx.Response(200, content=b"ok"),
        hosts=("firms.modaps.eosdis.nasa.gov",),
    )
    c = ctx(tmp_path, source="S25", secrets={"NASA_FIRMS_MAP_KEY": SECRET})
    with caplog.at_level(logging.DEBUG, logger="httpx"):
        f.fetch_bytes(
            c,
            "https://firms.modaps.eosdis.nasa.gov/api/area/csv",
            mapping_version="m1",
            secret_params={"MAP_KEY": "NASA_FIRMS_MAP_KEY"},
        )
    assert "MAP_KEY=REDACTED" in caplog.text
    assert SECRET not in caplog.text


def test_append_after_torn_ledger_line_does_not_merge(tmp_path):
    f, store, _ = make(tmp_path, lambda r: httpx.Response(200, content=b"x"))
    f.fetch_bytes(ctx(tmp_path), URL, mapping_version="m1")
    with open(store.root / "ledger.jsonl", "a", encoding="utf-8") as fh:
        fh.write('{"artifact": {"sha')  # crash mid-append
    f.fetch_bytes(ctx(tmp_path, run="run-2"), URL, mapping_version="m1")
    assert len(store.entries()) == 2  # the torn line is dropped, the new entry survives
