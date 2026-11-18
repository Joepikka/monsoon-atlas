"""M21 networks on train, scored on tune only (T283, plan item 8).

Two challengers to the T281 classical models, in plain torch (lazy import; no torch-geometric):

- MLP on the same tabular features as ridge (NaN lags as 0, month as sin and cos), scaled on the
  rows it is fitted on.
- GCN-GRU: per month, node features of the 30 districts (anomaly, observed flag, SPI-1/3/6,
  month sin and cos), two graph-convolution layers H' = relu(A H W) with A the row-normalised queen
  adjacency plus self loops, a GRU over the past 12 months shared by every district, and a linear
  head for the next-month anomaly per district. Ablation: the same network with A = identity.

Training mirrors LightGBM in m21_fit: fit on inner train (targets to 2011-11, 31-day purge), early
stopping on the inner validation slice of train (2012-01 to 2014-11), then refit on all train
rows for the early-stopped number of epochs. Dropout, weight decay, sizes and learning rate are
fixed in advance (no search). Five seeds per network; tune (2015-2017) is scored once per seed;
calibrate and the locked test are refused (m21_fit guards). Probabilistic scores use the inner
validation residuals of the early-stopped model, as LightGBM does.

Run from the repository root: .venv/Scripts/python -m atlas.models.nn_graph
"""

from __future__ import annotations

import copy
import csv
import json
import time
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa

from atlas.models import m21_data
from atlas.models import m21_fit as fit
from atlas.models.m05 import rows_in

ROOT = Path(__file__).resolve().parents[3]
NEIGHBOURS = ROOT / "reports/eda/10_spatial_statistics/district_neighbours.csv"
TRAIN, TUNE, INNER_VALID = fit.TRAIN, fit.TUNE, fit.INNER_VALID
INNER_END = date(INNER_VALID[0].year - 1, 11, 30)  # 31-day purge before the inner validation
SEEDS = (0, 1, 2, 3, 4)
WINDOW = 12
NODE_FEATURES = ("anom", "observed", "spi1", "spi3", "spi6", "month_sin", "month_cos")
GCN_HIDDEN, GRU_HIDDEN, MLP_HIDDEN = 16, 32, 32
DROPOUT, WEIGHT_DECAY, LR = 0.1, 1e-4, 3e-3
MAX_EPOCHS, PATIENCE = 150, 15
BATCH = {"mlp": 256, "gcn": 16}  # rows for the MLP, months (x 30 districts) for the GCN-GRU
NETWORKS = ("mlp", "gcn_gru", "gcn_gru_identity")
ELIGIBLE = ("sarima", "ridge", "lightgbm", "mlp", "gcn_gru")
MAX_SEED_SD = 0.01
CANDIDATE_RULE = (
    "Fixed before the networks were scored on tune. Eligible: SARIMA, ridge, LightGBM, MLP and "
    "GCN-GRU (the identity-matrix GCN-GRU is an ablation, not eligible). The default candidate is "
    "the classical model with the lowest tune MAE. A network replaces it only if the sd of its "
    f"tune MAE over the five seeds is at most {MAX_SEED_SD} and the lower 95% bound of its MAE "
    "improvement over that classical model (seed-mean errors, paired block bootstrap by month) is "
    "above 0; among such networks the lowest mean tune MAE wins. If the candidate's lower 95% "
    "bound of MAE improvement over climatology is not above 0, it is still named for the single "
    "test opening in T284 and is expected to be research-only."
)


# --- data ----------------------------------------------------------------------------------------


def adjacency(places: list[str], path: Path = NEIGHBOURS) -> np.ndarray:
    """Queen adjacency plus self loops in `places` order, each row divided by its sum."""
    with open(path, encoding="utf-8", newline="") as f:
        recs = list(csv.DictReader(f))
    by_name = {r["name"]: r["place_id"] for r in recs}
    idx = {p: i for i, p in enumerate(places)}
    if set(idx) != set(by_name.values()):
        raise ValueError("neighbour file and dataset districts differ")
    a = np.eye(len(places))
    for r in recs:
        for name in filter(None, r["neighbour_names"].split("; ")):
            a[idx[r["place_id"]], idx[by_name[name]]] = 1.0
    return a / a.sum(axis=1, keepdims=True)


def _index(m: date) -> int:
    return (m.year - 1981) * 12 + m.month - 1


