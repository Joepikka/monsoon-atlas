"""T176: M20 Rain what-if sensitivity explorer is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M20"
SOURCES = ("S43", "S35", "S36")
REASON = (
    "M20 blocked: it recomputes an already-approved flood score from the exact M01 or M08 "
    "input snapshot, and neither is approved: M01 is blocked (S43 has no labels, T085) and "
    "M08 is blocked (S35 is blocked and S36 holds 2018 district tables only). M05 is the "
    "only approved model and is a drought model, so it is not a base; the controls stay "
    "disabled (T176)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
