# ruff: noqa: E501
"""Score the approved M05 forecast once on the unused, provisional IMD 2025 year (T263, D98).

Run from the repository root: .venv/Scripts/python scripts/m05_monitor.py
Needs the S08 1981-2025 and S17 raw files (local only), the saved v1 fit and the geo and ml locks.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from m05_intervals import champion  # noqa: E402
from m05_release import RAW, s17  # noqa: E402

from atlas.config import load_state  # noqa: E402
from atlas.features import m05 as features  # noqa: E402
from atlas.ingest.s17 import S17  # noqa: E402
from atlas.models import m05  # noqa: E402
from atlas.models.registry import git_sha  # noqa: E402
from atlas.models.uncertainty import paired_block_bootstrap  # noqa: E402

REGISTRY = ROOT / "models/registry/M05"
OUTPUT = REGISTRY / "v1.monitor-2025.json"
REPORT = ROOT / "reports/models/m05-2025.md"
GATE = (0.75, 0.85)


def run() -> dict:
    release = json.loads((REGISTRY / "v1.json").read_text("utf-8"))
    fit = json.loads((ROOT / "data/models/m05/m05_fit.json").read_text("utf-8"))
    ka = load_state(ROOT / "configs/states/ka.yaml")
    raws = features.year_artifacts(RAW, range(1981, 2026))
    districts = S17("ka").parse(s17("e06"), ka.source("S17"), adm1=s17("e05"))
    rows = features.feature_rows(
        features.spi_table(features.district_monthly_rain(raws, districts))
    )
    known = m05.rows_in(rows, date(1981, 1, 1), date(2024, 12, 31))
    if m05.table_sha256(known) != release["dataset_sha256"]:
        raise SystemExit("The 1981-2024 rows no longer match the v1 dataset hash; stop (D98)")
    file_2025 = next(r for r in raws if r.source_url.endswith("rain=2025"))

    test, new = (
        m05.rows_in(rows, date(y0, 1, 1), date(y1, 12, 31))
        for y0, y1 in ((2020, 2024), (2025, 2025))
    )
    y_test = np.asarray(test[m05.TARGET].to_pylist(), dtype=float)
    y = np.asarray(new[m05.TARGET].to_pylist(), dtype=float)
    forecast, persistence = (
        champion(new, fit),
        np.asarray(new["spi3_lag1"].to_pylist(), dtype=float),
    )
    month = np.asarray(new["month_of_year"].to_pylist())
    cand_err, base_err = np.abs(forecast - y), np.abs(persistence - y)
    blocks = [m.strftime("%Y-%m") for m in new["target_month"].to_pylist()]
    imp = paired_block_bootstrap(base_err.tolist(), cand_err.tolist(), blocks)
    # D97 rule (last five years, by season) on the champion's own 2020-2024 residuals.
    residual = y_test - champion(test, fit)
    lower, upper = m05._offsets(
        residual, np.asarray(test["month_of_year"].to_pylist()), month, True
    )
    inside = (y >= forecast + lower) & (y <= forecast + upper)
    wet = np.isin(month, list(m05.MONSOON))
    mae = {"ridge": float(cand_err.mean()), "persistence": float(base_err.mean())}
    return {
        "model_id": "M05",
        "version": "v1",
        "decision": "D98",
        "evidence": "hindcast (D39); IMD 2025 data provisional (finality not stated)",
        "s08_2025_sha256": file_2025.sha256,
        "dataset_sha256_1981_2024": release["dataset_sha256"],
        "git_sha": git_sha(ROOT),
        "period": "2025-01-01/2025-12-31",
        "rows": int(len(y)),
        "months": len(set(blocks)),
        "mae": mae,
        "mae_ratio": mae["ridge"] / mae["persistence"],
        "improvement": {"mean": imp.mean, "lower95": imp.lower95, "upper95": imp.upper95},
        "drought_rows": int((y < -1.0).sum()),
        "interval80": {
            "rule": "last 5 years, by season (D97), champion residuals 2020-2024",
            "coverage": float(inside.mean()),
            "coverage_by_season": {
                "monsoon (Jun-Sep)": float(inside[wet].mean()),
                "rest of year": float(inside[~wet].mean()),
            },
            "mean_width": float((upper - lower).mean()),
            "gate": list(GATE),
            "shown": False,
        },
        "flag": "holds" if mae["ridge"] <= mae["persistence"] else "degraded",
    }


def report(r: dict) -> str:
    f = lambda v: f"{v:.3f}"  # noqa: E731
    imp, iv = r["improvement"], r["interval80"]
    return "\n".join(
        [
            "# M05 2025 monitoring check (T263)",
            "",
            f"**Flag: {r['flag']}.** On {r['rows']} district-months of 2025 the approved ridge forecast has MAE "
            f"{f(r['mae']['ridge'])} against {f(r['mae']['persistence'])} for persistence (ratio {f(r['mae_ratio'])}).",
            "",
            "This is a monitoring check fixed in D98 before scoring, not a new release. 2025 was never used",
            "by M05. IMD does not say the 2025 file is final, so the result is provisional, and like every",
            "M05 result it is a hindcast (D39).",
            "",
            "| Measure | Value |",
            "|---|---|",
            f"| Rows / months | {r['rows']} / {r['months']} |",
            f"| MAE ridge / persistence | {f(r['mae']['ridge'])} / {f(r['mae']['persistence'])} |",
            f"| Mean improvement (paired block bootstrap, months) | {f(imp['mean'])}, 95% [{f(imp['lower95'])}, {f(imp['upper95'])}] |",
            f"| Drought rows (SPI-3 < -1) | {r['drought_rows']} |",
            f"| 80% interval coverage (D97 rule) | {f(iv['coverage'])} |",
            *[f"| Interval coverage, {k} | {f(v)} |" for k, v in iv["coverage_by_season"].items()],
            f"| Mean interval width (SPI) | {f(iv['mean_width'])} |",
            "",
            "## Limits",
            "",
            "- Twelve months are below the 24-month minimum for a release decision, so the bootstrap",
            "  range is reported only and the intervals stay hidden whatever their coverage.",
            "- Rows from nearby districts in the same month move together; one dry or wet month can",
            "  move the whole year.",
            "",
            f"Record: `models/registry/M05/v1.monitor-2025.json`; S08 2025 file {r['s08_2025_sha256'][:12]};",
            "script: `scripts/m05_monitor.py`.",
            "",
        ]
    )


def main() -> None:
    result = run()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    REPORT.write_text(report(result), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {k: result[k] for k in ("flag", "mae", "mae_ratio", "improvement", "drought_rows")}
            | {"interval80": result["interval80"]["coverage"]}
        )
    )


if __name__ == "__main__":
    main()
