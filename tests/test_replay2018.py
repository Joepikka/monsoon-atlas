"""T142 acceptance: reconstructed records cannot appear in the as-known replay view, every
event-study chart carries a CI and source/vintage labels, the event-study checks behave on
hand-checkable inputs, and the three notebooks re-run byte for byte from a fresh process (skipped
when the local-only raw files are absent). The web contract runs through vitest."""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("scipy")  # the ml lock is not installed in CI (D35)

from atlas.analysis import event_study as es  # noqa: E402
from atlas.analysis.replay import LABEL, as_known, mode, validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EDA = ROOT / "reports/eda"
RAW = ROOT / "data/raw"
REPLAY_PATH = EDA / "05_kl_flood2018/replay2018.json"
# S08 area-averaged rain in mm: untracked since the H11 answer (D166), so absent in CI.
S08_LOCAL = [
    REPLAY_PATH,
    EDA / "05_kl_flood2018/monthly_2018.csv",
    EDA / "07_climate/s08_kerala_annual.csv",
]
needs_replay = pytest.mark.skipif(
    not REPLAY_PATH.exists(), reason="replay2018.json holds S08 rain and is local only (D166)"
)
REPLAY = json.loads(REPLAY_PATH.read_text("utf-8")) if REPLAY_PATH.exists() else None
SUMMARIES = {n: json.loads((EDA / n / "summary.json").read_text("utf-8")) for n in (
    "05_kl_flood2018", "06_rain_price", "07_climate")}  # fmt: skip
END = date(2018, 9, 30)


def test_mode_needs_a_publication_date_inside_the_window():
    assert mode(date(2018, 8, 7), END) == "as_known"
    assert mode(date(2019, 8, 1), END) == mode(None, END) == "reconstructed"


@needs_replay
def test_reconstructed_records_never_appear_in_as_known_mode():
    records = REPLAY["records"]
    for cursor in (date(2018, 6, 1), date(2018, 8, 7), date(2018, 8, 20), END, date(2030, 1, 1)):
        shown = as_known(records, cursor)
        assert all(r["mode"] == "as_known" for r in shown)
        assert all(date.fromisoformat(r["known_from"]) <= cursor for r in shown)
    assert as_known(records, date(2018, 8, 6)) == []  # nothing was issued before 7 Aug 2018
    assert not any(r["source_id"] == "S08" for r in as_known(records, END))
    counts = {m: sum(r["mode"] == m for r in records) for m in ("as_known", "reconstructed")}
    assert (
        counts
        == SUMMARIES["05_kl_flood2018"]["records_by_mode"]
        == {
            "as_known": 35,
            "reconstructed": 122,
        }
    )


@needs_replay
def test_exported_replay_has_labels_and_no_forecast_vintage():
    validate(REPLAY)
    assert REPLAY["label"] == LABEL and REPLAY["forecast_vintages"] == []
    bad = REPLAY | {"records": [REPLAY["records"][0] | {"mode": "as_known"}]}
    with pytest.raises(ValueError, match="mode"):
        validate(bad)
    with pytest.raises(ValueError, match="forecast vintage"):
        validate(REPLAY | {"forecast_vintages": [{"issued": "2018-08-01"}]})


def test_every_chart_has_source_and_vintage_and_event_charts_have_a_ci():
    charts = [c for s in SUMMARIES.values() for c in s["charts"]]
    assert charts and all(c["source"] and c["vintage"] for c in charts)
    assert all(c["ci"] for c in charts if c["kind"] == "event")
    assert all(c["ci"] is None for c in charts if c["kind"] == "projection")  # spread is not CI
    for name, s in SUMMARIES.items():
        assert {c["file"] for c in s["charts"]} == {p.name for p in (EDA / name).glob("*.png")}


def test_price_event_study_is_not_computable_and_association_only():
    s = SUMMARIES["06_rain_price"]
    assert s["n_price_rows"] == 0 and s["estimate"] == "not computable" and s["charts"] == []
    assert s["identification"]["label"] == es.ASSOCIATION


