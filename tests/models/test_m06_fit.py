"""T036: blocked fit leaves a no-model record, never weights or predictions."""

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from atlas.ingest.base import SourceUnavailable

ROOT = Path(__file__).resolve().parents[2]


def module():
    assert importlib.util.find_spec("atlas.models.m06") is not None, "M06 fit contract missing"
    return importlib.import_module("atlas.models.m06")


def test_blocked_fit_preserves_only_no_model_manifest(tmp_path):
    with pytest.raises(SourceUnavailable, match="M06 blocked"):
        module().fit(object(), object(), tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["m06_no_model.json"]
    record = json.loads((tmp_path / "m06_no_model.json").read_text("utf-8"))
    assert record["status"] == "blocked" and record["prediction_rows"] == 0
    assert record["weights"] is None and record["scores"] is None
    assert record["source_gate"]["status"] == "blocked"


def test_prediction_remains_unavailable():
    with pytest.raises(SourceUnavailable, match="M06 blocked"):
        module().predict(object(), object())


def test_notebook_runs_without_training_or_network():
    path = ROOT / "notebooks/models/m06.ipynb"
    assert path.exists(), "M06 blocked-status notebook missing"
    notebook = json.loads(path.read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout)["status"] == "blocked"
