"""T139: M10 is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M10"
SOURCES = ("S22", "S23")
REASON = (
    "M10 blocked: S22 exposes no price row and S23 is a one-day snapshot (5 Nov 2026) with an "
    "unverified price unit, so there is no weekly market-commodity panel, no 30-market sample "
    "and no 50 heavy-rain events; no effect can be estimated (T139)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