def panel(rows: pa.Table, places: list[str]) -> np.ndarray:
    """Node features per month from 1981-01: [months, districts, NODE_FEATURES]. Anomaly of month
    m from the rows' targets and lags; SPI of m from the spi*_lag1 of the row for m+1. A dry or
    unknown value is 0 with observed = 0."""
    months = _index(max(fit._months(rows))) + 1
    anom = np.full((months, len(places)), np.nan)
    spi = np.zeros((months, len(places), 3))
    idx = {p: i for i, p in enumerate(places)}
    for r in rows.to_pylist():
        i, j = _index(r["target_month"]), idx[r["place_id"]]
        anom[i, j] = r["target_anom"]
        for k in m21_data.LAGS:
            if r[f"anom_lag{k}"] is not None and i - k >= 0:
                anom[i - k, j] = r[f"anom_lag{k}"]
        spi[i - 1, j] = [r["spi1_lag1"], r["spi3_lag1"], r["spi6_lag1"]]
    angle = 2 * np.pi * (np.arange(months) % 12 + 1) / 12
    season = np.broadcast_to(
        np.stack([np.sin(angle), np.cos(angle)], axis=1)[:, None], (months, len(places), 2)
    )
    observed = np.isfinite(anom)
    return np.concatenate(
        [np.nan_to_num(anom)[..., None], observed[..., None], spi, season], axis=2
    ).astype(np.float32)


def _windows(pan: np.ndarray, months: list[date]) -> np.ndarray:
    """Inputs for target months: months t-12 .. t-1 only, [targets, WINDOW, districts, F]."""
    i = np.array([_index(m) for m in months])
    return pan[i[:, None] + np.arange(-WINDOW, 0)]


def _targets(rows: pa.Table, places: list[str]) -> tuple[list[date], np.ndarray]:
    months = sorted(set(fit._months(rows)))
    at = {m: i for i, m in enumerate(months)}
    idx = {p: i for i, p in enumerate(places)}
    y = np.full((len(months), len(places)), np.nan, dtype=np.float32)
    for p, m, z in zip(rows["place_id"].to_pylist(), fit._months(rows), fit._y(rows), strict=True):
        y[at[m], idx[p]] = z
    return months, y


# --- networks ------------------------------------------------------------------------------------


def _torch():
    import torch

    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    return torch


def gcn_gru(matrix: np.ndarray, n_features: int = len(NODE_FEATURES)):
    """Two graph convolutions (relu(A H W)) per month, a GRU over the months, a linear head."""
    torch = _torch()
    nn = torch.nn

    class GCNGRU(nn.Module):
        def __init__(self):
            super().__init__()
            self.register_buffer("adj", torch.as_tensor(matrix, dtype=torch.float32))
            self.gc1 = nn.Linear(n_features, GCN_HIDDEN)
            self.gc2 = nn.Linear(GCN_HIDDEN, GCN_HIDDEN)
            self.gru = nn.GRU(GCN_HIDDEN, GRU_HIDDEN, batch_first=True)
            self.drop = nn.Dropout(DROPOUT)
            self.head = nn.Linear(GRU_HIDDEN, 1)

        def forward(self, x):  # [batch, months, districts, features] -> [batch, districts]
            h = torch.relu(self.adj @ self.gc1(x))
            h = torch.relu(self.adj @ self.gc2(h))
            b, t, n, f = h.shape
            out, _ = self.gru(h.permute(0, 2, 1, 3).reshape(b * n, t, f))
            return self.head(self.drop(out[:, -1])).view(b, n)

    return GCNGRU()


def mlp(n_in: int):
    nn = _torch().nn
    return nn.Sequential(
        nn.Linear(n_in, MLP_HIDDEN),
        nn.ReLU(),
        nn.Dropout(DROPOUT),
        nn.Linear(MLP_HIDDEN, MLP_HIDDEN),
        nn.ReLU(),
        nn.Dropout(DROPOUT),
        nn.Linear(MLP_HIDDEN, 1),
        nn.Flatten(0),
    )


def _l1(pred, y):
    """Mean absolute error over the known targets (dry district-months are NaN and skipped)."""
    known = ~y.isnan()
    return (pred[known] - y[known]).abs().mean()


def _predict(model, x: np.ndarray) -> np.ndarray:
    torch = _torch()
    model.eval()
    with torch.no_grad():
        return model(torch.as_tensor(x)).numpy().astype(float)


