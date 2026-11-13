"""M21 classical models on train, scored on tune only (T281).

Per-district SARIMA, pooled ridge and pooled LightGBM, each fitted on train (1982-01 to 2014-11)
with every choice made inside train: SARIMA order by AIC, ridge alpha by rolling-origin CV,
LightGBM config and rounds by early stopping on an inner validation slice (2012-01 to 2014-11).
Tune (2015-2017) is scored once; calibrate and the locked test are refused. No candidate is named
here (T283 adds networks, T284 names the candidate before the test is opened).

Probabilistic scores use an ensemble: point forecast plus the model's out-of-sample train
residuals. Baselines: climatology (anomaly 0; terciles 1/3 each; train anomalies of that district
and calendar month for CRPS), the train median of that district and calendar month, persistence
and last year.

Run from the repository root: .venv/Scripts/python -m atlas.models.m21_fit
"""

from __future__ import annotations

import json
import time
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa

from atlas.features.base import LeakageError
from atlas.models import m21_data
from atlas.models.m05 import LGBM_SPACE as M05_LGBM_SPACE
from atlas.models.m05 import rows_in
from atlas.models.splits import rolling_origin
from atlas.models.uncertainty import paired_block_bootstrap

SEED = 42
TRAIN = m21_data.TRAIN
TUNE = m21_data.PERIODS["tune"]
INNER_VALID = (date(2012, 1, 1), TRAIN[1])  # LightGBM early stopping; inner train ends 2011-11
CV_FIRST_ORIGIN = date(2005, 1, 1)  # ridge: ten yearly rolling origins inside train
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0)
LGBM_SPACE = M05_LGBM_SPACE | {"objective": ("regression", "regression_l1")}
LGBM_TRIALS = 30
SARIMA_ORDERS = (  # small orders on an already deseasonalised anomaly
    ((0, 0, 0), (0, 0, 0, 0)),
    ((1, 0, 0), (0, 0, 0, 0)),
    ((0, 0, 1), (0, 0, 0, 0)),
    ((1, 0, 1), (0, 0, 0, 0)),
    ((2, 0, 0), (0, 0, 0, 0)),
    ((1, 0, 0), (1, 0, 0, 12)),
)
MODELS = ("sarima", "ridge", "lightgbm")


def _months(rows: pa.Table) -> list[date]:
    return rows["target_month"].to_pylist()


def train_only(rows: pa.Table) -> pa.Table:
    """Fitting accepts train rows only; any later target month is refused."""
    if max(_months(rows)) > TRAIN[1]:
        raise LeakageError(f"fit rows run past the train end {TRAIN[1]}")
    return rows


def scorable(rows: pa.Table) -> pa.Table:
    """Scoring stops at the tune end; calibrate and the locked test are refused before T284."""
    if max(_months(rows)) > m21_data.SCORABLE_END:
        raise LeakageError(f"rows after {m21_data.SCORABLE_END} are not scored before T284")
    return rows


def _y(rows: pa.Table) -> np.ndarray:
    return np.asarray(rows["target_anom"].to_pylist(), dtype=float)


def _x(rows: pa.Table) -> np.ndarray:
    """Features as floats; a lag that is a dry month stays NaN (LightGBM handles it natively)."""
    return np.column_stack(
        [np.asarray(rows[f].to_pylist(), dtype=float) for f in m21_data.FEATURES]
    )


def _ridge_x(rows: pa.Table) -> np.ndarray:
    """Ridge design: NaN lags become 0 (climatology), month becomes sin and cos."""
    x = np.nan_to_num(_x(rows)[:, :-1], nan=0.0)
    month = np.asarray(rows["month_of_year"].to_pylist(), dtype=float)
    return np.column_stack([x, np.sin(2 * np.pi * month / 12), np.cos(2 * np.pi * month / 12)])


# --- ridge ---------------------------------------------------------------------------------------


def _ridge(x: np.ndarray, y: np.ndarray, alpha: float):
    from sklearn.linear_model import Ridge

    mean, std = x.mean(axis=0), x.std(axis=0)
    std[std == 0] = 1.0
    model = Ridge(alpha=alpha).fit((x - mean) / std, y)
    return lambda new: model.predict((new - mean) / std), model, mean, std


