"""T108 acceptance: the price helpers report exact denominators and never a 0% or filled value for
zero rows, the unit audit equals the frozen S22/S23 discovery records, both adapters refuse, and
the notebook re-run from a fresh process reproduces the committed outputs byte for byte, with
discovery dates and no date after them. The notebook needs no local-only data, so it runs in CI."""

import csv
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from atlas.analysis.prices import audit_rows, label_summary, load_record, measure, month_counts
from atlas.config import load_state
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s22 import S22
from atlas.ingest.s23 import S23

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/eda/03_ka_prices"
RECORDS = {s: load_record(ROOT / f"configs/sources/{s.lower()}.yaml") for s in ("S22", "S23")}


def test_zero_rows_are_not_computable_never_zero_percent():
    for m in label_summary([], "blocked"):
        assert (m["count"], m["n"], m["share"]) == (0, 0, None)
        assert m["status"] == "not computable: blocked"
    assert month_counts([]) == {"n": 0, "by_month": None}
    assert measure("x", 0, 0, "r")["share"] is None


def test_label_denominators_leave_unknown_labels_out():
    cov, spike = label_summary([True, False, None, None, True], "r")
    assert (cov["count"], cov["n"], cov["share"], cov["status"]) == (3, 5, 0.6, "computed")
    assert (spike["count"], spike["n"], spike["share"]) == (2, 3, 2 / 3)  # unknowns not counted
    only_unknown = label_summary([None, None], "r")
    assert only_unknown[0]["share"] == 0.0 and only_unknown[1]["share"] is None
    assert only_unknown[1]["status"] == "not computable: r"


def test_month_counts_sum_to_the_total():
    got = month_counts([date(2024, 6, 1), date(2024, 6, 9), date(2025, 1, 2)])
    assert got["n"] == 3 and got["by_month"][6] == 2 and got["by_month"][1] == 1
    assert sum(got["by_month"].values()) == got["n"] and len(got["by_month"]) == 12


@pytest.mark.parametrize("sid", ["S22", "S23"])
def test_audit_rows_equal_the_discovery_field_map(sid):
    rec = RECORDS[sid]
    rows = audit_rows(rec)
    assert [r["canonical"] for r in rows] == [f["canonical"] for f in rec["field_map"]]
    assert [r["unit_status"] for r in rows] == [f["unit_status"] for f in rec["field_map"]]
    ids = {
        e["id"]
        for e in json.loads(
            (ROOT / f"tests/fixtures/{sid.lower()}/manifest.json").read_text("utf-8")
        )["evidence"]
    }
    assert all(set(r["evidence"].split()) <= ids for r in rows)
    assert rec["outcome"] == "blocked"


def test_s23_modal_price_unit_stays_unverified():
    modal = next(r for r in audit_rows(RECORDS["S23"]) if r["canonical"] == "modal_inr_quintal")
    assert modal["unit_status"] == "unlabelled"


@pytest.mark.parametrize("adapter, sid", [(S22, "S22"), (S23, "S23")])
def test_blocked_adapters_raise_before_returning_rows(adapter, sid):
    ka = load_state(ROOT / "configs/states/ka.yaml")
    with pytest.raises(SourceUnavailable, match=f"{sid} is blocked"):
        adapter().parse(None, ka.source(sid))


def test_notebook_reproduces_from_a_clean_process(tmp_path):
    nb = json.loads((ROOT / "notebooks/03_ka_prices.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    names = sorted(p.name for p in OUT.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name

    summary = json.loads((OUT / "summary.json").read_text("utf-8"))
    assert summary["price_rows"] == 0
    with open(OUT / "unit_audit.csv", encoding="utf-8") as f:
        audit = list(csv.DictReader(f))
    assert len(audit) == sum(len(r["field_map"]) for r in RECORDS.values())
    for sid, rec in RECORDS.items():
        s = summary["sources"][sid]
        assert s["discovered_at"] == rec["discovered_at"]
        assert s["fields"] == sum(s["fields_by_unit_status"].values()) == len(rec["field_map"])
        assert s["fields"] == sum(r["source"] == sid for r in audit)
    assert summary["market_season"]["n"] == 0 and summary["market_season"]["by_month"] is None
    for m in summary["measures"]:
        assert (m["n"], m["share"]) == (0, None) and m["status"].startswith("not computable")
    # no future data: every ISO date in any output is on or before the latest discovery date
    latest = max(date.fromisoformat(r["discovered_at"][:10]) for r in RECORDS.values())
    for p in OUT.glob("*.[cj][ss][vo]*"):
        for d in re.findall(r"\d{4}-\d{2}-\d{2}", p.read_text("utf-8")):
            assert date.fromisoformat(d) <= latest, (p.name, d)
