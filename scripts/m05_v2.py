"""Refit M05 as v2 with IMD 2025 and write its untested release record once (D166, D170).

Run from the repository root: .venv/Scripts/python scripts/m05_v2.py
Needs the S08 1981-2025 and S17 raw files (local only), the saved v1 fit and the geo and ml locks.
v2 keeps v1's model choice and alpha (selected on the 2017-2018 tune, D41); only the train window
grows. No year is held out, so the release has no test scores and is research_only.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from m05_release import RAW, s17  # noqa: E402

from atlas.config import load_state  # noqa: E402
from atlas.features import m05 as features  # noqa: E402
from atlas.ingest.s17 import S17  # noqa: E402
from atlas.models import m05  # noqa: E402
from atlas.models.registry import Release, git_sha, write_release  # noqa: E402

REGISTRY = ROOT / "models/registry"
FOLDER = ROOT / "data/models/m05/v2"
REASON = (
    "untested refit with IMD 2025 (D166, D170): no held-out year until the IMD 2026 and 2027 "
    "files exist; v1 stays the evaluated, approved release and the source of every accuracy number"
)


def main() -> None:
    v1 = json.loads((REGISTRY / "M05/v1.json").read_text("utf-8"))
    v1_fit = json.loads((ROOT / "data/models/m05/m05_fit.json").read_text("utf-8"))
    if v1_fit["dataset_sha256"] != v1["dataset_sha256"] or v1_fit["choice"] != "ridge":
        raise SystemExit("The saved v1 fit does not match the v1 release; stop")
    ka = load_state(ROOT / "configs/states/ka.yaml")
    raws = features.year_artifacts(RAW, range(1981, 2026))
    districts = S17("ka").parse(s17("e06"), ka.source("S17"), adm1=s17("e05"))
    rows = features.feature_rows(
        features.spi_table(features.district_monthly_rain(raws, districts))
    )
    known = m05.rows_in(rows, date(1981, 1, 1), date(2024, 12, 31))
    if m05.table_sha256(known) != v1["dataset_sha256"]:
        raise SystemExit("The 1981-2024 rows no longer match the v1 dataset hash; stop")

    (split,) = features.splits_v2()
    train = m05.rows_in(rows, split.train_start, split.train_end)
    fit = m05.refit(train, v1_fit["ridge"]["alpha"], split)
    split_sha = features.write_split_manifest(FOLDER / "m05_splits.json", "v2")
    data_sha = m05.table_sha256(rows)
    m05.save(fit, FOLDER, split_sha, data_sha)
    release = Release(
        model_id="M05",
        version="v2",
        created_at=datetime.now(UTC),
        dataset_sha256=data_sha,
        git_sha=git_sha(ROOT),
        cutoffs={
            "train": f"{split.train_start}/{split.train_end}",
            "alpha_selected_on_v1_tune": v1["cutoffs"]["tune"],
            "test": f"{split.test_start}/{split.test_end}",
            "split_manifest_sha256": split_sha,
            "source_sha256": ",".join(sorted(r.sha256[:16] for r in raws)),
        },
        baseline="persistence",
        baseline_scores={},
        candidate="ridge",
        status="research_only",
        reason=REASON,
    )
    path = write_release(release, REGISTRY)
    print(path, train.num_rows, "train rows", fit.ridge_alpha)


if __name__ == "__main__":
    main()
