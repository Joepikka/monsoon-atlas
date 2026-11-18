"""M21 monthly district rain-anomaly dataset, split manifest, data gate and baselines (T280).

Rows come from the M05 monthly district table (atlas.features.m05.district_monthly_rain, S08
1981-2025). Target at issue month t (00:00 IST on day 1 of t): the standardised anomaly of
month t rain, z = (rain - mean) / sd, with mean and sample sd per district and calendar month
from 1981-2010 only. Secondary target: tercile class (-1 below, 0 near, 1 above) against the
1981-2010 33rd and 67th percentiles. Dry-month rule: a district and calendar month whose
1981-2010 sd is below 10 mm has no anomaly; those rows are left out, never scored as zero.
Features use months up to t-1 only. Hindcast (D39): S08 is released yearly. Only indices leave
this module, never mm.

Run from the repository root: .venv/Scripts/python -m atlas.models.m21_data
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa

from atlas.data.asof import local_midnight_utc
from atlas.features import m05 as m05_features
from atlas.features.base import LeakageError
from atlas.models.m05 import rows_in, table_sha256
from atlas.models.splits import DatasetSplit, write_manifest
from atlas.models.uncertainty import paired_block_bootstrap

REFERENCE = m05_features.REFERENCE  # 1981-2010
DRY_SD_MM = 10.0
LAGS = tuple(range(1, 13))
PURGE_DAYS = 31  # one-month target: no training target month may touch the next period
FIRST_TARGET = date(1982, 1, 1)  # lags 1-12 need all of 1981
TRAIN = (FIRST_TARGET, date(2014, 11, 30))  # train 1982-2014 less the 31-day purge
PERIODS = {
    "tune": (date(2015, 1, 1), date(2017, 12, 31)),
    "calibrate": (date(2018, 1, 1), date(2019, 12, 31)),
    "test": (date(2020, 1, 1), date(2025, 12, 31)),
}
SCORABLE_END = PERIODS["tune"][1]  # T280 scores train and tune only
FEATURES = (
    *(f"anom_lag{k}" for k in LAGS),
    "spi1_lag1",
    "spi3_lag1",
    "spi6_lag1",
    "state_anom_lag1",
    "month_of_year",
)
BASELINES = ("climatology", "persistence", "last_year")


def _shift(d: date, months: int) -> date:
    i = d.year * 12 + d.month - 1 - months
    return date(i // 12, i % 12 + 1, 1)


def reference(monthly: pa.Table) -> dict[tuple[str, int], dict]:
    """1981-2010 mean, sd, terciles and dry flag per district and calendar month (mm, internal)."""
    ref: dict[tuple[str, int], list[float]] = {}
    for r in monthly.to_pylist():
        if REFERENCE[0] <= r["month"].year <= REFERENCE[1] and r["rain_mm"] is not None:
            ref.setdefault((r["place_id"], r["month"].month), []).append(r["rain_mm"])
    out = {}
    for key, values in ref.items():
        v = np.asarray(values)
        if len(v) < 25:
            raise ValueError(f"{key}: fewer than 25 reference years")
        sd = float(v.std(ddof=1))
        q33, q67 = np.quantile(v, [1 / 3, 2 / 3])
        out[key] = {
            "mean": float(v.mean()),
            "sd": sd,
            "q33": float(q33),
            "q67": float(q67),
            "dry": sd < DRY_SD_MM,
        }
    return out


def dataset(monthly: pa.Table) -> pa.Table:
    """One row per district and scored target month from 1982; features end at month t-1."""
    ref = reference(monthly)
    spi = {(r["place_id"], r["month"]): r for r in m05_features.spi_table(monthly).to_pylist()}
    anom: dict[tuple[str, date], float] = {}
    state: dict[date, list[float]] = {}
    for r in monthly.to_pylist():
        s = ref[(r["place_id"], r["month"].month)]
        if r["rain_mm"] is not None and not s["dry"]:
            z = (r["rain_mm"] - s["mean"]) / s["sd"]
            anom[(r["place_id"], r["month"])] = z
            state.setdefault(r["month"], []).append(z)
    rows = []
    for r in sorted(monthly.to_pylist(), key=lambda r: (r["place_id"], r["month"])):
        p, t = r["place_id"], r["month"]
        if t < FIRST_TARGET or (p, t) not in anom:
            continue  # dry district-month or missing rain: not a target
        s, prev = ref[(p, t.month)], spi[(p, _shift(t, 1))]
        lag_state = state.get(_shift(t, 1))
        rows.append(
            {
                "place_id": p,
                "name": r["name"],
                "issue_at": local_midnight_utc(t),
                "known_until": _shift(t, 1),
                "target_month": t,
                "month_of_year": t.month,
                **{f"anom_lag{k}": anom.get((p, _shift(t, k))) for k in LAGS},
                "spi1_lag1": prev["spi1"],
                "spi3_lag1": prev["spi3"],
                "spi6_lag1": prev["spi6"],
                "state_anom_lag1": float(np.mean(lag_state)) if lag_state else None,
                "target_anom": anom[(p, t)],
                "target_tercile": -1
                if r["rain_mm"] < s["q33"]
                else (1 if r["rain_mm"] > s["q67"] else 0),
            }
        )
    return pa.Table.from_pylist(rows)


def splits() -> list[DatasetSplit]:
    """Plan item 3: train 1982-2014 (purged 31 days), tune 2015-2017, calibrate 2018-2019,
    locked test 2020-2025."""
    return [
        DatasetSplit(
            name=name,
            train_start=TRAIN[0],
            train_end=TRAIN[1],
            test_start=start,
            test_end=end,
            purge_days=PURGE_DAYS,
        )
        for name, (start, end) in PERIODS.items()
    ]


def write_split_manifest(path: Path) -> str:
    return write_manifest(splits(), path)


def baselines(rows: pa.Table) -> dict[str, list[float]]:
    """Climatology (anomaly 0), persistence (anomaly of t-1), same month last year (t-12).
    shortcut: a lag that is a dry month has no anomaly, so that forecast falls back to 0."""
    lag1, lag12 = rows["anom_lag1"].to_pylist(), rows["anom_lag12"].to_pylist()
    return {
        "climatology": [0.0] * rows.num_rows,
        "persistence": [0.0 if v is None else v for v in lag1],
        "last_year": [0.0 if v is None else v for v in lag12],
    }


def score_baselines(rows: pa.Table) -> dict:
    """MAE of each baseline, and the paired block bootstrap (blocks = months) of the
    improvement over climatology. Rows after the tune period are refused."""
    months = rows["target_month"].to_pylist()
    if not months:
        raise ValueError("no rows to score")
    if max(months) > SCORABLE_END:
        raise LeakageError(f"rows after {SCORABLE_END} are not scored before T284")
    y = np.asarray(rows["target_anom"].to_pylist(), dtype=float)
    blocks = [m.strftime("%Y-%m") for m in months]
    err = {k: np.abs(np.asarray(v) - y) for k, v in baselines(rows).items()}
    out = {
        "rows": rows.num_rows,
        "months": len(set(blocks)),
        "mae": {k: float(e.mean()) for k, e in err.items()},
        "improvement_over_climatology": {},
    }
    for k in ("persistence", "last_year"):
        imp = paired_block_bootstrap(err["climatology"].tolist(), err[k].tolist(), blocks)
        out["improvement_over_climatology"][k] = {
            "mean": imp.mean,
            "lower95": imp.lower95,
            "upper95": imp.upper95,
        }
    out["strongest"] = min(BASELINES, key=lambda k: out["mae"][k])
    return out


def gate(monthly: pa.Table, rows: pa.Table, split_sha256: str, raws_sha256: list[str]) -> dict:
    """M21 data gate: M05's 30-year rule plus dataset and split hashes and per-split counts."""
    base = m05_features.gate(monthly, verified_taluks=False)
    ref = reference(monthly)
    dry = sorted(k for k, s in ref.items() if s["dry"])
    counts = {"train": rows_in(rows, *TRAIN).num_rows}
    counts |= {k: rows_in(rows, *v).num_rows for k, v in PERIODS.items()}
    known = {"train": rows_in(rows, *TRAIN), "tune": rows_in(rows, *PERIODS["tune"])}
    return {
        "model_id": "M21",
        "task": "T280",
        "status": base["status"],
        "reasons": base["reasons"],
        "unit": base["unit"],
        "years": base["years"],
        "evidence": "hindcast (D39); 2025 is provisional (D98)",
        "target": "z-score of month t district rain vs 1981-2010 mean and sd per calendar month",
        "dry_rule": {
            "rule": f"1981-2010 sd of monthly rain below {DRY_SD_MM:g} mm: no anomaly, not scored",
            "excluded_district_months": len(dry),
            "by_calendar_month": {
                str(m): sum(1 for _, mm in dry if mm == m) for m in sorted({mm for _, mm in dry})
            },
        },
        "features": list(FEATURES),
        "dataset_sha256": table_sha256(rows),
        "split_sha256": split_sha256,
        "source_sha256": ",".join(sorted(s[:16] for s in raws_sha256)),
        "rows": counts,
        "baselines": {k: score_baselines(v) for k, v in known.items()},
        "candidate": None,  # named by T281 or T283 before the test is opened
        "test_opened": False,
    }


def main() -> None:  # pragma: no cover - needs the local S08 and S17 raw files
    import sys

    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "scripts"))
    from m05_release import RAW, s17

    from atlas.config import load_state
    from atlas.ingest.s17 import S17

    ka = load_state(root / "configs/states/ka.yaml")
    raws = m05_features.year_artifacts(RAW, range(1981, 2026))
    districts = S17("ka").parse(s17("e06"), ka.source("S17"), adm1=s17("e05"))
    monthly = m05_features.district_monthly_rain(raws, districts)
    rows = dataset(monthly)
    out = root / "data/models/m21"
    out.mkdir(parents=True, exist_ok=True)
    import pyarrow.parquet as pq

    pq.write_table(rows, out / "m21_dataset.parquet")
    split_sha = write_split_manifest(root / "models/gates/m21_splits.json")
    result = gate(monthly, rows, split_sha, [r.sha256 for r in raws])
    (root / "models/gates/m21.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({k: result[k] for k in ("rows", "baselines")}, indent=2))


if __name__ == "__main__":
    main()
