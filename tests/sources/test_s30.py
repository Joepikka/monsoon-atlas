"""T029 acceptance: the S30 adapter reads the pinned unofficial GTFS feeds for one local service
date: calendar exceptions pick the right service, times past 24:00 are never wrapped, BMRCL times
are flagged imputed, and malformed, empty and changed feeds fail. Real feeds are local only
(restricted licence, D115), so those tests skip in CI; the fail-closed checks always run."""

import hashlib
import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s30 import FEEDS, HOSTS, MEASURES, S30, seconds

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = {
    e["id"]: e
    for e in json.loads((ROOT / "tests/fixtures/s30/manifest.json").read_text("utf-8"))["evidence"]
}
BMRCL_ZIP = ROOT / "data/raw" / EVIDENCE["e11"]["raw_path"]
BMTC_ZIP = ROOT / "data/raw" / EVIDENCE["e12"]["raw_path"]
FETCHED = datetime(2026, 11, 9, 11, 30, 22, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S30")
ADAPTER = S30("ka")
local = pytest.mark.skipif(not BMRCL_ZIP.exists(), reason="S30 raw feeds are local only (D115)")


def artifact(path: Path, feed: str = "bmrcl") -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/zip",
        response_status=200,
        source_url=FEEDS[feed][2],
        schema_mapping_version="s30-v1",
    )


def edited(tmp_path: Path, name: str, edit) -> RawArtifact:
    """A copy of the real BMRCL feed with one file's text changed."""
    out = tmp_path / "bmrcl.zip"
    with zipfile.ZipFile(BMRCL_ZIP) as src, zipfile.ZipFile(out, "w") as dst:
        for item in src.infolist():
            data = src.read(item)
            if item.filename == name:
                data = edit(data.decode("utf-8-sig")).encode("utf-8")
            dst.writestr(item, data)
    return artifact(out)


def test_gtfs_times_count_from_the_service_day_and_pass_24_hours():
    assert seconds(["00:30:00", "25:10:00", "5:00:00", ""]).to_pylist() == [
        1800,
        90600,
        18000,
        None,
    ]
    with pytest.raises(IngestError, match="H:MM:SS"):
        seconds(["7:5:00"])


def test_disabled_and_unpinned_feeds_fail_closed(tmp_path):
    raw = artifact(Path(__file__))
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(raw, CONFIG.model_copy(update={"enabled": False}))
    unpinned = raw.model_copy(
        update={
            "source_url": "https://raw.githubusercontent.com/Vonter/bmrcl-gtfs/main/gtfs/bmrcl.zip"
        }
    )
    with pytest.raises(IngestError, match="pinned"):
        ADAPTER.parse(unpinned, CONFIG)


def test_empty_response_is_not_a_feed(tmp_path):
    empty = tmp_path / "empty.zip"
    empty.write_bytes(b"")
    with pytest.raises(IngestError, match="not a GTFS zip"):
        ADAPTER.parse(artifact(empty), CONFIG)


@local
def test_roundtrip_keeps_ids_seconds_and_commit(tmp_path):
    table = ADAPTER.parse(artifact(BMRCL_ZIP), CONFIG, service_date=date(2026, 11, 11))
    pq.write_table(table, tmp_path / "s30.parquet")
    back = pq.read_table(tmp_path / "s30.parquet")
    assert back.equals(table)
    validate_table(back)
    assert read_mapping(back)["provider_to_canonical"]["stop_times.arrival_time"] == "arrival_sec"
    assert len(set(back["trip_id"].to_pylist())) == 901  # Wednesday: weekday service
    assert len(set(back["record_id"].to_pylist())) == back.num_rows
    first = back.slice(0, 1).to_pylist()[0]
    assert first["provenance"] == "reconstructed" and first["valid_at"] is None
    assert first["redistribution_allowed"] is False and first["quality_flags"] == ["imputed"]
    assert first["published_at"] == FEEDS["bmrcl"][1]
    assert first["snapshot_id"] == "S30-bmrcl-f402c4c69a5d-20261111"


