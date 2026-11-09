"""T133: M08 Kerala flood classifier is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M08"
SOURCES = ("S35", "S36")
REASON = (
    "M08 blocked: S35 is blocked and S36 holds 2018 district labels only, with no audited "
    "pre-2018 positives or negatives, so a forecasting classifier cannot be trained (T133)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
