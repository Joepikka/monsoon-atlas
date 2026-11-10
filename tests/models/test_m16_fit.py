"""T215: the M16 rule has nothing to fit; its flag counts on the held S08 grids are reproducible."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from atlas.features import m16 as rule
from atlas.ingest.base import SourceUnavailable
from atlas.models import m16

ROOT = Path(__file__).resolve().parents[2]
COUNTS = json.loads((ROOT / m16.COUNTS).read_text("utf-8"))


def test_fit_preserves_only_a_no_model_manifest_and_reads_no_rows(tmp_path):
    path = m16.fit(object(), object(), tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["m16_no_model.json"] == [path.name]
    record = json.loads(path.read_text("utf-8"))
    assert record["status"] == "research_only" and record["prediction_rows"] == 0
    assert record["weights"] is None and record["scores"] is None
    assert record["challengers"]["isolation_forest"].startswith("not run")
    assert record["label_gate"]["quality_claim_allowed"] is False
    assert record["rule"] == dict(rule.rule_parameters())


def test_no_flag_is_published_as_a_prediction():
    with pytest.raises(SourceUnavailable, match="M16 is research-only"):
        m16.predict(object(), object())


def test_counts_table_is_consistent_and_holds_counts_only():
    assert COUNTS["years"] == [1981, 2025] and COUNTS["rule"] == dict(rule.rule_parameters())
    assert COUNTS["flag_columns"] == ["state", "year", "season", "strength_band", "flags"]
    assert all(isinstance(r[-1], int) and r[-1] > 0 for r in COUNTS["flags"])
    assert {r[2] for r in COUNTS["flags"]} <= set(m16.SEASON_NAMES)
    assert {r[3] for r in COUNTS["flags"]} <= set(m16.BANDS)
    for state, total in COUNTS["totals"].items():
        mine = [c for c in COUNTS["coverage"] if c[0] == state]
        assert [c[1] for c in mine] == list(range(1981, 2026))
        assert sum(r[-1] for r in COUNTS["flags"] if r[0] == state) == total["flags_z"]
        assert total["flags_z"] == total["flags_high"] + total["flags_low"]
        assert total["cell_days"] == sum(sum(c[2:7]) for c in mine)
        assert all(sum(c[2:7]) % total["cells"] == 0 for c in mine)  # whole days of every cell
        assert total["flags_bound"] == 0  # no held S08 value is below 0 mm
    assert "not measured" in COUNTS["precision"]


def test_notebook_runs_without_training_or_network():
    notebook = json.loads((ROOT / "notebooks/models/m16.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    out = json.loads(result.stdout)
    assert out["status"] == "research_only" and out["totals"] == COUNTS["totals"]


def test_2025_counts_reproduce_from_the_local_s08_grids():
    try:
        again = m16.s08_flag_counts(ROOT / "data" / "raw", years=range(2024, 2026))
    except SourceUnavailable:
        pytest.skip("S08 2024-2025 year files are local only (git-ignored raw data)")
    for key in ("flags", "coverage"):
        mine = [r for r in again[key] if r[1] == 2025]
        kept = [r for r in COUNTS[key] if r[1] == 2025]
        assert mine == kept, key
