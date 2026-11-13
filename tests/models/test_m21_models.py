"""T281: M21 SARIMA, ridge and LightGBM fit on train and are scored on tune only. Synthetic rows
(CI) check that tune and later targets cannot reach a fit, that rows after tune are refused and
that seeds make runs repeatable; the committed gate and report must agree. The real dataset
(local only) must reproduce the gate's tune numbers."""

import json
import re
from datetime import date
from functools import cache
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

pytest.importorskip("lightgbm")
pytest.importorskip("sklearn")
pytest.importorskip("statsmodels")

from atlas.features.base import LeakageError  # noqa: E402
from atlas.models import m21_data  # noqa: E402
from atlas.models import m21_fit as fit  # noqa: E402
from atlas.models.m05 import rows_in  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GATE = json.loads((ROOT / "models/gates/m21.json").read_text("utf-8"))
REPORT = (ROOT / "reports/models/m21-tune.md").read_text("utf-8")


def synthetic(end_year: int = 2017, shift: float = 0.0) -> pa.Table:
    """Three districts of AR(1) anomalies 1981 to end_year; `shift` moves targets after train."""
    rng = np.random.default_rng(7)
    months = [date(y, m, 1) for y in range(1981, end_year + 1) for m in range(1, 13)]
    z = {}
    for p in ("a", "b", "c"):
        e = rng.standard_normal(len(months))
        for i in range(1, len(e)):
            e[i] += 0.3 * e[i - 1]
        z[p] = e
    rows = []
    for p, series in z.items():
        for i, t in enumerate(months):
            if t < m21_data.FIRST_TARGET:
                continue
            y = series[i] + (shift if t > fit.TRAIN[1] else 0.0)
            rows.append(
                {
                    "place_id": p,
                    "target_month": t,
                    "month_of_year": t.month,
                    **{f"anom_lag{k}": float(series[i - k]) for k in m21_data.LAGS},
                    "spi1_lag1": float(series[i - 1]),
                    "spi3_lag1": float(series[i - 3 : i].mean()),
                    "spi6_lag1": float(series[i - 6 : i].mean()),
                    "state_anom_lag1": float(np.mean([z[q][i - 1] for q in z])),
                    "target_anom": float(y),
                    "target_tercile": -1 if y < -0.43 else (1 if y > 0.43 else 0),
                }
            )
    return pa.Table.from_pylist(rows)


@cache
def synthetic_run(shift: float = 0.0) -> dict:
    return fit.run(synthetic(shift=shift), trials=3)


def test_fitters_refuse_rows_after_train():
    rows = synthetic()
    for fitter in (fit.fit_ridge, fit.fit_sarima, fit.fit_lightgbm, fit.tercile_bounds):
        with pytest.raises(LeakageError, match="train end"):
            fitter(rows)


def test_rows_after_tune_are_refused():
    with pytest.raises(LeakageError, match="not scored"):
        fit.run(synthetic(end_year=2018), trials=1)
    with pytest.raises(LeakageError, match="not scored"):
        fit.scorable(rows_in(synthetic(end_year=2020), date(2020, 1, 1), date(2020, 12, 31)))
    with pytest.raises(LeakageError, match="not scored"):  # the T280 guard still refuses
        m21_data.score_baselines(
            pa.table(
                {
                    "target_month": [date(2018, 1, 1)],
                    "target_anom": [0.0],
                    "anom_lag1": [0.0],
                    "anom_lag12": [0.0],
                }
            )
        )


def test_tune_targets_cannot_change_any_fit():
    a, b = synthetic_run()["fits"], synthetic_run(5.0)["fits"]
    assert a["ridge"]["coef"] == b["ridge"]["coef"]
    assert a["ridge"]["params"] == b["ridge"]["params"]
    assert a["lightgbm"]["model"] == b["lightgbm"]["model"]
    assert a["sarima"]["coef"] == b["sarima"]["coef"]
    # the shift does reach the tune scores, so the check above is not vacuous
    assert synthetic_run()["tune"]["models"]["ridge"]["mae"] != pytest.approx(
        synthetic_run(5.0)["tune"]["models"]["ridge"]["mae"]
    )


def test_seeds_make_runs_repeatable():
    def numbers(t: dict) -> dict:
        return {k: {m: v for m, v in d.items() if m != "train_seconds"} for k, d in t.items()}

    again = fit.run(synthetic(), trials=3)
    assert numbers(again["tune"]["models"]) == numbers(synthetic_run()["tune"]["models"])
    assert again["fits"]["lightgbm"]["model"] == synthetic_run()["fits"]["lightgbm"]["model"]


def test_report_and_gate_agree():
    tune = GATE["tune"]
    assert GATE["candidate"] is None and GATE["test_opened"] is False
    assert tune["task"] == "T281" and tune["rows"] == GATE["rows"]["tune"] == 897
    assert tune["dataset_sha256"] == GATE["dataset_sha256"]
    assert tune["split_sha256"] == GATE["split_sha256"]
    assert re.fullmatch(r"[0-9a-f]{40}", tune["git_sha"])
    assert set(tune["mlflow_run_ids"]) == set(fit.MODELS)
    for key, label in fit.LABELS.items():
        row = re.search(rf"\| {re.escape(label)} \| ([0-9.]+) \| ([^|]+) \|", REPORT)
        v = tune["models"][key]
        assert row and float(row.group(1)) == round(v["mae"], 3), key
        if "improvement_over_climatology" in v:
            assert row.group(2).strip() == fit._ci(v["improvement_over_climatology"]), key
    assert tune["models"]["climatology"]["mae"] == pytest.approx(
        GATE["baselines"]["tune"]["mae"]["climatology"]
    )
    beat = [
        k
        for k, v in tune["models"].items()
        if v.get("improvement_over_climatology", {}).get("lower95", -1) > 0
    ]
    assert sorted(beat) == tune["beat_climatology_mae"]
    if not beat:
        assert "nothing beats climatology on tune" in REPORT
    assert "no candidate is named" in REPORT


def test_real_dataset_reproduces_the_gate():
    pq = pytest.importorskip("pyarrow.parquet")
    path = ROOT / "data/models/m21/m21_dataset.parquet"
    if not path.exists():
        pytest.skip("the M21 dataset is local only")
    rows = pq.read_table(path)
    out = fit.run(rows_in(rows, fit.TRAIN[0], fit.TUNE[1]))["tune"]
    for key, v in GATE["tune"]["models"].items():
        assert out["models"][key]["mae"] == pytest.approx(v["mae"], abs=1e-9), key
        assert out["models"][key].get("params") == v.get("params"), key
