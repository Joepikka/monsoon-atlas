"""T136: M09 is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M09"
SOURCES = ("S37", "S42", "S14")
REASON = (
    "M09 blocked: S37 holds only state-level NRSC counts (no landslide point, date, positional "
    "error or survey footprint) and S42 imagery needs an unregistered account, so there is no "
    "label and no surveyed absence cell; the 200-landslide gate cannot pass (T136)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
