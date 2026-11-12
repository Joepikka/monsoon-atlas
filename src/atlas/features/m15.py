"""T162: M15 Heat exposure and heatwave outlook is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M15"
SOURCES = ("S01", "S02", "S16", "S18")
REASON = (
    "M15 blocked: no Delhi source is enabled, S01 keeps no issue-time forecast vintages "
    "(D07) so no forecast is matched to observed truth, S02 is ERA5 reanalysis, which "
    "supports trends and exposure only, and S18 holds only the owner's Southern Zone "
    "extract (D174), so no Delhi impervious input exists; calibration skill cannot be claimed "
    "(T162)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
