"""M05 Karnataka drought outlook: baselines and bounded candidates (T102).

Rows come from atlas.features.m05.feature_rows. The fit receives train and tune rows only; any
row whose target month falls in the test window (2020-2024) makes it fail. Baselines: SPI-3
persistence (last month's SPI-3) and month climatology (train mean per district and calendar
month). Candidates: ridge (provisional) and LightGBM, which replaces ridge only if the lower 95%
paired block bootstrap bound of its improvement on the tune rows is above 0. Everything is in
SPI units on identical rows. Results are a hindcast (D39).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa

from atlas.features.base import LeakageError
from atlas.models.splits import DatasetSplit
from atlas.models.uncertainty import paired_block_bootstrap

FEATURES = ("spi1_lag1", "spi3_lag1", "spi6_lag1", "rain_lag1_mm")
TARGET = "target_spi3"
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0)
LGBM_SPACE = {  # plan section 11
    "learning_rate": (0.02, 0.05, 0.1),
    "num_leaves": (7, 15, 31),
    "max_depth": (3, 5, 8, -1),
    "min_child_samples": (20, 50, 100),
    "feature_fraction": (0.7, 1.0),
    "lambda_l2": (0.0, 1.0, 10.0),
}
SEED = 42


def rows_in(table: pa.Table, start: date, end: date) -> pa.Table:
    months = table["target_month"].to_pylist()
    return table.take([i for i, m in enumerate(months) if start <= m <= end])


def _design(table: pa.Table, mean: np.ndarray | None = None, std: np.ndarray | None = None):
    x = np.column_stack([np.asarray(table[f].to_pylist(), dtype=float) for f in FEATURES])
    month = np.asarray(table["month_of_year"].to_pylist(), dtype=float)
    x = np.column_stack([x, np.sin(2 * np.pi * month / 12), np.cos(2 * np.pi * month / 12)])
    if mean is None:
        mean, std = x.mean(axis=0), x.std(axis=0)
        std[std == 0] = 1.0
    return (x - mean) / std, mean, std


@dataclass
class Fit:
    climatology: dict[tuple[str, int], float]
    scaler: tuple[list[float], list[float]]
    ridge_alpha: float
    ridge_coef: list[float]
    ridge_intercept: float
    lgbm_params: dict | None
    lgbm_model: str | None
    choice: str
    tune_mae: dict[str, float] = field(default_factory=dict)
    tune_improvement: dict[str, float] | None = None

    def predict(self, table: pa.Table) -> dict[str, list[float]]:
        """Predictions of every model on the same rows, in SPI units."""
        import lightgbm as lgb

        x, _, _ = _design(table, np.asarray(self.scaler[0]), np.asarray(self.scaler[1]))
        keys = zip(table["place_id"].to_pylist(), table["month_of_year"].to_pylist(), strict=True)
        out = {
            "persistence": [float(v) for v in table["spi3_lag1"].to_pylist()],
            "climatology": [self.climatology.get(k, 0.0) for k in keys],
            "ridge": (x @ np.asarray(self.ridge_coef) + self.ridge_intercept).tolist(),
        }
        if self.lgbm_model:
            booster = lgb.Booster(model_str=self.lgbm_model)
            out["lightgbm"] = booster.predict(x).tolist()
        return out


def fit(train: pa.Table, tune: pa.Table, test_split: DatasetSplit, *, lgbm_trials: int = 30) -> Fit:
    """Fit baselines and candidates on train, select on tune. Test rows are refused."""
    import lightgbm as lgb
    from sklearn.linear_model import Ridge

    window = (test_split.test_start, test_split.test_end)
    for name, part in (("train", train), ("tune", tune)):
        if any(window[0] <= m <= window[1] for m in part["target_month"].to_pylist()):
            raise LeakageError(f"{name} rows include the test window {window[0]}..{window[1]}")
    if train.num_rows == 0 or tune.num_rows == 0:
        raise ValueError("train and tune rows are both required")

    y_train = np.asarray(train[TARGET].to_pylist(), dtype=float)
    y_tune = np.asarray(tune[TARGET].to_pylist(), dtype=float)
    sums: dict[tuple[str, int], list[float]] = {}
    for p, m, y in zip(
        train["place_id"].to_pylist(), train["month_of_year"].to_pylist(), y_train, strict=True
    ):
        sums.setdefault((p, m), []).append(y)
    climatology = {k: float(np.mean(v)) for k, v in sums.items()}

    x_train, mean, std = _design(train)
    x_tune, _, _ = _design(tune, mean, std)
    best = None
    for alpha in RIDGE_ALPHAS:
        model = Ridge(alpha=alpha).fit(x_train, y_train)
        mae = float(np.abs(model.predict(x_tune) - y_tune).mean())
        if best is None or mae < best[0]:
            best = (mae, alpha, model)
    ridge_mae, alpha, ridge = best

    rng = np.random.default_rng(SEED)
    lgbm_best = None
    for _ in range(lgbm_trials):
        params = {k: v[rng.integers(len(v))] for k, v in LGBM_SPACE.items()}
        params = {k: (v.item() if hasattr(v, "item") else v) for k, v in params.items()}
        params |= {
            "objective": "regression",
            "seed": SEED,
            "deterministic": True,
            "num_threads": 4,
            "verbose": -1,
        }
        booster = lgb.train(
            params,
            lgb.Dataset(x_train, y_train),
            num_boost_round=1000,
            valid_sets=[lgb.Dataset(x_tune, y_tune)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )
        mae = float(
            np.abs(booster.predict(x_tune, num_iteration=booster.best_iteration) - y_tune).mean()
        )
        if lgbm_best is None or mae < lgbm_best[0]:
            lgbm_best = (mae, params | {"num_boost_round": booster.best_iteration}, booster)

    blocks = [m.strftime("%Y-%m") for m in tune["target_month"].to_pylist()]
    ridge_err = np.abs(ridge.predict(x_tune) - y_tune)
    choice, improvement, lgbm_params, lgbm_str, tune_mae = (
        "ridge",
        None,
        None,
        None,
        {"ridge": ridge_mae},
    )
    if lgbm_best is not None:
        lgbm_mae, lgbm_params, booster = lgbm_best
        lgbm_err = np.abs(booster.predict(x_tune, num_iteration=booster.best_iteration) - y_tune)
        imp = paired_block_bootstrap(ridge_err.tolist(), lgbm_err.tolist(), blocks)
        improvement = {"mean": imp.mean, "lower95": imp.lower95, "upper95": imp.upper95}
        tune_mae["lightgbm"] = lgbm_mae
        lgbm_str = booster.model_to_string(num_iteration=booster.best_iteration)
        if imp.lower95 > 0:
            choice = "lightgbm"
    tune_mae["persistence"] = float(
        np.abs(np.asarray(tune["spi3_lag1"].to_pylist(), dtype=float) - y_tune).mean()
    )
    return Fit(
        climatology=climatology,
        scaler=(mean.tolist(), std.tolist()),
        ridge_alpha=alpha,
        ridge_coef=ridge.coef_.tolist(),
        ridge_intercept=float(ridge.intercept_),
        lgbm_params=lgbm_params,
        lgbm_model=lgbm_str,
        choice=choice,
        tune_mae=tune_mae,
        tune_improvement=improvement,
    )


def save(result: Fit, folder: Path, split_sha256: str, dataset_sha256: str) -> Path:
    """Preprocessing, weights and hashes as plain files (LightGBM in its text format, no pickle)."""
    folder.mkdir(parents=True, exist_ok=True)
    meta = {
        "model_id": "M05",
        "evidence": "hindcast (D39)",
        "split_sha256": split_sha256,
        "dataset_sha256": dataset_sha256,
        "features": list(FEATURES) + ["month_sin", "month_cos"],
        "scaler": {"mean": result.scaler[0], "std": result.scaler[1]},
        "ridge": {
            "alpha": result.ridge_alpha,
            "coef": result.ridge_coef,
            "intercept": result.ridge_intercept,
        },
        "lightgbm_params": result.lgbm_params,
        "choice": result.choice,
        "tune_mae": result.tune_mae,
        "tune_improvement_lightgbm_vs_ridge": result.tune_improvement,
    }
    (folder / "m05_fit.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    if result.lgbm_model:
        (folder / "m05_lightgbm.txt").write_text(result.lgbm_model, encoding="utf-8", newline="\n")
    return folder / "m05_fit.json"


def no_model_manifest(folder: Path, gate_result: dict) -> Path:
    """A blocked gate leaves only this manifest: no weights, no predictions."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "m05_no_model.json"
    path.write_text(
        json.dumps({"model_id": "M05", "status": "blocked", **gate_result}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def table_sha256(table: pa.Table) -> str:
    rows = sorted(json.dumps(r, sort_keys=True, default=str) for r in table.to_pylist())
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def log_mlflow(result: Fit, tracking_uri: str, split_sha256: str, dataset_sha256: str) -> str:
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("M05")
    with mlflow.start_run(run_name="t102-fit") as run:
        mlflow.log_params(
            {
                "split_sha256": split_sha256,
                "dataset_sha256": dataset_sha256,
                "choice": result.choice,
                "ridge_alpha": result.ridge_alpha,
            }
        )
        mlflow.log_metrics({f"tune_mae_{k}": v for k, v in result.tune_mae.items()})
        return run.info.run_id
