"""M21 locked test, opened once, with split-conformal 80% intervals (T284, plan items 3 and 5).

Two steps, run once each and in this order from the repository root:

1. `.venv/Scripts/python -m atlas.models.m21_test prepare` writes REFIT_RULE, INTERVAL_RULE and
   PROMOTION_RULE into the gate and fixes the interval method and offsets on pre-test years only:
   the T281 LightGBM config refitted on train must reproduce its tune MAE; its tune residuals
   give offsets for each method and its calibrate coverage picks one (D97's rule). The candidate
   is then refitted with the frozen config on train + tune; its calibrate residuals give the
   offsets that the test will use.
2. `.venv/Scripts/python -m atlas.models.m21_test open` refuses if the test is open or no interval
   rule is written, marks the gate opened (time and git sha) before any test row is predicted,
   refits the candidate and every comparison once with frozen configs, scores the locked test
   2020-2025 once, applies the promotion rule mechanically and writes the report, card and release.

Hindcast (D39); 2025 is provisional (D98).
"""

from __future__ import annotations

import json
import sys
import warnings
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pyarrow as pa

from atlas.features.base import LeakageError
from atlas.models import m21_data
from atlas.models import m21_fit as fit
from atlas.models import nn_graph as nn
from atlas.models import spatial_ml as sm
from atlas.models.m05 import rows_in
from atlas.models.registry import Release
from atlas.models.uncertainty import conformal_interval, coverage

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "models/gates/m21.json"
DATASET = ROOT / "data/models/m21/m21_dataset.parquet"
TRAIN, TUNE = fit.TRAIN, fit.TUNE
CALIBRATE, TEST = m21_data.PERIODS["calibrate"], m21_data.PERIODS["test"]
REFIT = (TRAIN[0], date(2017, 11, 30))  # train + tune less the 31-day purge before calibrate
COVERAGE, SHOW = 0.8, (0.75, 0.85)
MONSOON = (6, 7, 8, 9)
METHODS = ("pooled", "seasonal")
SEASONS = {
    "winter (Jan-Feb)": (1, 2),
    "pre-monsoon (Mar-May)": (3, 4, 5),
    "monsoon (Jun-Sep)": MONSOON,
    "post-monsoon (Oct-Dec)": (10, 11, 12),
}
CANDIDATE = "lightgbm"
COMPARISONS = ("sarima", "ridge", "lightgbm_lags", "mlp", "gcn_gru", "gcn_gru_identity")
LABELS = fit.LABELS | nn.LABELS | {"lightgbm_lags": "LightGBM + spatial lags (T282)"}
REFIT_RULE = (
    "Fixed before the test was opened (T284). Every model, the candidate and each comparison, "
    "keeps the configuration frozen on train and tune (LightGBM parameters and rounds; ridge "
    "alpha; SARIMA order per district by AIC on train; network sizes and each seed's "
    "early-stopped epoch count) and is refitted once on train + tune, target months 1982-01 to "
    "2017-11 (31-day purge before calibrate). Nothing is re-tuned. Each refit's calibrate "
    "(2018-2019) residuals give its probabilistic ensemble (RPS, CRPS) and the candidate's "
    "interval offsets. The locked test 2020-2025 is scored once."
)
INTERVAL_RULE = (
    "80% nominal, D97 style. Methods: pooled split conformal (forecast plus the 10th and 90th "
    "percentiles of calibration residuals, y - forecast) and seasonal (the same, separately for "
    "June-September and the rest of the year). Chosen before the test on pre-test years only: "
    "offsets from the tune (2015-2017) residuals of the train fit, coverage checked on calibrate "
    "(2018-2019) with the same fit; the method whose coverage is closest to 80% wins (ties: "
    "narrower mean width). The chosen method's offsets are then taken from the calibrate "
    "residuals of the train + tune refit and applied unchanged to the test. Intervals are shown "
    "only if test coverage is within 75-85%."
)
PROMOTION_RULE = (
    "candidate_eligible only if the lower 95% bound of the MAE improvement over the strongest "
    "simple baseline on the test rows (climatology, persistence or last year; paired block "
    "bootstrap by month, 1,000 resamples, seed 42) is above 0, and then served only after owner "
    "approval (D38); otherwise research_only, published with its scores."
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _blocks(rows: pa.Table) -> list[str]:
    return [m.strftime("%Y-%m") for m in fit._months(rows)]


def _moy(rows: pa.Table) -> np.ndarray:
    return np.asarray(rows["month_of_year"].to_pylist())


# --- intervals -----------------------------------------------------------------------------------


def _group(moy: np.ndarray, method: str) -> np.ndarray:
    if method == "pooled":
        return np.full(len(moy), "all", dtype=object)
    return np.where(np.isin(moy, MONSOON), "monsoon (Jun-Sep)", "rest of year")


def offsets(resid: np.ndarray, moy: np.ndarray, method: str) -> dict[str, list[float]]:
    """10th and 90th residual percentiles per group (split conformal, 80%)."""
    g = _group(moy, method)
    return {k: list(conformal_interval(resid[g == k], COVERAGE)) for k in sorted(set(g))}


def interval(mu: np.ndarray, moy: np.ndarray, offs: dict, method: str):
    g = _group(moy, method)
    return (
        mu + np.array([offs[k][0] for k in g]),
        mu + np.array([offs[k][1] for k in g]),
    )


def choose(selection: list[dict]) -> str:
    """Coverage closest to 80% wins; ties go to the narrower interval."""
    return min(
        selection,
        key=lambda s: (round(abs(s["calibrate_coverage"] - COVERAGE), 12), s["calibrate_width"]),
    )["method"]


# --- step 1: rules and intervals, before the test ------------------------------------------------


def prepare(rows: pa.Table, gate: dict) -> dict:
    """Write the refit, interval and promotion rules and the interval offsets into the gate."""
    if gate["test_opened"]:
        raise ValueError("the test is already open")
    if gate["candidate"]["model"] != CANDIDATE:
        raise ValueError("this procedure is written for the named LightGBM candidate")
    rows = rows_in(rows, TRAIN[0], CALIBRATE[1])  # no test row is read here
    params = gate["tune"]["models"][CANDIDATE]["params"]
    tune, cal = rows_in(rows, *TUNE), rows_in(rows, *CALIBRATE)
    first = sm._booster(params, rows_in(rows, *TRAIN), m21_data.FEATURES)
    resid_tune = fit._y(tune) - first(tune)
    if not np.isclose(np.abs(resid_tune).mean(), gate["tune"]["models"][CANDIDATE]["mae"]):
        raise ValueError("the train fit does not reproduce the T281 tune MAE")
    mu, y_cal = first(cal), fit._y(cal)
    selection = []
    for method in METHODS:
        lo, hi = interval(mu, _moy(cal), offsets(resid_tune, _moy(tune), method), method)
        selection.append(
            {
                "method": method,
                "calibrate_coverage": coverage(y_cal, lo, hi),
                "calibrate_width": float((hi - lo).mean()),
            }
        )
    method = choose(selection)
    refit_rows = rows_in(rows, *REFIT)
    resid_cal = y_cal - sm._booster(params, refit_rows, m21_data.FEATURES)(cal)
    gate["test_protocol"] = {
        "task": "T284",
        "refit_rule": REFIT_RULE,
        "refit_rows": refit_rows.num_rows,
        "interval_rule": INTERVAL_RULE,
        "promotion_rule": PROMOTION_RULE,
        "intervals": {
            "method": method,
            "coverage": COVERAGE,
            "show_if": list(SHOW),
            "selection": selection,
            "offsets": offsets(resid_cal, _moy(cal), method),
            "calibrate_rows": cal.num_rows,
            "calibrate_mae": {
                CANDIDATE: float(np.abs(resid_cal).mean()),
                "climatology": float(np.abs(y_cal).mean()),
            },
        },
        "written_at": _now(),
    }
    return gate


# --- step 2: open once ---------------------------------------------------------------------------


def open_test(gate: dict, git_sha: str) -> dict:
    """Mark the locked test opened. A second opening is refused, whatever the reason."""
    if gate.get("test_opened"):
        raise ValueError("the M21 test was opened once already; it is never opened again")
    if "intervals" not in gate.get("test_protocol", {}):
        raise ValueError("write the refit and interval rules (prepare) before opening the test")
    return gate | {"test_opened": True, "test_opened_at": _now(), "test_git_sha": git_sha}


def _sarima(train: pa.Table, refit: pa.Table, rows: pa.Table, recorded: dict):
    """Orders per district by AIC on train (as T281), parameters re-estimated on the refit rows,
    one-step forecasts that read the anomalies up to month t-1 from `rows`."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    chosen = fit.fit_sarima(train)
    if chosen["params"]["orders"] != recorded:
        raise ValueError("SARIMA orders differ from the T281 gate")
    end, cache = max(fit._months(rows)), {}
    for p, (order, seasonal) in chosen["orders_by_place"].items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = SARIMAX(
                fit._series(refit, p, REFIT[1]), order=order, seasonal_order=seasonal, trend="c"
            ).fit(disp=False)
            cache[p] = res.apply(fit._series(rows, p, end)).predict()

    def predict(period):
        r = rows_in(rows, *period)
        return np.array(
            [
                cache[p][(m.year - TRAIN[0].year) * 12 + m.month - TRAIN[0].month]
                for p, m in zip(r["place_id"].to_pylist(), fit._months(r), strict=True)
            ]
        )

    return predict


def fitted(rows: pa.Table, gate: dict) -> dict[str, list]:
    """Every model refitted once on REFIT rows with its frozen config (REFIT_RULE). Each entry
    is a list (one per seed) of functions period -> forecasts for rows_in(rows, *period); every
    forecast reads months up to t-1 only."""
    refit, train, tune = rows_in(rows, *REFIT), rows_in(rows, *TRAIN), gate["tune"]
    feats = m21_data.FEATURES
    lgbm = sm._booster(tune["models"][CANDIDATE]["params"], refit, feats)
    ridge = fit._ridge(
        fit._ridge_x(refit), fit._y(refit), tune["models"]["ridge"]["params"]["alpha"]
    )
    places = sorted(set(refit["place_id"].to_pylist()))
    lagged = sm.spatial_lags(rows, places, sm.neighbours(places), sm.M21_SPATIAL)
    lags = sm._booster(
        tune["spatial"]["tune"]["models"]["lags"]["params"], rows_in(lagged, *REFIT), sm.WITH_LAGS
    )
    out = {
        CANDIDATE: [lambda p: lgbm(rows_in(rows, *p))],
        "sarima": [_sarima(train, refit, rows, tune["models"]["sarima"]["params"]["orders"])],
        "ridge": [lambda p: ridge[0](fit._ridge_x(rows_in(rows, *p)))],
        "lightgbm_lags": [lambda p: lags(rows_in(lagged, *p))],
    }
    seeds = {k: tune["networks"]["models"][k]["seeds"] for k in nn.NETWORKS}
    x_fit = fit._ridge_x(refit)
    scale, y_fit = nn._scaler(x_fit), fit._y(refit).astype(np.float32)
    out["mlp"] = []
    for s in seeds["mlp"]:
        model = nn._train(
            lambda n=x_fit.shape[1]: nn.mlp(n),
            scale(x_fit),
            y_fit,
            s["seed"],
            nn.BATCH["mlp"],
            epochs=s["best_epoch"],
        )["model"]
        out["mlp"].append(lambda p, m=model: nn._predict(m, scale(fit._ridge_x(rows_in(rows, *p)))))
    months, y_gcn = nn._targets(refit, places)
    x_gcn, pan = nn._windows(nn.panel(refit, places), months), nn.panel(rows, places)
    idx = {p: i for i, p in enumerate(places)}

    def gcn_predict(period, model):
        r = rows_in(rows, *period)
        ms = sorted(set(fit._months(r)))
        at = {m: i for i, m in enumerate(ms)}
        pred = nn._predict(model, nn._windows(pan, ms))
        return np.array(
            [
                pred[at[m], idx[p]]
                for p, m in zip(r["place_id"].to_pylist(), fit._months(r), strict=True)
            ]
        )

    for name, matrix in (
        ("gcn_gru", nn.adjacency(places)),
        ("gcn_gru_identity", np.eye(len(places))),
    ):
        out[name] = []
        for s in seeds[name]:
            model = nn._train(
                lambda a=matrix: nn.gcn_gru(a),
                x_gcn,
                y_gcn,
                s["seed"],
                nn.BATCH["gcn"],
                epochs=s["best_epoch"],
            )["model"]
            out[name].append(lambda p, m=model: gcn_predict(p, m))
    return out


def evaluate(rows: pa.Table, gate: dict, period: tuple[date, date] = TEST) -> dict:
    """Score the candidate, the baselines and the comparisons once on `period` rows."""
    if period == TEST and not gate.get("test_opened"):
        raise LeakageError("open the test (open_test) before any test row is scored")
    proto = gate["test_protocol"]["intervals"]
    models = fitted(rows, gate)
    cal, test, refit = (rows_in(rows, *p) for p in (CALIBRATE, period, REFIT))
    y, y_cal, blocks, moy = fit._y(test), fit._y(cal), _blocks(test), _moy(test)
    bounds = fit.tercile_bounds(rows_in(rows, *TRAIN))
    clim = fit._climatology_scores(refit, test)
    medians: dict[tuple[str, int], list[float]] = {}
    for r in refit.to_pylist():
        medians.setdefault((r["place_id"], r["month_of_year"]), []).append(r["target_anom"])
    keys = zip(test["place_id"].to_pylist(), moy.tolist(), strict=True)
    point = m21_data.baselines(test) | {
        "climatology_median": [float(np.median(medians[k])) for k in keys]
    }
    err = {k: np.abs(np.asarray(v) - y) for k, v in point.items()}
    strongest = min(m21_data.BASELINES, key=lambda k: err[k].mean())

    def compare(e: np.ndarray, mask=slice(None)) -> dict:
        b = list(np.asarray(blocks)[mask])
        return {
            "mae": float(e[mask].mean()),
            "improvement_over_baseline": fit._interval(err[strongest][mask], e[mask], b),
            "improvement_over_climatology": fit._interval(err["climatology"][mask], e[mask], b),
        }

    scores = {k: compare(e) for k, e in err.items()}
    scores["climatology"] |= {"rps": float(clim["rps"].mean()), "crps": float(clim["crps"].mean())}
    errors = dict(err)
    for name, preds in models.items():
        mus = [np.asarray(f(period), dtype=float) for f in preds]
        res = [y_cal - np.asarray(f(CALIBRATE), dtype=float) for f in preds]
        e = np.mean([np.abs(mu - y) for mu in mus], axis=0)  # seed-mean errors (T283)
        ens = [fit._ens_scores(mu, r, test, bounds) for mu, r in zip(mus, res, strict=True)]
        rps = np.mean([s["rps"] for s in ens], axis=0)
        crps = np.mean([s["crps"] for s in ens], axis=0)
        scores[name] = compare(e) | {
            "improvement_over_median": fit._interval(err["climatology_median"], e, blocks),
            "rps": float(rps.mean()),
            "rpss": float(1 - rps.mean() / clim["rps"].mean()),
            "rps_improvement": fit._interval(clim["rps"], rps, blocks),
            "crps": float(crps.mean()),
            "crps_improvement": fit._interval(clim["crps"], crps, blocks),
            "calibrate_mae": float(np.mean([np.abs(r).mean() for r in res])),
        }
        if len(preds) > 1:
            scores[name]["seed_mae"] = [float(np.abs(mu - y).mean()) for mu in mus]
        errors[name] = e
        if name == CANDIDATE:
            lo, hi = interval(mus[0], moy, proto["offsets"], proto["method"])
    inside, width = (y >= lo) & (y <= hi), hi - lo
    by_season = {}
    for season, months in SEASONS.items():
        m = np.isin(moy, months)
        by_season[season] = {
            "rows": int(m.sum()),
            "months": len({b for b, k in zip(blocks, m, strict=True) if k}),
            "mae": {k: float(errors[k][m].mean()) for k in (CANDIDATE, *m21_data.BASELINES)},
            "improvement_over_baseline": compare(errors[CANDIDATE], m)["improvement_over_baseline"],
            "interval_coverage": float(inside[m].mean()),
            "interval_width": float(width[m].mean()),
        }
    places = np.asarray(test["place_id"].to_pylist())
    by_place = [float(inside[places == p].mean()) for p in sorted(set(places))]
    cov = float(inside.mean())
    low = scores[CANDIDATE]["improvement_over_baseline"]["lower95"]
    status = "candidate_eligible" if low > 0 else "research_only"
    return {
        "task": "T284",
        "period": [period[0].isoformat(), period[1].isoformat()],
        "rows": test.num_rows,
        "months": len(set(blocks)),
        "strongest_baseline": strongest,
        "candidate": CANDIDATE,
        "models": scores,
        "by_season": by_season,
        "intervals": {
            "method": proto["method"],
            "coverage": cov,
            "width": float(width.mean()),
            "shown": SHOW[0] <= cov <= SHOW[1],
            "by_district": {
                "districts": len(by_place),
                "min": min(by_place),
                "max": max(by_place),
                "inside_75_85": sum(SHOW[0] <= c <= SHOW[1] for c in by_place),
            },
        },
        "promotion": {
            "baseline": strongest,
            "lower95": low,
            "status": status,
            "reason": f"lower 95% bound of the MAE improvement over {strongest} is {low:+.3f}, "
            + (
                "above 0; needs owner approval (D38)"
                if low > 0
                else "not above 0; published research-only with its scores"
            ),
        },
    }


# --- outputs -------------------------------------------------------------------------------------


def release(gate: dict) -> Release:
    t = gate["test"]
    c, b = t["models"][CANDIDATE], t["models"][t["strongest_baseline"]]
    return Release(
        model_id="M21",
        version="v1",
        created_at=datetime.now(UTC),
        dataset_sha256=gate["dataset_sha256"],
        git_sha=gate["test_git_sha"],
        cutoffs={
            "train": f"{REFIT[0].isoformat()}/{REFIT[1].isoformat()}",
            "selection_train": f"{TRAIN[0].isoformat()}/{TRAIN[1].isoformat()}",
            "tune": f"{TUNE[0].isoformat()}/{TUNE[1].isoformat()}",
            "calibrate": f"{CALIBRATE[0].isoformat()}/{CALIBRATE[1].isoformat()}",
            "test": "/".join(t["period"]),
            "split_manifest_sha256": gate["split_sha256"],
            "source_sha256": gate["source_sha256"],
        },
        baseline=t["strongest_baseline"],
        baseline_scores={k: b[k] for k in ("mae", "rps", "crps") if k in b},
        candidate=CANDIDATE,
        candidate_scores={k: c[k] for k in ("mae", "rps", "rpss", "crps")}
        | {
            "interval80_coverage": t["intervals"]["coverage"],
            "interval80_width": t["intervals"]["width"],
        },
        improvement=c["improvement_over_baseline"] | {"n_rows": t["rows"], "n_blocks": t["months"]},
        status=t["promotion"]["status"],
        reason=t["promotion"]["reason"],
    )


def render(gate: dict) -> str:
    """reports/models/m21.md, from the gate only."""
    t, tp, tune = gate["test"], gate["test_protocol"], gate["tune"]
    iv, m, pr = t["intervals"], t["models"], t["promotion"]
    base = t["strongest_baseline"]
    net, sp = tune["networks"]["models"], tune["spatial"]["tune"]["models"]
    lines = [
        "# M21 Karnataka monthly district rain-anomaly forecast: locked test (T284)",
        "",
        f"**Status: {pr['status']}.** The named candidate (LightGBM): {pr['reason']}. "
        f"80% intervals covered {iv['coverage']:.3f} of test outcomes, "
        + (
            "inside the 75-85% gate, so they may be shown."
            if iv["shown"]
            else "outside the 75-85% gate, so they stay hidden."
        ),
        "",
        "**This is a hindcast** (D39): features assume IMD rain up to the previous month was "
        "known on day 1 of the month; IMD publishes the gridded files yearly. 2025 is "
        "provisional (D98). Not a forecast service and not an emergency product.",
        "",
        "## Question, data and target",
        "",
        "Will next month be wetter or drier than normal in this district? Target: the z-score of "
        "month t district rain against the 1981-2010 mean and sd of that district and calendar "
        "month (S08 IMD gridded rain, 30 geoBoundaries 2021 districts; only indices leave the "
        f"pipeline). Dry district-months (1981-2010 sd below 10 mm, "
        f"{gate['dry_rule']['excluded_district_months']} of 360) are left out, never scored. "
        "Features: anomaly lags 1-12, SPI-1/3/6 and the state-mean anomaly at t-1, calendar "
        "month. Splits: train 1982-01 to 2014-11, tune 2015-2017, calibrate 2018-2019, locked "
        "test 2020-2025 (31-day purge).",
        "",
        "## The story before the test (train and tune only)",
        "",
        "- Baselines (T280, D214): climatology (anomaly 0) beat persistence and last year on "
        f"tune (MAE {gate['baselines']['tune']['mae']['climatology']:.3f}, "
        f"{gate['baselines']['tune']['mae']['persistence']:.3f}, "
        f"{gate['baselines']['tune']['mae']['last_year']:.3f}).",
        "- Classical (T281, D216), tune MAE: SARIMA per district "
        f"{tune['models']['sarima']['mae']:.3f}, ridge {tune['models']['ridge']['mae']:.3f}, "
        f"LightGBM {tune['models']['lightgbm']['mae']:.3f} "
        f"({fit._ci(tune['models']['lightgbm']['improvement_over_climatology'])} "
        "over climatology).",
        "- Networks (T283, D217), five seeds, tune MAE mean: MLP "
        f"{net['mlp']['summary']['mae_mean']:.3f}, GCN-GRU "
        f"{net['gcn_gru']['summary']['mae_mean']:.3f}"
        f", identity ablation {net['gcn_gru_identity']['summary']['mae_mean']:.3f}; the graph "
        f"added nothing ({fit._ci(tune['networks']['graph_over_identity'])}).",
        "- Spatial (T282, D218): neighbour lags at t-1, tune MAE "
        f"{sp['lags']['mae']:.3f} vs {sp['base']['mae']:.3f} without; leaky cross-validation "
        "overstated skill by about 0.08 MAE; residuals are spatially correlated within a month "
        "(about 2 independent values per month), so every interval resamples whole months.",
        f"- Candidate named before the test by a written rule: **LightGBM** "
        f"({gate['candidate']['reason']})",
        "",
        "## Protocol fixed before the test was opened",
        "",
        f"Written to the gate at {tp['written_at']}; the test was opened at "
        f"{gate['test_opened_at']} (git {gate['test_git_sha'][:12]}, the commit before T284).",
        "",
        f"- Refit: {tp['refit_rule']} ({tp['refit_rows']} rows.)",
        f"- Intervals: {tp['interval_rule']}",
        f"- Promotion: {tp['promotion_rule']}",
        "",
        "Interval method selection (pre-test years only):",
        "",
        "| Method | Calibrate coverage (offsets from tune) | Mean width |",
        "|---|---|---|",
        *(
            f"| {s['method']} | {s['calibrate_coverage']:.3f} | {s['calibrate_width']:.3f} |"
            for s in tp["intervals"]["selection"]
        ),
        "",
        f"Chosen: **{tp['intervals']['method']}**. Offsets from the refit's calibrate residuals: "
        + "; ".join(
            f"{k} [{v[0]:+.3f}, {v[1]:+.3f}]" for k, v in tp["intervals"]["offsets"].items()
        )
        + ".",
        "",
        "## Locked test 2020-2025, opened once",
        "",
        f"{t['rows']} district-months in {t['months']} months. Strongest simple baseline on the "
        f"test rows: **{base}**. Improvement = baseline loss minus model loss, paired block "
        "bootstrap by month (1,000 resamples, seed 42), 95% interval. RPS: terciles, RPSS = "
        "1 - RPS / RPS of climatology (1/3 each). CRPS: forecast plus the model's calibrate "
        "residuals; climatology uses the train + tune anomalies of that district and month. "
        "Networks: mean over five seeds (seed-mean errors).",
        "",
        f"| Model | Role | Test MAE | MAE improvement over {base} (95% interval) | RPSS | CRPS "
        "| CRPS improvement (95% interval) |",
        "|---|---|---|---|---|---|---|",
    ]
    for k in (*m21_data.BASELINES, "climatology_median", CANDIDATE, *COMPARISONS):
        v = m[k]
        role = (
            "candidate"
            if k == CANDIDATE
            else ("baseline" if k in m21_data.BASELINES else "comparison, not eligible")
        )
        rpss = f"{v['rpss']:+.3f}" if "rpss" in v else ("0" if k == "climatology" else "-")
        crps = f"{v['crps']:.3f}" if "crps" in v else "-"
        crps_ci = fit._ci(v["crps_improvement"]) if "crps_improvement" in v else "-"
        lines.append(
            f"| {LABELS[k]} | {role} | {v['mae']:.3f} | {fit._ci(v['improvement_over_baseline'])} "
            f"| {rpss} | {crps} | {crps_ci} |"
        )
    beat = [k for k in COMPARISONS if m[k]["improvement_over_baseline"]["lower95"] > 0]
    c = m[CANDIDATE]
    lines += [
        "",
        "Reading:",
        "",
        "- MAE: "
        + (
            "comparisons whose lower 95% bound is above 0: "
            + ", ".join(LABELS[k] for k in beat)
            + ". They were not the named candidate, so this test cannot promote them; a claim "
            "for any of them needs a new rule and an untouched test period."
            if beat
            else "no comparison has a lower 95% bound above 0."
        ),
        f"- Terciles: the candidate's RPS improvement over climatology is "
        f"{fit._ci(c['rps_improvement'])} and its CRPS improvement {fit._ci(c['crps_improvement'])}"
        "; the promotion rule is on MAE only, so these are reported, not used.",
        f"- Intervals: coverage {iv['coverage']:.3f} is just inside the gate; by district it "
        f"runs from {iv['by_district']['min']:.3f} to {iv['by_district']['max']:.3f}, so a good "
        "average hides districts where the 80% interval is too narrow.",
        "",
        "By season (candidate; improvement over the strongest baseline; 80% interval):",
        "",
        "| Season | Rows | Months | LightGBM MAE | Climatology MAE | Improvement (95% interval) "
        "| Interval coverage | Mean width |",
        "|---|---|---|---|---|---|---|---|",
        *(
            f"| {s} | {v['rows']} | {v['months']} | {v['mae'][CANDIDATE]:.3f} "
            f"| {v['mae']['climatology']:.3f} | {fit._ci(v['improvement_over_baseline'])} "
            f"| {v['interval_coverage']:.3f} | {v['interval_width']:.3f} |"
            for s, v in t["by_season"].items()
        ),
        "",
        "## Gates",
        "",
        "| Gate | Achieved | Rule | Result |",
        "|---|---|---|---|",
        f"| MAE improvement over {base}, lower 95% bound | {pr['lower95']:+.3f} | above 0 "
        f"| {'pass' if pr['lower95'] > 0 else 'fail'} |",
        f"| 80% interval coverage | {iv['coverage']:.3f} (mean width {iv['width']:.3f}) "
        f"| 0.75 to 0.85 | {'pass, shown' if iv['shown'] else 'fail, hidden'} |",
        f"| Interval coverage by district | {iv['by_district']['min']:.3f} to "
        f"{iv['by_district']['max']:.3f}; {iv['by_district']['inside_75_85']} of "
        f"{iv['by_district']['districts']} inside 75-85% | reported | - |",
        "",
        f"**Outcome: {pr['status']}.** Applied mechanically from the rule above; no model, "
        "feature, interval or threshold was changed after the test numbers were seen.",
        "",
        "## Limits",
        "",
        "- Hindcast only (S08 is released yearly); 2025 is provisional (D98). M05 was tested on "
        "2020-2024 with related inputs, so every M21 choice was fixed on train and tune only.",
        "- 72 test months; districts move together within a month, so the effective sample is "
        "far smaller than the row count.",
        "- One-month rain anomalies from local history alone are close to unpredictable; no "
        "ocean index (ENSO, IOD) is used (it would need a new source and verify task).",
        "- Comparisons were scored at the same single opening and are labelled; none can be "
        "promoted from this test.",
        "- Ballari includes Vijayanagara (geoBoundaries 2021 lines).",
        "",
        f"Release: `models/registry/M21/v1.json` (dataset {gate['dataset_sha256'][:12]}, split "
        f"{gate['split_sha256'][:12]}). MLflow run `{t['mlflow_run_id']}` (experiment M21). "
        "Tune details: [m21-tune.md](m21-tune.md). Card: [m21-card.md](m21-card.md).",
        "",
    ]
    return "\n".join(lines)


def render_card(gate: dict) -> str:
    """reports/models/m21-card.md in the M05 card format, from the gate only."""
    t, tp = gate["test"], gate["test_protocol"]
    pr, iv = t["promotion"], t["intervals"]
    c, b = t["models"][CANDIDATE], t["models"][t["strongest_baseline"]]
    rows = [
        (
            "Scope",
            "Karnataka; regression of the monthly rain anomaly with tercile probabilities. Not "
            "an emergency decision system. Hindcast only (D39).",
        ),
        (
            "Target, horizon and unit",
            "Month t district rain as a z-score against the 1981-2010 mean and sd of that "
            "district and calendar month (unitless), issued at 00:00 IST on day 1 of t. Dry "
            "district-months (1981-2010 sd below 10 mm) are not scored.",
        ),
        (
            "Features and lag evidence",
            "S08 anomaly lags 1-12, SPI-1/3/6 and the state-mean anomaly at t-1, calendar month. "
            "No month-t value. IMD releases yearly files, so the issue-time availability is "
            "assumed (D39).",
        ),
        (
            "Train, tune, calibration and test",
            "Choices on train 1982-01 to 2014-11 and tune 2015-2017; refit on 1982-01 to 2017-11; "
            "calibrate 2018-2019 (intervals); locked test 2020-2025, opened once on "
            f"{gate['test_opened_at'][:10]}; 31-day purges.",
        ),
        ("Units of analysis", "30 geoBoundaries 2021 districts (Ballari includes Vijayanagara)."),
        (
            "Baselines",
            "Climatology (anomaly 0), persistence (t-1) and same month last year; "
            f"{t['strongest_baseline']} is strongest on the test rows "
            f"(MAE {b['mae']:.3f}). Train median per district and month reported too.",
        ),
        (
            "Candidates",
            "LightGBM named by a written rule on tune (D217). Scored as comparisons, not "
            "eligible: SARIMA per district, ridge, LightGBM with spatial lags, MLP, GCN-GRU and "
            "its identity ablation.",
        ),
        (
            "Achieved metrics (test)",
            f"MAE {c['mae']:.3f} vs {b['mae']:.3f}; improvement "
            f"{c['improvement_over_baseline']['mean']:+.3f}, 95% CI "
            f"{c['improvement_over_baseline']['lower95']:+.3f} to "
            f"{c['improvement_over_baseline']['upper95']:+.3f}; RPSS {c['rpss']:+.3f}; CRPS "
            f"{c['crps']:.3f} vs {t['models']['climatology']['crps']:.3f} for climatology.",
        ),
        (
            "Uncertainty",
            f"Split-conformal 80% intervals ({tp['intervals']['method']} offsets from 2018-2019 "
            f"residuals, fixed before the test): coverage {iv['coverage']:.3f}, mean width "
            f"{iv['width']:.3f}; "
            + (
                "inside the 75-85% gate, may be shown."
                if iv["shown"]
                else "outside 75-85%, hidden."
            ),
        ),
        (
            "Data licence",
            "IMD rain may not be reproduced; only derived indices and model outputs are published "
            "(D129, D158). Cite Pai et al. (2014).",
        ),
        (
            "Limits",
            "Meteorological anomaly only; no ocean indices; 72 test months with districts that "
            "move together; 2025 provisional (D98).",
        ),
        ("Status", f"{pr['status']}: {pr['reason']}."),
        (
            "Retraining",
            "Any change of target, features, unit or boundary is a new version with an untouched "
            "test period (2026 onwards).",
        ),
    ]
    return "\n".join(
        [
            "# Model card: M21 Karnataka monthly rain-anomaly forecast",
            "",
            "Fields follow the M05 card. Results come from [the evaluation report](m21.md), the "
            "release `models/registry/M21/v1.json` and the gate `models/gates/m21.json`.",
            "",
            "| Card field | This release (v1, test opened once) |",
            "|---|---|",
            *(f"| {k} | {v} |" for k, v in rows),
            "",
        ]
    )


def log_mlflow(test: dict, tracking_uri: str, hashes: dict) -> str:
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("M21")
    c = test["models"][CANDIDATE]
    with mlflow.start_run(run_name="t284-test") as run:
        mlflow.log_params({"task": "T284", "model": CANDIDATE, **hashes})
        metrics = {f"test_{k}": c[k] for k in ("mae", "rps", "rpss", "crps")}
        metrics |= {
            f"test_improvement_{k}": c["improvement_over_baseline"][k]
            for k in ("mean", "lower95", "upper95")
        }
        metrics |= {f"test_mae_{k}": v["mae"] for k, v in test["models"].items() if k != CANDIDATE}
        metrics |= {"test_interval80_coverage": test["intervals"]["coverage"]}
        mlflow.log_metrics(metrics)
        mlflow.set_tags(
            {"split": "test", "evidence": "hindcast (D39)", "status": test["promotion"]["status"]}
        )
        return run.info.run_id


def _write(gate: dict) -> None:
    GATE.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(step: str) -> None:  # pragma: no cover - needs the local dataset
    import pyarrow.parquet as pq

    from atlas.models.m05 import table_sha256
    from atlas.models.registry import git_sha, write_release

    rows = pq.read_table(DATASET)
    gate = json.loads(GATE.read_text("utf-8"))
    if table_sha256(rows) != gate["dataset_sha256"]:
        raise ValueError("dataset hash differs from the gate; rebuild with atlas.models.m21_data")
    if step == "prepare":
        _write(prepare(rows, gate))
        print(json.dumps(gate["test_protocol"]["intervals"], indent=2))
        return
    if step == "render":  # rewrite the report and card from the gate; the test is not reopened
        if not gate["test_opened"] or "test" not in gate:
            raise ValueError("nothing to render before the test is opened")
        reports = ROOT / "reports/models"
        (reports / "m21.md").write_text(render(gate), encoding="utf-8", newline="\n")
        (reports / "m21-card.md").write_text(render_card(gate), encoding="utf-8", newline="\n")
        return
    if step != "open":
        raise ValueError("step is prepare, open or render")
    gate = open_test(gate, git_sha(ROOT))
    _write(gate)  # opened before any test row is predicted
    test = evaluate(rows, gate, TEST)
    hashes = {k: gate[k] for k in ("dataset_sha256", "split_sha256")} | {
        "git_sha": gate["test_git_sha"]
    }
    uri = f"sqlite:///{(ROOT / 'data/models/mlflow.db').as_posix()}"
    gate["test"] = test | {"mlflow_run_id": log_mlflow(test, uri, hashes)}
    _write(gate)
    reports = ROOT / "reports/models"
    (reports / "m21.md").write_text(render(gate), encoding="utf-8", newline="\n")
    (reports / "m21-card.md").write_text(render_card(gate), encoding="utf-8", newline="\n")
    write_release(release(gate), ROOT / "models/registry")
    print(json.dumps({k: v["mae"] for k, v in test["models"].items()}, indent=2))
    print(json.dumps(test["promotion"] | {"intervals": test["intervals"]}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
