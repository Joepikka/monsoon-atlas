"""T159: M14 Delhi station pollution forecast is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M14"
SOURCES = ("S24", "S04")
REASON = (
    "M14 blocked: S24 CPCB station data is blocked (D133, D134): resource ID, licence, "
    "fields, units, averaging interval and history are unread and there are 0 station "
    "rows, so no PM2.5 label exists; S04 CAMS is a model estimate and baseline input, "
    "never a label (T159)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
