"""T227: resumable real-report census; failures never become empty observations."""

import hashlib
import json
import runpy
from datetime import date
from pathlib import Path

import httpx
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore

ROOT = Path(__file__).resolve().parents[2]
API = runpy.run_path(str(ROOT / "scripts/s32_history.py"))
FIX = ROOT / "tests/fixtures"
CONFIG = load_state(ROOT / "configs/states/kl.yaml").source("S32")


def setup(tmp_path, handler):
    fetcher = Fetcher(
        RawStore(tmp_path / "raw"),
        {"kseb.in"},
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    ctx = FetchContext(
        source_id="S32",
        state="kl",
        run_id="history-test",
        requested_at="2026-11-06T00:00:00Z",
        raw_root=tmp_path / "raw",
        budget=Budget(max_requests=20, max_bytes=1024**2),
    )
    return fetcher, ctx


def test_empty_real_report_and_resume_do_not_refetch(tmp_path):
    requests = []

    def handler(req):
        requests.append(req)
        return httpx.Response(
            200,
            content=(FIX / "s32_kseb_e04.html").read_bytes(),
            headers={"content-type": "text/html"},
        )

    fetcher, ctx = setup(tmp_path, handler)
    out = tmp_path / "census.json"
    result = API["audit"](date(2023, 10, 25), date(2023, 10, 25), out, CONFIG, fetcher, ctx)
    assert result["complete"] and result["days"][0]["outcome"] == "empty"
    assert result["days"][0]["rows"] == 0
    assert len(requests) == 1
    assert json.loads(out.read_text())["days"][0]["artifact"]["sha256"]
    again = API["audit"](date(2023, 10, 25), date(2023, 10, 25), out, CONFIG, fetcher, ctx)
    assert again["complete"] and len(requests) == 1


def test_parse_failure_is_not_empty_and_raw_evidence_is_retained(tmp_path):
    fetcher, ctx = setup(
        tmp_path,
        lambda r: httpx.Response(
            200,
            content=(FIX / "s32_kseb_e02.html").read_bytes(),
            headers={"content-type": "text/html"},
        ),
    )
    result = API["audit"](
        date(2023, 10, 25), date(2023, 10, 25), tmp_path / "c.json", CONFIG, fetcher, ctx
    )
    row = result["days"][0]
    assert not result["complete"] and row["outcome"] == "failed"
    assert row["artifact"]["sha256"] and "date" in row["error"]


def test_three_failures_stop_requests_and_mark_remaining_unattempted(tmp_path):
    requests = []

    def handler(req):
        requests.append(req)
        return httpx.Response(404)

    fetcher, ctx = setup(tmp_path, handler)
    result = API["audit"](
        date(2024, 1, 1), date(2024, 1, 5), tmp_path / "c.json", CONFIG, fetcher, ctx
    )
    assert [r["outcome"] for r in result["days"]] == ["failed"] * 3 + ["not_attempted"] * 2
    assert not result["complete"] and len(requests) == 3


def test_pacer_spaces_http_attempts_including_retries():
    ticks, sleeps = [10.0], []

    def sleep(seconds):
        sleeps.append(seconds)
        ticks[0] += seconds

    pace = API["pacer"](3.0, clock=lambda: ticks[0], sleep=sleep)
    pace(None)
    ticks[0] += 1.0
    pace(None)
    pace(None)
    assert sleeps == [2.0, 3.0]


def test_relative_legacy_ledger_path_is_serialized_under_raw_root(tmp_path, monkeypatch):
    fetcher, ctx = setup(
        tmp_path,
        lambda r: httpx.Response(
            200,
            content=(FIX / "s32_kseb_e04.html").read_bytes(),
            headers={"content-type": "text/html"},
        ),
    )
    from atlas.contracts import RawArtifact

    raw = fetcher.fetch_bytes(
        ctx, "https://kseb.in/dashboard/view/waterlevel?date=2023-10-25", mapping_version="s32-v1"
    )
    raw = RawArtifact.model_validate(raw.model_dump() | {"path": raw.path.relative_to(tmp_path)})
    monkeypatch.chdir(tmp_path)
    stored = API["public_artifact"](raw, ctx.raw_root)
    assert not Path(stored["path"]).is_absolute()
    assert (ctx.raw_root / stored["path"]).read_bytes() == raw.path.read_bytes()


def test_full_census_accounts_for_each_real_date():
    path = FIX / "s32_history_manifest.json"
    assert path.exists(), "Run the real T227 census before claiming completion"
    census = json.loads(path.read_text("utf-8"))
    assert census["start"] == "2024-08-15" and census["end"] == "2026-07-15"
    expected = [d.isoformat() for d in API["dates"](date(2024, 8, 15), date(2026, 7, 15))]
    assert [r["date"] for r in census["days"]] == expected
    assert len(expected) == 700
    for row in census["days"]:
        assert row["url"].endswith("?date=" + row["date"])
        if row["outcome"] in {"data", "empty"}:
            assert row["artifact"]["sha256"] and row["error"] is None
            assert row["artifact"]["source_url"] == row["url"]
            assert row["rows"] == row["valid"] + row["quarantined"] + row["incomplete"]
            assert row["outcome"] != "empty" or row["rows"] == 0
        else:
            assert row["outcome"] in {"failed", "not_attempted"} and row["error"]
    assert census["complete"] == all(r["outcome"] in {"data", "empty"} for r in census["days"])


def test_local_census_evidence_hashes():
    path = FIX / "s32_history_manifest.json"
    assert path.exists(), "Run the real T227 census before claiming completion"
    root = ROOT / "data/raw"
    if not root.exists():
        pytest.skip("The immutable raw evidence is local only")
    census = json.loads(path.read_text("utf-8"))
    artifacts = [r["artifact"] for r in census["days"] if r["artifact"]]
    if census["robots"]:
        artifacts.append(census["robots"]["artifact"])
    for artifact in artifacts:
        raw = (root / artifact["path"]).resolve()
        assert raw.is_relative_to(root.resolve())
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == artifact["sha256"]