def _train(make, x, y, seed: int, batch: int, valid=None, epochs: int | None = None) -> dict:
    """AdamW on L1. With `valid`, stop when its MAE has not improved for PATIENCE epochs and
    return the best state; otherwise train exactly `epochs` epochs."""
    torch = _torch()
    torch.manual_seed(seed)
    model = make()
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    gen = torch.Generator().manual_seed(seed)
    xt, yt = torch.as_tensor(x), torch.as_tensor(y)
    curve, best = [], (np.inf, 0, None)
    for epoch in range(1, (epochs or MAX_EPOCHS) + 1):
        model.train()
        for i in torch.randperm(len(xt), generator=gen).split(batch):
            opt.zero_grad()
            _l1(model(xt[i]), yt[i]).backward()
            opt.step()
        if valid is not None:
            p, v = _predict(model, valid[0]), valid[1]
            curve.append(float(np.nanmean(np.abs(p - v))))
            if curve[-1] < best[0]:
                best = (curve[-1], epoch, copy.deepcopy(model.state_dict()))
            elif epoch - best[1] >= PATIENCE:
                break
    if valid is not None:
        model.load_state_dict(best[2])
    return {"model": model, "curve": curve, "best_epoch": best[1], "valid_mae": best[0]}


def _early_stopped(make, inner, valid, full, seed: int, batch: int) -> dict:
    """Early stopping on the inner validation slice, then a refit on all train rows."""
    stop = _train(make, *inner, seed, batch, valid=valid)
    resid = valid[1] - _predict(stop["model"], valid[0])  # y - forecast, out of sample
    final = _train(make, *full, seed, batch, epochs=stop["best_epoch"])
    return {
        "model": final["model"],
        "residuals": resid[np.isfinite(resid)].ravel(),
        "curve": stop["curve"],
        "params": {
            "seed": seed,
            "best_epoch": stop["best_epoch"],
            "inner_valid_mae": stop["valid_mae"],
            "parameters": sum(p.numel() for p in final["model"].parameters()),
        },
    }


def _scaler(x: np.ndarray):
    mean, std = x.mean(axis=0), x.std(axis=0)
    std[std == 0] = 1.0
    return lambda new: ((new - mean) / std).astype(np.float32)


def fit_mlp(train: pa.Table, seed: int) -> dict:
    train = fit.train_only(train)
    parts = [rows_in(train, TRAIN[0], INNER_END), rows_in(train, *INNER_VALID), train]
    inner_scale, full_scale = _scaler(fit._ridge_x(parts[0])), _scaler(fit._ridge_x(train))
    xs = [inner_scale(fit._ridge_x(parts[0])), inner_scale(fit._ridge_x(parts[1]))]
    xs.append(full_scale(fit._ridge_x(train)))
    data = [(x, fit._y(p).astype(np.float32)) for x, p in zip(xs, parts, strict=True)]
    out = _early_stopped(lambda: mlp(xs[0].shape[1]), *data, seed, BATCH["mlp"])
    model = out["model"]
    return out | {
        "predict": lambda rows, history=None: _predict(model, full_scale(fit._ridge_x(rows)))
    }


def fit_gcn_gru(train: pa.Table, seed: int, matrix: np.ndarray) -> dict:
    train = fit.train_only(train)
    places = sorted(set(train["place_id"].to_pylist()))
    if matrix.shape != (len(places), len(places)):
        raise ValueError("matrix does not match the districts")
    pan = panel(train, places)
    data = []
    for part in (rows_in(train, TRAIN[0], INNER_END), rows_in(train, *INNER_VALID), train):
        months, y = _targets(part, places)
        data.append((_windows(pan, months), y))
    out = _early_stopped(lambda: gcn_gru(matrix), *data, seed, BATCH["gcn"])
    model, idx = out["model"], {p: i for i, p in enumerate(places)}

    def predict(rows: pa.Table, history: pa.Table) -> np.ndarray:
        """Inputs come from `history` up to month t-1 for each target month t."""
        months = sorted(set(fit._months(rows)))
        at = {m: i for i, m in enumerate(months)}
        pred = _predict(model, _windows(panel(fit.scorable(history), places), months))
        return np.array(
            [
                pred[at[m], idx[p]]
                for p, m in zip(rows["place_id"].to_pylist(), fit._months(rows), strict=True)
            ]
        )

    return out | {"predict": predict}


# --- scoring -------------------------------------------------------------------------------------


