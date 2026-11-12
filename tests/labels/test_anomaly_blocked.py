"""T212 and T213: the two anomaly adjudication batches are one recorded blocked batch (D159)."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECORD = json.loads((ROOT / "eval/anomalies/blocked.json").read_text("utf-8"))
COUNTS = json.loads((ROOT / "reports/models/m16-flag-counts.json").read_text("utf-8"))


def test_evidence_hashes_match_the_files_on_disk():
    assert set(RECORD["evidence"]) == {
        "reports/models/m16-flag-counts.json",
        "configs/sources/s08.yaml",
    }
    for name, sha in RECORD["evidence"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, name


def test_nothing_is_selected_or_adjudicated_and_requirements_match_the_plan():
    counts = RECORD["counts"]
    assert RECORD["status"] == "blocked"
    zero = ("flags_selected", "flags_adjudicated", "flags_second_reviewed", "batches_completed")
    assert [counts[k] for k in zero] == [0, 0, 0, 0]
    assert (counts["batches"], counts["required_per_batch"], counts["required_total"]) == (
        2,
        50,
        100,
    )
    assert counts["second_review_required_per_batch"] == counts["required_per_batch"] // 10
    assert RECORD["labels"] == ["data error", "genuine extreme", "normal", "unknown"]


def test_candidate_flags_are_the_counts_of_the_committed_table():
    candidates = RECORD["counts"]["candidate_real_flags"]
    assert candidates == {
        "S08_ka": COUNTS["totals"]["ka"]["flags_z"],
        "S08_kl": COUNTS["totals"]["kl"]["flags_z"],
    }
    assert all(n > 100 for n in candidates.values())  # enough to select from, once evidence exists


@pytest.mark.parametrize("batch", [1, 2])
def test_batch_is_recorded_blocked_and_no_file_exists(batch):
    task = RECORD["tasks"][batch - 1]
    assert task == {
        "task": f"T{211 + batch}",
        "batch": batch,
        "planned_file": f"eval/anomalies/batch_{batch}.jsonl",
    }
    assert not list((ROOT / "eval/anomalies").glob("batch_*.jsonl"))
    assert not (ROOT / f"tests/labels/test_anomaly_{batch}.py").exists()


def test_retry_condition_needs_independent_evidence_and_the_owner():
    retry = RECORD["retry_condition"]
    assert "independent" in retry and "S02" in retry and "S07" in retry
    assert "owner" in retry and "does not assign the labels" in retry
