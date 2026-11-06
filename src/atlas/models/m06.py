"""T036: M06 cannot fit or predict while its data gate is blocked."""

from __future__ import annotations

import json
from pathlib import Path

from atlas.features.m06 import REASON, data_gate
from atlas.ingest.base import SourceUnavailable


def no_model_manifest(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "m06_no_model.json"
    record = {
        "model_id": "M06",
        "status": "blocked",
        "source_gate": data_gate(),
        "weights": None,
        "scores": None,
        "prediction_rows": 0,
    }
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def fit(train, tune, folder: Path):
    no_model_manifest(folder)
    raise SourceUnavailable(REASON)


def predict(model, rows):
    raise SourceUnavailable(REASON)