@local
def test_calendar_exceptions_choose_the_service():
    def trips(day):
        table = ADAPTER.parse(artifact(BMRCL_ZIP), CONFIG, service_date=day)
        return len(set(table["trip_id"].to_pylist()))

    # 10 Nov 2026 (Tuesday) is in calendar_dates: weekday removed, holiday added
    assert (trips(date(2026, 11, 10)), trips(date(2026, 11, 11))) == (835, 901)
    assert (trips(date(2026, 11, 15)), trips(date(2026, 11, 16))) == (615, 928)
    assert trips(date(2028, 1, 4)) == 0  # after the feed's end date


@local
def test_times_past_midnight_are_not_wrapped():
    table = ADAPTER.parse(artifact(BMRCL_ZIP), CONFIG, service_date=date(2026, 11, 11))
    assert pc.max(table["departure_sec"]).as_py() == 24 * 3600 + 29 * 60 + 25
    late = table.filter(pc.greater_equal(table["arrival_sec"], 86400))
    assert late.num_rows > 0 and set(late["service_date"].to_pylist()) == {date(2026, 11, 11)}


@local
def test_default_service_date_is_the_local_fetch_date():
    table = ADAPTER.parse(artifact(BMRCL_ZIP), CONFIG)
    assert set(table["service_date"].to_pylist()) == {date(2026, 11, 9)}


@local
@pytest.mark.parametrize(
    ("name", "edit", "match"),
    [
        ("stop_times.txt", lambda t: t.replace(",05:00:00,", ",5:0:00,", 1), "H:MM:SS"),
        ("stop_times.txt", lambda t: t.replace("departure_time", "departure", 1), "columns"),
        ("stop_times.txt", lambda t: t.replace(",TGTP_PF1,2,", ",TGTP_PF1,1,", 1), "repeated"),
        ("stop_times.txt", lambda t: t.replace("\nt1078,", "\nnope,", 1), "unknown trips"),
        ("agency.txt", lambda t: t.replace("Asia/Kolkata", "UTC"), "agency_timezone"),
        ("calendar.txt", lambda t: t.replace("20260817", "2026-08-17", 1), "calendar"),
    ],
    ids=["time format", "changed column", "repeated sequence", "unknown trip", "timezone", "date"],
)
def test_malformed_copies_rejected(tmp_path, name, edit, match):
    with pytest.raises(IngestError, match=match):
        ADAPTER.parse(edited(tmp_path, name, edit), CONFIG, service_date=date(2026, 11, 11))


@local
def test_bmtc_runs_every_day_without_flags():
    table = ADAPTER.parse(artifact(BMTC_ZIP, "bmtc"), CONFIG, service_date=date(2026, 11, 10))
    assert table.num_rows == 1540686 and len(set(table["trip_id"].to_pylist())) == 57836
    assert pc.max(table["arrival_sec"]).as_py() < 86400
    assert pc.list_value_length(table["quality_flags"]).to_pylist().count(0) == table.num_rows


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s30.json").read_text("utf-8"))
    names = {"string": "string", "int64": "int64", "date32[day]": "date32"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


@local
def test_fetch_reads_only_the_pinned_commits(tmp_path):
    seen: list[str] = []
    files = {FEEDS["bmrcl"][2]: BMRCL_ZIP, FEEDS["bmtc"][2]: BMTC_ZIP}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=files[str(request.url)].read_bytes())

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S30",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=2, max_bytes=100 * 1024**2),
        raw_root=tmp_path,
    )
    bmrcl, bmtc = S30("ka", fetcher).fetch(ctx)
    assert seen == [FEEDS["bmrcl"][2], FEEDS["bmtc"][2]]
    assert (bmrcl.sha256, bmtc.sha256) == (EVIDENCE["e11"]["sha256"], EVIDENCE["e12"]["sha256"])
    assert ADAPTER.parse(bmrcl, CONFIG, service_date=date(2026, 11, 11)).num_rows > 0
