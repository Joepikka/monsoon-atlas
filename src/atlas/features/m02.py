"""T092: M02 reservoir level and storage is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M02"
SOURCES = ("S28",)
REASON = (
    "M02 blocked: no verified daily reservoir level or storage history (S28 KWRIS, T008), so "
    "labels, features and forecasts cannot be built (T092)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
