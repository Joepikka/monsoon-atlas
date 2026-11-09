"""T091: blocked M01 is reported without a release, score or serving fallback beyond the labelled
exposure index."""

import hashlib
import json
from pathlib import Path

import pytest

from atlas.features.m01 import data_gate
from atlas.models.registry import champion

ROOT = Path(__file__).resolve().parents[2]


def test_status_record_binds_the_gate_and_holds_no_results():
    status = json.loads((ROOT / "models/registry/m01.json").read_text("utf-8"))
    assert (status["model_id"], status["status"], status["prediction_rows"]) == (
        "M01",
        "blocked",
        0,
    )
    assert status["evidence"] == data_gate()["evidence"]
    gate = (ROOT / "reports/models/m01-data-gate.json").read_bytes()
    assert status["source_gate_sha256"] == hashlib.sha256(gate).hexdigest()
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
    with pytest.raises(LookupError, match="no releases for M01"):
        champion(ROOT / "models/registry", "M01")


def test_report_separates_plan_from_results_and_labels_the_fallback():
    report = (ROOT / "reports/models/m01.md").read_text("utf-8")
    assert "Not evaluated" in report and "No flood probability" in report
    assert "not a flood probability" in report and "m01-data-gate.json" in report
