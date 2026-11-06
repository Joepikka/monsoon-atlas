"""T035 blocked branch: no labels/features/predictions without verified price history."""

import hashlib
import importlib
import json
from pathlib import Path

import pytest
import yaml

from atlas.ingest.base import SourceUnavailable

ROOT = Path(__file__).resolve().parents[2]


def module():
    assert importlib.util.find_spec("atlas.features.m06") is not None, "M06 data gate missing"
    return importlib.import_module("atlas.features.m06")


def test_gate_reports_real_source_failures_and_evidence_hashes():
    gate = module().data_gate()
    assert gate["status"] == "blocked" and gate["model_id"] == "M06"
    assert gate["prediction_rows"] == 0
    assert gate["sources"]["S22"]["outcome"] == "blocked"
    assert gate["sources"]["S23"]["licence"] == "open"
    assert gate["sources"]["S23"]["units"] == "unlabelled"
    assert gate["sources"]["S23"]["earliest_date"] == "2026-11-05"
    assert gate["split_manifest"] is None
    for name, sha in gate["evidence"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    assert json.loads((ROOT / "reports/models/m06-data-gate.json").read_text("utf-8")) == gate


def test_plan_target_is_preserved_without_claiming_labels_exist():
    path = ROOT / "configs/models/m06.yaml"
    assert path.exists(), "M06 model configuration missing"
    config = yaml.safe_load(path.read_text("utf-8"))
    assert config["enabled"] is False and config["state"] == "ka"
    assert config["target"] == {
        "price_multiplier": 1.25,
        "prior_observed_days": 28,
        "min_prior_observations": 20,
        "horizon_calendar_days": 16,
        "min_future_observations": 8,
    }
    assert config["planned_splits"]["locked_test"] == ["2025-01-01", "2026-05-31"]
    assert config["label_publication_delay_days"] is None


@pytest.mark.parametrize("operation", ["build_features", "export_predictions"])
def test_blocked_branch_does_not_consume_input_or_export(operation):
    # An opaque sentinel is sufficient: blocked code must not even inspect data.
    with pytest.raises(SourceUnavailable, match="M06 blocked"):
        getattr(module(), operation)(object())
