"""T104 acceptance: scheduled positions use the right GTFS service day (00:30 next day, 25:10),
never place a vehicle off a known shape or outside its service day, pause on gaps and missing
shapes, label every marker scheduled-not-live, and keep the S21 railway timetable a historical
reference that never becomes an ETA. S30 feeds are local only (D115): those tests skip in CI."""

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.s21 import BASE, S21
from atlas.ingest.s30 import FEEDS, S30
from atlas.transit.schedule import (
    RAIL_LABEL,
    SCHEDULED_LABEL,
    TZ,
    instant,
    load_network,
    rail_reference,
    scheduled_positions,
    service_dates,
    service_seconds,
    snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
STATE = load_state(ROOT / "configs/states/ka.yaml")
EVIDENCE = {
    e["id"]: e
    for e in json.loads((ROOT / "tests/fixtures/s30/manifest.json").read_text("utf-8"))["evidence"]
}
BMRCL_ZIP = ROOT / "data/raw" / EVIDENCE["e11"]["raw_path"]
BMTC_ZIP = ROOT / "data/raw" / EVIDENCE["e12"]["raw_path"]
local = pytest.mark.skipif(not BMRCL_ZIP.exists(), reason="S30 raw feeds are local only (D115)")
NOV11, NOV12 = date(2026, 11, 11), date(2026, 11, 12)


def s30_raw(path: Path, feed: str) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=datetime(2026, 11, 9, 11, 30, 22, tzinfo=UTC),
        media_type="application/zip",
        response_status=200,
        source_url=FEEDS[feed][2],
        schema_mapping_version="s30-v1",
    )


def s21_table() -> pa.Table:
    """Real CC0 S21 subsets (T074 fixtures)."""

    def art(name: str, file: str) -> RawArtifact:
        path = ROOT / "tests/fixtures" / file
        return RawArtifact(
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            path=path,
            fetched_at=datetime(2026, 11, 9, 9, 46, 43, tzinfo=UTC),
            media_type="application/json",
            response_status=200,
            source_url=f"{BASE}/{name}",
            schema_mapping_version="s21-v1",
        )

    return S21("ka", "Karnataka").parse(
        art("schedules.json", "s21_datameet_schedules_4_trains.json"),
        STATE.source("S21"),
        stations=art("stations.json", "s21_datameet_stations_subset.json"),
    )


@pytest.fixture(scope="module")
def bmrcl():
    raw = s30_raw(BMRCL_ZIP, "bmrcl")
    tables = {d: S30("ka").parse(raw, STATE.source("S30"), service_date=d) for d in (NOV11, NOV12)}
    return load_network(raw), tables


def test_25_10_is_01_10_on_the_next_calendar_day():
    at = datetime(2026, 11, 12, 1, 10, tzinfo=TZ)
    assert instant(NOV11, 25 * 3600 + 10 * 60) == at
    assert (service_seconds(at, NOV11), service_seconds(at, NOV12)) == (90600, 4200)
    assert service_seconds(at.astimezone(UTC), NOV11) == 90600


def test_00_30_belongs_to_today_and_yesterday_service_days():
    at = datetime(2026, 11, 12, 0, 30, tzinfo=TZ)
    assert service_dates(at)[:2] == [NOV12, NOV11]
    assert (service_seconds(at, NOV12), service_seconds(at, NOV11)) == (1800, 88200)
    with pytest.raises(ValueError, match="timezone"):
        service_seconds(datetime(2026, 11, 12, 0, 30), NOV12)


def test_rail_timetable_is_reference_only_and_never_an_eta():
    table = s21_table()
    rows = rail_reference(table)
    assert len(rows) == table.num_rows and {r["label"] for r in rows} == {RAIL_LABEL}
    assert {r["mode"] for r in rows} == {"historical_reference"}
    for row in rows:
        assert not any(isinstance(v, datetime) for v in row.values())
        assert not any(k == "eta" or k.endswith(("_sec", "_at")) for k in row)
    with pytest.raises(ValueError, match="historical"):
        scheduled_positions(None, [table], datetime(2026, 11, 12, 8, tzinfo=TZ))


