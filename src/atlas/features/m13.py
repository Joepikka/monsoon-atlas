"""T156: M13 Delhi bunching anomaly is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M13"
SOURCES = ("S38",)
REASON = (
    "M13 blocked: S38 is blocked on owner step H04 (D135), so there are 0 completed "
    "trajectories, 0 service days and no verified scheduled headways; bunching cannot be "
    "labelled and no flag or persistence forecast can be made (T156)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
