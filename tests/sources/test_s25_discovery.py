"""T075 acceptance: the S25 (NASA FIRMS) discovery record passes the discovery contract. First
blocked on the owner's MAP_KEY (H09); retried 12 Nov 2026 with the key (D176): available, with the
key never recorded. Licence, latency and field units are checked against the evidence."""

import html
import re


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s25_discovery_contract(record):
    assert record("S25").problems() == []


def test_s25_is_available_with_the_owner_key(record):
    d = record("S25").discovery
    assert (d.outcome, d.licence.status, d.source_check.status) == ("available", "open", "pass")
    assert d.account_required and d.access.status == "owner_key" and d.retry_condition is None
    assert d.dependents == ["T076"] and "not a confirmed building fire" in d.source_check.detail


def test_recorded_urls_and_files_never_carry_the_key(record):
    rec = record("S25")
    keyed = [e for e in rec.manifest.evidence if "/csv/" in e.url]
    assert [e.id for e in keyed] == ["e08", "e09"]
    assert all("/csv/MAP_KEY/" in e.url for e in keyed)
    header = rec.raw("e09").read_text("utf-8").splitlines()[0]
    assert header.startswith("latitude,longitude,bright_ti4") and header.endswith("frp,daynight")
    assert "VIIRS_NOAA20_NRT,2026-08-01,2026-11-12" in rec.raw("e08").read_text("utf-8")


def test_no_data_committed(record):
    assert record("S25").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S25").check_local_hashes()


def test_pages_are_script_shells_and_dist_is_closed(record):
    rec = record("S25")
    shells = {e.sha256 for e in rec.manifest.evidence if e.id in ("e03", "e04")}
    assert len(shells) == 1 and "/dist/firms_content" in rec.raw("e03").read_text("utf-8")
    assert "Disallow: /dist/" in rec.raw("e01").read_text("utf-8")


def test_licence_latency_and_units(record):
    rec = record("S25")
    tool = text(rec, "e02")
    assert "NASA supports full and open sharing of data" in tool
    assert "Global data are available within 3 hours of satellite observation" in tool
    fields = text(rec, "e05")
    assert "fire radiative power in MW (megawatts)" in fields
    assert "Confidence values are set to low, nominal and high" in fields