@local
def test_after_midnight_trips_run_on_the_previous_service_date(bmrcl):
    net, tables = bmrcl
    at = datetime(2026, 11, 12, 0, 20, tzinfo=TZ)
    markers = scheduled_positions(net, list(tables.values()), at)
    assert len(markers) == 2 and {m["service_date"] for m in markers} == {"2026-11-11"}
    for m in markers:
        assert instant(NOV11, m["departed_sec"]) <= at < instant(NOV11, m["arrives_sec"])
        assert m["departed_sec"] >= 86400 and m["status"] == "moving"
    # 00:30: the latest 11 Nov trip ended at 24:29:25 and 12 Nov service starts at 05:00
    assert scheduled_positions(net, list(tables.values()), at.replace(minute=30)) == []


@local
def test_no_position_outside_its_service_day_or_off_the_line(bmrcl):
    net, tables = bmrcl
    at = datetime(2026, 11, 12, 8, 0, tzinfo=TZ)
    assert scheduled_positions(net, [tables[NOV11]], at) == []  # 11 Nov ended at 24:29:25
    later = S30("ka").parse(
        s30_raw(BMRCL_ZIP, "bmrcl"), STATE.source("S30"), service_date=date(2026, 11, 14)
    )
    assert scheduled_positions(net, [later], at) == []
    markers = scheduled_positions(net, list(tables.values()), at)
    assert markers and {m["service_date"] for m in markers} == {"2026-11-12"}
    for m in markers:
        assert m["label"] == SCHEDULED_LABEL and m["live"] is False and m["approximate"] is True
        assert m["source_revision"] == FEEDS["bmrcl"][0]
        assert 12.8 < m["lat"] < 13.1 and 77.4 < m["lon"] < 77.8
        if m["status"] == "at_stop":
            assert (m["lat"], m["lon"]) == net.stops[m["from_stop_id"]]


@local
def test_missing_shape_or_time_pauses_without_a_position(bmrcl):
    net, tables = bmrcl
    at = datetime(2026, 11, 12, 8, 0, tzinfo=TZ)
    moving = next(
        m for m in scheduled_positions(net, [tables[NOV12]], at) if m["status"] == "moving"
    )
    shape = net.trip_shape.pop(moving["trip_id"])
    try:
        paused = [
            m
            for m in scheduled_positions(net, [tables[NOV12]], at)
            if m["trip_id"] == moving["trip_id"]
        ]
        assert paused[0]["status"] == "paused" and paused[0]["pause_reason"] == "missing shape"
        assert paused[0]["lat"] is None and paused[0]["lon"] is None
    finally:
        net.trip_shape[moving["trip_id"]] = shape
    table = tables[NOV12]
    gap = pc.and_(
        pc.equal(table["trip_id"], moving["trip_id"]),
        pc.equal(table["stop_id"], moving["to_stop_id"]),
    )
    arrival = pc.if_else(gap, pa.scalar(None, pa.int64()), table["arrival_sec"])
    holed = table.set_column(table.schema.get_field_index("arrival_sec"), "arrival_sec", arrival)
    found = [m for m in scheduled_positions(net, [holed], at) if m["trip_id"] == moving["trip_id"]]
    assert found[0]["pause_reason"] == "missing time" and found[0]["lat"] is None


@local
def test_snapshot_carries_revision_service_date_caveats_and_stations(bmrcl):
    net, tables = bmrcl
    data = snapshot(
        [net], list(tables.values()), datetime(2026, 11, 12, 8, 0, tzinfo=TZ), rail=s21_table()
    )
    json.dumps(data)  # the web layer reads it as JSON
    feed = data["feeds"][0]
    assert (feed["source_revision"], feed["service_dates"]) == (FEEDS["bmrcl"][0], ["2026-11-12"])
    assert "approximated" in feed["uncertainty"]
    kinds = [s["kind"] for s in data["stations"]]
    assert kinds.count("metro_station") == 83 and kinds.count("railway_station") > 0
    assert data["rail"]["mode"] == "historical_reference"


@local
def test_bmtc_positions_are_labelled_and_pauses_have_no_position():
    raw = s30_raw(BMTC_ZIP, "bmtc")
    table = S30("ka").parse(raw, STATE.source("S30"), service_date=NOV12)
    markers = scheduled_positions(
        load_network(raw), [table], datetime(2026, 11, 12, 8, 0, tzinfo=TZ)
    )
    assert len(markers) > 1000 and all(m["label"] == SCHEDULED_LABEL for m in markers)
    assert all((m["lat"] is None) == (m["status"] == "paused") for m in markers)
    assert "inaccurate" in markers[0]["uncertainty"]


def test_web_layer_contract(web_check):
    web_check("test", "--", "src/map/ScheduledTransit.test.ts")
