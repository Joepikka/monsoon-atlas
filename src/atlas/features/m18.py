"""T209: M18 Malayalam/English news event extraction is blocked: no labels, features or
predictions."""

from __future__ import annotations

import hashlib

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M18"
SOURCES = ("S41",)
NEWS_RECORD = "eval/news/blocked.json"
REASON = (
    "M18 blocked: S41 is blocked (T125, no publisher permission to store or classify items), "
    "so there are 0 permitted articles; the twenty annotation batches T189 to T208 are "
    "recorded as blocked (D155) with 0 articles selected, 0 labelled and 0 owner-reviewed, and "
    "owner step H13 has not happened; the gate needs 1000 permitted annotated texts (T209)."
)


def data_gate() -> dict:
    gate = blocked.data_gate(MODEL_ID, SOURCES, REASON)
    gate["evidence"][NEWS_RECORD] = hashlib.sha256(
        (blocked.ROOT / NEWS_RECORD).read_bytes()
    ).hexdigest()
    return gate


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)
