"""M21 spatial lags, spatial cross-validation and residual Moran's I; M05 spatial challenger
(T282, plan item 7). Research and comparison only: nothing here is or names the M21 candidate.

- Spatial lags: the mean over a district's queen neighbours (no self) of the anomaly, SPI-1 and
  SPI-3 of month t-1. A neighbour's value for month t is never a feature (issue-time rule).
- M21 on tune: the T281 LightGBM procedure (same search, seed and inner validation) with and
  without the lags, tune 2015-2017 scored once; the plain refit must reproduce the gate MAE.
- Cross-validation inside train only (scored months 2005-01 to 2014-11): random 5-fold,
  leave-one-region-out over all months, yearly rolling origins, and leave-one-region-out with
  rolling origins. Regions: five contiguous blocks of districts (Ward on centroids with queen
  connectivity), one per fold via atlas.models.splits.spatial_blocks.
- Moran's I of tune residuals per month before and after the lags (atlas.analysis.spatial,
  999 permutations, BH across months); a month with a dry (unscored) district is not tested.
- M05 spatial challenger: v1 ridge (alpha 0.1) with and without neighbour SPI-1/SPI-3 at t-1 on
  the D97 rolling origins 2000-2015, target months before 2020 only (2020-2024 has been used).

The notebook notebooks/15_ka_spatial_ml.ipynb calls build(); then
`.venv/Scripts/python -m atlas.models.spatial_ml` logs MLflow, adds the gate key tune.spatial and
appends the T282 section to reports/models/m21-tune.md from the written summary.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa

from atlas.analysis.spatial import benjamini_hochberg, permutation_test, row_standardised
from atlas.models import m05
from atlas.models import m21_fit as fit
from atlas.models import nn_graph as nn
from atlas.models.m05 import rows_in
from atlas.models.splits import rolling_origin, spatial_blocks
from atlas.models.uncertainty import paired_block_bootstrap

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "data/models/m21/m21_dataset.parquet"
GATE = ROOT / "models/gates/m21.json"
OUTLINES = ROOT / "web/src/ka-districts.json"  # read only: centroids for the CV regions
TRAIN, TUNE = fit.TRAIN, fit.TUNE
SEED, PERMUTATIONS, Q = 282, 999, 0.05
REGIONS, RANDOM_FOLDS = 5, 5
CV_FIRST_ORIGIN = fit.CV_FIRST_ORIGIN  # 2005-01: the ridge CV origins of T281
M05_END = date(2019, 12, 31)  # 2020-2024 was the M05 v1 test: never re-scored
# feature -> columns whose row value describes month t - shift; the lag reads month t-1 only
M21_SPATIAL = {
    "nbr_anom_lag1": (("target_anom", 0), ("anom_lag1", 1)),
    "nbr_spi1_lag1": (("spi1_lag1", 1),),
    "nbr_spi3_lag1": (("spi3_lag1", 1),),
}
M05_SPATIAL = {"nbr_spi1_lag1": (("spi1_lag1", 1),), "nbr_spi3_lag1": (("spi3_lag1", 1),)}
WITH_LAGS = (*fit.m21_data.FEATURES, *M21_SPATIAL)
SCHEMES = {
    "random": "random 5-fold over district-months",
    "region": "leave one region out, all months",
    "temporal": "yearly rolling origins, all districts",
    "region_temporal": "leave one region out with yearly rolling origins",
}


# --- weights and lags ----------------------------------------------------------------------------


def neighbours(places: list[str]) -> list[list[int]]:
    """Queen neighbours (no self) in `places` order, from the committed T109 neighbour file."""
    a = nn.adjacency(places) > 0
    np.fill_diagonal(a, False)
    return [np.flatnonzero(r).tolist() for r in a]


def month_grid(rows: pa.Table, places: list[str], sources) -> np.ndarray:
    """[months from 1981-01, districts] of the values the rows carry for each month; NaN where
    unknown. A source (column, shift) gives the value of month t - shift for the row of month t."""
    months = [nn._index(m) for m in rows["target_month"].to_pylist()]
    col = {p: j for j, p in enumerate(places)}
    cols = [col[p] for p in rows["place_id"].to_pylist()]
    grid = np.full((max(months) + 1, len(places)), np.nan)
    for name, shift in sources:
        for i, j, v in zip(months, cols, rows[name].to_pylist(), strict=True):
            if v is not None and i - shift >= 0 and np.isnan(grid[i - shift, j]):
                grid[i - shift, j] = v
    return grid


def neighbour_mean(grid: np.ndarray, nbrs: list[list[int]]) -> np.ndarray:
    """Mean over each district's neighbours with a value; NaN when none has one."""
    out = np.full(grid.shape, np.nan)
    for j, nb in enumerate(nbrs):
        v = grid[:, nb]
        n = np.isfinite(v).sum(axis=1)
        out[:, j] = np.where(n > 0, np.nansum(v, axis=1) / np.maximum(n, 1), np.nan)
    return out


