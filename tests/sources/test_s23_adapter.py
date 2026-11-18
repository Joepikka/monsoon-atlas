"""T270: S23 per-day adapter, resumable backfill and clean build, offline.

Fixtures in tests/fixtures/s23_days are real per-day responses (T269 evidence e20, e21, e23,
e24) recorded with public parameters only. Changed copies made inside a test (a dropped record,
an empty price) exist only in tmp_path to exercise the checks; they are never ingested.
"""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.http import Fetcher, FixtureTransport
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s23 import (
    HOSTS,
    MAPPING_VERSION,
    PAUSE_S,
    S23,
    SECRET_ENV,
    URL,
    backfill,
    build,
    day_check,
    day_params,
    done_days,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/s23_days"
CONFIG = load_state(ROOT / "configs/states/ka.yaml").source("S23")
KEY = "test-key-not-a-real-key"
D2019, EMPTY = date(2019, 1, 2), date(2004, 7, 15)
NOV4, NOV12 = date(2026, 11, 4), date(2026, 11, 12)


class Recording(FixtureTransport):
    """Fixture replay that also records each request URL as sent (with the key)."""

    def __init__(self):
        super().__init__(FIXTURES, secret_names=("api-key",))
        self.sent: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.sent.append(str(request.url))
        return super().handle_request(request)


def setup(tmp_path):
    transport = Recording()
    fetcher = Fetcher(RawStore(tmp_path / "raw"), HOSTS, transport=transport, sleep=lambda s: None)
    ctx = FetchContext(
        source_id="S23",
        state="ka",
        run_id="t270",
        requested_at=datetime.now(UTC),
        raw_root=tmp_path / "raw",
        budget=Budget(max_requests=20, max_bytes=1024**2),
        secrets={SECRET_ENV: KEY},
    )
    return transport, fetcher, ctx


def fetched(tmp_path, day) -> RawArtifact:
    _, fetcher, ctx = setup(tmp_path)
    return S23(fetcher=fetcher).fetch_day(ctx, day)


def changed_copy(tmp_path, raw: RawArtifact, edit) -> RawArtifact:
    body = json.loads(raw.path.read_bytes())
    edit(body)
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return raw.model_copy(update={"path": path})


def test_one_request_per_day_two_seconds_apart_key_only_in_the_request(tmp_path):
    transport, fetcher, ctx = setup(tmp_path)
    pauses = []
    arts = S23([D2019, EMPTY], fetcher=fetcher, sleep=pauses.append).fetch(ctx)
    assert pauses == [PAUSE_S] and PAUSE_S >= 2.0
    assert len(transport.sent) == 2 and all(f"api-key={KEY}" in u for u in transport.sent)
    assert all("Arrival_Date" in u and "offset=0" in u for u in transport.sent)
    for art in arts:
        assert art.source_url.startswith(f"{URL}?") and "api-key" not in art.source_url
    for path in (tmp_path / "raw").rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes(), path


def test_day_params_are_the_verified_per_day_query():
    assert day_params(D2019) == {
        "filters[State]": "Karnataka",
        "filters[Commodity]": "Onion",
        "filters[Arrival_Date]": "02/01/2019",
        "format": "json",
        "limit": "1000",
        "offset": "0",
    }


def test_rows_equal_the_reported_total_and_a_mismatch_is_reported(tmp_path):
    raw = fetched(tmp_path, D2019)
    assert day_check(raw) | {"updated_date": None} == {
        "date": "2019-01-02",
        "total": 14,
        "rows": 14,
        "ok": True,
        "updated_date": None,
    }
    assert day_check(fetched(tmp_path, EMPTY))["total"] == 0
    short = changed_copy(tmp_path, raw, lambda b: b["records"].pop())
    check = day_check(short)
    assert (check["total"], check["rows"], check["ok"]) == (14, 13, False)


def test_parse_gives_canonical_rows_in_rupees_per_quintal(tmp_path):
    old, new = fetched(tmp_path, D2019), fetched(tmp_path, NOV4)
    for raw, n in ((old, 14), (new, 23)):
        table = S23().parse(raw, CONFIG)
        validate_table(table, measures=["modal_inr_quintal"])
        assert table.num_rows == n and len(set(table["record_id"].to_pylist())) == n
        assert set(table["price_unit"].to_pylist()) == {"Rs./Quintal"}
        assert set(table["commodity"].to_pylist()) == {"Onion"}
        assert set(table["date_local"].to_pylist()) == {raw_day(raw)}
        assert all("api-key" not in u for u in table["source_url"].to_pylist())
        assert table["modal_inr_quintal"].null_count == 0
    row = S23().parse(old, CONFIG).to_pylist()[0]
    assert row["market_id"] == "karnataka/dharwad/hubli (amaragol)"
    assert (row["min_inr_quintal"], row["modal_inr_quintal"], row["max_inr_quintal"]) == (
        180.0,
        560.0,
        1100.0,
    )
    assert row["commodity_code"] == "23" and row["provenance"] == "official"
    # Integer prices (from Nov 2025) parse to the same type as the older strings.
    assert S23().parse(new, CONFIG).schema.field("modal_inr_quintal").type == "double"
    path = tmp_path / "s23.parquet"
    pq.write_table(S23().parse(old, CONFIG), path)
    back = pq.read_table(path)
    assert read_mapping(back)["provider_to_canonical"]["Modal_Price"] == "modal_inr_quintal"


def raw_day(raw: RawArtifact) -> date:
    return date.fromisoformat(day_check(raw)["date"])


def test_missing_price_is_null_with_a_reason_never_zero(tmp_path):
    raw = fetched(tmp_path, D2019)

    def blank(body):
        body["records"][0]["Modal_Price"] = ""
        body["records"][1]["Modal_Price"] = "NR"

    rows = S23().parse(changed_copy(tmp_path, raw, blank), CONFIG).to_pylist()
    assert rows[0]["modal_inr_quintal"] is None and rows[0]["missing_reason"] == "not_reported"
    assert rows[1]["modal_inr_quintal"] is None and rows[1]["missing_reason"] == "quality_rejected"
    assert rows[2]["modal_inr_quintal"] is not None and rows[2]["missing_reason"] is None


def test_identical_rows_are_kept_apart(tmp_path):
    raw = fetched(tmp_path, D2019)
    twin = changed_copy(tmp_path, raw, lambda b: b["records"].append(b["records"][0]))
    table = S23().parse(twin, CONFIG)
    assert table.num_rows == 15 and len(set(table["record_id"].to_pylist())) == 15


def test_parse_refuses_a_disabled_config_and_the_other_resource(tmp_path):
    raw = fetched(tmp_path, D2019)
    with pytest.raises(SourceUnavailable, match="disabled"):
        S23().parse(raw, CONFIG.model_copy(update={"enabled": False}))
    other = raw.model_copy(
        update={
            "source_url": "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        }
    )
    with pytest.raises(SourceUnavailable, match="per-day"):
        S23().parse(other, CONFIG)


def test_backfill_checkpoints_each_day_resumes_and_a_rerun_downloads_nothing(tmp_path):
    transport, fetcher, _ = setup(tmp_path)
    ckpt = tmp_path / "raw/S23/checkpoint.jsonl"
    days = [EMPTY, D2019, NOV4, NOV12]
    kwargs = dict(
        fetcher=fetcher,
        secrets={SECRET_ENV: KEY},
        raw_root=tmp_path / "raw",
        checkpoint=ckpt,
        sleep=lambda s: None,
    )
    first = backfill(days, max_days=2, **kwargs)  # stopped after two days
    assert (first["done"], first["rows"]) == (2, 14) and sorted(done_days(ckpt)) == [
        "2004-07-15",
        "2019-01-02",
    ]
    second = backfill(days, **kwargs)  # resumes with the two days left
    assert len(transport.sent) == 4
    # 12/11/2026 is the resource's last update day (updated_date 2026-11-12): not final yet.
    assert (second["done"], second["provisional"], second["rows"]) == (1, 1, 23)
    assert set(done_days(ckpt)) == {"2004-07-15", "2019-01-02", "2026-11-04"}
    entry = done_days(ckpt)["2019-01-02"]
    assert entry["ok"] and entry["total"] == entry["rows"] == 14
    assert KEY not in ckpt.read_text("utf-8") and "api-key" not in ckpt.read_text("utf-8")
    third = backfill(days[:3], **kwargs)
    assert third["todo"] == 0 and len(transport.sent) == 4  # nothing downloaded again


def test_build_writes_parquet_and_a_manifest_with_per_year_counts(tmp_path):
    _, fetcher, _ = setup(tmp_path)
    ckpt = tmp_path / "raw/S23/checkpoint.jsonl"
    backfill(
        [EMPTY, D2019, NOV4],
        fetcher=fetcher,
        secrets={SECRET_ENV: KEY},
        raw_root=tmp_path / "raw",
        checkpoint=ckpt,
        sleep=lambda s: None,
    )
    manifest = build(CONFIG, raw_root=tmp_path / "raw", checkpoint=ckpt, clean=tmp_path / "clean")
    table = pq.read_table(tmp_path / "clean/onion.parquet")
    assert table.num_rows == manifest["rows"] == 37
    assert manifest["rows_per_year"] == {"2004": 0, "2019": 14, "2026": 23}
    assert (manifest["days_checked"], manifest["days_with_rows"]) == (3, 2)
    assert manifest["mismatched_days"] == [] and manifest["mapping_version"] == MAPPING_VERSION
    saved = json.loads((tmp_path / "clean/manifest.json").read_text("utf-8"))
    assert saved == manifest
