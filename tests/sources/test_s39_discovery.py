"""T083 acceptance: the S39 (Telegram Bot API) discovery record passes the discovery contract as a
blocked result: the bot token and terms are owner step H08; limits are checked against the docs."""

import html
import re


def text(rec, eid) -> str:
    page = rec.raw(eid).read_text("utf-8", errors="replace")
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", page, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s39_discovery_contract(record):
    assert record("S39").problems() == []


def test_s39_is_blocked_on_the_owner_bot(record):
    d = record("S39").discovery
    assert (d.outcome, d.licence.status, d.source_check.status) == (
        "blocked",
        "restricted",
        "blocked",
    )
    assert d.account_required and "H08" in d.retry_condition and d.dependents == ["T084"]


def test_no_data_committed(record):
    assert record("S39").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S39").check_local_hashes()


def test_limits_retry_after_and_terms(record):
    rec = record("S39")
    api = text(rec, "e01")
    assert "https://api.telegram.org/bot<token>/METHOD_NAME" in api and "retry_after" in api
    faq = text(rec, "e02")
    assert "In a group, bots are not be able to send more than 20 messages per minute" in faq
    assert "shall constitute your acceptance" in text(rec, "e03")
