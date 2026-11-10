"""T167 blocked branch: M19 has no labels, features or predictions; the gate cites real
source evidence."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from atlas.features import m19
from atlas.ingest.base import SourceUnavailable

ROOT = Path(__file__).resolve().parents[2]


def test_gate_reports_the_blocked_sources_with_evidence_hashes():
    gate = m19.data_gate()
    assert (gate["model_id"], gate["status"], gate["prediction_rows"]) == ("M19", "blocked", 0)
    assert gate["sources"]["S28"]["outcome"] == "blocked"
    assert gate["sources"]["S28"]["history"] == "not_public"
    assert gate["split_manifest"] is None
    for name, sha in gate["evidence"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    assert json.loads((ROOT / "reports/models/m19-data-gate.json").read_text("utf-8")) == gate


def test_plan_target_is_preserved_without_claiming_labels_exist():
    config = yaml.safe_load((ROOT / "configs/models/m19.yaml").read_text("utf-8"))
    assert config["enabled"] is False and config["status"] == "blocked"
    assert config["model_id"] == "M19" and config["split_manifest"] is None
    assert config["fallback"].startswith("none")
    assert config["depends_on"] == ["M02"]


def test_upstream_models_are_blocked():
    for model in ["M02"]:
        record = json.loads((ROOT / f"models/registry/{model.lower()}.json").read_text("utf-8"))
        assert (record["status"], record["prediction_rows"]) == ("blocked", 0), model


@pytest.mark.parametrize("operation", ["build_features", "export_predictions"])
def test_blocked_branch_does_not_consume_input(operation):
    with pytest.raises(SourceUnavailable, match="M19 blocked"):
        getattr(m19, operation)(object())
