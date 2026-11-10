"""T170: M11 Karnataka-to-Kerala flood transfer is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M11"
SOURCES = ("S43", "S35", "S36")
REASON = (
    "M11 blocked: it freezes the Karnataka flood model M01 and needs common Kerala flood "
    "labels, but M01 is blocked (S43 has no official dated ward-level inundation records, "
    "T085) and M08 is blocked (S35 is blocked and S36 holds 2018 district tables only), so "
    "there is no frozen Karnataka score, no common 2023-24 labels and no 30 Kerala flood "
    "events (T170)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
