"""T111 acceptance: the S26 (aisstream ships) discovery record passes the discovery contract as a
blocked result: the API key is owner step H12 and no data terms are published."""

import html
import re


def text(rec, eid) -> str:
    page = rec.raw(eid).read_text("utf-8", errors="replace")
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", page, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s26_discovery_contract(record):
    assert record("S26").problems() == []


def test_s26_is_blocked_on_the_owner_key(record):
    d = record("S26").discovery
    assert (d.outcome, d.licence.status, d.source_check.status) == (
        "blocked",
        "unverified",
        "blocked",
    )
    assert d.account_required and "H12" in d.retry_condition and d.dependents == ["T112"]
    assert (d.state, d.history.status, d.earliest_date) == ("kl", "not_public", None)


def test_no_data_committed(record):
    assert record("S26").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S26").check_local_hashes()


def test_key_quotas_and_units_are_documented(record):
    rec = record("S26")
    assert "Sign in with GitHub and create an API key in Account" in text(rec, "e01")
    docs = text(rec, "e03")
    assert "wss://stream.aisstream.io/v0/stream" in docs
    assert "3 subscribed connections" in docs and "no SLA or uptime guarantee" in docs
    assert "Speed over ground in knots" in docs and "Course over ground in degrees" in docs
    assert "terms" not in text(rec, "e04").lower()
