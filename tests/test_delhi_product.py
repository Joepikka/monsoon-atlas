"""T165: Delhi transit, AQI and exposure interface, tested without any Delhi feed (D142).

S38 (bus positions) and S24 (station air quality) are blocked, so the real states are
"unavailable". The rules that need values (route-time-weighted ambient concentration, unit and
averaging comparison) run on small hand-built TEST INPUTS that are never presented as Delhi data.
The web components are tested in web/src/components/*.test.ts; here we check their constants.
"""

import json
import math
import os
import re
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from atlas.analysis.prices import load_record
from atlas.analysis.route_exposure import (
    AMBIENT_LABEL,
    Basis,
    Reading,
    Segment,
    blocked_card,
    blocked_view,
    compare_layers,
    planned_coverage,
    route_exposure,
)
from atlas.config import load_state
from atlas.ingest.s04 import UNIT

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "web/src/components"
NOTEBOOKS = {"08_delhi_transit": "transit_view.json", "09_delhi_air": "air_view.json"}
RECORD = {s: load_record(ROOT / f"configs/sources/{s.lower()}.yaml") for s in ("S04", "S24", "S38")}
T0 = datetime(2026, 11, 10, 6, 0, tzinfo=UTC)  # TEST INPUT time, not an observation


def basis(**over) -> Basis:
    return replace(Basis("observation", "pm2_5", "ug/m3", 60), **over)  # TEST INPUT


def seg(
    minutes_from: int, minutes: int, value: float, b: Basis | None = None, stamp=None
) -> Segment:
    start = T0 + timedelta(minutes=minutes_from)
    stamp = stamp or T0 + timedelta(hours=1)  # an hourly average ending at 07:00
    return Segment(
        start, start + timedelta(minutes=minutes), Reading(b or basis(), value, stamp, "end")
    )


def test_ambient_concentration_is_time_weighted_and_not_a_dose():
    got = route_exposure([seg(0, 10, 30.0), seg(10, 30, 50.0)])  # (30*600 + 50*1800) / 2400
    assert got["status"] == "computed" and math.isclose(got["ambient_concentration"], 45.0)
    assert (got["duration_s"], got["segments"], got["unit"]) == (2400.0, 2, "ug/m3")
    assert got["label"] == AMBIENT_LABEL and "not an inhaled dose" in AMBIENT_LABEL
    assert not [k for k in got if "dose" in k or "breath" in k or "inhal" in k]
    assert route_exposure([seg(30, 10, 5.0), seg(0, 10, 15.0)])["ambient_concentration"] == 10.0


def test_start_stamped_windows_are_honoured():
    start_stamped = Reading(basis(), 20.0, T0, "start")  # window 06:00 to 07:00
    ok = Segment(T0 + timedelta(minutes=5), T0 + timedelta(minutes=55), start_stamped)
    assert route_exposure([ok])["ambient_concentration"] == 20.0
    late = Segment(T0 + timedelta(minutes=50), T0 + timedelta(minutes=70), start_stamped)
    assert "outside" in route_exposure([late])["reason"]


@pytest.mark.parametrize(
    ("segments", "why"),
    [
        ([seg(0, 10, 30.0), seg(10, 10, 30.0, basis(unit="ppb"))], "unit differs"),
        ([seg(0, 10, 30.0), seg(10, 10, 30.0, basis(interval_minutes=1440))], "interval_minutes"),
        ([seg(0, 10, 30.0), seg(10, 10, 30.0, basis(kind="model"))], "kind differs"),
        ([seg(0, 10, 30.0), seg(10, 10, 30.0, basis(pollutant="no2"))], "pollutant differs"),
        ([seg(0, 10, 30.0, stamp=T0 - timedelta(minutes=1))], "outside"),  # window ends 05:59
        ([seg(55, 10, 30.0)], "outside"),  # runs past the 07:00 end of the hourly window
        ([seg(0, 10, 30.0, stamp=T0 + timedelta(hours=3))], "outside"),
        ([seg(0, 10, 30.0, basis(interval_minutes=0))], "instantaneous"),
        ([seg(0, 20, 30.0), seg(10, 20, 30.0)], "overlap"),
        ([seg(0, 0, 30.0)], "longer than zero"),
        ([seg(0, 10, -1.0)], "not negative"),
        ([seg(0, 10, math.nan)], "finite"),
        ([], "no segments"),
    ],
)
def test_exposure_refuses_unsafe_inputs_with_a_reason(segments, why):
    got = route_exposure(segments)
    assert got["status"] == "unavailable" and why in got["reason"], got
    assert "ambient_concentration" not in got


