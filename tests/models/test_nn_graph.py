"""T283: M21 MLP and GCN-GRU (plain torch) fit on train and scored on tune only. Synthetic rows
check shapes, that the identity ablation differs only in its matrix, that tune and later rows
cannot reach a fit or a forecast's inputs, and that seeds make fits repeatable. The real queen
matrix must be row-normalised; the committed gate and report must agree, and the candidate must
follow the rule written into the gate."""

import csv
import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

pytest.importorskip("torch")

from test_m21_models import synthetic, synthetic_run  # noqa: E402

from atlas.features.base import LeakageError  # noqa: E402
from atlas.models import m21_fit as fit  # noqa: E402
from atlas.models import nn_graph as nn  # noqa: E402
from atlas.models.m05 import rows_in  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GATE = json.loads((ROOT / "models/gates/m21.json").read_text("utf-8"))
REPORT = (ROOT / "reports/models/m21-tune.md").read_text("utf-8")
PLACES = ["a", "b", "c"]
CHAIN = np.array([[1, 1, 0], [1, 1, 1], [0, 1, 1]]) / np.array([[2], [3], [2]])


@pytest.fixture
def short(monkeypatch):
    monkeypatch.setattr(nn, "MAX_EPOCHS", 4)
    monkeypatch.setattr(nn, "PATIENCE", 2)


def train_rows() -> pa.Table:
    return rows_in(synthetic(), *nn.TRAIN)


def bump(rows: pa.Table, month: date, delta: float) -> pa.Table:
    """Change the anomaly of `month` everywhere it appears: its target and later rows' lags."""
    out = []
    for r in rows.to_pylist():
        k = (r["target_month"].year - month.year) * 12 + r["target_month"].month - month.month
        if k == 0:
            r["target_anom"] += delta
        elif 1 <= k <= 12:
            r[f"anom_lag{k}"] += delta
        out.append(r)
    return pa.Table.from_pylist(out)


def test_shapes():
    torch = nn._torch()
    pan = nn.panel(train_rows(), PLACES)
    assert pan.shape == (nn._index(nn.TRAIN[1]) + 1, 3, len(nn.NODE_FEATURES))
    x = nn._windows(pan, [date(2000, 1, 1), date(2000, 2, 1)])
    assert x.shape == (2, nn.WINDOW, 3, len(nn.NODE_FEATURES))
    last = rows_in(train_rows(), date(1999, 12, 1), date(1999, 12, 31))
    assert x[0, -1, :, 0] == pytest.approx(last["target_anom"].to_pylist())  # ends at t-1
    assert nn.gcn_gru(CHAIN)(torch.as_tensor(x)).shape == (2, 3)
    n_in = fit._ridge_x(last).shape[1]
    assert nn.mlp(n_in)(torch.zeros(5, n_in)).shape == (5,)


def test_adjacency_is_row_normalised_queen_with_self_loops():
    with open(nn.NEIGHBOURS, encoding="utf-8", newline="") as f:
        recs = list(csv.DictReader(f))
    places = sorted(r["place_id"] for r in recs)
    a = nn.adjacency(places)
    assert a.shape == (30, 30)
    assert a.sum(axis=1) == pytest.approx(np.ones(30))
    assert (np.diag(a) > 0).all() and ((a > 0) == (a > 0).T).all()
    for i, r in enumerate(sorted(recs, key=lambda r: r["place_id"])):
        assert (a[i] > 0).sum() == int(r["neighbours"]) + 1
        assert set(a[i][a[i] > 0].round(12)) == {round(1 / (int(r["neighbours"]) + 1), 12)}
    with pytest.raises(ValueError, match="differ"):
        nn.adjacency(places[:-1])


def test_identity_ablation_differs_only_in_the_matrix():
    torch = nn._torch()
    torch.manual_seed(0)
    graph = nn.gcn_gru(CHAIN)
    torch.manual_seed(0)
    ident = nn.gcn_gru(np.eye(3))
    g, i = graph.state_dict(), ident.state_dict()
    assert g.keys() == i.keys()
    assert [k for k in g if not torch.equal(g[k], i[k])] == ["adj"]
    assert torch.equal(i["adj"], torch.eye(3))
    x = torch.randn(2, nn.WINDOW, 3, len(nn.NODE_FEATURES))
    graph.eval(), ident.eval()
    assert not torch.allclose(graph(x), ident(x))


def test_fitters_refuse_rows_after_train(short):
    rows = synthetic()
    with pytest.raises(LeakageError, match="train end"):
        nn.fit_mlp(rows, 0)
    with pytest.raises(LeakageError, match="train end"):
        nn.fit_gcn_gru(rows, 0, CHAIN)
    with pytest.raises(LeakageError, match="not scored"):
        nn.run(synthetic(end_year=2018), {}, seeds=(0,), matrix=CHAIN)


def test_forecasts_see_only_months_before_the_target(short):
    rows = rows_in(synthetic(), nn.TRAIN[0], nn.TUNE[1])
    dec = rows_in(rows, date(2017, 12, 1), date(2017, 12, 31))
    for f in (nn.fit_mlp(train_rows(), 0), nn.fit_gcn_gru(train_rows(), 0, CHAIN)):
        base = f["predict"](dec, rows)
        same = bump(rows, date(2017, 12, 1), 5.0)
        assert f["predict"](rows_in(same, date(2017, 12, 1), date(2017, 12, 31)), same) == (
            pytest.approx(base)
        )
        moved = bump(rows, date(2017, 11, 1), 5.0)  # t-1 does reach the forecast
        assert f["predict"](rows_in(moved, date(2017, 12, 1), date(2017, 12, 31)), moved) != (
            pytest.approx(base)
        )


