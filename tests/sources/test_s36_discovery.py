"""T121 acceptance: the S36 (KSDMA post-disaster assessment) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status."""

import re
import shutil
import subprocess

import pytest


def page_text(path, page: int) -> str:
    """One PDF page as text. The PDFs use Identity-H fonts, so the stdlib cannot read them."""
    exe = shutil.which("pdftotext")
    if not exe:
        pytest.skip("pdftotext not on PATH (T122 pins a PDF parser)")
    args = [exe, "-layout", "-f", str(page), "-l", str(page), str(path), "-"]
    return subprocess.run(args, capture_output=True, check=True).stdout.decode("utf-8", "replace")


def pdf_pages(path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?!s)", path.read_bytes()))


def test_s36_discovery_contract(record):
    assert record("S36").problems() == []


def test_s36_status(record):
    d = record("S36").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "restricted",
        "partial",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert {"T122", "T133", "T134", "T135"} <= set(d.dependents)
    assert (d.earliest_date, d.latest_date) == ("2013-06-01", "2018-08-30")


def test_no_documents_committed(record):
    assert record("S36").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S36").check_local_hashes()


def test_revalidated_memorandum_is_the_s35_copy(record):
    e07 = next(e for e in record("S36").manifest.evidence if e.id == "e07")
    s35 = next(e for e in record("S35").manifest.evidence if e.id == "e06")
    assert e07.status == 304
    assert (e07.url, e07.sha256, e07.raw_path) == (s35.url, s35.sha256, s35.raw_path)


def test_memoranda_page_lists_2018_and_2013_memoranda(record):
    page = record("S36").raw("e03").read_text(encoding="utf-8")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
    assert "29th May to 31st July 2018" in text and "Submitted on: 7-08-2018" in text
    assert "1st August to 30th August 2018" in text and "Submitted on: 13-09-2018" in text
    for name in ("Memorandum1-Floods-2018.pdf", "6.Memorandum-Monsoon-Calamity-2013.pdf"):
        assert name in page, name
    assert "All rights reserved" in page


def test_inundation_maps_are_single_images(record):
    rec = record("S36")
    maps = rec.raw("e05").read_text(encoding="utf-8")
    assert "Flood_2018-1.pdf" in maps and "FLOOD_INUNDATION2013.pdf" in maps
    for eid in ("e09", "e10"):
        assert pdf_pages(rec.raw(eid)) == 1, eid
    assert b"/Font" not in rec.raw("e10").read_bytes()  # 2013 map: one raster, no text layer


def test_only_dated_district_table_and_fatality_totals(record):
    rec = record("S36")
    flooded = page_text(rec.raw("e06"), 9)
    assert "as on 16-7-2018" in flooded
    table = flooded[flooded.index("Flooded Area (ha)") : flooded.index("Total")]
    rows = dict(re.findall(r"(?m)^\s*([A-Z][a-z]+)\s+(\d+)\s*$", table))
    assert len(rows) == 7 and sum(map(int, rows.values())) == 55007
    fatal = page_text(rec.raw("e07"), 20)
    rows = re.findall(r"(?m)^\s*([A-Z][a-z]+)\s+(\d+)\s+(\d+)\s*$", fatal)
    districts = {d: int(n) for d, n, _ in rows if d != "Total"}
    assert len(districts) == 14 and sum(districts.values()) == 339
    assert all(int(cost) == 4 * int(n) for _, n, cost in rows)  # relief at Rs 4 lakh per death