def spatial_lags(rows: pa.Table, places: list[str], nbrs: list[list[int]], spec) -> pa.Table:
    """Append the neighbour means of month t-1 to every row of month t."""
    i = np.array([nn._index(m) - 1 for m in rows["target_month"].to_pylist()])
    if (i < 0).any():
        raise ValueError("a row's month t-1 is before 1981-01")
    j = np.array([places.index(p) for p in rows["place_id"].to_pylist()])
    for name, sources in spec.items():
        lag = neighbour_mean(month_grid(rows, places, sources), nbrs)[i, j]
        rows = rows.append_column(name, pa.array([None if np.isnan(v) else float(v) for v in lag]))
    return rows


def centroids(places: list[str], path: Path = OUTLINES) -> np.ndarray:
    """District centroids (lon, lat) from the committed simplified S17 outlines (D209)."""
    import shapely.geometry

    feats = json.loads(path.read_text("utf-8"))["features"]
    c = {f["properties"]["place_id"]: shapely.geometry.shape(f["geometry"]).centroid for f in feats}
    return np.array([[c[p].x, c[p].y] for p in places])


def regions(
    places: list[str], nbrs: list[list[int]], lonlat: np.ndarray, k: int = REGIONS
) -> dict[str, str]:
    """k contiguous regions: Ward on centroids (longitude scaled by cos latitude) with queen
    connectivity, so every region is one connected block. Named R1.. in place order."""
    from sklearn.cluster import AgglomerativeClustering

    a = np.zeros((len(places), len(places)))
    for i, nb in enumerate(nbrs):
        a[i, nb] = 1.0
    xy = lonlat * [np.cos(np.radians(lonlat[:, 1].mean())), 1.0]
    labels = AgglomerativeClustering(n_clusters=k, connectivity=a, linkage="ward").fit_predict(xy)
    name = {lab: f"R{n}" for n, lab in enumerate(dict.fromkeys(labels.tolist()), start=1)}
    return {p: name[lab] for p, lab in zip(places, labels.tolist(), strict=True)}


def connected(members: list[int], nbrs: list[list[int]]) -> bool:
    seen, todo = {members[0]}, [members[0]]
    while todo:
        for j in nbrs[todo.pop()]:
            if j in members and j not in seen:
                seen.add(j)
                todo.append(j)
    return len(seen) == len(members)


# --- scoring helpers -----------------------------------------------------------------------------


def _ci(base: np.ndarray, cand: np.ndarray, blocks: list[str]) -> dict:
    imp = paired_block_bootstrap(base.tolist(), cand.tolist(), blocks)
    return {"mean": imp.mean, "lower95": imp.lower95, "upper95": imp.upper95}


def _blocks(rows: pa.Table) -> list[str]:
    return [m.strftime("%Y-%m") for m in fit._months(rows)]


