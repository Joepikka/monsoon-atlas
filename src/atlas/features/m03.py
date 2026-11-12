"""T095: M03 Karnataka reservoir inflow is blocked; no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M03"
SOURCES = ("S28",)
REASON = (
    "M03 blocked: no verified daily reported reservoir inflow with units (S28 KWRIS, T008); "
    "inflow is never inferred from levels (T095)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
