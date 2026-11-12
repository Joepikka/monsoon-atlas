"""T061 acceptance: the S11 (OpenSky flight fallback) discovery record passes the discovery
contract as a blocked result: the terms page could not be read and using the API means accepting
it, so the source stays disabled; credits and units are checked against the published docs."""

import html
import re


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s11_discovery_contract(record):
    assert record("S11").problems() == []


def test_s11_is_blocked_and_disabled(record):
    rec = record("S11")
    d = rec.discovery
    assert (d.outcome, d.licence.status, d.source_check.status) == (
        "blocked",
        "unverified",
        "blocked",
    )
    assert d.dependents == ["T062"] and "owner reads" in d.retry_condition
    assert [f.url.rsplit("/", 1)[-1] for f in d.failed_fetches] == [
        "robots.txt",
        "",
        "terms-of-use",
    ]
    assert all("403" in f.error for f in d.failed_fetches)  # enabled + blocked fails the contract


def test_no_data_committed(record):
    assert record("S11").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S11").check_local_hashes()


def test_terms_clause_and_research_use(record):
    rec = record("S11")
    assert "By using the OpenSky API, you agree with our terms of use" in text(rec, "e01")
    intro = text(rec, "e02")
    assert "research and non-commerical purposes" in intro
    assert "for more details on the data license model" in intro


def test_credits_and_units_from_the_rest_docs(record):
    rest = text(record("S11"), "e03")
    assert "Anonymous 400 Daily Standard user 4,000 Daily" in rest
    assert "429 Too Many Requests" in rest
    assert "baro_altitude float Barometric altitude in meters" in rest
    assert "velocity float Velocity over ground in m/s" in rest
    assert "time_position int Unix timestamp (seconds)" in rest
