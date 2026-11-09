"""T098: M04 rain-gauge gap filling is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M04"
SOURCES = (
    "S27",
    "S29",
)
REASON = (
    "M04 blocked: no daily gauge rainfall with coordinates (S27 blocked, T077; S29 annual "
    "totals only, D113), so no gauge-day can be withheld (T098)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
