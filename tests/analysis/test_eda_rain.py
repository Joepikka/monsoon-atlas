"""T107 acceptance: the Karnataka rainfall helpers use exact denominators, the S29-to-S17 district
crosswalk is explicit and complete, and the notebook re-run from a fresh process reproduces the
committed outputs byte for byte, with source dates and no data after the frozen fetches. S08 and
S29 raw files are local only, so the notebook run skips in CI; the helper checks always run."""

import csv
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

from atlas.analysis.rain import annual_grid_totals, compare, load_crosswalk, station_coverage

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/eda/02_ka_rain"
CROSSWALK = ROOT / "configs/crosswalks/s29_s17_districts.csv"
RAW = ROOT / "data/raw"
LOCAL = (RAW / "S08").exists() and (RAW / "S29").exists()
S29_NAMES = set(  # district names in the 2020-2024 S29 files (D113)
    "BAGALKOTE,BALLARI,BELAGAVI,BENGALURU RURAL,BENGALURU URBAN,BIDAR,CHAMARAJANAGARA,"
    "CHIKKABALLAPURA,CHIKKAMAGALURU,CHITRADURGA,DAKSHINA KANNADA,DAVANAGERE,DHARWAD,GADAG,HASSAN,"
    "HAVERI,KALABURAGI,KODAGU,KOLAR,KOPPALA,MANDYA,MYSURU,RAICHUR,RAMANAGARA,SHIVAMOGGA,TUMAKURU,"
    "UDUPI,UTTARA KANNADA,VIJAYAPURA,YADGIR,VIJAYANAGAR".split(",")
)
S17_NAMES = set(  # geoBoundaries S17 districts
    "Bagalkot,Bangalore,Bangalore Rural,Belgaum,Bellary,Bidar,Bijapur,Chamarajanagar,"
    "Chikkaballapura,Chikmagalur,Chitradurga,Dakshina Kannada,Davanagere,Dharwad,Gadag,Gulbarga,"
    "Hassan,Haveri,Kodagu,Kolar,Koppal,Mandya,Mysore,Raichur,Ramanagara,Shimoga,Tumkur,Udupi,"
    "Uttara Kannada,Yadgir".split(",")
)


def test_annual_grid_total_needs_all_twelve_months():
    def months(name, year, values):
        return [
            {"name": name, "month": date(year, m, 1), "rain_mm": v} for m, v in enumerate(values, 1)
        ]

    rows = months("A", 2020, [10.0] * 12) + months("B", 2020, [1.0] * 11 + [None])
    rows += months("C", 2021, [2.0] * 11)
    assert annual_grid_totals(rows) == {("A", 2020): 120.0, ("B", 2020): None, ("C", 2021): None}


def test_compare_denominators_and_bias_sign():
    gauge = [
        {"area_id": "X", "year": 2020, "rain_mm": 100.0},
        {"area_id": "X", "year": 2021, "rain_mm": 100.0},
        {"area_id": "Y", "year": 2020, "rain_mm": 50.0},
        {"area_id": "Z", "year": 2020, "rain_mm": None},
    ]
    grid = {("x", 2020): 125.0, ("z", 2020): 7.0}
    rows = compare(gauge, grid, {"X": "x", "Y": "y", "Z": "z"}, {("X", 2021): "split"})
    assert [r["status"] for r in rows] == ["compared", "excluded: split", "missing", "missing"]
    assert (rows[0]["bias_mm"], rows[0]["ratio"]) == (25.0, 1.25)  # grid minus gauge
    assert all(r["grid_mm"] is None for r in rows[1:3]) and rows[3]["grid_mm"] is None
    with pytest.raises(KeyError):
        compare([{"area_id": "Q", "year": 2020, "rain_mm": 1.0}], grid, {"X": "x"}, {})


def test_station_coverage_counts_every_station_in_its_district():
    rows = [
        {"area_id": "A / T1 / s1", "rain_mm": 1.0},
        {"area_id": "A / T1 / s2", "rain_mm": None},
        {"area_id": "A / T2 / s3", "rain_mm": 0.0},
        {"area_id": "B / T3 / s4", "rain_mm": 5.0},
    ]
    assert station_coverage(rows) == [
        {"district": "A", "stations": 3, "with_value": 2, "share": 2 / 3},
        {"district": "B", "stations": 1, "with_value": 1, "share": 1.0},
    ]


def test_crosswalk_is_explicit_one_to_one_and_covers_every_s29_name():
    cw = load_crosswalk(CROSSWALK)
    assert sorted(cw.values()) == sorted(S17_NAMES) and len(cw) == 30
    assert S29_NAMES - set(cw) == {"VIJAYANAGAR"}  # carved from Ballari in 2021: no S17 polygon
    assert set(cw) <= S29_NAMES


@pytest.mark.skipif(not LOCAL, reason="S08 and S29 raw files are local only")
def test_notebook_reproduces_from_a_clean_process(tmp_path):
    nb = json.loads((ROOT / "notebooks/02_ka_rain.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    names = sorted(p.name for p in OUT.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name

    summary = json.loads((OUT / "summary.json").read_text("utf-8"))
    s29, s08 = summary["s29"], summary["s08"]
    with open(OUT / "district_year_comparison.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    status = [r["status"] for r in rows]
    assert len(rows) == s29["district_years"] == 30 + 31 * 3  # 2020, 2021, 2022, 2024
    assert status.count("compared") == s29["compared"] == len(rows) - s29["excluded"]
    assert s29["excluded"] == sum(s29["excluded_by_district"].values()) == 6
    assert s29["missing"] == status.count("missing") == 0
    assert all(s.startswith("excluded: ") for s in status if s not in {"compared", "missing"})
    assert {r["year"] for r in rows} == {"2020", "2021", "2022", "2024"}
    assert "2023" not in {r["year"] for r in rows}  # 2023 has station totals only
    assert s08["grid_district_years"] == 30 * 5 and s08["grid_district_years_null"] == 0
    with open(OUT / "station_coverage_2023.csv", encoding="utf-8") as f:
        cov = list(csv.DictReader(f))
    assert sum(int(c["stations"]) for c in cov) == s29["stations"]
    assert sum(int(c["with_value"]) for c in cov) == s29["stations_with_value"]
    # no data from after the frozen fetches: every data year ends before the first fetch
    first_fetch = min(datetime.fromisoformat(t) for t in (s29["first_fetch"], s08["first_fetch"]))
    assert max(s29["years"]) <= 2024 and date.fromisoformat(s08["data_end"]) < first_fetch.date()
    assert any("Seasonal comparison impossible" in limit for limit in summary["limits"])
