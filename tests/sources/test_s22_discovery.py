"""T023 acceptance: the S22 (India Data Portal Agmarknet) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status."""


def test_s22_discovery_contract(record):
    assert record("S22").problems() == []


def test_s22_is_blocked_without_guessed_endpoints(record):
    rec = record("S22")
    d = rec.discovery
    assert d.outcome == "blocked" and d.licence.status == "unverified"
    assert {"T024", "T035"} <= set(d.dependents) and "T025" in d.retry_condition
    assert all("indiadataportal.com" in e.url for e in rec.manifest.evidence)


def test_no_data_committed(record):
    assert record("S22").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S22").check_local_hashes()


def test_agmarknet_page_serves_no_data(record):
    page = record("S22").raw("e02").read_text("utf-8")
    assert '"variables":{"id":"agmarknet"}' in page
    assert ".csv" not in page and "/api/" not in page
