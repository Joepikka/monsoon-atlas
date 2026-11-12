"""T089 blocked branch: no flood labels, features or probabilities without S43; the fallback
rainfall exposure index sums real S01 forecast hours per ward and is labelled non-probabilistic."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.features import m01
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s01 import S01

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
CELL = "om_ecmwf_ifs025_13.0000N_77.5000E"


def s01_table():
    def artifact(path: Path) -> RawArtifact:
        return RawArtifact(
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            path=path,
            fetched_at=datetime(2026, 11, 5, 12, 55, tzinfo=UTC),
            media_type="application/json",
            response_status=200,
            source_url="https://api.open-meteo.com/v1/forecast",
            schema_mapping_version="s01-v1",
        )

    config = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S01")
    forecast = FIX / "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
    meta = FIX / "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
    return S01("ka", [(12.97, 77.59)]).parse(artifact(forecast), config, meta=artifact(meta))


def test_gate_reports_the_blocked_label_source_with_evidence_hashes():
    gate = m01.data_gate()
    assert (gate["model_id"], gate["status"], gate["prediction_rows"]) == ("M01", "blocked", 0)
    assert gate["sources"]["S43"]["outcome"] == "blocked" and gate["split_manifest"] is None
    for name, sha in gate["evidence"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    assert json.loads((ROOT / "reports/models/m01-data-gate.json").read_text("utf-8")) == gate


def test_plan_target_is_preserved_without_claiming_labels_exist():
    config = yaml.safe_load((ROOT / "configs/models/m01.yaml").read_text("utf-8"))
    assert config["enabled"] is False and config["status"] == "blocked"
    assert config["target"]["horizon_hours"] == 24
    assert config["data_gate"]["min_positive_ward_days"] == 100
    assert config["planned_splits"]["locked_test"] == ["2024-01-01", "2024-12-31"]


@pytest.mark.parametrize("operation", ["build_features", "export_predictions"])
def test_blocked_branch_does_not_consume_input(operation):
    with pytest.raises(SourceUnavailable, match="M01 blocked"):
        getattr(m01, operation)(object())


def test_exposure_index_sums_the_next_24_forecast_hours():
    table = s01_table()
    issued = datetime(2026, 11, 5, tzinfo=UTC)
    index = m01.exposure_index(table, {"ward-a": CELL, "ward-b": "no-such-cell"}, issued)
    rows = {r["ward_id"]: r for r in index.to_pylist()}
    hours = [
        r["rain_mm"]
        for r in table.to_pylist()
        if issued < r["valid_at"] <= datetime(2026, 11, 6, tzinfo=UTC)
    ]
    assert len(hours) == 24 and rows["ward-a"]["rain_next_24h_mm"] == round(sum(hours), 3)
    assert rows["ward-a"]["forecast_issued_at"] == datetime(2026, 11, 5, tzinfo=UTC)
    assert rows["ward-b"]["rain_next_24h_mm"] is None
    assert rows["ward-b"]["missing_reason"] == "not_yet_available"
    assert set(index["probabilistic"].to_pylist()) == {False}
    assert "not a flood probability" in rows["ward-a"]["label"]


def test_exposure_index_never_uses_hours_past_the_forecast_end():
    table = s01_table()
    late = datetime(2026, 11, 20, 12, tzinfo=UTC)  # the run's last 23 hours have no rain
    row = m01.exposure_index(table, {"ward-a": CELL}, late).to_pylist()[0]
    assert row["rain_next_24h_mm"] is None
