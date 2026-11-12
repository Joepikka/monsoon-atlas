"""T028 acceptance: the S30 (BMTC and Namma Metro GTFS) discovery record passes the discovery
contract; the absence of an operator feed, the pinned commits, licences and the plan's GTFS checks
(calendar exceptions, times above 24:00, stop coordinates) are checked against the evidence."""

import csv
import io
import json
import zipfile
from collections import Counter

BMTC = "ee945dc0c21b29193f88e3e1e9af218dd24ea182"
BMRCL = "f402c4c69a5d314320024f84620fa83e909c4188"


def body(rec, eid):
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def table(zf, name):
    return list(csv.DictReader(io.TextIOWrapper(zf.open(name), "utf-8-sig")))


def test_s30_discovery_contract(record):
    assert record("S30").problems() == []


def test_s30_status(record):
    d = record("S30").discovery
    assert d.outcome == "available" and d.retry_condition is None
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "restricted",
        "partial",
        "pass",
    )
    assert [f.url for f in d.failed_fetches] == [
        "https://mybmtc.karnataka.gov.in/en",
        "https://mybmtc.karnataka.gov.in/robots.txt",
    ]


def test_no_data_committed(record):
    assert record("S30").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S30").check_local_hashes()


def test_no_operator_feed_is_published(record):
    rec = record("S30")
    rows = list(csv.DictReader(io.StringIO(rec.raw("e01").read_text("utf-8"))))
    bengaluru = [r for r in rows if r["location.municipality"] == "Bengaluru"]
    assert [(r["mdb_source_id"], r["is_official"], r["status"]) for r in bengaluru] == [
        ("2013", "", "deprecated"),
        ("2595", "False", ""),
    ]
    karnataka = [r["mdb_source_id"] for r in rows if r["location.subdivision_name"] == "Karnataka"]
    assert karnataka == ["2013", "2595"]
    assert not any(k in r["provider"].lower() for r in rows for k in ("bmrcl", "namma metro"))
    gtfs = [p["name"] for p in body(rec, "e02")["result"]["results"]]
    assert gtfs == ["hyderabad-metro-rail-gtfs", "hyderabad-bus-stops"]
    assert "gtfs" not in rec.raw("e04").read_text("utf-8").lower()


def test_pinned_commits_and_licences(record):
    rec = record("S30")
    assert (body(rec, "e07")["sha"], body(rec, "e10")["sha"]) == (BMTC, BMRCL)
    assert body(rec, "e07")["commit"]["committer"]["date"] == "2026-09-08T03:58:57Z"
    assert body(rec, "e10")["commit"]["committer"]["date"] == "2026-08-17T16:33:48Z"
    assert BMTC in rec.manifest.evidence[11].url and BMRCL in rec.manifest.evidence[10].url
    assert (
        body(rec, "e06")["license"]["spdx_id"]
        == body(rec, "e09")["license"]["spdx_id"]
        == "ODbL-1.0"
    )
    bmtc = rec.raw("e05").read_text("utf-8")
    assert "Unofficial GTFS" in bmtc and "copyright by BMTC" in bmtc and "inaccurate" in bmtc
    assert "approximation" in rec.raw("e08").read_text("utf-8")


def test_bmrcl_calendar_exceptions_and_late_times(record):
    zf = zipfile.ZipFile(record("S30").raw("e11"))
    exceptions = Counter(
        (r["service_id"], r["exception_type"]) for r in table(zf, "calendar_dates.txt")
    )
    assert exceptions == {("holiday", "1"): 32, ("weekday", "2"): 31, ("monday", "2"): 1}
    times = table(zf, "stop_times.txt")
    late = [r for r in times if int(r["arrival_time"][:2]) >= 24]
    assert (len(times), len(late), len({r["trip_id"] for r in late})) == (88906, 150, 23)
    past = {r["trip_id"] for r in times if int(r["departure_time"][:2]) >= 24}
    assert len(past) == 25
    assert max(r["departure_time"] for r in times) == "24:29:25"
    stops = table(zf, "stops.txt")
    assert len(stops) == 488 and all(12.8 < float(s["stop_lat"]) < 13.1 for s in stops)


def test_bmtc_single_service_and_far_stops(record):
    zf = zipfile.ZipFile(record("S30").raw("e12"))
    assert [r["service_id"] for r in table(zf, "calendar.txt")] == ["1"]
    assert "calendar_dates.txt" not in zf.namelist()
    with zf.open("stop_times.txt") as f:
        assert sum(1 for _ in f) - 1 == 1540686
    stops = table(zf, "stops.txt")
    assert len(stops) == 9960 and all(s["stop_lat"] and s["stop_lon"] for s in stops)
    assert max(float(s["stop_lat"]) for s in stops) == 17.77218
