"""T103 acceptance: the release manifest verifies source and split hashes and the gate decision;
a failing or unapproved model stays disabled; the report never substitutes targets for achieved
scores. Consistency checks run in CI; hash re-computation needs the local raw files."""

import json
import re
import shutil
from pathlib import Path

import pytest

from atlas.models.registry import Release, approve, champion

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "models" / "registry"
RELEASE = Release.model_validate_json((REGISTRY / "M05" / "v1.json").read_text("utf-8"))
EVALUATION = json.loads((REGISTRY / "M05" / "v1.evaluation.json").read_text("utf-8"))
REPORT = (ROOT / "reports" / "models" / "m05.md").read_text("utf-8")


def test_release_records_gate_decision_and_hashes():
    assert (
        RELEASE.model_id == "M05" and RELEASE.approval == "pending"
    )  # the release file never changes
    assert RELEASE.status == EVALUATION["status"]
    assert (RELEASE.status == "candidate_eligible") == all(EVALUATION["gates"].values())
    assert RELEASE.cutoffs["test"] == "2020-01-01/2024-12-31"
    assert len(RELEASE.cutoffs["split_manifest_sha256"]) == 64 and len(RELEASE.git_sha) == 40
    assert RELEASE.candidate_scores["mae"] == EVALUATION["mae"][RELEASE.candidate]
    assert RELEASE.baseline_scores["mae"] == EVALUATION["mae"][RELEASE.baseline]


def test_report_shows_achieved_scores_not_targets():
    ev = EVALUATION
    row = re.search(
        r"\| MAE candidate / baseline \| ([0-9.]+) / ([0-9.]+) \(ratio ([0-9.]+)\)", REPORT
    )
    assert row and float(row.group(1)) == round(ev["mae"][ev["candidate"]], 3)
    assert float(row.group(2)) == round(ev["mae"][ev["baseline"]], 3)
    assert (
        float(row.group(3)) == round(ev["mae_ratio"], 3) != 0.95
    )  # the gate value is not the score
    assert f"| Drought PR-AUC (SPI-3 < -1) | {ev['pr_auc']:.3f} |" in REPORT
    assert "hindcast" in REPORT and "not groundwater" in REPORT
    assert f"Status: {RELEASE.status}" in REPORT


def test_unapproved_or_failing_model_stays_disabled(tmp_path):
    root = tmp_path / "registry"
    shutil.copytree(REGISTRY, root)
    approval = root / "M05" / "v1.approval.json"
    if (
        approval.exists()
    ):  # the owner approved v1 (D43): ridge serves; check the unapproved case too
        assert champion(root, "M05") == RELEASE.candidate
        approval.unlink()
    assert champion(root, "M05") == RELEASE.baseline  # without approval the baseline serves
    failing = RELEASE.model_copy(
        update={"version": "v2", "status": "baseline_only", "reason": "a failing candidate"}
    )
    (root / "M05" / "v2.json").write_text(failing.model_dump_json(indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="only eligible candidates"):
        approve(root, "M05", "v2", "approved", by="owner")
    assert champion(root, "M05") == RELEASE.baseline


V2 = Release.model_validate_json((REGISTRY / "M05" / "v2.json").read_text("utf-8"))
V1_SHA256 = {  # D170: the v2 refit leaves every v1 file byte-unchanged
    "v1.json": "177bb2a51d887b13ac4b98219f0d1425f1419e7d61f2ea2fb42905fb20460071",
    "v1.approval.json": "61fa37ece887133d393f69d42ea222c3064468caa1389a4cf41a1aadca0a5d6e",
    "v1.evaluation.json": "057bca169a212da11c67698abc4cfc0bf791ae872cc502515b8e6bc0b49a9424",
    "v1.intervals.json": "4ab187f51c540731ae67323a245c52a5576f7203a72aa3a44c2bf266fecf0368",
    "v1.monitor-2025.json": "7bbd3de51c9414ed67acfca5f3fdab0a749c79c3763bfcea9b63afe3ab8eade5",
}


def test_v2_is_an_untested_refit_that_v1_keeps_serving(tmp_path):
    import hashlib
    from datetime import date

    from atlas.features import m05 as features
    from atlas.models.splits import write_manifest

    assert (V2.status, V2.approval, V2.candidate, V2.baseline) == (
        "research_only",
        "pending",
        RELEASE.candidate,
        RELEASE.baseline,
    )
    assert V2.baseline_scores == {} and V2.candidate_scores is None and V2.improvement is None
    assert "untested" in V2.reason and not (REGISTRY / "M05" / "v2.approval.json").exists()
    shutil.copytree(REGISTRY, tmp_path / "registry")
    with pytest.raises(ValueError, match="only eligible candidates"):
        approve(tmp_path / "registry", "M05", "v2", "approved", by="owner")
    assert champion(REGISTRY, "M05") == RELEASE.candidate  # v1's approved ridge (D43)
    (split,) = features.splits_v2()
    assert (
        V2.cutoffs["train"] == "1981-07-01/2025-09-30" == f"{split.train_start}/{split.train_end}"
    )
    assert V2.cutoffs["test"] == "2026-01-01/2027-12-31" and split.test_start == date(2026, 1, 1)
    assert V2.cutoffs["alpha_selected_on_v1_tune"] == RELEASE.cutoffs["tune"]
    assert V2.cutoffs["split_manifest_sha256"] == write_manifest([split], tmp_path / "s.json")
    v1_sources = set(RELEASE.cutoffs["source_sha256"].split(","))
    assert v1_sources < set(V2.cutoffs["source_sha256"].split(","))  # 1981-2024 plus 2025
    assert V2.dataset_sha256 != RELEASE.dataset_sha256
    for name, digest in V1_SHA256.items():
        assert hashlib.sha256((REGISTRY / "M05" / name).read_bytes()).hexdigest() == digest, name


def test_v2_artifacts_bind_the_release_hashes():
    path = ROOT / "data/models/m05/v2/m05_fit.json"
    if not path.exists():
        pytest.skip("M05 v2 weights are local only (data/models is git-ignored)")
    saved = json.loads(path.read_text("utf-8"))
    v1_fit = json.loads((ROOT / "data/models/m05/m05_fit.json").read_text("utf-8"))
    assert saved["dataset_sha256"] == V2.dataset_sha256
    assert saved["split_sha256"] == V2.cutoffs["split_manifest_sha256"]
    assert (saved["choice"], saved["ridge"]["alpha"]) == ("ridge", v1_fit["ridge"]["alpha"])
    assert saved["tune_mae"] == {} and saved["lightgbm_params"] is None


def test_hashes_match_the_local_data(tmp_path):
    pytest.importorskip("shapely")
    pytest.importorskip("lightgbm")
    from atlas.features import m05 as features
    from atlas.ingest.base import SourceUnavailable

    try:
        raws = features.year_artifacts(ROOT / "data" / "raw", range(1981, 2025))
    except SourceUnavailable:
        pytest.skip("S08 1981-2024 year files are local only")
    assert RELEASE.cutoffs["source_sha256"] == ",".join(sorted(r.sha256[:16] for r in raws))
    split = features.write_split_manifest(tmp_path / "s.json")
    assert split == RELEASE.cutoffs["split_manifest_sha256"]
    try:
        raws = features.year_artifacts(ROOT / "data" / "raw", range(1981, 2026))
    except SourceUnavailable:
        pytest.skip("S08 2025 year file is local only")
    assert V2.cutoffs["source_sha256"] == ",".join(sorted(r.sha256[:16] for r in raws))
