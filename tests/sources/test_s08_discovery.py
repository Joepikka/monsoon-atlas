"""T057 acceptance: the S08 (IMD Pune gridded rainfall) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status."""

import html
import re

import numpy as np

NX, NY = 135, 129  # longitude 66.5E to 100.0E, latitude 6.5N to 38.5N, 0.25 degree
DAYS = {"e04": 366, "e05": 365, "e06": 365}  # 2024 is a leap year; 1901 and 2025 are not


def text(path) -> str:
    page = path.read_text(encoding="utf-8", errors="replace")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


def grid(path, days: int) -> np.ndarray:
    return np.fromfile(path, dtype="<f4").reshape(days, NY, NX)


def cell(lat: float, lon: float) -> tuple[int, int]:
    return round((lat - 6.5) / 0.25), round((lon - 66.5) / 0.25)


def test_s08_discovery_contract(record):
    assert record("S08").problems() == []


def test_s08_status(record):
    d = record("S08").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "restricted",
        "available",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert (d.earliest_date, d.latest_date) == ("1901-01-01", "2025-12-31")
    assert {"T058", "T101", "T102", "T103"} <= set(d.dependents)


def test_no_data_committed(record):
    assert record("S08").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S08").check_local_hashes()


def test_file_size_is_days_times_grid(record):
    sizes = {e.id: e.bytes for e in record("S08").manifest.evidence}
    for eid, days in DAYS.items():
        assert sizes[eid] == days * NX * NY * 4, eid  # float32, no header


def test_page_states_grid_units_and_years(record):
    rec = record("S08")
    page = text(rec.raw("e03"))
    for phrase in ("135x129 grid points", "millimeter (mm)", "1901 to 2024", "UNDEF -999.0"):
        assert phrase in page, phrase
    assert "XDEF 135 LINEAR 66.5 0.25 YDEF 129 LINEAR 6.5 0.25" in page
    years = re.findall(r'<option value=\s*"(\d{4})"', rec.raw("e03").read_text("utf-8"))
    assert (min(years), max(years), len(years)) == ("1901", "2025", 125)
    assert "should not be reproduced anywhere without prior permission" in text(rec.raw("e02"))


def test_grids_parse_with_a_fixed_land_mask(record):
    rec = record("S08")
    masks = []
    for eid, days in DAYS.items():
        a = grid(rec.raw(eid), days)
        land = a[0] != -999
        assert ((a == -999) == ~land).all(), eid  # -999 only outside land, on every day
        assert a[:, land].min() >= 0, eid
        masks.append(land)
    assert masks[0].sum() == 4964 and all((m == masks[0]).all() for m in masks)


def test_2024_totals_are_plausible(record):
    a = grid(record("S08").raw("e04"), DAYS["e04"])
    bengaluru, agumbe = a[:, *cell(13.0, 77.5)].sum(), a[:, *cell(13.5, 75.0)].sum()
    assert 900 < bengaluru < 1100 and agumbe > 5000  # little-endian read, not byte-swapped
