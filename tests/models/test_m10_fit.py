"""T140: blocked M10 fit leaves a no-model record, never weights or predictions."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from atlas.ingest.base import SourceUnavailable
from atlas.models import m10

ROOT = Path(__file__).resolve().parents[2]


def test_blocked_fit_preserves_only_no_model_manifest(tmp_path):
    with pytest.raises(SourceUnavailable, match="M10 blocked"):
        m10.fit(object(), object(), tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["m10_no_model.json"]
    record = json.loads((tmp_path / "m10_no_model.json").read_text("utf-8"))
    assert record["status"] == "blocked" and record["prediction_rows"] == 0
    assert record["weights"] is None and record["scores"] is None


def test_prediction_remains_unavailable():
    with pytest.raises(SourceUnavailable, match="M10 blocked"):
        m10.predict(object(), object())


def test_notebook_runs_without_training_or_network():
    notebook = json.loads((ROOT / "notebooks/models/m10.ipynb").read_text("utf-8"))
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