def fit_ridge(train: pa.Table) -> dict:
    """Alpha by mean MAE over yearly rolling origins inside train (31-day purge)."""
    train = train_only(train)
    folds = rolling_origin(
        TRAIN[0],
        CV_FIRST_ORIGIN,
        TRAIN[1],
        step_days=365,
        horizon_days=m21_data.PURGE_DAYS,
        publication_lag_days=0,
    )
    cv, oof = {}, {}
    for alpha in RIDGE_ALPHAS:
        errs = []
        for s in folds:
            a, b = (
                rows_in(train, s.train_start, s.train_end),
                rows_in(train, s.test_start, s.test_end),
            )
            predict = _ridge(_ridge_x(a), _y(a), alpha)[0]
            errs.append(predict(_ridge_x(b)) - _y(b))
        cv[alpha], oof[alpha] = (
            float(np.mean([np.abs(e).mean() for e in errs])),
            np.concatenate(errs),
        )
    alpha = min(RIDGE_ALPHAS, key=cv.get)
    predict, model, mean, std = _ridge(_ridge_x(train), _y(train), alpha)
    return {
        "predict": lambda rows, history=None: predict(_ridge_x(rows)),
        "residuals": -oof[alpha],  # y - forecast
        "params": {"alpha": alpha, "cv_folds": len(folds)},
        "cv_mae": {str(k): v for k, v in cv.items()},
        "coef": model.coef_.tolist(),
    }


# --- LightGBM ------------------------------------------------------------------------------------


def _lgbm_params(rng: np.random.Generator) -> dict:
    params = {k: v[rng.integers(len(v))] for k, v in LGBM_SPACE.items()}
    params = {k: (v.item() if hasattr(v, "item") else v) for k, v in params.items()}
    return params | {"seed": SEED, "deterministic": True, "num_threads": 4, "verbose": -1}