def test_exposure_needs_time_zones():
    naive = Segment(
        datetime(2026, 11, 10, 6), datetime(2026, 11, 10, 6, 10), Reading(basis(), 1.0, T0, "end")
    )
    assert "time zone" in route_exposure([naive])["reason"]
    with pytest.raises(ValueError, match="stamp_is"):
        Reading(basis(), 1.0, T0, "middle")
    with pytest.raises(ValueError, match="kind"):
        Basis("station", "pm2_5", "ug/m3", 60)


def test_station_and_model_layers_compare_only_on_identical_units_and_averaging():
    station, model = basis(), basis(kind="model")
    assert compare_layers(station, model) == {
        "status": "comparable",
        "pollutant": "pm2_5",
        "unit": "ug/m3",
        "interval_minutes": 60,
    }
    for other, why in [
        (basis(kind="model", unit="ppb"), "unit differs"),
        (basis(kind="model", interval_minutes=1440), "interval_minutes differs"),
        (basis(kind="model", pollutant="no2"), "pollutant differs"),
    ]:
        assert why in compare_layers(station, other)["reason"]
    assert "distinct" in compare_layers(station, station)["reason"]
    assert "distinct" in compare_layers(model, station)["reason"]  # layers cannot be swapped


def test_real_delhi_results_are_unavailable_with_the_source_outcomes():
    assert RECORD["S24"]["outcome"] == RECORD["S38"]["outcome"] == "blocked"
    assert "S24 blocked" in compare_layers(None, basis(kind="model"))["reason"]
    assert "S04 is not configured" in compare_layers(basis(), None)["reason"]
    reason = route_exposure(None)["reason"]
    assert "S38 blocked" in reason and "S24 blocked" in reason


def test_cams_basis_has_the_s04_unit_and_is_a_model_estimate():
    detail = RECORD["S04"]["units"]["detail"]
    assert RECORD["S04"]["units"]["status"] == "labelled" and UNIT in detail
    assert "instant" in detail
    pm25 = next(f for f in RECORD["S04"]["field_map"] if f["canonical"] == "pm25_ugm3")
    assert pm25["upstream"] == "pm2_5" and UNIT in pm25["detail"]


def test_delhi_has_no_station_or_model_air_source_enabled():
    dl = load_state(ROOT / "configs/states/dl.yaml")
    assert not any(s.enabled for s in dl.sources)
    assert "S04" not in {s.source_id for s in dl.sources}  # CAMS is Karnataka-only (D141)
    assert all(f["upstream"] is None for f in RECORD["S24"]["field_map"])  # nothing read


def test_blocked_views_use_the_source_record_and_refuse_available_ones():
    view = blocked_view(RECORD["S38"])
    assert view["state"] == "unavailable" and view["source_id"] == "S38"
    assert "H04" in view["retry_condition"] and "blocked" in view["reason"]
    with pytest.raises(ValueError, match="not blocked"):
        blocked_view(RECORD["S04"])


def test_blocked_cards_show_planned_coverage_and_no_score():
    for model, sid in (("m12", "S38"), ("m14", "S24")):
        registry = json.loads((ROOT / f"models/registry/{model}.json").read_text("utf-8"))
        config = load_record(ROOT / f"configs/models/{model}.yaml")
        card = blocked_card(registry, config)
        assert card["status"] == "blocked" and sid in card["reason"]
        assert set(card) == {"status", "model_id", "reason", "coverage"}  # no score of any kind
        assert card["coverage"] == planned_coverage(config)
        assert card["coverage"]["status"] == "planned, not started"
        assert card["coverage"]["test_period"] == ["2028-04-27", "2028-05-26"]
        assert card["coverage"]["months"] == [1, 2, 3, 4, 5]  # collect_from to end of locked test
    with pytest.raises(ValueError, match="not blocked"):
        blocked_card({"model_id": "M05", "status": "approved"}, config)


