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
    assert RELEASE.model_id == "M05" and RELEASE.approval == "pending"
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
    assert champion(root, "M05") == RELEASE.baseline  # pending approval: the baseline serves
    failing = RELEASE.model_copy(
        update={"version": "v2", "status": "baseline_only", "reason": "a failing candidate"}
    )
    (root / "M05" / "v2.json").write_text(failing.model_dump_json(indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="only eligible candidates"):
        approve(root, "M05", "v2", "approved", by="owner")
    assert champion(root, "M05") == RELEASE.baseline


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
