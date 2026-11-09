"""T137: M09 cannot fit or predict while its data gate is blocked (T136)."""

from __future__ import annotations

from pathlib import Path

from atlas.features.m09 import REASON, data_gate
from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked


def no_model_manifest(folder: Path) -> Path:
    return blocked.no_model_manifest(folder, data_gate())


def fit(train, tune, folder: Path):
    no_model_manifest(folder)
    raise SourceUnavailable(REASON)


def predict(model, rows):
    raise SourceUnavailable(REASON)
