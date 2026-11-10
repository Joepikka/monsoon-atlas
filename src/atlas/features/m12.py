"""T153: M12 Delhi bus arrival and delay is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M12"
SOURCES = ("S38",)
REASON = (
    "M12 blocked: S38 is blocked on owner step H04 (D135), so no static GTFS, real-time "
    "sample or trip linkage was read and there are 0 vehicle positions and 0 service "
    "days; a scheduled-delay label cannot be built and no arrival or delay can be "
    "predicted (T153)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
