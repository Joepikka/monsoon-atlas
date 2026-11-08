# ruff: noqa: E501
"""Recalibrate the M05 80% intervals with the D97 rule and check them once on 2020-2024 (T262).

Run from the repository root: .venv/Scripts/python scripts/m05_intervals.py
Needs the S08 1981-2024 and S17 raw files (local only), the saved v1 fit and the geo and ml locks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from m05_release import build  # noqa: E402

from atlas.models import m05  # noqa: E402
from atlas.models.registry import git_sha  # noqa: E402

REGISTRY = ROOT / "models/registry/M05"
OUTPUT = REGISTRY / "v1.intervals.json"
REPORT = ROOT / "reports/models/m05-intervals.md"
GATE = (0.75, 0.85)


def champion(test, fit: dict) -> np.ndarray:
    """The approved v1 ridge forecast, from the saved weights (never refitted)."""
    mean, std = (np.asarray(fit["scaler"][k]) for k in ("mean", "std"))
    x, _, _ = m05._design(test, mean, std)
    return x @ np.asarray(fit["ridge"]["coef"]) + fit["ridge"]["intercept"]


def run() -> dict:
    release = json.loads((REGISTRY / "v1.json").read_text("utf-8"))
    fit = json.loads((ROOT / "data/models/m05/m05_fit.json").read_text("utf-8"))
    rows, _, _, _, _, test, _ = build()
    if not (m05.table_sha256(rows) == fit["dataset_sha256"] == release["dataset_sha256"]):
        raise SystemExit("Rebuilt M05 rows do not match the v1 release dataset hash")
    res = m05.rolling_residuals(rows, fit["ridge"]["alpha"])
    table = m05.choose_rule(res)
    best = table[0]
    window, seasonal = best["window_years"], best["seasonal"]
    cal = (res["year"] >= 2020 - window) & (res["year"] < 2020)
    y = np.asarray(test[m05.TARGET].to_pylist(), dtype=float)
    month = np.asarray(test["month_of_year"].to_pylist())
    forecast = champion(test, fit)
    persistence = np.asarray(test["spi3_lag1"].to_pylist(), dtype=float)
    lower, upper = m05._offsets(res["ridge"][cal], res["month"][cal], month, seasonal)
    wet = np.isin(month, list(m05.MONSOON))
    inside = (y >= forecast + lower) & (y <= forecast + upper)
    score = m05.interval_score(res["ridge"][cal], res["month"][cal], y, forecast, month, seasonal)
    base = m05.interval_score(
        res["persistence"][cal], res["month"][cal], y, persistence, month, seasonal
    )
    quantiles = {
        name: [float(lower[sel][0]), float(upper[sel][0])]
        for name, sel in (("monsoon (Jun-Sep)", wet), ("rest of year", ~wet))
    }
    return {
        "model_id": "M05",
        "version": "v1",
        "decision": "D97",
        "point_forecast": "approved v1 ridge, unchanged",
        "dataset_sha256": release["dataset_sha256"],
        "git_sha": git_sha(ROOT),
        "residuals": "out-of-sample ridge refits at origins 2000, 2005, 2010, 2015 (v1 alpha and features, 92-day purge)",
        "selection_years": "2010/2019",
        "selection": table,
        "rule": {"window_years": window, "seasonal": seasonal},
        "calibration_years": f"{2020 - window}/2019",
        "offsets_q10_q90": quantiles,
        "test": {
            "period": "2020-01-01/2024-12-31",
            "rows": int(len(y)),
            "coverage": score["coverage"],
            "mean_width": score["width"],
            "coverage_by_season": {
                "monsoon (Jun-Sep)": float(inside[wet].mean()),
                "rest of year": float(inside[~wet].mean()),
            },
            "persistence_same_rule": {"coverage": base["coverage"], "mean_width": base["width"]},
        },
        "gate": list(GATE),
        "publishable": GATE[0] <= score["coverage"] <= GATE[1],
        "second_look": "The 2020-2024 test was already used once for the v1 intervals (65% coverage). The rule was chosen on 2010-2019 only; this is the second use of the test years, for intervals only.",
        "v1_interval80_coverage": json.loads((REGISTRY / "v1.evaluation.json").read_text("utf-8"))[
            "interval80_coverage"
        ],
    }


def report(result: dict) -> str:
    f = lambda v: f"{v:.3f}"  # noqa: E731
    test, rule = result["test"], result["rule"]

    def name(r: dict) -> str:
        years = f"{r['window_years']} year{'s' if r['window_years'] > 1 else ''}"
        return f"last {years}, {'by season' if r['seasonal'] else 'pooled'}"

    return "\n".join(
        [
            "# M05 80% interval recalibration (T262)",
            "",
            f"**Result: {'intervals may be shown' if result['publishable'] else 'intervals stay hidden'}.** "
            f"Test coverage {f(test['coverage'])} against the {result['gate'][0]:.0%}-{result['gate'][1]:.0%} gate "
            f"(v1 intervals: {f(result['v1_interval80_coverage'])}).",
            "",
            "The point forecasts are the approved v1 ridge and do not change. The rule was fixed in D97",
            "before any interval was computed. It is a hindcast, like every M05 result (D39).",
            "",
            "## Choosing the rule on 2010-2019",
            "",
            "Residuals come from ridge refits at origins 2000, 2005, 2010 and 2015, each predicting the",
            "next five years out of sample. Each year from 2010 to 2019 is covered using residuals from",
            "the years before it. The rule with mean coverage closest to 80% wins.",
            "",
            "| Rule | Mean coverage 2010-2019 | Mean width (SPI) |",
            "|---|---|---|",
            *[f"| {name(r)} | {f(r['coverage'])} | {f(r['width'])} |" for r in result["selection"]],
            "",
            f"Chosen: **{name(rule)}**, calibrated on {result['calibration_years'].replace('/', ' to ')}.",
            "",
            "## One check on 2020-2024",
            "",
            "| Measure | Value |",
            "|---|---|",
            f"| Rows | {test['rows']} |",
            f"| 80% interval coverage | {f(test['coverage'])} |",
            f"| Mean width (SPI) | {f(test['mean_width'])} |",
            *[f"| Coverage, {k} | {f(v)} |" for k, v in test["coverage_by_season"].items()],
            f"| Persistence with the same rule: coverage / width | {f(test['persistence_same_rule']['coverage'])} / {f(test['persistence_same_rule']['mean_width'])} |",
            "",
            "Offsets added to the forecast (10th and 90th residual percentiles, SPI):",
            "",
            *[f"- {k}: {f(lo)} to {f(hi)}" for k, (lo, hi) in result["offsets_q10_q90"].items()],
            "",
            "## Limits",
            "",
            f"- {result['second_look']}",
            "- Residuals of nearby districts in the same month move together, so coverage varies from",
            "  year to year more than independent rows would suggest; conformal guarantees assume",
            "  exchangeable rows, which time series only approximate.",
            "- Refit residuals stand in for the champion's own pre-test errors, because the champion was",
            "  trained on everything before 2016-10.",
            "",
            "Record: `models/registry/M05/v1.intervals.json`; script: `scripts/m05_intervals.py`.",
            "",
        ]
    )


def main() -> None:
    result = run()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    REPORT.write_text(report(result), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {"rule": result["rule"], "test": result["test"], "publishable": result["publishable"]}
        )
    )


if __name__ == "__main__":
    main()