def test_cluster_robust_se_matches_a_hand_calculation():
    # intercept only, y = 1, 3, 5, 7, clusters a a b b: beta 4, cluster scores -4 and 4,
    # CR1 factor 2/1 * 3/3 = 2, so var = 2 * (1/4) * 32 * (1/4) = 4 and se = 2
    beta, cov = es.ols_cluster([1, 3, 5, 7], np.ones((4, 1)), ["a", "a", "b", "b"])
    assert beta[0] == pytest.approx(4) and cov[0, 0] == pytest.approx(4)
    ci = es.ci95(beta, cov, 2)[0]
    assert ci == pytest.approx([4 - 12.7062 * 2, 4 + 12.7062 * 2], abs=1e-3)  # t(1) = 12.706
    with pytest.raises(ValueError):
        es.ols_cluster([1, 2], np.ones((2, 1)), ["a", "a"])


def test_event_design_recovers_a_known_effect_and_flat_leads():
    units, periods, events, y = [], [], [], []
    for u, e in (("t1", 3), ("t2", 4), ("c1", None), ("c2", None)):
        for p in range(8):
            effect = 5.0 if e is not None and p - e in (0, 1) else 0.0
            units.append(u)
            periods.append(p)
            events.append(e)
            y.append(10 + p + (u == "t2") + effect)  # unit and period effects, no noise
    X, names, keep = es.event_design(units, periods, events, leads=2, lags=1)
    beta, _ = es.ols_cluster(np.array(y)[keep], X, np.array(units)[keep])
    coef = dict(zip(names, beta, strict=True))
    assert coef["event_time=0"] == pytest.approx(5) and coef["event_time=1"] == pytest.approx(5)
    assert coef["event_time=-2"] == pytest.approx(0, abs=1e-9)
    assert "event_time=-1" not in coef and keep.sum() < len(y)  # out-of-window rows dropped


def test_failed_pretrend_or_placebo_means_association_only():
    ok = [(-1.0, 1.0), (-0.5, 0.2)]
    assert es.verdict(ok, (-0.3, 0.4))["label"] == es.CAUSAL
    assert es.verdict([(0.1, 1.0)], (-0.3, 0.4))["label"] == es.ASSOCIATION  # pre-trend
    assert es.verdict(ok, (0.2, 0.9))["label"] == es.ASSOCIATION  # placebo
    assert es.verdict([], None)["label"] == es.ASSOCIATION  # no data


def test_coef_chart_refuses_missing_ci_or_labels(tmp_path):
    ci = [[-1.0, 1.0], [0.5, 2.0]]
    rec = es.coef_chart(tmp_path / "c.png", [-2, 0], [0.0, 1.2], ci, source="S", vintage="V",
                        label="association only")  # fmt: skip
    assert rec["ci"] and (tmp_path / "c.png").exists()
    with pytest.raises(ValueError, match="vintage"):
        es.coef_chart(tmp_path / "d.png", [0], [1.0], [[0, 2]], source="S", vintage="", label="x")
    with pytest.raises(ValueError, match="CI"):
        es.coef_chart(tmp_path / "e.png", [0], [1.0], [[np.nan, 2]], source="S", vintage="V",
                      label="x")  # fmt: skip


def _local(*sources):
    return all((RAW / s).exists() for s in sources)


@pytest.mark.parametrize(
    ("name", "sources"),
    [
        ("05_kl_flood2018", ("S08", "S32", "S36")),
        ("06_rain_price", ()),
        ("07_climate", ("S06", "S08")),
    ],
)
def test_notebook_reproduces_from_a_clean_process(tmp_path, name, sources):
    if not _local(*sources):
        pytest.skip("raw files are local only")
    if not all(p.exists() for p in S08_LOCAL if p.parent.name == name):
        pytest.skip("S08 outputs are untracked (D166) and absent here")
    nb = json.loads((ROOT / f"notebooks/{name}.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    out = EDA / name
    names = sorted(p.name for p in out.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for n in names:
        assert (tmp_path / n).read_bytes() == (out / n).read_bytes(), n


def test_web_replay_contract(web_check):
    web_check("run", "test", "--", "src/components/Replay.test.ts")
