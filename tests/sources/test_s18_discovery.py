"""T021 acceptance: the S18 (Geofabrik OSM extracts) discovery record passes the discovery contract
only with cited evidence and explicit access, licence and history status."""


def test_s18_discovery_contract(record):
    assert record("S18").problems() == []


def test_s18_is_blocked_by_robots(record):
    d = record("S18").discovery
    assert d.outcome == "blocked" and d.access.status == "robots_disallow"
    assert (d.licence.status, d.source_check.status) == ("open", "fail")
    assert d.dependents == ["T022"] and "data/raw/S18" in d.retry_condition


def test_no_data_committed(record):
    assert record("S18").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S18").check_local_hashes()


def test_robots_disallows_extract_files(record):
    rules = record("S18").raw("e01").read_text("utf-8").split()
    for pattern in ("*.osm.pbf", "*.shp.zip"):
        assert pattern in rules, pattern
    page = " ".join(record("S18").raw("e03").read_text("utf-8").split())
    assert "File size: 533&nbsp;MB" in page and "License: ODbL 1.0" in page
    assert not any(e.url.endswith(".pbf") for e in record("S18").manifest.evidence)
