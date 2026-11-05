"""T034 acceptance: a worse challenger cannot become champion; a missing test score never turns
into 0; the same seed gives the same interval; releases are immutable and need owner approval.
Real-data cases use IMD 2024 daily rain at the Bengaluru cell (S08, local raw; skipped in CI)."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from atlas.models.evaluate import decide
from atlas.models.registry import Release, approve, champion, git_sha, log_to_mlflow, write_release
from atlas.models.uncertainty import (
    conformal_interval,
    coverage,
    paired_block_bootstrap,
    select_threshold,
)

ROOT = Path(__file__).resolve().parents[2]


def bengaluru_2024() -> tuple[np.ndarray, list[str]]:
    manifest = json.loads((ROOT / "tests/fixtures/s08/manifest.json").read_text("utf-8"))
    e04 = next(e for e in manifest["evidence"] if e["id"] == "e04")
    path = ROOT / "data" / "raw" / e04["raw_path"]
    if not path.exists():
        pytest.skip("S08 year file is local only (IMD forbids reproduction)")
    grid = np.fromfile(path, dtype="<f4").reshape(366, 129, 135)
    rain = grid[:, round((13.0 - 6.5) / 0.25), round((77.5 - 66.5) / 0.25)].astype(float)
    months = [(date(2024, 1, 1) + timedelta(days=i)).strftime("%Y-%m") for i in range(366)]
    return rain, months


def losses():
    """Absolute errors on 2 Jan to 31 Dec 2024 for persistence and for a constant 50 mm."""
    rain, months = bengaluru_2024()
    truth = rain[1:]
    persistence = np.abs(truth - rain[:-1])
    constant = np.abs(truth - 50.0)
    return persistence.tolist(), constant.tolist(), months[1:]


def release(**changes) -> Release:
    base = {
        "model_id": "M05",
        "version": "v1",
        "created_at": datetime(2026, 11, 5, tzinfo=UTC),
        "dataset_sha256": "a" * 64,
        "git_sha": git_sha(ROOT),
        "cutoffs": {"train": "1981-01-01/2016-12-31", "test": "2020-01-01/2024-12-31"},
        "baseline": "persistence",
        "baseline_scores": {"mae": 1.0},
        "status": "baseline_only",
        "reason": "test",
    }
    return Release(**(base | changes))


def test_worse_challenger_cannot_become_champion(tmp_path):
    persistence, constant, months = losses()
    d = decide(persistence, constant, months, min_rows=300, min_blocks=12)
    assert d.status == "baseline_only" and d.improvement.upper95 < 0
    write_release(release(candidate="constant_50mm", status=d.status, reason=d.reason), tmp_path)
    with pytest.raises(ValueError, match="only eligible candidates"):
        approve(tmp_path, "M05", "v1", "approved", by="owner")
    assert champion(tmp_path, "M05") == "persistence"


def test_better_candidate_still_needs_owner_approval(tmp_path):
    persistence, constant, months = losses()
    d = decide(constant, persistence, months, min_rows=300, min_blocks=12)  # baseline = constant
    assert d.status == "candidate_eligible" and d.improvement.lower95 > 0
    r = release(baseline="constant_50mm", candidate="persistence", status=d.status, reason=d.reason)
    write_release(r, tmp_path)
    assert champion(tmp_path, "M05") == "constant_50mm"  # no silent promotion
    approve(tmp_path, "M05", "v1", "approved", by="owner")
    assert champion(tmp_path, "M05") == "persistence"
    with pytest.raises(FileExistsError, match="immutable"):
        write_release(r, tmp_path)


def test_small_sample_is_research_only():
    persistence, constant, months = losses()
    d = decide(persistence[:20], constant[:20], months[:20], min_rows=300, min_blocks=12)
    assert d.status == "research_only" and d.improvement is None


def test_missing_score_never_becomes_zero():
    d = decide([1.0, 2.0, 3.0], [1.0, None, 3.0], ["a", "b", "c"], min_rows=1, min_blocks=1)
    assert d.status == "research_only" and "not treated as 0" in d.reason
    assert decide(None, [1.0], ["a"], min_rows=1, min_blocks=1).status == "research_only"
    with pytest.raises(ValueError, match="never replaced by 0"):
        paired_block_bootstrap([1.0, float("nan")], [1.0, 1.0], ["a", "b"])


def test_repeat_seed_gives_same_interval():
    base = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0]
    cand = [2.0, 1.5, 3.0, 0.5, 4.0, 7.0, 2.5, 5.0]
    blocks = ["m1", "m1", "m2", "m2", "m3", "m3", "m4", "m4"]
    first = paired_block_bootstrap(base, cand, blocks)
    assert first == paired_block_bootstrap(base, cand, blocks)  # seed 42, 1000 resamples
    assert first.n_blocks == 4 and first.mean == pytest.approx(5.5 / 8)


def test_interval_and_threshold_use_validation_rows_only():
    rain, _ = bengaluru_2024()
    residuals = (rain[1:182] - rain[:181]).tolist()  # January to June as validation
    lo, hi = conformal_interval(residuals, coverage=0.8)
    test_truth, test_pred = rain[183:], rain[182:-1]  # July to December
    covered = coverage(test_truth, test_pred + lo, test_pred + hi)
    assert lo <= 0 <= hi and 0.5 < covered <= 1.0
    wet = (rain[1:182] > 10).astype(int)
    threshold = select_threshold(wet, rain[:181] / 100, max_alert_rate=0.1)
    assert ((rain[:181] / 100) >= threshold).mean() <= 0.1


def test_release_records_hashes_cutoffs_and_approval(tmp_path):
    path = write_release(release(), tmp_path)
    saved = json.loads(path.read_text("utf-8"))
    assert len(saved["git_sha"]) == 40 and saved["dataset_sha256"] == "a" * 64
    assert saved["cutoffs"]["test"] == "2020-01-01/2024-12-31" and saved["approval"] == "pending"


def test_release_can_be_mirrored_to_local_mlflow(tmp_path):
    pytest.importorskip("mlflow")
    run_id = log_to_mlflow(release(), f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}")
    assert run_id
