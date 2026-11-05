# ruff: noqa: E501
"""Evaluate M05 on the locked 2020-2024 test once and write the release and report (T103).

Run from the repository root: .venv/Scripts/python scripts/m05_release.py
Needs the S08 1981-2024 and S17 raw files (local only) and the geo and ml locks.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas.config import load_state  # noqa: E402
from atlas.contracts import RawArtifact  # noqa: E402
from atlas.features import m05 as features  # noqa: E402
from atlas.ingest.s17 import S17  # noqa: E402
from atlas.models import m05  # noqa: E402
from atlas.models.registry import Release, git_sha, write_release  # noqa: E402

RAW = ROOT / "data" / "raw"


def s17(eid: str) -> RawArtifact:
    manifest = json.loads((ROOT / "tests/fixtures/s17/manifest.json").read_text("utf-8"))
    e = next(x for x in manifest["evidence"] if x["id"] == eid)
    return RawArtifact(
        sha256=e["sha256"],
        path=RAW / e["raw_path"],
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="s17-v1",
    )


def build():
    ka = load_state(ROOT / "configs/states/ka.yaml")
    raws = features.year_artifacts(RAW, range(1981, 2025))
    districts = S17("ka").parse(s17("e06"), ka.source("S17"), adm1=s17("e05"))
    rows = features.feature_rows(
        features.spi_table(features.district_monthly_rain(raws, districts))
    )
    tune_s, cal_s, test_s = features.splits()
    part = lambda s: m05.rows_in(rows, s.test_start, s.test_end)  # noqa: E731
    train = m05.rows_in(rows, tune_s.train_start, tune_s.train_end)
    return rows, raws, train, part(tune_s), part(cal_s), part(test_s), test_s


def report(ev: dict, release: Release) -> str:
    f = lambda v: f"{v:.3f}"  # noqa: E731
    imp = ev["improvement"] or {}
    lines = [
        "# M05 Karnataka drought outlook: locked test result (T103)",
        "",
        f"**Status: {release.status}** (approval: {release.approval}). {release.reason}.",
        "",
        "**This is a hindcast** (D39): features assume IMD rain up to the previous month was known at",
        "issue time; IMD publishes the gridded files yearly, so live outlooks are not possible from S08.",
        "",
        f"Test: {ev['rows']} district-months, {ev['months']} months (2020-2024), 30 districts",
        "(geoBoundaries 2021 lines; no taluk polygons). Baseline: strongest of SPI-3 persistence and month",
        f"climatology on the test rows = **{ev['baseline']}**. Candidate: **{ev['candidate']}**.",
        "",
        "| Measure | Achieved | Gate |",
        "|---|---|---|",
        f"| MAE candidate / baseline | {f(ev['mae'][ev['candidate']])} / {f(ev['mae'][ev['baseline']])} (ratio {f(ev['mae_ratio'])}) | ratio <= 0.95 and lower 95% bound > 0 |",
        f"| Improvement (paired block bootstrap, months) | mean {f(imp.get('mean', float('nan')))}, 95% [{f(imp.get('lower95', float('nan')))}, {f(imp.get('upper95', float('nan')))}] | lower bound > 0 |",
        f"| Drought PR-AUC (SPI-3 < -1) | {f(ev['pr_auc'])} | > prevalence {f(ev['drought_prevalence'])} |",
        f"| Brier skill vs baseline | {f(ev['brier_skill'])} | > 0 |",
        f"| CRPS candidate / baseline | {f(ev['crps'][ev['candidate']])} / {f(ev['crps'][ev['baseline']])} | candidate lower |",
        f"| 80% interval coverage (spread from 2019) | {f(ev['interval80_coverage'])} | reported |",
        "",
        "All test MAEs: " + ", ".join(f"{k} {f(v)}" for k, v in sorted(ev["mae"].items())) + ".",
        "",
        "Calibration by season (candidate drought probability):",
        "",
        "| Season | Rows | Observed drought share | Mean probability |",
        "|---|---|---|---|",
        *[
            f"| {k} | {v['rows']} | {f(v['observed_drought'])} | {f(v['mean_probability'])} |"
            for k, v in ev["calibration_by_season"].items()
        ],
        "",
        "Gates: "
        + ", ".join(f"{k} {'pass' if ok else 'fail'}" for k, ok in ev["gates"].items())
        + ".",
        "",
        "## Limits (claims this result does not support)",
        "",
        "- SPI is meteorological drought only: not groundwater, crop yield loss or household water.",
        f"- 80% intervals cover {ev['interval80_coverage']:.0%} of test outcomes: too narrow (spread from one",
        "  calibration year, 2019). Do not publish them as 80% intervals until recalibrated.",
        "- Drought probabilities run slightly high in both seasons (see the calibration table).",
        "- District lines are geoBoundaries 2021 (Ballari includes Vijayanagara).",
        "- One IMD day (12 Oct 2023) has gaps outside Karnataka; none in the state (D40).",
        "- A candidate is served only after the owner approves the release (D38); until then the",
        "  baseline is the champion.",
        "",
        "Retraining rule: refit quarterly when a new IMD year file is published; any change of target,",
        "unit or boundary version is a new model version with an untouched test period.",
        "",
        f"Release: `models/registry/M05/{release.version}.json` (git {release.git_sha[:12]}, dataset",
        f"{release.dataset_sha256[:12]}, split manifest {release.cutoffs['split_manifest_sha256'][:12]}).",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    rows, raws, train, tune, cal, test, test_s = build()
    fit = m05.fit(train, tune, test_s, lgbm_trials=30)
    ev = m05.evaluate(fit, cal, test)
    split_sha = features.write_split_manifest(ROOT / "data/models/m05/m05_splits.json")
    release = Release(
        model_id="M05",
        version="v1",
        created_at=datetime.now(UTC),
        dataset_sha256=m05.table_sha256(rows),
        git_sha=git_sha(ROOT),
        cutoffs={
            "train": "1981-07-01/2016-09-30",
            "tune": "2017-01-01/2018-12-31",
            "calibrate": "2019-01-01/2019-12-31",
            "test": "2020-01-01/2024-12-31",
            "split_manifest_sha256": split_sha,
            "source_sha256": ",".join(sorted(r.sha256[:16] for r in raws)),
        },
        baseline=ev["baseline"],
        baseline_scores={
            "mae": ev["mae"][ev["baseline"]],
            "brier": ev["brier"][ev["baseline"]],
            "crps": ev["crps"][ev["baseline"]],
        },
        candidate=ev["candidate"],
        candidate_scores={
            "mae": ev["mae"][ev["candidate"]],
            "brier": ev["brier"][ev["candidate"]],
            "crps": ev["crps"][ev["candidate"]],
            "pr_auc": ev["pr_auc"],
        },
        improvement=ev["improvement"],
        status=ev["status"],
        reason=ev["reason"],
    )
    path = write_release(release, ROOT / "models" / "registry")
    (ROOT / "models/registry/M05/v1.evaluation.json").write_text(
        json.dumps(ev, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    out = ROOT / "reports/models/m05.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report(ev, release), encoding="utf-8", newline="\n")
    print(path, ev["status"], ev["gates"])


if __name__ == "__main__":
    main()
