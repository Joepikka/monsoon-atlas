"""T125 acceptance: the S41 (permitted news RSS) discovery record passes the discovery contract
only with cited evidence and explicit access, licence and history status."""

import re


def text(path) -> str:
    page = path.read_text(encoding="utf-8", errors="replace")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))


def test_s41_discovery_contract(record):
    assert record("S41").problems() == []


def test_s41_is_blocked_with_explicit_status(record):
    d = record("S41").discovery
    assert d.outcome == "blocked"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "restricted",
        "partial",
        "fail",
    )
    assert d.no_card and not d.account_required
    assert {"T126", "T211"} <= set(d.dependents)
    assert "written permission" in d.retry_condition
    assert len(d.failed_fetches) == 2


def test_only_manifest_committed(record):
    assert record("S41").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S41").check_local_hashes()


def test_mathrubhumi_robots_publishes_kerala_feed(record):
    robots = record("S41").raw("e01").read_text(encoding="utf-8")
    assert "Sitemap: https://english.mathrubhumi.com/rss/news/kerala" in robots
    assert "Crawl-delay" not in robots


def test_kerala_feed_fields_and_offset(record):
    feed = record("S41").raw("e02").read_text(encoding="utf-8")
    item = feed[feed.index("<item>") : feed.index("</item>")]
    tags = set(re.findall(r"<(\w+)>", item))
    assert {"title", "link", "guid", "category", "description", "pubDate"} <= tags
    assert "language" not in feed
    assert re.search(r"<pubDate>\w{3}, \d\d \w{3} 20\d\d [\d:]{8} \+0530</pubDate>", item)


def test_terms_restrict_to_personal_use(record):
    r = record("S41")
    mb = text(r.raw("e04"))
    assert "personal, non-commercial consumption and use only" in mb
    assert "prior written consent" in mb
    assert "personal use of RSS feeds" in text(r.raw("e09"))
    assert "personal use of its RSS feeds" in text(r.raw("e11"))
    assert "personal use only" in text(r.raw("e07"))
    assert "automatically agree" in text(r.raw("e06"))