def moran_by_month(resid, rows: pa.Table, places: list[str], nbrs, seed: int = SEED) -> list[dict]:
    """Moran's I of residuals per month with every district scored; others are skipped."""
    w, rng = row_standardised(nbrs), np.random.default_rng(seed)
    col = {p: j for j, p in enumerate(places)}
    grid: dict[date, np.ndarray] = {}
    for p, m, r in zip(rows["place_id"].to_pylist(), fit._months(rows), resid, strict=True):
        grid.setdefault(m, np.full(len(places), np.nan))[col[p]] = r
    out = []
    for m in sorted(grid):
        x = grid[m]
        if np.isnan(x).any():
            out.append({"month": m.isoformat()[:7], "districts": int(np.isfinite(x).sum())})
            continue
        out.append(
            {"month": m.isoformat()[:7], "districts": len(x)}
            | permutation_test(x, w, rng, PERMUTATIONS)
        )
    tested = [r for r in out if "p" in r]
    for r, q in zip(tested, benjamini_hochberg([r["p"] for r in tested]), strict=True):
        r["q_bh"], r["significant_q05"] = float(q), bool(q <= Q)
    return out


def moran_summary(by_month: list[dict]) -> dict:
    tested = [r for r in by_month if "p" in r]
    i = [r["moran_i"] for r in tested]
    return {
        "months": len(by_month),
        "months_tested": len(tested),
        "significant_bh": sum(r["significant_q05"] for r in tested),
        "significant_bh_positive": sum(
            r["significant_q05"] and r["moran_i"] > r["expected"] for r in tested
        ),
        "moran_i_median": float(np.median(i)),
        "moran_i_min": float(min(i)),
        "moran_i_max": float(max(i)),
    }


def effective_size(resid, rows: pa.Table, places: list[str]) -> dict:
    """Kish design effect from the one-way intra-month correlation of residuals (complete months):
    n_eff per month = k / (1 + (k - 1) ICC) for k districts."""
    by: dict[date, list[float]] = {}
    for m, r in zip(fit._months(rows), resid, strict=True):
        by.setdefault(m, []).append(r)
    x = np.array([v for v in by.values() if len(v) == len(places)])
    g, k = x.shape
    msb = k * ((x.mean(axis=1) - x.mean()) ** 2).sum() / (g - 1)
    msw = ((x - x.mean(axis=1, keepdims=True)) ** 2).sum() / (g * (k - 1))
    icc = (msb - msw) / (msb + (k - 1) * msw)
    return {
        "months": g,
        "districts": k,
        "icc": float(icc),
        "n_eff_per_month": k / (1 + (k - 1) * icc),
    }


# --- M21 on tune ---------------------------------------------------------------------------------


def tune_comparison(lagged: pa.Table, trials: int = fit.LGBM_TRIALS) -> dict:
    """LightGBM with the T281 features and with the spatial lags, fitted on train, tune once."""
    lagged = fit.scorable(lagged)
    train, tune = rows_in(lagged, *TRAIN), rows_in(lagged, *TUNE)
    y, blocks = fit._y(tune), _blocks(tune)
    fits = {
        "base": fit.fit_lightgbm(train, trials),
        "lags": fit.fit_lightgbm(train, trials, WITH_LAGS),
    }
    mu = {k: np.asarray(f["predict"](tune), dtype=float) for k, f in fits.items()}
    err = {k: np.abs(v - y) for k, v in mu.items()}
    err0 = np.abs(y)
    models = {
        k: {
            "mae": float(err[k].mean()),
            "improvement_over_climatology": _ci(err0, err[k], blocks),
            "params": fits[k]["params"],
        }
        for k in fits
    }
    return {
        "rows": tune.num_rows,
        "months": len(set(blocks)),
        "climatology_mae": float(err0.mean()),
        "models": models,
        "lags_over_base": _ci(err["base"], err["lags"], blocks),
        "residuals": {k: y - v for k, v in mu.items()},
        "tune": tune,
    }


# --- cross-validation inside train ---------------------------------------------------------------


