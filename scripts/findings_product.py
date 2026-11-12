"""Bundle the Karnataka analysis results for the site's Data findings page (D199).

Every number is copied from a committed report or the M05 registry through the same row functions
the Power BI report uses (powerbi/build_pbip.py), so the page and the report cannot disagree.
Rain stays an index (no S08 mm), and bus access stays derived shares (no stop, route or time, D191).

Run:  .venv/Scripts/python scripts/findings_product.py   (writes web/src/findings.json)
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "src" / "findings.json"
_spec = importlib.util.spec_from_file_location("build_pbip", ROOT / "powerbi" / "build_pbip.py")
bp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bp)


def product() -> dict:
    hosp = json.loads((bp.ACCESS / "summary.json").read_text("utf-8"))
    bus = json.loads((bp.BUS / "summary.json").read_text("utf-8"))
    trends = bp.trend_rows()
    err, gain = bp.model_rows()
    looks, _ = bp.interval_rows()
    moran = bp.moran_rows()
    return {
        "schema_version": 1,
        "state": "ka",
        "hospital": {
            "hospitals": hosp["hospitals"],
            "statewide": hosp["statewide"],
            "districts": [
                {"district": r[0], "people": r[1], "mean_km": r[2], "share_beyond_10km": r[6]}
                for r in bp.access_rows()
            ],
            "lorenz": hosp["lorenz"],
            "limits": hosp["limits"],
            "report": "notebooks/11_ka_hospital_access.ipynb",
        },
        "trends": {
            "tested": len(trends),
            "significant": sum(1 for r in trends if r[6] < 0.05),
            "rows": [
                {"district": r[0], "sen_pct_per_decade": r[3], "fdr_q": r[6], "significance": r[8]}
                for r in trends
            ],
            "report": "reports/eda/08_climate_product/climate.json",
        },
        "bus": {
            "district": bus["district"]["name"],
            "service_date": bus["service_date"],
            "covered_share": bus["population"]["covered_share"],
            "people": bus["population"]["total"],
            "bands": [{"band": r[0], "cells": r[2], "people": r[3]} for r in bp.bus_rows()],
            "limits": bus["limits"],
            "report": "notebooks/04_bmtc_coverage.ipynb",
        },
        "model": {
            "mae": [{"period": p, "model": m, "mae": v} for p, m, v in err],
            "gain": [
                {"period": r[0], "mean": r[4], "lower95": r[5], "upper95": r[6], "promoted": r[7]}
                for r in gain
            ],
            "gates": [
                {"check": r[1], "value": r[2], "reference": r[3], "passed": r[4]}
                for r in bp.gate_rows()
            ],
            "report": "reports/models/m05.md",
        },
        "intervals": {
            "gate": [0.75, 0.85],
            "looks": [{"stage": r[1], "coverage": r[2], "result": r[3]} for r in looks],
        },
        "spatial": {
            "months": len(moran),
            "significant": sum(1 for r in moran if r[4] == "yes"),
            "moran": [{"month": r[0], "moran_i": r[1], "significant": r[4]} for r in moran],
            "report": "reports/eda/10_spatial_statistics/summary.json",
        },
    }


def text() -> str:
    return json.dumps(product(), indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    OUT.write_text(text(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
