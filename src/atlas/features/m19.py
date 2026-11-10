"""T167: M19 GRU reservoir challenger is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M19"
SOURCES = ("S28",)
REASON = (
    "M19 blocked: it must beat the M02 baseline on the same reservoir level target, and M02 "
    "is blocked because S28 KWRIS has no verified daily reservoir level history (T092), so "
    "there are no reservoirs with 5 years of daily data, no M02 baseline and no target; no "
    "free GPU session exists either, as the Kaggle owner step H10 is open (T167)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
