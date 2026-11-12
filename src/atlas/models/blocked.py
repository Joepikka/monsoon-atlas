"""Shared pieces of a blocked model branch (plan: "If evidence gate fails, write blocked evidence
and stop this model branch; remaining model tasks only test disabled state").

A blocked model has a planned config, a data gate built from the real source discoveries (with
SHA256 of every evidence file), a no-model manifest, a status record bound to the gate's hash,
and a report. It never has labels, weights, scores or predictions. Pattern of M06 (T035-T037).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from atlas.config import load_yaml
from atlas.ingest.discovery import Discovery

ROOT = Path(__file__).resolve().parents[3]


def _sha(name: str) -> str:
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def data_gate(model_id: str, sources: tuple[str, ...], reason: str) -> dict:
    """Checked evidence only; planned split dates are not an evaluated split."""
    found, evidence = {}, {}
    for sid in sources:
        config = f"configs/sources/{sid.lower()}.yaml"
        d = load_yaml(ROOT / config, Discovery)
        found[sid] = {
            "outcome": d.outcome,
            "licence": d.licence.status,
            "units": d.units.status,
            "history": d.history.status,
            "earliest_date": d.earliest_date,
            "latest_date": d.latest_date,
            "retry_condition": d.retry_condition,
        }
        for name in (config, f"tests/fixtures/{sid.lower()}/manifest.json"):
            evidence[name] = _sha(name)
    model_config = f"configs/models/{model_id.lower()}.yaml"
    evidence[model_config] = _sha(model_config)
    return {
        "model_id": model_id,
        "status": "blocked",
        "reason": reason,
        "sources": found,
        "evidence": evidence,
        "split_manifest": None,
        "prediction_rows": 0,
    }


def gate_path(model_id: str) -> Path:
    return ROOT / "reports" / "models" / f"{model_id.lower()}-data-gate.json"


def write_gate(gate: dict) -> Path:
    path = gate_path(gate["model_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def status_record(gate: dict, state: str) -> dict:
    """The registry status file: bound to the gate's bytes, never a release."""
    model_id = gate["model_id"]
    return {
        "model_id": model_id,
        "state": state,
        "status": "blocked",
        "reason": gate["reason"],
        "evidence": gate["evidence"],
        "source_gate_sha256": hashlib.sha256(gate_path(model_id).read_bytes()).hexdigest(),
        "dataset_sha256": None,
        "split_sha256": None,
        "weights": None,
        "baseline_scores": None,
        "candidate_scores": None,
        "improvement": None,
        "prediction_rows": 0,
        "report": f"reports/models/{model_id.lower()}.md",
    }


def no_model_manifest(folder: Path, gate: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{gate['model_id'].lower()}_no_model.json"
    record = {
        "model_id": gate["model_id"],
        "status": "blocked",
        "source_gate": gate,
        "weights": None,
        "scores": None,
        "prediction_rows": 0,
    }
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path
