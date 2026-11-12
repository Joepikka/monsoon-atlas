"""T146 acceptance: the S24 (CPCB station pollution via data.gov.in) discovery record passes the
discovery contract as a blocked result: the resource ID and licence could not be read."""

import json


def test_s24_discovery_contract(record):
    assert record("S24").problems() == []


def test_s24_is_blocked_with_nothing_assumed(record):
    rec = record("S24")
    d = rec.discovery
    assert (d.outcome, d.state, d.licence.status, d.source_check.status) == (
        "blocked",
        "dl",
        "unverified",
        "blocked",
    )
    assert d.account_required and d.no_card and d.units.status == "unlabelled"
    assert (d.history.status, d.earliest_date, d.latest_date) == ("not_public", None, None)
    assert d.dependents == ["T147", "T150", "T159"]
    # No upstream field is claimed: the resource was never read.
    assert all(f.upstream is None and f.unit_status == "absent" for f in d.field_map)
    assert {f.canonical for f in d.field_map} == {
        "station_id",
        "observed_at",
        "pollutant",
        "concentration",
        "unit",
        "averaging_hours",
        "reported_aqi",
    }
    assert all("api-key" not in e.url for e in rec.manifest.evidence)


def test_evidence_is_not_an_s24_sample(record):
    meta = json.loads(record("S24").raw("e01").read_text("utf-8"))
    assert meta["title"].startswith("Current Daily Price of Various Commodities")


def test_no_data_committed(record):
    assert record("S24").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S24").check_local_hashes()
