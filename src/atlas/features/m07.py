"""T130: M07 Kerala seven-day dam forecast is blocked: no labels, features or predictions."""

from __future__ import annotations

import hashlib

import yaml

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M07"
SOURCES = ("S32", "S33", "S34")
REASON = (
    "M07 blocked: a known vertical datum exists for 4 of the 8 dams the gate needs (D103, T129), "
    "S32 daily history is sampled dates only and S34 awaits the unapproved T118 bulk OCR, so "
    "labels, features and forecasts cannot be built (T130)."
)
DAMS = blocked.ROOT / "configs" / "states" / "kl" / "dams.yaml"


def data_gate() -> dict:
    gate = blocked.data_gate(MODEL_ID, SOURCES, REASON)
    registry = DAMS.relative_to(blocked.ROOT).as_posix()
    dams = yaml.safe_load(DAMS.read_text("utf-8"))
    known = sum(d["datum_status"] == "known" for d in dams["dams"])
    required = dams["datum_gate"]["required_known_dams"]
    gate["datum"] = {
        "registered": len(dams["dams"]),
        "known": known,
        "required": required,
        "met": known >= required,
    }
    gate["evidence"][registry] = hashlib.sha256(DAMS.read_bytes()).hexdigest()
    return gate


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