def cv_folds(train: pa.Table, region_of: dict[str, str], scheme: str) -> list[tuple]:
    """(fit mask, score mask) pairs; every train row from 2005-01 is scored exactly once."""
    train = fit.train_only(train)
    months = np.array(fit._months(train))
    region = np.array([region_of[p] for p in train["place_id"].to_pylist()])
    scored = months >= CV_FIRST_ORIGIN
    origins = rolling_origin(
        TRAIN[0],
        CV_FIRST_ORIGIN,
        TRAIN[1],
        step_days=365,
        horizon_days=fit.m21_data.PURGE_DAYS,
        publication_lag_days=0,
    )
    blocks = spatial_blocks(region_of, len(set(region_of.values())))  # one region per fold
    if scheme == "random":
        fold = np.random.default_rng(SEED).permutation(len(months)) % RANDOM_FOLDS
        folds = [(fold != k, scored & (fold == k)) for k in range(RANDOM_FOLDS)]
    elif scheme == "region":
        folds = [(~np.isin(region, b), scored & np.isin(region, b)) for b in blocks]
    elif scheme in ("temporal", "region_temporal"):
        folds = []
        for s in origins:
            past = months <= s.train_end
            window = (months >= s.test_start) & (months <= s.test_end)
            if scheme == "temporal":
                folds.append((past, window))
            else:
                folds += [(past & ~np.isin(region, b), window & np.isin(region, b)) for b in blocks]
    else:
        raise ValueError(scheme)
    if not (np.sum([v for _, v in folds], axis=0) == scored).all():
        raise ValueError(f"{scheme}: scored rows are not each scored exactly once")
    return folds


def _booster(params: dict, rows: pa.Table, features: tuple[str, ...]):
    import lightgbm as lgb

    p = {
        k: v for k, v in params.items() if k not in ("num_boost_round", "trials", "inner_valid_mae")
    }
    b = lgb.train(p, lgb.Dataset(fit._x(rows, features), fit._y(rows)), params["num_boost_round"])
    return lambda r: b.predict(fit._x(r, features))


def spatial_cv(train: pa.Table, region_of: dict[str, str], params: dict) -> dict:
    """Each scheme with and without lags, the tune-selected config of each held fixed."""
    months = np.array(fit._months(train))
    scored = train.filter(pa.array(months >= CV_FIRST_ORIGIN))
    y, blocks = fit._y(scored), _blocks(scored)
    err0 = np.abs(y)
    out = {}
    for scheme in SCHEMES:
        folds = cv_folds(train, region_of, scheme)
        err = {}
        for name, features in (("base", fit.m21_data.FEATURES), ("lags", WITH_LAGS)):
            pred = np.full(len(months), np.nan)
            for a, b in folds:
                if b.any():
                    pred[b] = _booster(params[name], train.filter(pa.array(a)), features)(
                        train.filter(pa.array(b))
                    )
            err[name] = np.abs(pred[months >= CV_FIRST_ORIGIN] - y)
        out[scheme] = {
            "label": SCHEMES[scheme],
            "folds": len(folds),
            **{
                k: {"mae": float(e.mean()), "improvement_over_climatology": _ci(err0, e, blocks)}
                for k, e in err.items()
            },
            "lags_over_base": _ci(err["base"], err["lags"], blocks),
        }
    honest = out["region_temporal"]
    for v in out.values():  # how much each scheme overstates the honest one (positive = more)
        v["overstatement"] = {
            k: v[k]["improvement_over_climatology"]["mean"]
            - honest[k]["improvement_over_climatology"]["mean"]
            for k in ("base", "lags")
        }
    return {
        "scored": f"{CV_FIRST_ORIGIN:%Y-%m} to {TRAIN[1]:%Y-%m} inside train",
        "rows": scored.num_rows,
        "months": len(set(blocks)),
        "climatology_mae": float(err0.mean()),
        "schemes": out,
    }


# --- M05 spatial challenger, pre-2020 only -------------------------------------------------------


def _m05_design(table: pa.Table, extra: tuple[str, ...], mean=None, std=None):
    """m05._design plus extra columns (same order, sin/cos month last, train scaling)."""
    x = np.column_stack(
        [np.asarray(table[f].to_pylist(), dtype=float) for f in (*m05.FEATURES, *extra)]
    )
    month = np.asarray(table["month_of_year"].to_pylist(), dtype=float)
    x = np.column_stack([x, np.sin(2 * np.pi * month / 12), np.cos(2 * np.pi * month / 12)])
    if mean is None:
        mean, std = x.mean(axis=0), x.std(axis=0)
        std[std == 0] = 1.0
    return (x - mean) / std, mean, std


