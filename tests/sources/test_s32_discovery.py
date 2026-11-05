"""T113 acceptance: the S32 (KSEB daily water level) discovery record passes the discovery contract
only with cited evidence and explicit access, licence and history status."""

import html
import re
from datetime import datetime

DAMS = {
    "IDUKKI", "IDAMALAYAR", "KAKKI (ANATHODE )", "BANASURASAGAR (K A SCHEME)", "SHOLAYAR",
    "MADUPETTY", "ANAYIRANKAL", "PONMUDI", "KUTTIYADI (KAKKAYAM)", "PAMBA", "PORINGALKUTHU",
    "KUNDALA", "KALLARKUTTY", "LOWER PERIYAR", "MOOZHIYAR", "SENGULAM (PUMPING STORAGE DAM)",
}  # fmt: skip


def report(path):
    """(as-on date, header, rows) of one daily report page."""
    page = path.read_text(encoding="utf-8", errors="replace")
    as_on = re.search(r"WATER LEVELS OF MAIN RESERVOIRS \(As on ([^)]+)\)", page)
    table = re.search(r"(?is)<table[^>]*>.*?Name of Dam.*?</table>", page)
    rows = [
        [
            re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", c))).strip()
            for c in re.findall(r"(?is)<t[hd][^>]*>(.*?)</t[hd]>", r)
        ]
        for r in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", table.group(0) if table else "")
    ]
    day = datetime.strptime(as_on.group(1), "%d-%b-%Y").date() if as_on else None
    return day, (rows[0] if rows else []), rows[1:]


def dated_pages(rec):
    for e in rec.manifest.evidence:
        if "?date=" in e.url:
            yield e.id, e.url.split("?date=")[1]


def test_s32_discovery_contract(record):
    assert record("S32").problems() == []


def test_s32_status(record):
    d = record("S32").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.units.status) == ("open", "partial", "labelled")
    assert (d.earliest_date, d.no_card, d.account_required) == ("2023-10-26", True, False)
    inflow = next(f for f in d.field_map if f.canonical == "inflow_m3s")
    assert "not converted" in inflow.detail  # MU is energy, not a flow


def test_no_reports_committed(record):
    assert record("S32").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S32").check_local_hashes()


def test_sixteen_dams_with_units_in_header(record):
    _, header, rows = report(record("S32").raw("e02"))
    assert {r[0] for r in rows} == DAMS
    assert header[2:5] == [
        "Today's Water level (metre)",
        "Today's Live Storage (MCM)",
        "%Storage wrt Live Storage at FRL",
    ]
    assert header[7] == "Inflow MU"


def test_report_date_comes_from_the_page_not_the_fetch(record):
    rec = record("S32")
    for eid, requested in dated_pages(rec):
        day, _, _ = report(rec.raw(eid))
        assert day.isoformat() == requested, eid


def test_coverage_matches_record(record):
    rec = record("S32")
    sample = {d: len(report(rec.raw(e))[2]) for e, d in dated_pages(rec) if e >= "e08"}
    assert len(sample) == 73 and set(sample.values()) == {0, 16}
    with_rows = sorted(d for d, n in sample.items() if n)
    assert (with_rows[0], with_rows[-1]) == ("2023-11-15", "2026-11-01")
    assert not [d for d in with_rows if "2024-08-15" <= d <= "2026-07-15"]
    assert len(report(rec.raw("e03"))[2]) == 16  # 2023-10-26, earliest found
    assert report(rec.raw("e04"))[2] == []  # 2023-10-25
    assert report(rec.raw("e05"))[2] == []  # 2018-08-15


def test_early_reports_break_header_units(record):
    rec = record("S32")
    first = {r[0]: r for r in report(rec.raw("e03"))[2]}  # 2023-10-26
    assert float(first["IDUKKI"][2]) > 2000  # feet, although the header says metre
    assert float(first["IDUKKI"][4]) > 100  # % storage scaled by 100
    december = {r[0]: r for r in report(rec.raw("e10"))[2]}  # 2023-12-01
    for r in december.values():
        assert float(r[4]) <= 100
    assert 700 < float(december["IDUKKI"][2]) < 735
