"""T117 acceptance: the S34 (KSDMA dam level reports) discovery record passes the discovery contract
only with cited evidence and explicit access, licence and history status."""

import html
import re
from collections import Counter
from datetime import datetime


def archive_labels(path) -> list[str]:
    page = path.read_text(encoding="utf-8", errors="replace")
    return [
        re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", text))).strip()
        for _, text in re.findall(r'(?is)<a[^>]*href="([^"]+\.pdf)"[^>]*>(.*?)</a>', page)
    ]


def parse(label: str):
    try:
        return datetime.strptime(label, "%d/%m/%Y").date()
    except ValueError:
        return None


def test_s34_discovery_contract(record):
    assert record("S34").problems() == []


def test_s34_status(record):
    d = record("S34").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.units.status) == (
        "restricted",
        "available",
        "labelled",
    )
    assert d.source_check.status == "pass_with_manual_review"
    assert (d.earliest_date, d.latest_date) == ("2020-06-20", "2026-11-04")


def test_no_reports_committed(record):
    assert record("S34").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S34").check_local_hashes()


def test_archive_span_and_label_errors(record):
    labels = archive_labels(record("S34").raw("e04"))
    dates = [parse(x) for x in labels]
    valid = sorted({d for d in dates if d and d.year < 2100})
    assert (len(labels), sum(d is not None for d in dates), len(valid)) == (2322, 2305, 2296)
    assert (valid[0].isoformat(), valid[-1].isoformat()) == ("2020-06-20", "2026-11-04")
    assert Counter(d.year for d in valid)[2021] == 357
    unparsed = [x for x, d in zip(labels, dates, strict=True) if d is None]
    assert {"31/11/2020", "31/09/2024", "12/06/02023", "/07/2026"} <= set(unparsed)
    assert any(d and d.year > 2100 for d in dates)  # one label is in the year 2121


def test_archive_reports_are_scanned_images(record):
    for eid, pages in (("e08", 6), ("e10", 7), ("e12", 9)):
        pdf = record("S34").raw(eid).read_bytes()
        assert len(re.findall(rb"/Subtype\s*/Image", pdf)) == pages, eid
