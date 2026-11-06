"""T037: blocked data is reported without a release, score or serving fallback."""

import hashlib
import json
from pathlib import Path

import pytest

from atlas.features.m06 import data_gate
from atlas.models.registry import champion

ROOT = Path(__file__).resolve().parents[2]


def test_blocked_manifest_preserves_actual_evidence():
    path = ROOT / "models/registry/m06.json"
    assert path.exists(), "M06 status record missing"
    status = json.loads(path.read_text("utf-8"))
    assert status["model_id"] == "M06" and status["status"] == "blocked"
    assert status["evidence"] == data_gate()["evidence"]
    gate_path = ROOT / "reports/models/m06-data-gate.json"
    assert status["source_gate_sha256"] == hashlib.sha256(gate_path.read_bytes()).hexdigest()
    assert status["prediction_rows"] == 0
    for key in (
        "dataset_sha256",
        "split_sha256",
        "weights",
        "baseline_scores",
        "candidate_scores",
        "improvement",
    ):
        assert status[key] is None, key


def test_blocked_status_cannot_become_a_champion():
    with pytest.raises(LookupError, match="no releases for M06"):
        champion(ROOT / "models/registry", "M06")


def test_report_distinguishes_planned_target_from_achieved_metrics():
    path = ROOT / "reports/models/m06.md"
    assert path.exists(), "M06 blocked report missing"
    report = path.read_text("utf-8")
    assert "Not evaluated" in report and "unverified" in report
    assert "m06-data-gate.json" in report
    assert "No price forecast" in report
