"""T059 acceptance: the S10 (adsb.lol live aircraft) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status; units, the
millisecond clock, stale ages and owner fields are checked against the raw evidence."""

import html
import json
import re
from datetime import UTC, datetime


def body(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s10_discovery_contract(record):
    assert record("S10").problems() == []


def test_s10_status(record):
    d = record("S10").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "partial",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert (d.earliest_date, d.latest_date) == ("2026-11-09", "2026-11-09")


def test_no_data_committed(record):
    assert record("S10").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S10").check_local_hashes()


def test_licence_terms_and_endpoint(record):
    rec = record("S10")
    assert "license: ODbL 1.0" in text(rec, "e02")
    spec = body(rec, "e08")
    assert spec["info"]["license"]["name"].startswith("Open Data Commons Open Database License")
    assert "You can use the API for free" in spec["info"]["description"]
    radius = spec["paths"]["/v2/point/{lat}/{lon}/{radius}"]["get"]["parameters"][2]
    assert radius["name"] == "radius" and radius["schema"]["maximum"] == 250


def test_units_from_the_field_reference(record):
    ref = text(record("S10"), "e09")
    assert "alt_baro: the aircraft barometric altitude in feet" in ref
    assert "gs: ground speed in knots" in ref
    assert 'seen_pos: how long ago (in seconds before "now")' in ref
    assert "LADD = dbFlags & 8" in ref and "PIA = dbFlags & 4" in ref


def test_sample_clock_is_milliseconds_and_positions_are_fresh(record):
    rec = record("S10")
    sample = body(rec, "e10")
    fetched = next(e.fetched_at for e in rec.manifest.evidence if e.id == "e10")
    now = datetime.fromtimestamp(sample["now"] / 1000, UTC)
    assert abs((now - fetched).total_seconds()) < 5  # milliseconds, not seconds
    aircraft = sample["ac"]
    assert len(aircraft) == sample["total"] == 20
    assert max(a["seen_pos"] for a in aircraft) < 300
    assert sum(a.get("alt_baro") == "ground" for a in aircraft) == 5
    assert all(a["hex"] for a in aircraft)
    fields = set().union(*aircraft)
    assert not fields & {"ownOp", "owner", "operator"}  # no owner data to strip or enrich
