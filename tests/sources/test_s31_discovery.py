"""T081 acceptance: the S31 (Karnataka RERA) discovery record passes the discovery contract as a
blocked result: reuse needs K-RERA's emailed permission; the list contents and the individual
promoter names are checked against the evidence."""

import html
import re


def text(rec, eid) -> str:
    page = rec.raw(eid).read_text("utf-8", errors="replace")
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", page, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s31_discovery_contract(record):
    assert record("S31").problems() == []


def test_s31_is_blocked_on_permission(record):
    d = record("S31").discovery
    assert (d.outcome, d.licence.status, d.source_check.status) == (
        "blocked",
        "restricted",
        "blocked",
    )
    assert d.dependents == ["T082"] and "permission" in d.retry_condition


def test_no_data_committed(record):
    assert record("S31").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S31").check_local_hashes()


def test_copyright_policy_requires_permission(record):
    policy = text(record("S31"), "e03")
    assert (
        "may be reproduced free of charge after taking proper permission by sending a mail"
        in policy
    )


def test_list_is_embedded_and_has_no_captcha(record):
    page = record("S31").raw("e02").read_text("utf-8", errors="replace")
    applications = re.findall(r"appNo : '([^']+)'", page)
    registered = re.findall(r"applicationNameList2\s*\.push\('(PRM[^']*)'\)", page)
    assert (len(applications), len(registered)) == (10106, 9065)
    assert "captcha" not in page.lower()
