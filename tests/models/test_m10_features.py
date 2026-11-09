"""T139 blocked branch: M10 has no labels, features or predictions; the gate cites real
source evidence."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from atlas.features import m10
from atlas.ingest.base import SourceUnavailable

ROOT = Path(__file__).resolve().parents[2]


def test_gate_reports_the_blocked_sources_with_evidence_hashes():
    gate = m10.data_gate()
    assert (gate["model_id"], gate["status"], gate["prediction_rows"]) == ("M10", "blocked", 0)
    assert gate["sources"]["S22"]["outcome"] == "blocked"
    assert gate["sources"]["S23"]["latest_date"] == "2026-11-05" and gate["split_manifest"] is None
    for name, sha in gate["evidence"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    assert json.loads((ROOT / "reports/models/m10-data-gate.json").read_text("utf-8")) == gate


def test_plan_target_is_preserved_without_claiming_labels_exist():
    config = yaml.safe_load((ROOT / "configs/models/m10.yaml").read_text("utf-8"))
    assert config["enabled"] is False and config["status"] == "blocked"
    assert config["model_id"] == "M10" and config["split_manifest"] is None
    assert config["fallback"].startswith("none")


@pytest.mark.parametrize("operation", ["build_features", "export_predictions"])
def test_blocked_branch_does_not_consume_input(operation):
    with pytest.raises(SourceUnavailable, match="M10 blocked"):
        getattr(m10, operation)(object())
