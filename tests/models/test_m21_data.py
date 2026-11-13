"""T280 acceptance: the M21 split manifest and data gate match the plan and their hashes; the
locked test is neither scored nor opened; baselines are scored on train and tune only; the
report shows the gate's tune numbers. Real IMD rain checks (S08 1981-2025, local raw; skipped in
CI): the dataset hash, the dry-month rule, the lag rules and a future-data mutation test."""

import json
import re
from datetime import date
from functools import cache
from pathlib import Path

import pyarrow as pa
import pytest
import yaml

from atlas.features.base import LeakageError
from atlas.models import m21_data as m21

ROOT = Path(__file__).resolve().parents[2]
GATE = json.loads((ROOT / "models/gates/m21.json").read_text("utf-8"))
REPORT = (ROOT / "reports/models/m21-data.md").read_text("utf-8")


def test_split_manifest_matches_the_plan_and_the_gate(tmp_path):
    digest = m21.write_split_manifest(tmp_path / "s.json")
    committed = json.loads((ROOT / "models/gates/m21_splits.json").read_text("utf-8"))
    assert digest == committed["sha256"] == GATE["split_sha256"]
    spans = {s.name: (s.test_start, s.test_end) for s in m21.splits()}
    assert spans == {
        "tune": (date(2015, 1, 1), date(2017, 12, 31)),
        "calibrate": (date(2018, 1, 1), date(2019, 12, 31)),
        "test": (date(2020, 1, 1), date(2025, 12, 31)),
    }
    for s in m21.splits():
        assert (s.train_start, s.train_end, s.purge_days) == (
            date(1982, 1, 1),
            date(2014, 11, 30),
            31,
        )


def test_gate_keeps_the_test_closed_and_scores_train_and_tune_only():
    assert GATE["status"] == "ok" and GATE["years"] == [1981, 2025]
    assert GATE["test_opened"] is False and GATE["candidate"] is None
    assert set(GATE["baselines"]) == {"train", "tune"}
    assert GATE["rows"]["test"] == 6 * (360 - GATE["dry_rule"]["excluded_district_months"])
    assert len(GATE["dataset_sha256"]) == 64 and "hindcast" in GATE["evidence"]
    tune = GATE["baselines"]["tune"]
    assert tune["strongest"] == min(tune["mae"], key=tune["mae"].get)
    assert tune["rows"] == GATE["rows"]["tune"] and tune["months"] == 36


def test_scoring_refuses_rows_after_the_tune_period():
    for month in (date(2018, 1, 1), date(2020, 1, 1)):
        rows = pa.table(
            {
                "target_month": [month],
                "target_anom": [0.0],
                "anom_lag1": [0.0],
                "anom_lag12": [0.0],
            }
        )
        with pytest.raises(LeakageError, match="not scored"):
            m21.score_baselines(rows)


def test_report_and_config_match_the_gate():
    tune = GATE["baselines"]["tune"]
    for name, label in (
        ("climatology", "Climatology"),
        ("persistence", "Persistence"),
        ("last_year", "Same month last year"),
    ):
        row = re.search(rf"\| {label}[^|]*\| ([0-9.]+) \|", REPORT)
        assert row and float(row.group(1)) == round(tune["mae"][name], 3), name
    assert "not scored" in REPORT and "hindcast" in REPORT
    config = yaml.safe_load((ROOT / "configs/models/m21.yaml").read_text("utf-8"))
    assert config["model_id"] == "M21" and config["enabled"] is False
    assert config["rain_source"] == "S08" and config["data_gate"] == "models/gates/m21.json"


# --- real IMD rain (local only) ---------------------------------------------------------------


@cache
def monthly() -> pa.Table:
    pytest.importorskip("shapely")
    pytest.importorskip("scipy")
    from atlas.config import load_state
    from atlas.contracts import RawArtifact
    from atlas.features import m05
    from atlas.ingest.base import SourceUnavailable
    from atlas.ingest.s17 import S17

    raw = ROOT / "data" / "raw"
    manifest = json.loads((ROOT / "tests/fixtures/s17/manifest.json").read_text("utf-8"))

    def s17(eid: str) -> RawArtifact:
        e = next(x for x in manifest["evidence"] if x["id"] == eid)
        if not (raw / e["raw_path"]).exists():
            pytest.skip("raw evidence is local only")
        return RawArtifact(
            sha256=e["sha256"],
            path=raw / e["raw_path"],
            fetched_at=e["fetched_at"],
            media_type=e["media_type"],
            response_status=e["status"],
            source_url=e["url"],
            schema_mapping_version="test",
        )

    try:
        raws = m05.year_artifacts(raw, range(1981, 2026))
    except SourceUnavailable:
        pytest.skip("S08 1981-2025 year files are local only")
    ka = load_state(ROOT / "configs/states/ka.yaml")
    return m05.district_monthly_rain(
        raws, S17("ka").parse(s17("e06"), ka.source("S17"), adm1=s17("e05"))
    )


@cache
def rows() -> pa.Table:
    return m21.dataset(monthly())


def test_dataset_reproduces_the_gate_hash_and_counts():
    from atlas.models.m05 import rows_in, table_sha256

    t = rows()
    assert table_sha256(t) == GATE["dataset_sha256"]
    assert rows_in(t, *m21.TRAIN).num_rows == GATE["rows"]["train"]
    assert "rain_mm" not in t.column_names  # indices only, never mm


def test_dry_rule_target_and_lag_rules():
    ref = m21.reference(monthly())
    dry = {k for k, s in ref.items() if s["dry"]}
    assert len(dry) == GATE["dry_rule"]["excluded_district_months"]
    f = rows().to_pylist()
    assert all((r["place_id"], r["month_of_year"]) not in dry for r in f)  # never scored as 0
    assert all(r["known_until"] < r["target_month"] for r in f)
    by_key = {(r["place_id"], r["target_month"]): r for r in f}
    for r in f[:2000]:
        prev = by_key.get((r["place_id"], r["known_until"]))
        if prev:
            assert r["anom_lag1"] == prev["target_anom"]  # last month's target is this feature
    ref_z = [r["target_anom"] for r in f if r["target_month"].year <= 2010]
    mean = sum(ref_z) / len(ref_z)
    assert (
        abs(mean) < 0.05 and 0.9 < (sum((z - mean) ** 2 for z in ref_z) / len(ref_z)) ** 0.5 < 1.1
    )


def test_future_data_mutation_cannot_change_earlier_features():
    base = monthly()
    month = date(2016, 6, 1)  # a tune month, so the locked test is not touched
    rain = [
        r * 10 + 500 if m == month else r
        for r, m in zip(base["rain_mm"].to_pylist(), base["month"].to_pylist(), strict=True)
    ]
    mutated = m21.dataset(base.set_column(3, "rain_mm", pa.array(rain)))
    before = {(r["place_id"], r["target_month"]): r for r in rows().to_pylist()}
    after = {(r["place_id"], r["target_month"]): r for r in mutated.to_pylist()}
    for key, r in before.items():
        if key[1] <= month:
            assert {k: after[key][k] for k in m21.FEATURES} == {k: r[k] for k in m21.FEATURES}
    june = [k for k in before if k[1] == month]
    assert june and all(after[k]["target_anom"] != before[k]["target_anom"] for k in june)
    july = [k for k in before if k[1] == date(2016, 7, 1)]
    assert all(after[k]["anom_lag1"] != before[k]["anom_lag1"] for k in july)  # control