def m05_challenger(rows: pa.Table, alpha: float, places: list[str], nbrs) -> dict:
    """v1 ridge against ridge plus neighbour SPI at t-1 on the D97 origins, months to 2019-12."""
    from sklearn.linear_model import Ridge

    rows = rows_in(rows, min(rows["target_month"].to_pylist()), M05_END)  # never 2020+
    rows = spatial_lags(rows, places, nbrs, M05_SPATIAL)
    first, parts = min(rows["target_month"].to_pylist()), []
    for origin in m05.ORIGINS:
        train = rows_in(rows, first, origin - timedelta(days=m05.PURGE_DAYS + 1))
        stop = min(date(origin.year + 5, 1, 1) - timedelta(days=1), M05_END)
        window = rows_in(rows, origin, stop)
        y, part = np.asarray(window[m05.TARGET].to_pylist(), dtype=float), {}
        for name, extra in (("ridge", ()), ("ridge_spatial", tuple(M05_SPATIAL))):
            x, mean, std = _m05_design(train, extra)
            model = Ridge(alpha=alpha).fit(
                x, np.asarray(train[m05.TARGET].to_pylist(), dtype=float)
            )
            part[name] = y - model.predict(_m05_design(window, extra, mean, std)[0])
        part["persistence"] = y - np.asarray(window["spi3_lag1"].to_pylist(), dtype=float)
        parts.append((window, part))
    table = pa.concat_tables([w for w, _ in parts])
    resid = {k: np.concatenate([p[k] for _, p in parts]) for k in parts[0][1]}
    reference = m05.rolling_residuals(rows, alpha, end=M05_END)["ridge"]
    if not np.allclose(resid["ridge"], reference, atol=1e-9):
        raise ValueError("the no-lag ridge does not reproduce m05.rolling_residuals")
    blocks, err = _blocks(table), {k: np.abs(v) for k, v in resid.items()}
    moran = {
        k: moran_summary(moran_by_month(resid[k], table, places, nbrs))
        for k in ("ridge", "ridge_spatial")
    }
    return {
        "origins": [o.isoformat() for o in m05.ORIGINS],
        "first_month": f"{min(fit._months(table)):%Y-%m}",
        "last_month": f"{max(fit._months(table)):%Y-%m}",
        "rows": table.num_rows,
        "months": len(set(blocks)),
        "alpha": alpha,
        "features_added": list(M05_SPATIAL),
        "mae": {k: float(e.mean()) for k, e in err.items()},
        "spatial_over_ridge": _ci(err["ridge"], err["ridge_spatial"], blocks),
        "ridge_over_persistence": _ci(err["persistence"], err["ridge"], blocks),
        "moran": moran,
        "status": "research-only",
    }