def _scores(mu, y, err0, blocks, resid, tune, bounds, clim) -> dict:
    err = np.abs(mu - y)
    ens = fit._ens_scores(mu, resid, tune, bounds)
    return {
        "mae": float(err.mean()),
        "improvement_over_climatology": fit._interval(err0, err, blocks),
        "rps": float(ens["rps"].mean()),
        "rpss": float(1 - ens["rps"].mean() / clim["rps"].mean()),
        "rps_improvement": fit._interval(clim["rps"], ens["rps"], blocks),
        "crps": float(ens["crps"].mean()),
        "crps_improvement": fit._interval(clim["crps"], ens["crps"], blocks),
    }


def _summary(seeds: list[dict]) -> dict:
    out = {}
    for k in ("mae", "rpss", "crps"):
        v = np.array([s[k] for s in seeds])
        out |= {
            f"{k}_mean": float(v.mean()),
            f"{k}_sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0,
        }
    mae = [s["mae"] for s in seeds]
    low = [s["improvement_over_climatology"]["lower95"] for s in seeds]
    return out | {
        "mae_min": min(mae),
        "mae_max": max(mae),
        "improvement_lower95_min": min(low),
        "improvement_lower95_max": max(low),
    }


def name_candidate(classical: dict, networks: dict) -> dict:
    """CANDIDATE_RULE, on tune numbers only."""
    best = min(("sarima", "ridge", "lightgbm"), key=lambda k: classical[k]["mae"])
    winners = [
        k
        for k in ("mlp", "gcn_gru")
        if networks[k]["summary"]["mae_sd"] <= MAX_SEED_SD
        and networks[k]["improvement_over_best_classical"]["lower95"] > 0
    ]
    if winners:
        name = min(winners, key=lambda k: networks[k]["summary"]["mae_mean"])
        mae, low = networks[name]["summary"]["mae_mean"], networks[name]["seed_mean"]["lower95"]
        why = f"network beat {best} on tune (lower 95% bound above 0, seed sd <= {MAX_SEED_SD})"
    else:
        name, mae = best, classical[best]["mae"]
        low = classical[best]["improvement_over_climatology"]["lower95"]
        why = "lowest classical tune MAE; no network beat it with a lower 95% bound above 0"
    expected = "promotable if the test agrees" if low > 0 else "research-only"
    return {
        "model": name,
        "reason": f"{why}; tune MAE {mae:.3f}, lower 95% bound vs climatology {low:+.3f}, "
        f"so expected {expected}.",
        "expected": expected,
        "named_by": "T283",
    }


def run(rows: pa.Table, classical: dict, seeds=SEEDS, matrix=None, trials=fit.LGBM_TRIALS) -> dict:
    """Fit each network once per seed on train and score tune once per seed. `classical` is the
    T281 tune section (models); its best model is refitted (deterministic) for paired errors."""
    history = fit.scorable(rows)
    train, tune = rows_in(rows, *TRAIN), rows_in(rows, *TUNE)
    places = sorted(set(train["place_id"].to_pylist()))
    matrix = adjacency(places) if matrix is None else matrix
    y, blocks = fit._y(tune), [m.strftime("%Y-%m") for m in fit._months(tune)]
    bounds, clim, err0 = fit.tercile_bounds(train), fit._climatology_scores(train, tune), np.abs(y)
    best = min(("sarima", "ridge", "lightgbm"), key=lambda k: classical[k]["mae"])
    refit = {
        "sarima": fit.fit_sarima,
        "ridge": fit.fit_ridge,
        "lightgbm": lambda t: fit.fit_lightgbm(t, trials),
    }[best](train)
    err_best = np.abs(np.asarray(refit["predict"](tune, history), dtype=float) - y)
    if not np.isclose(err_best.mean(), classical[best]["mae"], atol=1e-9):
        raise ValueError(f"{best} refit does not reproduce its T281 tune MAE")
    fitters = {
        "mlp": fit_mlp,
        "gcn_gru": lambda t, s: fit_gcn_gru(t, s, matrix),
        "gcn_gru_identity": lambda t, s: fit_gcn_gru(t, s, np.eye(len(places))),
    }
    models, errors, fits = {}, {}, {}
    for name, fitter in fitters.items():
        per_seed, errs = [], []
        for seed in seeds:
            start = time.perf_counter()
            f = fitter(train, seed)
            seconds = time.perf_counter() - start
            mu = np.asarray(f["predict"](tune, history), dtype=float)
            errs.append(np.abs(mu - y))
            s = _scores(mu, y, err0, blocks, f["residuals"], tune, bounds, clim)
            per_seed.append({"seed": seed} | s | {"train_seconds": round(seconds, 1)} | f["params"])
            fits[(name, seed)] = f
        errors[name] = np.mean(errs, axis=0)
        models[name] = {
            "seeds": per_seed,
            "summary": _summary(per_seed),
            "seed_mean": fit._interval(err0, errors[name], blocks),
            "improvement_over_best_classical": fit._interval(err_best, errors[name], blocks),
        }
    out = {
        "task": "T283",
        "rows": tune.num_rows,
        "months": len(set(blocks)),
        "seeds": list(seeds),
        "best_classical": best,
        "settings": {
            "window": WINDOW,
            "node_features": list(NODE_FEATURES),
            "gcn_hidden": GCN_HIDDEN,
            "gru_hidden": GRU_HIDDEN,
            "mlp_hidden": MLP_HIDDEN,
            "dropout": DROPOUT,
            "weight_decay": WEIGHT_DECAY,
            "lr": LR,
            "max_epochs": MAX_EPOCHS,
            "patience": PATIENCE,
            "batch": BATCH,
            "loss": "L1",
        },
        "models": models,
        # graph minus identity: positive means the adjacency helps
        "graph_over_identity": fit._interval(errors["gcn_gru_identity"], errors["gcn_gru"], blocks),
    }
    return {"networks": out, "fits": fits}


