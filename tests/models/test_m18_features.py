"""T209 blocked branch: M18 has no labels, features or predictions; the gate cites real
source evidence."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from atlas.features import m18
from atlas.ingest.base import SourceUnavailable

ROOT = Path(__file__).resolve().parents[2]


def test_gate_reports_the_blocked_source_with_evidence_hashes():
    gate = m18.data_gate()
    assert (gate["model_id"], gate["status"], gate["prediction_rows"]) == ("M18", "blocked", 0)
    assert gate["sources"]["S41"]["outcome"] == "blocked"
    assert gate["split_manifest"] is None
    assert "eval/news/blocked.json" in gate["evidence"]
    for name, sha in gate["evidence"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    assert json.loads((ROOT / "reports/models/m18-data-gate.json").read_text("utf-8")) == gate


def test_plan_target_is_preserved_without_claiming_labels_exist():
    config = yaml.safe_load((ROOT / "configs/models/m18.yaml").read_text("utf-8"))
    assert config["enabled"] is False and config["status"] == "blocked"
    assert config["model_id"] == "M18" and config["split_manifest"] is None
    assert config["fallback"].startswith("none")
    assert config["planned_splits"]["collect_from"] == "2027-10-18"  # planned only
    assert config["planned_splits"]["locked_test"] == ["2028-01-31", "2028-02-14"]
    assert config["data_gate"]["min_permitted_annotated_texts"] == 1000


def test_news_batches_record_has_no_articles_or_labels():
    record = json.loads((ROOT / "eval/news/blocked.json").read_text("utf-8"))
    counts = record["counts"]
    assert record["status"] == "blocked" and not list((ROOT / "eval/news").glob("batch_*.jsonl"))
    assert (counts["articles_selected"], counts["records_labelled"]) == (0, 0)
    assert counts["records_reviewed_by_owner"] == 0


@pytest.mark.parametrize("operation", ["build_features", "export_predictions"])
def test_blocked_branch_does_not_consume_input(operation):
    with pytest.raises(SourceUnavailable, match="M18 blocked"):
        getattr(m18, operation)(object())
