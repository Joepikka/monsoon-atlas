"""T071 acceptance: the S20 (USGS earthquakes) discovery record passes the discovery contract;
history, status, magnitude gaps and the 30-day default window are checked against the evidence."""

import json
from collections import Counter


def body(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def test_s20_discovery_contract(record):
    assert record("S20").problems() == []


def test_s20_status(record):
    d = record("S20").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "restricted",
        "available",
        "pass",
    )
    assert (d.earliest_date, d.latest_date) == ("1959-10-12", "2024-12-04")
    assert sum("202" in f.error for f in d.failed_fetches) == 2


def test_no_data_committed(record):
    assert record("S20").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S20").check_local_hashes()


def test_default_window_and_full_history(record):
    rec = record("S20")
    assert body(rec, "e05") == {"count": 0, "maxAllowed": 20000}
    assert body(rec, "e08") == {"count": 95, "maxAllowed": 20000}
    events = body(rec, "e09")["features"]
    assert len(events) == 95 and {e["properties"]["status"] for e in events} == {"reviewed"}
    assert sum(e["properties"]["mag"] is None for e in events) == 16
    karnataka = [
        e
        for e in events
        if 11.5 <= e["geometry"]["coordinates"][1] <= 18.5
        and 74 <= e["geometry"]["coordinates"][0] <= 78.6
    ]
    assert len(karnataka) == 28


def test_feed_status_ids_and_updates(record):
    rec = record("S20")
    first, later = body(rec, "e07")["features"], body(rec, "e10")["features"]
    assert Counter(e["properties"]["status"] for e in first) == {"automatic": 136, "reviewed": 50}
    assert sum(e["properties"]["ids"].count(",") > 2 for e in first) == 11
    a = {e["id"]: e["properties"]["updated"] for e in first}
    b = {e["id"]: e["properties"]["updated"] for e in later}
    assert len(a.keys() & b.keys()) == 185 and all(a[i] == b[i] for i in a.keys() & b.keys())
