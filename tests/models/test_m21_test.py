"""T284: the M21 locked test was opened once, after the refit, interval and promotion rules were
written into the gate; a second opening is refused; the promotion outcome follows the rule; the
report, card, release and config agree with the gate. The real dataset (local only) must
reproduce the candidate's test MAE and interval coverage."""

import json
import re
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from atlas.features.base import LeakageError
from atlas.models import m21_data
from atlas.models import m21_test as t
from atlas.models.registry import Release

ROOT = Path(__file__).resolve().parents[2]
GATE = json.loads((ROOT / "models/gates/m21.json").read_text("utf-8"))
TEST = GATE["test"]
REPORT = (ROOT / "reports/models/m21.md").read_text("utf-8")
CARD = (ROOT / "reports/models/m21-card.md").read_text("utf-8")
RELEASE = json.loads((ROOT / "models/registry/M21/v1.json").read_text("utf-8"))


def test_the_gate_records_one_opening():
    assert GATE["test_opened"] is True and re.fullmatch(r"[0-9a-f]{40}", GATE["test_git_sha"])
    assert TEST["period"] == ["2020-01-01", "2025-12-31"]
    assert TEST["rows"] == GATE["rows"]["test"] and TEST["months"] == 72
    assert TEST["candidate"] == GATE["candidate"]["model"] == "lightgbm"


def test_rules_and_interval_method_were_written_before_opening():
    tp = GATE["test_protocol"]
    assert datetime.fromisoformat(tp["written_at"]) < datetime.fromisoformat(GATE["test_opened_at"])
    assert (tp["refit_rule"], tp["interval_rule"], tp["promotion_rule"]) == (
        t.REFIT_RULE,
        t.INTERVAL_RULE,
        t.PROMOTION_RULE,
    )
    iv = tp["intervals"]
    assert iv["method"] == t.choose(iv["selection"]) == TEST["intervals"]["method"]
    assert {s["method"] for s in iv["selection"]} == set(t.METHODS) and iv["coverage"] == 0.8


def test_a_second_opening_is_refused():
    with pytest.raises(ValueError, match="opened once already"):
        t.open_test(GATE, "0" * 40)
    with pytest.raises(ValueError, match="already open"):
        t.prepare(None, GATE)
    closed = GATE | {"test_opened": False}
    with pytest.raises(LeakageError, match="before any test row"):
        t.evaluate(None, closed, t.TEST)
    unwritten = {k: v for k, v in closed.items() if k != "test_protocol"}
    with pytest.raises(ValueError, match="before opening"):
        t.open_test(unwritten, "0" * 40)
    opened = t.open_test(closed, "a" * 40)
    assert opened["test_opened"] is True and closed["test_opened"] is False


def test_promotion_is_mechanical():
    m = TEST["models"]
    assert TEST["strongest_baseline"] == min(m21_data.BASELINES, key=lambda k: m[k]["mae"])
    low = m["lightgbm"]["improvement_over_baseline"]["lower95"]
    status = "candidate_eligible" if low > 0 else "research_only"
    assert TEST["promotion"]["lower95"] == low and TEST["promotion"]["status"] == status
    assert RELEASE["status"] == status and RELEASE["approval"] == "pending"
    config = yaml.safe_load((ROOT / "configs/models/m21.yaml").read_text("utf-8"))
    assert config["status"] == status and config["enabled"] is False


def test_interval_gate():
    iv = TEST["intervals"]
    assert iv["shown"] == (0.75 <= iv["coverage"] <= 0.85)
    for s in TEST["by_season"].values():
        assert 0 <= s["interval_coverage"] <= 1 and s["interval_width"] > 0
    assert sum(s["rows"] for s in TEST["by_season"].values()) == TEST["rows"]


def test_report_card_and_release_equal_the_gate():
    for k, v in TEST["models"].items():
        row = re.search(rf"\| {re.escape(t.LABELS[k])} \| [^|]+ \| ([0-9.]+) \|", REPORT)
        assert row and float(row.group(1)) == round(v["mae"], 3), k
    iv, pr = TEST["intervals"], TEST["promotion"]
    for text in (REPORT, CARD):
        assert (
            f"{iv['coverage']:.3f}" in text and pr["status"] in text and "hindcast" in text.lower()
        )
    assert f"{pr['lower95']:+.3f}" in REPORT and "opened once" in REPORT
    release = Release.model_validate(RELEASE)
    c = TEST["models"]["lightgbm"]
    assert release.candidate_scores["mae"] == c["mae"]
    assert release.improvement["lower95"] == c["improvement_over_baseline"]["lower95"]
    assert release.baseline == TEST["strongest_baseline"]
    assert release.git_sha == GATE["test_git_sha"]


def test_real_dataset_reproduces_the_candidate():
    pytest.importorskip("lightgbm")
    pq = pytest.importorskip("pyarrow.parquet")
    import numpy as np

    from atlas.models import spatial_ml as sm
    from atlas.models.m05 import rows_in, table_sha256
    from atlas.models.uncertainty import coverage

    if not t.DATASET.exists():
        pytest.skip("the M21 dataset is local only")
    rows = pq.read_table(t.DATASET)
    assert table_sha256(rows) == GATE["dataset_sha256"]
    params = GATE["tune"]["models"]["lightgbm"]["params"]
    model = sm._booster(params, rows_in(rows, *t.REFIT), m21_data.FEATURES)
    test = rows_in(rows, *t.TEST)
    y, mu = np.asarray(test["target_anom"].to_pylist()), model(test)
    assert np.isclose(np.abs(mu - y).mean(), TEST["models"]["lightgbm"]["mae"])
    iv = GATE["test_protocol"]["intervals"]
    lo, hi = t.interval(mu, t._moy(test), iv["offsets"], iv["method"])
    assert np.isclose(coverage(y, lo, hi), TEST["intervals"]["coverage"])