def test_late_gps_rule_matches_the_worker_and_no_component_is_mounted():
    worker = (ROOT / "worker/src/transit.ts").read_text("utf-8")
    transit = (COMPONENTS / "Transit.tsx").read_text("utf-8")
    assert re.search(r"export const STALE_SECONDS = 120;", worker)
    assert re.search(r"export const STALE_SECONDS = 120;", transit)  # one number, checked here
    for name in ("Transit", "AirQuality"):
        assert (COMPONENTS / f"{name}.tsx").exists() and (COMPONENTS / f"{name}.test.ts").exists()
    for path in (ROOT / "web/src").rglob("*.ts*"):
        if path.parent != COMPONENTS and ".test." not in path.name:
            text = path.read_text("utf-8")
            assert not re.search(r"/(Transit|AirQuality|ScoreCard)['\"]", text), path  # H11 gate


def test_component_labels_keep_layers_and_marker_kinds_separate():
    transit = (COMPONENTS / "Transit.tsx").read_text("utf-8")
    air = (COMPONENTS / "AirQuality.tsx").read_text("utf-8")
    for kind in ("scheduled", "live", "predicted"):
        assert re.search(rf"\b{kind}: '", transit), kind
    assert "not live" in transit and "not observed" in transit
    assert "Station measurement (observation)" in air
    assert "Gridded model estimate (CAMS), not a measurement" in air


def run_notebook(name: str, out: Path) -> None:
    nb = json.loads((ROOT / f"notebooks/{name}.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(out)}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_notebook_reproduces_from_a_clean_process(name, tmp_path):
    out = ROOT / "reports/eda" / name
    run_notebook(name, tmp_path)
    names = sorted(p.name for p in out.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    assert not [n for n in names if n.endswith((".png", ".svg"))]  # nothing exists to draw
    for n in names:
        assert (tmp_path / n).read_bytes() == (out / n).read_bytes(), n


def test_notebook_outputs_say_unavailable_and_blocked_and_hold_no_values():
    transit = json.loads((ROOT / "reports/eda/08_delhi_transit/summary.json").read_text("utf-8"))
    assert transit["positions_read"] == 0 and transit["adapter_error"].startswith("S38 is blocked")
    assert transit["markers"] == {"scheduled": 0, "live": 0, "predicted": 0}
    assert (
        transit["view"]["state"] == "unavailable" and transit["view"]["card"]["status"] == "blocked"
    )
    assert transit["fields"] == sum(transit["fields_by_unit_status"].values()) == 8
    assert transit["fields_by_unit_status"] == {"absent": 8}
    air = json.loads((ROOT / "reports/eda/09_delhi_air/summary.json").read_text("utf-8"))
    assert air["station_rows"] == 0 and air["adapter_error"].startswith("S24 is blocked")
    assert (air["s24_enabled_in_dl"], air["s04_listed_in_dl"]) == (False, False)
    assert air["comparison"]["status"] == air["route_exposure"]["status"] == "unavailable"
    assert air["cams_basis"] == {
        "kind": "model",
        "pollutant": "pm2_5",
        "unit": UNIT,
        "interval_minutes": 0,
    }
    assert air["view"]["station"]["layer"] == "station" and air["view"]["model"]["layer"] == "model"
    assert air["view"]["station"]["source_id"] != air["view"]["model"]["source_id"]
    # no future data: the only dates after the frozen discovery are the planned (not started) window
    planned = {"2028-01-17", "2028-04-27", "2028-05-26"}
    latest = max(
        d[:10] for r in RECORD.values() for d in (r["discovered_at"], r["latest_date"]) if d
    )  # S04's latest_date is the end of its forecast horizon
    for name in NOTEBOOKS:
        for p in (ROOT / "reports/eda" / name).glob("*.[cj][ss][vo]*"):
            for d in set(re.findall(r"\d{4}-\d{2}-\d{2}", p.read_text("utf-8"))):
                assert d <= latest or d in planned, (p.name, d)
    for name, view_file in NOTEBOOKS.items():
        view = json.loads((ROOT / "reports/eda" / name / view_file).read_text("utf-8"))
        assert view["card"]["status"] == "blocked"
