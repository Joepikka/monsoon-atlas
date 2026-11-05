"""T119 acceptance: the S35 (Kerala 2018 flood dataset) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status."""

import json
import re


def page_metadata(path) -> dict:
    page = path.read_text(encoding="utf-8", errors="replace")
    blob = re.search(r'(?is)<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', page)
    return json.loads(blob.group(1))


def test_s35_discovery_contract(record):
    assert record("S35").problems() == []


def test_s35_is_blocked_with_explicit_status(record):
    d = record("S35").discovery
    assert d.outcome == "blocked"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "unverified",
        "not_public",
        "fail",
    )
    assert d.account_required and d.no_card
    assert {"T120", "T133", "T134", "T135"} <= set(d.dependents)
    assert "T121" in d.retry_condition


def test_no_data_committed(record):
    assert record("S35").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S35").check_local_hashes()


def test_kaggle_pages_need_sign_in_and_state_no_licence(record):
    rec = record("S35")
    licences = {}
    for eid in ("e01", "e02", "e03", "e04", "e05"):
        meta = page_metadata(rec.raw(eid))
        assert meta["distribution"][0]["requiresSubscription"] is True, eid
        licences[eid] = meta["license"]["name"]
    assert licences["e01"] == licences["e02"] == "Other (specified in description)"
    assert {licences[e] for e in ("e03", "e04", "e05")} == {"Unknown"}
    for eid in ("e01", "e02"):
        assert "licen" not in page_metadata(rec.raw(eid))["description"].lower(), eid


def test_official_memorandum_is_cited_and_public(record):
    rec = record("S35")
    assert "Memorandum2-Floods-2018.pdf" in page_metadata(rec.raw("e01"))["description"]
    assert rec.raw("e06").read_bytes()[:5] == b"%PDF-"