# --- outputs -------------------------------------------------------------------------------------


def log_mlflow(networks: dict, fits: dict, tracking_uri: str, hashes: dict) -> dict[str, list[str]]:
    """One run per network and seed in experiment M21, with the inner-validation loss curve."""
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("M21")
    ids: dict[str, list[str]] = {}
    for name in NETWORKS:
        for s in networks["models"][name]["seeds"]:
            with mlflow.start_run(run_name=f"t283-{name}-seed{s['seed']}") as run:
                mlflow.log_params(
                    {"task": "T283", "model": name, **hashes}
                    | {
                        k: json.dumps(v) if isinstance(v, dict | list) else v
                        for k, v in networks["settings"].items()
                    }
                    | {k: s[k] for k in ("seed", "best_epoch", "parameters")}
                )
                metrics = {
                    f"tune_{k}": s[k] for k in ("mae", "rps", "rpss", "crps", "train_seconds")
                }
                for k in ("improvement_over_climatology", "rps_improvement", "crps_improvement"):
                    metrics |= {f"tune_{k}_{b}": s[k][b] for b in ("mean", "lower95", "upper95")}
                mlflow.log_metrics(metrics | {"inner_valid_mae": s["inner_valid_mae"]})
                for step, v in enumerate(fits[(name, s["seed"])]["curve"], start=1):
                    mlflow.log_metric("inner_valid_mae_curve", v, step=step)
                mlflow.set_tags({"split": "tune", "evidence": "hindcast (D39)"})
                ids.setdefault(name, []).append(run.info.run_id)
    return ids


LABELS = {
    "mlp": "MLP (tabular features)",
    "gcn_gru": "GCN-GRU (queen adjacency)",
    "gcn_gru_identity": "GCN-GRU, identity ablation",
}


