"""T115: real access evidence; soft-404 pages never certify a reservoir archive."""

from pathlib import Path

from atlas.config import load_state

ROOT = Path(__file__).resolve().parents[2]


def test_s33_discovery_contract(record):
    assert record("S33").problems() == []


def test_s33_stays_disabled_when_no_archive_artifact_is_available(record):
    d = record("S33").discovery
    assert d.outcome == "blocked"
    assert d.access.status == "soft_404"
    assert (d.licence.status, d.history.status) == ("unverified", "not_public")
    assert d.earliest_date is None and d.latest_date is None
    assert d.units.status == "not_checked" and d.source_check.status == "fail"
    assert set(d.dependents) == {"T116", "T130"}
    assert "monthly" in d.retry_condition.lower()
    assert not load_state(ROOT / "configs/states/kl.yaml").source("S33").enabled
    assert all(f.upstream is None and f.unit_status == "absent" for f in d.field_map)


def test_every_sampled_dams_page_is_the_recorded_error_page(record):
    rec = record("S33")
    for eid in ("e04", "e07", "e08", "e09"):
        page = rec.raw(eid).read_text("utf-8")
        assert "wrong address" in page.lower()
    assert not any(e.media_type == "application/pdf" for e in rec.manifest.evidence)


def test_error_page_evidence_describes_what_was_observed(record):
    rec = record("S33")
    for eid in ("e04", "e07", "e08", "e09"):
        evidence = next(e for e in rec.manifest.evidence if e.id == eid)
        assert "wrong" in evidence.shows.lower(), eid


def test_monthly_dashboard_link_is_not_a_reservoir_dataset(record):
    page = record("S33").raw("e06").read_text("utf-8")
    assert "Consumer Count" in page and "Consumption" in page
    assert "Reservoir" not in page


def test_missing_robots_file_is_reported_without_claiming_a_restriction(record):
    rec = record("S33")
    failure = next(
        f for f in rec.discovery.failed_fetches if f.url == "https://dams.kseb.in/robots.txt"
    )
    assert "404" in failure.error
    assert "400-499" in rec.raw("e05").read_text("utf-8")


def test_no_raw_pages_committed(record):
    assert record("S33").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S33").check_local_hashes()
