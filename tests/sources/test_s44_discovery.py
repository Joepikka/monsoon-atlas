"""T087 acceptance: the S44 (district crime statistics) discovery record passes the discovery
contract; licence label, police units and table layouts are checked against the evidence."""

import csv
import html
import io
import re


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def rows(rec, eid) -> list[list[str]]:
    return list(csv.reader(io.StringIO(rec.raw(eid).read_bytes().decode("utf-8-sig"))))


def test_s44_discovery_contract(record):
    assert record("S44").problems() == []


def test_s44_status(record):
    d = record("S44").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert (d.earliest_date, d.latest_date) == ("2022-01-01", "2025-12-31")


def test_no_data_committed(record):
    assert record("S44").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S44").check_local_hashes()


def test_licence_label_and_source(record):
    page = text(record("S44"), "e01")
    assert "License Other (Public Domain)" in page and "Source ksp.karnataka.gov.in" in page


def test_police_units_and_layouts(record):
    rec = record("S44")
    y2024 = rows(rec, "e04")
    assert y2024[0][:4] == ["Sl No", "DISTRICT/UNITS", "MURDER", "ATTEMPT TO MURDER"]
    units = [r[1] for r in y2024[1:]]
    assert {
        "Bengaluru City",
        "Bengaluru Dist",
        "Karnataka Railways",
        "CID",
        "Central Range",
    } <= set(units)
    assert units[-1] == "Total"
    y2023 = rows(rec, "e05")
    assert y2023[0] == ["Districts", "IPC Cases", "SLL Cases", "Total"]
    assert y2023[-1][0] == "TOTAL" and "Shimoga" in [r[0] for r in y2023]
