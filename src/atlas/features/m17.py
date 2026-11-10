"""T173: M17 Sentinel-1 flood extent U-Net is blocked: no labels, features or predictions."""

from __future__ import annotations

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M17"
SOURCES = ("S42", "S43", "S35", "S36")
REASON = (
    "M17 blocked: S42 Sentinel-1 imagery needs a Copernicus account (proposed owner step "
    "H15), so no scene was read, and no independent inundation masks exist (S35 is blocked, "
    "S36 holds 2018 district tables and S43 has no official impact labels), so there are "
    "not 5 distinct labelled events; training would also need a Kaggle or Colab GPU, not "
    "the 2 GB local card (T173)."
)


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