def m05_rows() -> tuple[pa.Table, float]:  # pragma: no cover - needs the local S08 and S17 raw
    """The M05 v1 dataset rebuilt from raw (hash-checked against the saved v1 fit)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from m05_release import RAW, s17

    from atlas.config import load_state
    from atlas.features import m05 as features
    from atlas.ingest.s17 import S17

    ka = load_state(ROOT / "configs/states/ka.yaml")
    districts = S17("ka").parse(s17("e06"), ka.source("S17"), adm1=s17("e05"))
    raws = features.year_artifacts(RAW, range(1981, 2025))
    rows = features.feature_rows(
        features.spi_table(features.district_monthly_rain(raws, districts))
    )
    saved = json.loads((ROOT / "data/models/m05/m05_fit.json").read_text("utf-8"))
    if m05.table_sha256(rows) != saved["dataset_sha256"]:
        raise ValueError("M05 dataset hash differs from the saved v1 fit")
    return rows, saved["ridge"]["alpha"]


# --- build ---------------------------------------------------------------------------------------


def build(out: Path) -> dict:  # pragma: no cover - needs the local M21 dataset and M05 raw
    import pyarrow.parquet as pq

    rows = pq.read_table(DATASET)
    gate = json.loads(GATE.read_text("utf-8"))
    if m05.table_sha256(rows) != gate["dataset_sha256"]:
        raise ValueError("dataset hash differs from the gate")
    history = fit.scorable(rows_in(rows, TRAIN[0], TUNE[1]))
    places = sorted(set(history["place_id"].to_pylist()))
    names = dict(zip(history["place_id"].to_pylist(), history["name"].to_pylist(), strict=True))
    nbrs = neighbours(places)
    region_of = regions(places, nbrs, centroids(places))
    lagged = spatial_lags(history, places, nbrs, M21_SPATIAL)

    t = tune_comparison(lagged)
    if not np.isclose(t["models"]["base"]["mae"], gate["tune"]["models"]["lightgbm"]["mae"]):
        raise ValueError("LightGBM refit does not reproduce its T281 tune MAE")
    tune, resid = t.pop("tune"), t.pop("residuals")
    by_month = {k: moran_by_month(resid[k], tune, places, nbrs) for k in resid}
    y = fit._y(tune)
    district = []
    for p in places:
        sel = np.array([q == p for q in tune["place_id"].to_pylist()])
        district.append(
            {
                "place_id": p,
                "name": names[p],
                "region": region_of[p],
                "rows": int(sel.sum()),
                **{
                    f"improvement_{k}": float(np.abs(y[sel]).mean() - np.abs(resid[k][sel]).mean())
                    for k in resid
                },
            }
        )
    cv = spatial_cv(
        rows_in(lagged, *TRAIN), region_of, {k: v["params"] for k, v in t["models"].items()}
    )
    m05_table, alpha = m05_rows()
    if set(m05_table["place_id"].to_pylist()) != set(places):
        raise ValueError("M05 and M21 districts differ")
    lag_ci = t["lags_over_base"]
    summary = {
        "task": "T282",
        "evidence": "hindcast (D39); research and comparison only, never the M21 candidate",
        "inputs": {
            "m21_dataset_sha256": gate["dataset_sha256"],
            "m21_split_sha256": gate["split_sha256"],
            "m05_dataset_sha256": m05.table_sha256(m05_table),
            "neighbours": "reports/eda/10_spatial_statistics/district_neighbours.csv",
        },
        "spatial_features": {
            "nbr_anom_lag1": "mean M21 anomaly of month t-1 over queen neighbours with a value",
            "nbr_spi1_lag1": "mean SPI-1 of month t-1 over queen neighbours",
            "nbr_spi3_lag1": "mean SPI-3 of month t-1 over queen neighbours",
            "rule": "month t-1 only; a neighbour's month t value is never a feature",
        },
        "regions": {
            "rule": f"{REGIONS} contiguous blocks: Ward on district centroids with queen "
            "connectivity (fixed before any CV score)",
            "members": {
                r: sorted(names[p] for p in places if region_of[p] == r)
                for r in sorted(set(region_of.values()))
            },
        },
        "tune": t | {"lag_helps": lag_ci["lower95"] > 0},
        "moran": {
            "residuals": "tune target minus LightGBM forecast (anomaly units)",
            "permutations": PERMUTATIONS,
            "seed": SEED,
            "q": Q,
            "rule": "months with a dry (unscored) district are not tested",
            "before": moran_summary(by_month["base"]),
            "after": moran_summary(by_month["lags"]),
            "by_month": [
                {"month": b["month"], "districts": b["districts"]}
                | {
                    f"{k}_{s}": r[f]
                    for k, r in (("before", b), ("after", a))
                    for s, f in (("i", "moran_i"), ("p", "p"), ("q", "q_bh"))
                    if f in r
                }
                for b, a in zip(by_month["base"], by_month["lags"], strict=True)
            ],
            "effective_size": effective_size(resid["base"], tune, places),
        },
        "districts": district,
        "cv": cv,
        "m05_challenger": m05_challenger(m05_table, alpha, places, nbrs),
        "limits": [
            "Hindcast (D39); tune is 36 months, so intervals are wide.",
            "The CV reuses each model's config chosen on the inner slice 2012-01..2014-11, which "
            "lies inside the scored CV months: all schemes share that optimism.",
            "Regions come from centroids and the adjacency; another partition gives other numbers.",
            "Neighbours outside Karnataka are not in the weights (30 S17 districts).",
            "M05 challenger: pre-2020 rolling origins only, research-only; it waits for the "
            "2026-2027 test defined for M05 v2.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return {"summary": summary, "places": places, "region_of": region_of}


# --- outputs -------------------------------------------------------------------------------------


def log_mlflow(s: dict, tracking_uri: str, hashes: dict) -> dict[str, str]:
    """One M21 run (tune and CV metrics) and one M05 run (pre-2020 challenger)."""
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    ids = {}
    mlflow.set_experiment("M21")
    with mlflow.start_run(run_name="t282-lightgbm-spatial-lags") as run:
        mlflow.log_params(
            {"task": "T282", "model": "lightgbm+spatial_lags", **hashes}
            | {"features_added": ",".join(M21_SPATIAL), "regions": REGIONS}
        )
        t, m = s["tune"], {}
        for k in ("base", "lags"):
            m[f"tune_mae_{k}"] = t["models"][k]["mae"]
        for b in ("mean", "lower95", "upper95"):
            m[f"tune_lags_over_base_{b}"] = t["lags_over_base"][b]
        for k in ("before", "after"):
            m[f"moran_median_{k}"] = s["moran"][k]["moran_i_median"]
            m[f"moran_significant_bh_{k}"] = s["moran"][k]["significant_bh"]
        for name, v in s["cv"]["schemes"].items():
            for k in ("base", "lags"):
                m[f"cv_{name}_{k}_mae"] = v[k]["mae"]
                m[f"cv_{name}_{k}_improvement"] = v[k]["improvement_over_climatology"]["mean"]
        mlflow.log_metrics(m)
        mlflow.set_tags({"split": "train-cv and tune", "role": "comparison, never the candidate"})
        ids["m21"] = run.info.run_id
    mlflow.set_experiment("M05")
    c = s["m05_challenger"]
    with mlflow.start_run(run_name="t282-m05-spatial-challenger") as run:
        mlflow.log_params(
            {"task": "T282", "model": "ridge+spatial_lags", "alpha": c["alpha"]}
            | {
                "origins": ",".join(c["origins"]),
                "dataset_sha256": s["inputs"]["m05_dataset_sha256"],
            }
        )
        mlflow.log_metrics(
            {f"mae_{k}": v for k, v in c["mae"].items()}
            | {
                f"spatial_over_ridge_{b}": c["spatial_over_ridge"][b]
                for b in ("mean", "lower95", "upper95")
            }
        )
        mlflow.set_tags(
            {"status": "research-only", "months": f"{c['first_month']}..{c['last_month']}"}
        )
        ids["m05"] = run.info.run_id
    return ids


HEADER = "# M21 spatial lags and spatial checks (T282)"


def render(s: dict) -> str:
    """The T282 section appended to reports/models/m21-tune.md, from summary.json only."""
    t, mo, cv, c = s["tune"], s["moran"], s["cv"], s["m05_challenger"]
    b, a = t["models"]["base"], t["models"]["lags"]
    helps = "helps" if t["lag_helps"] else "does not help"
    rows = [
        HEADER,
        "",
        "**Comparison only: never the candidate, and the test is not opened.** Spatial lags are "
        "the mean over a district's queen neighbours of the anomaly, SPI-1 and SPI-3 of month "
        "t-1 (a neighbour's month t value is never a feature). LightGBM is refitted with the T281 "
        "procedure with and without them; tune 2015-2017 scored once. Notebook "
        "`notebooks/15_ka_spatial_ml.ipynb`, outputs in `reports/eda/15_ka_spatial_ml/`.",
        "",
        f"**The spatial lag {helps} on tune**: MAE improvement of the lags over plain LightGBM "
        f"{fit._ci(t['lags_over_base'])} (paired block bootstrap by month, 95% interval).",
        "",
        "| Model | Tune MAE | MAE improvement over climatology (95% interval) |",
        "|---|---|---|",
        *(
            f"| {label} | {m['mae']:.3f} | {fit._ci(m['improvement_over_climatology'])} |"
            for label, m in (("LightGBM, T281 features (refit)", b), ("LightGBM + spatial lags", a))
        ),
        "",
        "## Moran's I of tune residuals",
        "",
        f"{mo['before']['months_tested']} of {mo['before']['months']} tune months have every "
        f"district scored ({mo['permutations']} permutations, BH at q = {mo['q']}). Median I "
        f"{mo['before']['moran_i_median']:.2f} before and "
        f"{mo['after']['moran_i_median']:.2f} after the lags; significant months "
        f"{mo['before']['significant_bh']} and "
        f"{mo['after']['significant_bh']}. Intra-month correlation of residuals "
        f"{mo['effective_size']['icc']:.2f}, so a month of 30 districts carries about "
        f"{mo['effective_size']['n_eff_per_month']:.1f} independent values: every interval here "
        "resamples whole months.",
        "",
        f"## Cross-validation inside train ({cv['scored']}, {cv['rows']} district-months)",
        "",
        "Improvement over climatology (MAE, 95% interval); overstatement = this scheme minus "
        "leave-one-region-out with rolling origins (the honest one).",
        "",
        "| Scheme | Folds | Without lags | With lags | Overstatement without / with |",
        "|---|---|---|---|---|",
    ]
    for v in cv["schemes"].values():
        rows.append(
            f"| {v['label']} | {v['folds']} | {fit._ci(v['base']['improvement_over_climatology'])} "
            f"| {fit._ci(v['lags']['improvement_over_climatology'])} "
            f"| {v['overstatement']['base']:+.3f} / {v['overstatement']['lags']:+.3f} |"
        )
    rows += [
        "",
        "## M05 spatial challenger (research-only)",
        "",
        f"v1 ridge (alpha {c['alpha']:g}) with and without neighbour SPI-1 and SPI-3 at t-1, D97 "
        f"rolling origins, {c['first_month']} to {c['last_month']} ({c['rows']} district-months; "
        "2020-2024 was the v1 test and is not re-scored). MAE "
        f"{c['mae']['ridge']:.3f} without and {c['mae']['ridge_spatial']:.3f} with the lags; "
        f"improvement {fit._ci(c['spatial_over_ridge'])}. Median Moran's I of residuals "
        f"{c['moran']['ridge']['moran_i_median']:.2f} without and "
        f"{c['moran']['ridge_spatial']['moran_i_median']:.2f} with. Not promotable: it waits for "
        "the 2026-2027 test defined for M05 v2.",
        "",
        f"MLflow: M21 run `{s['mlflow_run_ids']['m21']}`, M05 run `{s['mlflow_run_ids']['m05']}`.",
        "",
    ]
    return "\n".join(rows)


def main() -> None:  # pragma: no cover - needs the notebook's summary and the local MLflow store
    from atlas.models.registry import git_sha

    s = json.loads((ROOT / "reports/eda/15_ka_spatial_ml/summary.json").read_text("utf-8"))
    gate = json.loads(GATE.read_text("utf-8"))
    if gate["test_opened"] or s["inputs"]["m21_dataset_sha256"] != gate["dataset_sha256"]:
        raise ValueError("gate and summary disagree, or the test is open")
    hashes = {
        "dataset_sha256": gate["dataset_sha256"],
        "split_sha256": gate["split_sha256"],
        "git_sha": git_sha(ROOT),
    }
    uri = f"sqlite:///{(ROOT / 'data/models/mlflow.db').as_posix()}"
    s["mlflow_run_ids"] = log_mlflow(s, uri, hashes)
    gate["tune"]["spatial"] = {
        "task": "T282",
        "role": "comparison only; never the candidate",
        **hashes,
        "tune": s["tune"],
        "moran": {k: s["moran"][k] for k in ("before", "after", "effective_size")},
        "cv": {
            k: {kk: v[kk] for kk in ("base", "lags", "overstatement")}
            for k, v in s["cv"]["schemes"].items()
        },
        "mlflow_run_ids": s["mlflow_run_ids"],
    }
    GATE.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8", newline="\n")
    path = ROOT / "reports/models/m21-tune.md"
    text = path.read_text("utf-8").split("\n" + HEADER)[0].rstrip("\n") + "\n"
    path.write_text(text + "\n" + render(s), encoding="utf-8", newline="\n")
    print(json.dumps(s["mlflow_run_ids"]))


if __name__ == "__main__":
    main()
