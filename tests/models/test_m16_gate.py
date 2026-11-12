"""T216: M16 is published as research-only with no score, interval or prediction."""

import hashlib
import json
from pathlib import Path

import pytest

from atlas.features import m16 as rule
from atlas.models import m16
from atlas.models.registry import Release, champion

ROOT = Path(__file__).resolve().parents[2]
STATUS = json.loads((ROOT / "models/registry/m16.json").read_text("utf-8"))
REPORT = (ROOT / "reports/models/m16.md").read_text("utf-8")


def test_status_is_the_framework_research_only_status_with_every_score_null():
    assert "research_only" in Release.model_fields["status"].annotation.__args__
    assert (STATUS["model_id"], STATUS["status"], STATUS["prediction_rows"]) == (
        "M16",
        "research_only",
        0,
    )
    for key in ("dataset_sha256", "split_sha256", "weights", "baseline_scores", "candidate_scores"):
        assert STATUS[key] is None, key
    assert STATUS["improvement"] is None
    assert STATUS["label_gate"] == {
        "adjudicated_flags": 0,
        "required": 100,
        "quality_claim_allowed": False,
    }


def test_status_and_gate_files_are_what_the_code_writes_and_bind_their_evidence():
    gate = rule.data_gate()
    assert json.loads((ROOT / "reports/models/m16-data-gate.json").read_text("utf-8")) == gate
    assert STATUS == m16.status_record()
    gate_bytes = (ROOT / "reports/models/m16-data-gate.json").read_bytes()
    assert STATUS["source_gate_sha256"] == hashlib.sha256(gate_bytes).hexdigest()
    for name, sha in gate["evidence"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, name
    assert gate["sources"]["S22"]["outcome"] == gate["sources"]["S23"]["outcome"] == "blocked"
    assert gate["split_manifest"] is None


def test_adjudication_record_is_consistent_with_the_status():
    record = json.loads((ROOT / "eval/anomalies/blocked.json").read_text("utf-8"))
    assert record["counts"]["flags_adjudicated"] == STATUS["label_gate"]["adjudicated_flags"] == 0
    assert record["counts"]["required_total"] == STATUS["label_gate"]["required"]


def test_research_only_status_cannot_become_a_champion_or_a_prediction():
    with pytest.raises(LookupError, match="no releases for M16"):
        champion(ROOT / "models/registry", "M16")
    assert not (ROOT / "models/registry/M16").exists()


def test_report_states_the_limits_and_makes_no_quality_claim():
    for phrase in (
        "research-only",
        "precision not measured (0 of 100",
        "not a real-world incident",
        "m16-flag-counts.json",
        "IsolationForest",
        "not measured",
    ):
        assert phrase in REPORT, phrase
    assert "Precision >=" not in REPORT and "precision of" not in REPORT.lower()
    totals = json.loads((ROOT / m16.COUNTS).read_text("utf-8"))["totals"]
    assert f"{totals['ka']['flags_z']:,}" in REPORT and f"{totals['kl']['flags_z']:,}" in REPORT
