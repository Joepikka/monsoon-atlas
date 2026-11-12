"""T077 acceptance: the S27 (KSNDMC gauges) discovery record passes the discovery contract as a
blocked result: no HTTPS, and only undocumented template endpoints over HTTP (D112)."""

import html
import re


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s27_discovery_contract(record):
    assert record("S27").problems() == []


def test_s27_is_blocked(record):
    d = record("S27").discovery
    assert (d.outcome, d.licence.status, d.history.status) == (
        "blocked",
        "unverified",
        "not_public",
    )
    assert d.dependents == ["T078"] and "HTTPS" in d.retry_condition
    assert len(d.failed_fetches) == 3 and all("ConnectError" in f.error for f in d.failed_fetches)


def test_no_data_committed(record):
    assert record("S27").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S27").check_local_hashes()


def test_http_pages_are_framework_templates(record):
    rec = record("S27")
    assert all("plain HTTP" in e.shows for e in rec.manifest.evidence)  # D112 label
    assert "ASP.NET is a free web framework" in text(rec, "e01")
    help_page = text(rec, "e02")
    assert "Provide a general description of your APIs here" in help_page
    assert "GetTrg24HourRainfallByDate?trgId={trgId}" in help_page
    assert help_page.count("No documentation available") == 3