def test_seeds_make_fits_repeatable(short):
    def state(f):
        return {k: v.tolist() for k, v in f["model"].state_dict().items()}

    for fitter in (nn.fit_mlp, lambda t, s: nn.fit_gcn_gru(t, s, CHAIN)):
        a, b, c = fitter(train_rows(), 1), fitter(train_rows(), 1), fitter(train_rows(), 2)
        assert state(a) == state(b) and a["residuals"].tolist() == b["residuals"].tolist()
        assert state(a) != state(c)


def test_run_on_synthetic_rows(short):
    classical = synthetic_run()["tune"]["models"]
    out = nn.run(rows_in(synthetic(), nn.TRAIN[0], nn.TUNE[1]), classical, (0, 1), CHAIN, 3)
    net = out["networks"]
    assert set(net["models"]) == set(nn.NETWORKS) and net["rows"] == 3 * 36
    for m in net["models"].values():
        assert [s["seed"] for s in m["seeds"]] == [0, 1]
        assert m["summary"]["mae_mean"] == pytest.approx(np.mean([s["mae"] for s in m["seeds"]]))
    assert set(net["graph_over_identity"]) == {"mean", "lower95", "upper95"}
    assert nn.name_candidate(classical, net["models"])["model"] in nn.ELIGIBLE


def test_candidate_rule():
    def cls(mae, low):
        return {"mae": mae, "improvement_over_climatology": {"lower95": low}}

    classical = {"sarima": cls(0.91, -0.02), "ridge": cls(0.92, -0.03), "lightgbm": cls(0.88, 0.01)}

    def net(mae, sd, low_vs_best):
        return {
            "summary": {"mae_mean": mae, "mae_sd": sd},
            "seed_mean": {"lower95": 0.02},
            "improvement_over_best_classical": {"lower95": low_vs_best},
        }

    pick = nn.name_candidate(
        classical, {"mlp": net(0.87, 0.005, -0.01), "gcn_gru": net(0.85, 0.02, 0.01)}
    )
    assert pick["model"] == "lightgbm" and pick["expected"] != "research-only"
    pick = nn.name_candidate(
        classical, {"mlp": net(0.87, 0.005, 0.001), "gcn_gru": net(0.85, 0.02, 0.01)}
    )
    assert pick["model"] == "mlp"
    classical["lightgbm"] = cls(0.88, -0.01)
    pick = nn.name_candidate(
        classical, {"mlp": net(0.9, 0.0, -0.1), "gcn_gru": net(0.9, 0.0, -0.1)}
    )
    assert pick["model"] == "lightgbm" and pick["expected"] == "research-only"


def test_report_and_gate_agree():
    net = GATE["tune"]["networks"]
    assert GATE["test_opened"] is False and GATE["candidate_rule"] == nn.CANDIDATE_RULE
    assert GATE["candidate"] == nn.name_candidate(GATE["tune"]["models"], net["models"])
    assert GATE["candidate"]["model"] in nn.ELIGIBLE
    assert net["task"] == "T283" and net["rows"] == GATE["rows"]["tune"] == 897
    assert net["dataset_sha256"] == GATE["dataset_sha256"]
    assert net["seeds"] == list(nn.SEEDS)
    assert re.fullmatch(r"[0-9a-f]{40}", net["git_sha"])
    assert {k: len(v) for k, v in net["mlflow_run_ids"].items()} == dict.fromkeys(nn.NETWORKS, 5)
    for key, label in nn.LABELS.items():
        m = net["models"][key]
        row = re.search(
            rf"\| {re.escape(label)} \| ([0-9.]+) \(([0-9.]+)\) \|[^|]+\| ([^|]+) \|", REPORT
        )
        assert row, key
        assert float(row.group(1)) == round(m["summary"]["mae_mean"], 3), key
        assert float(row.group(2)) == round(m["summary"]["mae_sd"], 3), key
        assert row.group(3).strip() == fit._ci(m["seed_mean"]), key
        assert [s["seed"] for s in m["seeds"]] == list(nn.SEEDS)
    assert fit._ci(net["graph_over_identity"]) in REPORT
    assert nn.CANDIDATE_RULE in REPORT
    assert f"Named candidate: {GATE['candidate']['model']}." in REPORT
    assert GATE["candidate"]["reason"] in REPORT


def test_real_dataset_reproduces_a_gate_seed():
    pq = pytest.importorskip("pyarrow.parquet")
    path = ROOT / "data/models/m21/m21_dataset.parquet"
    if not path.exists():
        pytest.skip("the M21 dataset is local only")
    rows = rows_in(pq.read_table(path), nn.TRAIN[0], nn.TUNE[1])
    train, tune = rows_in(rows, *nn.TRAIN), rows_in(rows, *nn.TUNE)
    places = sorted(set(train["place_id"].to_pylist()))
    f = nn.fit_gcn_gru(train, nn.SEEDS[0], nn.adjacency(places))
    mae = float(np.abs(f["predict"](tune, rows) - fit._y(tune)).mean())
    assert mae == pytest.approx(GATE["tune"]["networks"]["models"]["gcn_gru"]["seeds"][0]["mae"])
