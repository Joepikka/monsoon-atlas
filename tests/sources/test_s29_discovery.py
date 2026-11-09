"""T079 acceptance: the S29 (OpenCity KSNDMC hobli rainfall) discovery record passes the discovery
contract; the annual-only coverage, licence label, layouts and hierarchy counts are checked
against the evidence (D113)."""

import csv
import html
import io
import re
from collections import Counter


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def rows(rec, eid) -> list[list[str]]:
    raw = rec.raw(eid).read_bytes()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("cp1252")
    return list(csv.reader(io.StringIO(content)))


def test_s29_discovery_contract(record):
    assert record("S29").problems() == []


def test_s29_status(record):
    d = record("S29").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert (d.earliest_date, d.latest_date) == ("2020-01-01", "2025-12-31")


def test_no_data_committed(record):
    assert record("S29").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S29").check_local_hashes()


def test_licence_label_and_crawl_delay(record):
    rec = record("S29")
    page = text(rec, "e02")
    assert "License Other (Public Domain)" in page and "Source https://www.ksndmc.org/" in page
    assert "Crawl-Delay: 10" in rec.raw("e01").read_text("utf-8")


def test_layouts_levels_and_units(record):
    rec = record("S29")
    levels = {}
    for eid in ("e05", "e06", "e08"):
        body = rows(rec, eid)
        assert body[0][2:4] == ["Normal (mm)", "Actual (mm)"], eid
        levels[eid] = Counter(r[0] for r in body[1:] if r and r[0])
    assert levels["e05"] == levels["e06"] == {"D": 31, "T": 227, "H": 850}
    assert levels["e08"] == {"D": 31, "T": 236, "H": 850}
    assert rows(rec, "e09")[0][:4] == ["Sl.No", "District/Taluk/Hobli", "Normal_mm", "Actual_mm"]
    stations = rows(rec, "e07")
    assert stations[0] == ["DISTRICT", "TALUK", "STATION", "TOTAL_RAIN (mm)"]
    assert len(stations) - 1 == 5266
