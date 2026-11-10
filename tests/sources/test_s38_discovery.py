"""T148 acceptance: the S38 (Delhi Open Transit Data) discovery record passes the discovery
contract as a blocked result: static files and the feed need the owner's registration (H04)."""


def test_s38_discovery_contract(record):
    assert record("S38").problems() == []


def test_s38_is_blocked_with_nothing_assumed(record):
    rec = record("S38")
    d = rec.discovery
    assert (d.outcome, d.state, d.licence.status, d.source_check.status) == (
        "blocked",
        "dl",
        "restricted",
        "blocked",
    )
    assert d.access.status == "form_and_key_required_owner_step"
    assert d.account_required and d.no_card and d.units.status == "unlabelled"
    assert (d.history.status, d.earliest_date, d.latest_date) == ("not_public", None, None)
    assert d.provider_quota.status == "not_published"
    assert d.dependents == ["T149", "T150", "T151", "T152", "T153", "T156"]
    assert "H04" in d.retry_condition
    # No upstream field is claimed: no feed or file was read.
    assert all(f.upstream is None and f.unit_status == "absent" for f in d.field_map)
    assert {f.canonical for f in d.field_map} == {
        "vehicle_id",
        "trip_id",
        "route_id",
        "position_at",
        "lat",
        "lon",
        "speed_ms",
        "feed_version",
    }
    assert [f.error[:8] for f in d.failed_fetches] == ["HTTP 404", "HTTP 401"]
    assert all(e.url.startswith("https://otd.delhi.gov.in/") for e in rec.manifest.evidence)
    assert all("key=" not in e.url for e in rec.manifest.evidence)


def test_evidence_shows_forms_and_documented_path(record):
    rec = record("S38")
    docs = rec.raw("e05").read_text("utf-8")
    assert "/api/realtime/VehiclePositions.pb?key=YOUR_PRIVATE_KEY" in docs
    assert "rough" in docs and "estimate" in docs
    assert 'action="/data/static/"' in rec.raw("e02").read_text("utf-8")
    assert 'action="/data/realtime/"' in rec.raw("e04").read_text("utf-8")


def test_no_data_committed(record):
    assert record("S38").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S38").check_local_hashes()
