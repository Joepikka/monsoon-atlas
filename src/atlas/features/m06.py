"""T035: evidence-backed blocked M06 branch; no synthetic labels or price features."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from atlas.config import load_yaml
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.discovery import Discovery

ROOT = Path(__file__).resolve().parents[3]
REASON = (
    "M06 blocked: verified Karnataka price history, price units and publication timing "
    "are required before implementing labels, features or predictions (T035)."
)


def data_gate() -> dict:
    """Describe checked evidence; planned split dates are not an evaluated split."""
    sources, evidence = {}, {}
    for sid in ("S22", "S23"):
        config = f"configs/sources/{sid.lower()}.yaml"
        discovery = load_yaml(ROOT / config, Discovery)
        sources[sid] = {
            "outcome": discovery.outcome,
            "licence": discovery.licence.status,
            "units": discovery.units.status,
            "history": discovery.history.status,
            "earliest_date": discovery.earliest_date,
            "latest_date": discovery.latest_date,
            "retry_condition": discovery.retry_condition,
        }
        for name in (config, f"tests/fixtures/{sid.lower()}/manifest.json"):
            evidence[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    name = "configs/models/m06.yaml"
    evidence[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    return {
        "model_id": "M06",
        "status": "blocked",
        "reason": REASON,
        "sources": sources,
        "evidence": evidence,
        "split_manifest": None,
        "prediction_rows": 0,
    }


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)


def write_gate(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data_gate(), indent=2) + "\n", encoding="utf-8", newline="\n")
    return path
