"""T021 acceptance: the S18 (Geofabrik OSM extracts) discovery record passes the discovery contract
only with cited evidence and explicit access, licence and history status. Retried on the owner's
browser download (D174): available, while robots.txt still bars the pipeline (D34)."""


def test_s18_discovery_contract(record):
    assert record("S18").problems() == []


def test_s18_is_available_through_the_owner_download(record):
    d = record("S18").discovery
    assert d.outcome == "available" and d.access.status == "owner_browser_download"
    assert (d.licence.status, d.source_check.status) == ("open", "pass")
    assert "e05" in d.source_check.evidence and d.retry_condition is None
    assert "Shelter opening status is never inferred" in d.source_check.detail


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
    pbf = [e for e in record("S18").manifest.evidence if e.url.endswith(".pbf")]
    assert [e.id for e in pbf] == ["e05"]  # the owner's browser download, not the pipeline
    assert "Owner browser download" in pbf[0].shows