def fit_lightgbm(train: pa.Table, trials: int = LGBM_TRIALS) -> dict:
    """Seeded random search; early stopping and selection on the inner validation slice of train.
    The chosen config is refitted on all train rows with its early-stopped number of rounds."""
    import lightgbm as lgb

    train = train_only(train)
    inner = rows_in(train, TRAIN[0], date(INNER_VALID[0].year - 1, 11, 30))  # 31-day purge
    valid = rows_in(train, *INNER_VALID)
    xi, yi, xv, yv = _x(inner), _y(inner), _x(valid), _y(valid)
    rng, best = np.random.default_rng(SEED), None
    for _ in range(trials):
        params = _lgbm_params(rng)
        booster = lgb.train(
            params,
            lgb.Dataset(xi, yi),
            num_boost_round=1000,
            valid_sets=[lgb.Dataset(xv, yv)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )
        resid = yv - booster.predict(xv, num_iteration=booster.best_iteration)
        mae = float(np.abs(resid).mean())
        if best is None or mae < best[0]:
            best = (mae, params | {"num_boost_round": booster.best_iteration}, resid)
    mae, params, resid = best
    rounds = params["num_boost_round"]
    booster = lgb.train(
        {k: v for k, v in params.items() if k != "num_boost_round"},
        lgb.Dataset(_x(train), _y(train)),
        num_boost_round=rounds,
    )
    return {
        "predict": lambda rows, history=None: booster.predict(_x(rows)),
        "residuals": resid,
        "params": params | {"trials": trials, "inner_valid_mae": mae},
        "model": booster.model_to_string(),
    }


# --- SARIMA --------------------------------------------------------------------------------------


def _series(rows: pa.Table, place: str, end: date) -> np.ndarray:
    """Monthly anomaly series of one district from 1982-01 to `end`; NaN where none (dry)."""
    n = (end.year - TRAIN[0].year) * 12 + end.month - TRAIN[0].month + 1
    out = np.full(n, np.nan)
    for p, m, z in zip(rows["place_id"].to_pylist(), _months(rows), _y(rows).tolist(), strict=True):
        i = (m.year - TRAIN[0].year) * 12 + m.month - TRAIN[0].month
        if p == place and 0 <= i < n:
            out[i] = z
    return out


def fit_sarima(train: pa.Table) -> dict:
    """Per district, the order with the lowest AIC on train; a constant term throughout."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    train = train_only(train)
    fits, resid = {}, []
    for place in sorted(set(train["place_id"].to_pylist())):
        y = _series(train, place, TRAIN[1])
        best = None
        for order, seasonal in SARIMA_ORDERS:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = SARIMAX(y, order=order, seasonal_order=seasonal, trend="c").fit(disp=False)
            if best is None or res.aic < best[0]:
                best = (res.aic, order, seasonal, res)
        _, order, seasonal, res = best
        fits[place] = (order, seasonal, res)
        r = (y - res.predict())[13:]  # one-step-ahead errors after a year of burn-in
        resid.append(r[np.isfinite(r)])

    def predict(rows: pa.Table, history: pa.Table) -> np.ndarray:
        """One-step-ahead forecasts with the train parameters held fixed (no refit): the filter
        reads the observed anomalies up to month t-1 from `history`, as the lag features do."""
        end = max(_months(scorable(history)))
        cache = {}
        for place, (_, _, res) in fits.items():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                cache[place] = res.apply(_series(history, place, end)).predict()
        return np.array(
            [
                cache[p][(m.year - TRAIN[0].year) * 12 + m.month - TRAIN[0].month]
                for p, m in zip(rows["place_id"].to_pylist(), _months(rows), strict=True)
            ]
        )

    orders = {}
    for order, seasonal, _ in fits.values():
        key = f"{order}x{seasonal}" if seasonal[3] else str(order)
        orders[key] = orders.get(key, 0) + 1
    return {
        "predict": predict,
        "residuals": np.concatenate(resid),
        "params": {"selection": "AIC on train", "orders": orders},
        "coef": {p: res.params.tolist() for p, (_, _, res) in fits.items()},
    }


# --- scoring -------------------------------------------------------------------------------------


def tercile_bounds(train: pa.Table) -> dict[tuple[str, int], tuple[float, float]]:
    """Tercile edges in anomaly units per district and calendar month: midpoints between the
    observed 1982-2010 classes (classes come from 1981-2010 mm terciles; anomaly is monotone)."""
    groups: dict[tuple[str, int], list[tuple[float, int]]] = {}
    for r in train_only(train).to_pylist():
        if r["target_month"].year <= m21_data.REFERENCE[1]:
            groups.setdefault((r["place_id"], r["month_of_year"]), []).append(
                (r["target_anom"], r["target_tercile"])
            )
    out = {}
    for key, v in groups.items():
        below, near, above = ([a for a, t in v if t == c] for c in (-1, 0, 1))
        # tied mm terciles (many zero-rain years) can leave a class empty
        lo = (max(below) + min(near or above)) / 2 if below else -np.inf
        hi = (max(near or below) + min(above)) / 2 if above else np.inf
        out[key] = (lo, hi)
    return out


def _rps(p_below: np.ndarray, p_above: np.ndarray, cls: np.ndarray) -> np.ndarray:
    """Ranked probability score for three ordered classes, scaled to 0..1."""
    f1, f2 = p_below, 1 - p_above
    return ((f1 - (cls == -1)) ** 2 + (f2 - (cls <= 0)) ** 2) / 2


def _ens_scores(mu: np.ndarray, resid: np.ndarray, rows: pa.Table, bounds) -> dict:
    """CRPS and RPS of the ensemble mu + residuals (the same residuals for every row)."""
    y, cls = _y(rows), np.asarray(rows["target_tercile"].to_pylist())
    r = np.sort(resid)
    n = len(r)
    spread = 2 * np.sum((2 * np.arange(n) - n + 1) * r) / n**2  # E|R - R'|
    members = mu[:, None] + r[None, :]
    crps = np.abs(members - y[:, None]).mean(axis=1) - spread / 2
    keys = zip(rows["place_id"].to_pylist(), rows["month_of_year"].to_pylist(), strict=True)
    lo, hi = np.array([bounds[k] for k in keys]).T
    rps = _rps((members < lo[:, None]).mean(axis=1), (members > hi[:, None]).mean(axis=1), cls)
    return {"crps": crps, "rps": rps}


def _climatology_scores(train: pa.Table, rows: pa.Table) -> dict:
    """Climatology: terciles 1/3 each; CRPS of the train anomalies of that district and month."""
    groups: dict[tuple[str, int], list[float]] = {}
    for r in train.to_pylist():
        groups.setdefault((r["place_id"], r["month_of_year"]), []).append(r["target_anom"])
    crps = []
    for p, m, y in zip(
        rows["place_id"].to_pylist(),
        rows["month_of_year"].to_pylist(),
        _y(rows).tolist(),
        strict=True,
    ):
        x = np.asarray(groups[(p, m)])
        crps.append(np.abs(x - y).mean() - np.abs(x[:, None] - x[None, :]).mean() / 2)
    cls = np.asarray(rows["target_tercile"].to_pylist())
    third = np.full(rows.num_rows, 1 / 3)
    return {"crps": np.asarray(crps), "rps": _rps(third, third, cls)}


def _interval(base: np.ndarray, cand: np.ndarray, blocks: list[str]) -> dict:
    imp = paired_block_bootstrap(base.tolist(), cand.tolist(), blocks)
    return {"mean": imp.mean, "lower95": imp.lower95, "upper95": imp.upper95}


def run(rows: pa.Table, trials: int = LGBM_TRIALS) -> dict:
    """Fit the three families on train, score them and the baselines on tune. Returns plain
    numbers for the gate plus each fit (for MLflow)."""
    history = scorable(rows)  # train, the Dec 2014 purge month and tune; nothing later
    train, tune = rows_in(rows, *TRAIN), rows_in(rows, *TUNE)
    y, blocks = _y(tune), [m.strftime("%Y-%m") for m in _months(tune)]
    bounds = tercile_bounds(train)
    clim = _climatology_scores(train, tune)
    medians: dict[tuple[str, int], list[float]] = {}
    for r in train.to_pylist():
        medians.setdefault((r["place_id"], r["month_of_year"]), []).append(r["target_anom"])
    keys = list(zip(tune["place_id"].to_pylist(), tune["month_of_year"].to_pylist(), strict=True))
    point = m21_data.baselines(tune) | {
        "climatology_median": [float(np.median(medians[k])) for k in keys]
    }
    err0 = np.abs(y)
    out = {
        "rows": tune.num_rows,
        "months": len(set(blocks)),
        "models": {
            "climatology": {
                "mae": float(err0.mean()),
                "rps": float(clim["rps"].mean()),
                "crps": float(clim["crps"].mean()),
            }
        },
    }
    err_med = np.abs(np.asarray(point["climatology_median"]) - y)
    for name in ("climatology_median", "persistence", "last_year"):
        err = np.abs(np.asarray(point[name]) - y)
        out["models"][name] = {
            "mae": float(err.mean()),
            "improvement_over_climatology": _interval(err0, err, blocks),
        }
    fits = {}
    for name, fitter in (
        ("sarima", fit_sarima),
        ("ridge", fit_ridge),
        ("lightgbm", lambda t: fit_lightgbm(t, trials)),
    ):
        start = time.perf_counter()
        fit = fitter(train)
        seconds = time.perf_counter() - start
        mu = np.asarray(fit["predict"](tune, history), dtype=float)
        err = np.abs(mu - y)
        ens = _ens_scores(mu, fit["residuals"], tune, bounds)
        out["models"][name] = {
            "mae": float(err.mean()),
            "improvement_over_climatology": _interval(err0, err, blocks),
            "improvement_over_median": _interval(err_med, err, blocks),
            "rps": float(ens["rps"].mean()),
            "rpss": float(1 - ens["rps"].mean() / clim["rps"].mean()),
            "rps_improvement": _interval(clim["rps"], ens["rps"], blocks),
            "crps": float(ens["crps"].mean()),
            "crps_improvement": _interval(clim["crps"], ens["crps"], blocks),
            "train_seconds": round(seconds, 1),
            "params": fit["params"],
        }
        fits[name] = fit
    out["beat_climatology_mae"] = sorted(
        k
        for k, v in out["models"].items()
        if v.get("improvement_over_climatology", {}).get("lower95", -1) > 0
    )
    return {"tune": out, "fits": fits}


# --- outputs -------------------------------------------------------------------------------------


def log_mlflow(tune: dict, tracking_uri: str, hashes: dict) -> dict[str, str]:
    """One run per model family in experiment M21: params, tune metrics, hashes and git sha."""
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("M21")
    ids = {}
    for name in MODELS:
        m = tune["models"][name]
        with mlflow.start_run(run_name=f"t281-{name}") as run:
            mlflow.log_params(
                {"task": "T281", "model": name, **hashes}
                | {k: json.dumps(v) if isinstance(v, dict) else v for k, v in m["params"].items()}
            )
            metrics = {f"tune_{k}": m[k] for k in ("mae", "rps", "rpss", "crps", "train_seconds")}
            for k in (
                "improvement_over_climatology",
                "improvement_over_median",
                "rps_improvement",
                "crps_improvement",
            ):
                metrics |= {f"tune_{k}_{s}": m[k][s] for s in ("mean", "lower95", "upper95")}
            mlflow.log_metrics(metrics)
            mlflow.set_tags({"split": "tune", "evidence": "hindcast (D39)"})
            ids[name] = run.info.run_id
    return ids


LABELS = {
    "climatology": "Climatology (anomaly 0)",
    "climatology_median": "Train median of district and month",
    "persistence": "Persistence (t-1)",
    "last_year": "Same month last year (t-12)",
    "sarima": "SARIMA per district",
    "ridge": "Ridge (pooled)",
    "lightgbm": "LightGBM (pooled)",
}


def _ci(v: dict | None) -> str:
    return "-" if v is None else f"{v['mean']:+.3f} [{v['lower95']:+.3f}, {v['upper95']:+.3f}]"


def render(tune: dict) -> str:
    """reports/models/m21-tune.md, written from the gate's tune section only."""
    m = tune["models"]
    lines = [
        "# M21 classical models on the tune years (T281)",
        "",
        "**Tune only (2015-2017). Calibrate (2018-2019) and the locked test (2020-2025) are not "
        "scored. T281 named no candidate**; T283 (below) adds networks and names it, and T284 "
        "opens the test once. Hindcast (D39).",
        "",
        "Every choice was made inside train (1982-01 to 2014-11): SARIMA order by AIC per "
        "district, ridge alpha by mean MAE over ten yearly rolling origins (31-day purge), "
        f"LightGBM by a seeded random search of {m['lightgbm']['params']['trials']} configs with "
        "early stopping on an inner validation slice (2012-01 to 2014-11), then refitted on all "
        "train rows. Tune was scored once.",
        "",
        f"{tune['rows']} district-months in {tune['months']} months. MAE of the anomaly (lower is "
        "better). Improvement = climatology loss minus model loss, paired block bootstrap by "
        "month (1,000 resamples, seed 42), 95% interval. RPS is the tercile ranked probability "
        "score (climatology: 1/3 each); RPSS = 1 - RPS / RPS of climatology. CRPS: the model's "
        "forecast plus its out-of-sample train residuals; climatology uses the train anomalies of "
        "the same district and calendar month.",
        "",
        "| Model | Tune MAE | MAE improvement over climatology (95% interval) | RPS | RPSS "
        "| CRPS | CRPS improvement (95% interval) | Train seconds |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for k in ("climatology", "climatology_median", "persistence", "last_year", *MODELS):
        v = m[k]
        rps = f"{v['rps']:.3f}" if "rps" in v else "-"
        rpss = f"{v['rpss']:+.3f}" if "rpss" in v else ("0" if k == "climatology" else "-")
        crps = f"{v['crps']:.3f}" if "crps" in v else "-"
        secs = f"{v['train_seconds']:.1f}" if "train_seconds" in v else "-"
        lines.append(
            f"| {LABELS[k]} | {v['mae']:.3f} | {_ci(v.get('improvement_over_climatology'))} "
            f"| {rps} | {rpss} | {crps} | {_ci(v.get('crps_improvement'))} | {secs} |"
        )
    beat = tune["beat_climatology_mae"]
    lines += [
        "",
        "## Reading",
        "",
        (
            "On MAE, the lower 95% bound is above 0 for: "
            + ", ".join(LABELS[k] for k in beat)
            + "."
            if beat
            else "On MAE, nothing beats climatology on tune: no lower 95% bound is above 0."
        ),
        "The train median of the district and calendar month is a stronger point baseline than "
        "anomaly 0, because monthly rain is skewed (the median anomaly is below 0); a model "
        "that only learns this shift is not skill. MAE improvement over that median (95% "
        "interval): "
        + "; ".join(f"{LABELS[k]} {_ci(m[k]['improvement_over_median'])}" for k in MODELS)
        + ".",
        "",
        "## Choices made on train",
        "",
        f"- SARIMA orders chosen: {m['sarima']['params']['orders']} (districts per order).",
        f"- Ridge alpha: {m['ridge']['params']['alpha']:g}.",
        "- LightGBM: "
        + ", ".join(
            f"{k} {round(v, 3) if isinstance(v, float) else v}"
            for k, v in m["lightgbm"]["params"].items()
            if k not in ("seed", "deterministic", "num_threads", "verbose", "trials")
        )
        + ".",
        "",
        "## Runs",
        "",
        f"MLflow experiment M21 in `data/models/mlflow.db` (local), git {tune['git_sha'][:12]} "
        "(the commit before T281; the T281 code is in the T281 commit). Run IDs: "
        + ", ".join(f"{k} `{tune['mlflow_run_ids'][k]}`" for k in MODELS)
        + f". Dataset sha256 {tune['dataset_sha256'][:16]}, split sha256 "
        f"{tune['split_sha256'][:16]}.",
        "",
        "## Limits",
        "",
        "- Hindcast only; S08 is released yearly. The tune years are 36 months, so intervals are "
        "wide.",
        "- SARIMA forecasts are one step ahead with train parameters held fixed; the filter reads "
        "anomalies up to month t-1, the same information as the lag features. ETS was not fitted: "
        "dry months leave gaps that SARIMA's state-space filter handles and ETS does not.",
        "- Probabilistic scores use pooled residuals (anomalies are already standardised per "
        "district and month).",
        "- Tercile edges in anomaly units are midpoints between the 1982-2010 classes in train; "
        "1981 has no row (lags need a year).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - needs the local dataset
    import pyarrow.parquet as pq

    from atlas.models.m05 import table_sha256
    from atlas.models.registry import git_sha

    root = Path(__file__).resolve().parents[3]
    rows = pq.read_table(root / "data/models/m21/m21_dataset.parquet")
    gate_path = root / "models/gates/m21.json"
    gate = json.loads(gate_path.read_text("utf-8"))
    if table_sha256(rows) != gate["dataset_sha256"]:
        raise ValueError("dataset hash differs from the gate; rebuild with atlas.models.m21_data")
    result = run(rows_in(rows, TRAIN[0], TUNE[1]))
    tune = result["tune"]
    hashes = {
        "dataset_sha256": gate["dataset_sha256"],
        "split_sha256": gate["split_sha256"],
        "git_sha": git_sha(root),
    }
    uri = f"sqlite:///{(root / 'data/models/mlflow.db').as_posix()}"
    tune = {"task": "T281"} | hashes | tune | {"mlflow_run_ids": log_mlflow(tune, uri, hashes)}
    gate["tune"] = tune
    gate_path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8", newline="\n")
    (root / "reports/models/m21-tune.md").write_text(render(tune), encoding="utf-8", newline="\n")
    print(json.dumps({k: v["mae"] for k, v in tune["models"].items()}, indent=2))


if __name__ == "__main__":
    main()