def render(networks: dict, candidate: dict, rule: str) -> str:
    """The T283 section appended to reports/models/m21-tune.md, from the gate only."""
    m, st = networks["models"], networks["settings"]
    lines = [
        "# M21 networks on the tune years (T283)",
        "",
        "**Tune only. Calibrate and the locked test are not scored.** Plain torch on CPU, "
        f"{len(networks['seeds'])} seeds each (seeds {networks['seeds']}). Each seed: fit on "
        "inner train (to 2011-11), early stopping on the inner validation slice of train "
        "(2012-01 to 2014-11, patience "
        f"{st['patience']}, at most {st['max_epochs']} epochs), refit on all train rows for the "
        "early-stopped number of epochs, tune scored once. Sizes, dropout "
        f"{st['dropout']}, weight decay {st['weight_decay']} and learning rate {st['lr']} were "
        "fixed in advance; L1 loss.",
        "",
        "- MLP: the ridge features (12 anomaly lags, SPI-1/3/6, state anomaly at t-1, month sin "
        f"and cos), two hidden layers of {st['mlp_hidden']}.",
        "- GCN-GRU: per month, the 30 districts' anomaly, observed flag, SPI-1/3/6 and month sin "
        f"and cos; two graph convolutions relu(A H W) of width {st['gcn_hidden']} with A the "
        "row-normalised queen adjacency plus self loops; a GRU of width "
        f"{st['gru_hidden']} over the past {st['window']} months; a linear head per district.",
        "- Ablation: the same GCN-GRU with A = identity (no neighbour information).",
        "",
        "Mean over seeds, seed sd in brackets. MAE improvement: climatology minus model, paired "
        "block bootstrap by month on the seed-mean errors. Lower bounds per seed: lowest and "
        "highest over the seeds.",
        "",
        "| Model | Tune MAE (sd) | MAE range | MAE improvement over climatology (95% interval) "
        "| Lower bounds per seed | RPSS (sd) | CRPS (sd) | Parameters | Seconds per seed |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for k in NETWORKS:
        s, seeds = m[k]["summary"], m[k]["seeds"]
        secs = np.mean([x["train_seconds"] for x in seeds])
        lines.append(
            f"| {LABELS[k]} | {s['mae_mean']:.3f} ({s['mae_sd']:.3f}) "
            f"| {s['mae_min']:.3f}-{s['mae_max']:.3f} | {fit._ci(m[k]['seed_mean'])} "
            f"| {s['improvement_lower95_min']:+.3f} to {s['improvement_lower95_max']:+.3f} "
            f"| {s['rpss_mean']:+.3f} ({s['rpss_sd']:.3f}) | {s['crps_mean']:.3f} "
            f"({s['crps_sd']:.3f}) | {seeds[0]['parameters']} | {secs:.1f} |"
        )
    best = networks["best_classical"]
    lines += [
        "",
        "## Reading",
        "",
        f"- Against the best classical model ({fit.LABELS[best]}), MAE improvement (95% "
        "interval): "
        + "; ".join(
            f"{LABELS[k]} {fit._ci(m[k]['improvement_over_best_classical'])}"
            for k in ("mlp", "gcn_gru")
        )
        + ".",
        "- Ablation, identity minus adjacency (positive means the neighbours help): "
        f"{fit._ci(networks['graph_over_identity'])}.",
        "",
        "## Candidate",
        "",
        f"Rule (written into the gate before the networks were scored): {rule}",
        "",
        f"**Named candidate: {candidate['model']}.** {candidate['reason']}",
        "",
        "## Runs",
        "",
        f"MLflow experiment M21, {sum(len(v) for v in networks['mlflow_run_ids'].values())} runs "
        "(one per network and seed, with the inner-validation loss curve), git "
        f"{networks['git_sha'][:12]} (the commit before T283).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - needs the local dataset
    import pyarrow.parquet as pq

    from atlas.models.m05 import table_sha256
    from atlas.models.registry import git_sha

    rows = pq.read_table(ROOT / "data/models/m21/m21_dataset.parquet")
    gate_path = ROOT / "models/gates/m21.json"
    gate = json.loads(gate_path.read_text("utf-8"))
    if table_sha256(rows) != gate["dataset_sha256"]:
        raise ValueError("dataset hash differs from the gate; rebuild with atlas.models.m21_data")
    if gate.get("candidate_rule") != CANDIDATE_RULE:
        raise ValueError("write CANDIDATE_RULE into the gate before scoring the networks")
    if gate["test_opened"]:
        raise ValueError("the test is already open")
    start = time.perf_counter()
    result = run(rows_in(rows, TRAIN[0], TUNE[1]), gate["tune"]["models"])
    hashes = {
        "dataset_sha256": gate["dataset_sha256"],
        "split_sha256": gate["split_sha256"],
        "git_sha": git_sha(ROOT),
    }
    uri = f"sqlite:///{(ROOT / 'data/models/mlflow.db').as_posix()}"
    networks = result["networks"] | hashes
    networks["mlflow_run_ids"] = log_mlflow(networks, result["fits"], uri, hashes)
    networks["total_seconds"] = round(time.perf_counter() - start, 1)
    gate["tune"]["networks"] = networks
    gate["candidate"] = name_candidate(gate["tune"]["models"], networks["models"])
    gate_path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8", newline="\n")
    report = fit.render(gate["tune"]) + "\n" + render(networks, gate["candidate"], CANDIDATE_RULE)
    (ROOT / "reports/models/m21-tune.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps({k: v["summary"] for k, v in networks["models"].items()}, indent=2))
    print(json.dumps(gate["candidate"], indent=2))


if __name__ == "__main__":
    main()
