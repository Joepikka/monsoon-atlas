"""T235: local CAP projection and immutable prepared transport; never publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.prepared import canonical, materialize, utc
from atlas.ingest.raw_store import LEDGER
from atlas.ingest.s09 import BASE, S09, _time, superseded_identities
from atlas.ingest.s09_collect import validate_cap

ROOT = Path(__file__).resolve().parents[3]
MAX_BYTES = 1024**2
CAP_URL = re.compile(re.escape(BASE) + r"/FetchXMLFile\?identifier=\d+$")


def retained_artifacts(raw_root: Path) -> list[RawArtifact]:
    """Preparation cannot silently lose a control because a ledger line is damaged."""
    path = raw_root / LEDGER
    if not path.exists():
        return []
    try:
        lines = path.read_text("utf-8").splitlines()
    except UnicodeError:
        raise IngestError("Retained raw ledger is not valid UTF-8") from None
    artifacts = []
    for number, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
            raw = RawArtifact.model_validate(entry["artifact"])
            if entry["http"]["status"] != raw.response_status:
                raise ValueError("Conflicting HTTP metadata")
        except (KeyError, TypeError, ValueError):
            raise IngestError(f"Invalid retained raw ledger entry at line {number}") from None
        artifacts.append(raw)
    return artifacts


def verify_retained_inputs(previous: dict, output_root: Path, inputs: list[dict]) -> None:
    """Known evidence cannot vanish or be retimed between append-only preparations."""
    try:
        revision = previous["inputs_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", revision):
            raise ValueError("Invalid input identity")
        encoded = (output_root / f"{revision}.inputs.json").read_bytes()
        if hashlib.sha256(encoded).hexdigest() != revision:
            raise ValueError("Input hash mismatch")
        prior = json.loads(encoded)["inputs"]
        current = {(item["source_url"], item["sha256"]): item for item in inputs}
        for item in prior:
            retained = current[(item["source_url"], item["sha256"])]
            if retained["content_fetched_at"] != item[
                "content_fetched_at"
            ] or datetime.fromisoformat(retained["checked_at"]) < datetime.fromisoformat(
                item["checked_at"]
            ):
                raise ValueError("Retained evidence clocks changed")
    except (OSError, KeyError, TypeError, ValueError):
        raise IngestError("Previously retained CAP input evidence is missing or changed") from None


def warning(row: dict, warning_text: str) -> dict:
    record = {
        "id": row["record_id"],
        "title": f"{row['event']} — {row['area_text']}",
        "source_id": "S09",
        "source_url": row["source_url"],
        "provenance": "official",
        "kind": "alert",
        "spatial_scope": "area",
        "longitude": None,
        "latitude": None,
        "location_note": (
            "Area description only; map geometry unavailable. See the original source."
        ),
        "warning_text": warning_text,
        "area_text": row["area_text"],
        "instruction": row["instruction"],
        "severity": row["severity"],
        "value": None,
        "unit": None,
        "market": None,
        "missing_reason": None,
        "evidence": None,
        "place_id": None,
        "boundary_version": None,
        "model_id": None,
        "model_status": None,
    }
    for field in ("issued_at", "valid_at", "available_at", "fetched_at", "expires_at"):
        record[field] = utc(row[field]) if row[field] else None
    if any(isinstance(v, str) and len(v) > 2000 for v in record.values()):
        raise IngestError("CAP projection exceeds a browser text-field bound")
    return record


def prepare(
    raw_root: Path, output_root: Path, *, as_of: datetime, max_bytes: int = MAX_BYTES
) -> dict:
    config = load_state(ROOT / "configs/states/ka.yaml").source("S09")
    if not config.enabled:
        raise SourceUnavailable(f"S09 is disabled; {config.verify_task} must pass")
    if as_of.utcoffset() != timedelta(0) or as_of > datetime.now(UTC):
        raise ValueError("Preparation cutoff must be aware UTC and cannot be in the future")
    if not 1 <= max_bytes <= MAX_BYTES:
        raise ValueError("Preparation byte bound must be between 1 and 1048576")
    raw_root, output_root = Path(raw_root).resolve(), Path(output_root).resolve()
    artifacts = []
    for raw in retained_artifacts(raw_root):
        if not CAP_URL.fullmatch(raw.source_url):
            continue  # RSS validation cannot validate linked CAP documents.
        if raw.fetched_at > as_of:
            continue
        if raw.response_status not in {200, 304}:
            raise IngestError("CAP evidence must be a successful 200 or 304 response")
        if raw.schema_mapping_version != "s09-v1" or not raw.path.resolve().is_relative_to(
            raw_root
        ):
            raise IngestError("CAP evidence mapping or path is outside the retained capture")
        if (
            not raw.path.is_file()
            or hashlib.sha256(raw.path.read_bytes()).hexdigest() != raw.sha256
        ):
            raise IngestError("CAP raw evidence failed hash verification")
        artifacts.append(raw)
    # Keep content's earliest actual retrieval separately from subsequent validation.
    origins, checks = {}, {}
    for raw in sorted(artifacts, key=lambda r: r.fetched_at):
        key = (raw.source_url, raw.sha256)
        if raw.response_status == 200:
            origins.setdefault(key, raw)
        checks[key] = max(checks.get(key, raw.fetched_at), raw.fetched_at)
    selected, inputs, successes = {}, [], []
    for key, checked in sorted(checks.items()):
        raw = origins.get(key)
        if raw is None:
            raise IngestError("CAP validation has no retained original 200 response")
        item = {
            "source_url": raw.source_url,
            "sha256": raw.sha256,
            "path": raw.path.resolve().relative_to(raw_root).as_posix(),
            "content_fetched_at": utc(raw.fetched_at),
            "checked_at": utc(checked),
        }
        inputs.append(item)
        try:
            header = validate_cap(raw)
        except IngestError:
            item["outcome"] = "invalid_document"
            continue
        item["outcome"] = "validated_document"
        successes.append(checked)
        sent = _time(header["sent"])
        if sent > as_of or header["status"] != "Actual" or header["scope"] != "Public":
            continue
        identity = (header["sender"], header["identifier"], sent)
        if identity not in selected or selected[identity][2] < checked:
            selected[identity] = (raw, header, checked)
    if not successes:
        raise SourceUnavailable(
            "S09: no validated CAP evidence at this cutoff; preparation unavailable"
        )
    controls = [
        {
            "sender": h["sender"],
            "alert_id": h["identifier"],
            "sent_at": _time(h["sent"]),
            "msg_type": h["msg_type"],
            "references": h["references"],
        }
        for _, h, _ in selected.values()
    ]
    replaced = superseded_identities(controls)
    records = []
    for identity, (raw, header, _) in sorted(selected.items()):
        if (
            identity in replaced
            or header["msg_type"] not in {"Alert", "Update"}
            or not header["has_info"]
        ):
            continue
        rows, warning_text = S09("ka").parse_with_warning_text(raw, config)
        for row in rows.to_pylist():
            if row["expires_at"] is None or row["expires_at"] > as_of:
                records.append(warning(row, warning_text))
    manifest = canonical(
        {
            "schema_version": 1,
            "mapping_version": "s09-prepared-v2",
            "state": "ka",
            "source_id": "S09",
            "as_of": utc(as_of),
            "coverage": "partial",
            "inputs": inputs,
        }
    )
    revision = hashlib.sha256(manifest.encode("utf-8")).hexdigest()
    detail = (
        "CAP-only retained subset; complete Karnataka coverage is unverified. "
        "An empty result does not establish an absence of hazards."
    )
    if any(item["outcome"] == "invalid_document" for item in inputs):
        detail += " Some retained source documents could not be validated."
    envelope = {
        "source_id": "S09",
        "snapshot": {
            "schema_version": 1,
            "state": "ka",
            "release_id": f"S09-{revision[:20]}",
            "data_revision": revision,
            "as_of": utc(as_of),
            "records": records,
            "places": [],
            "facilities": [],
            "sources": [
                {
                    "source_id": "S09",
                    "status": "partial",
                    "last_success_at": utc(max(successes)),
                    "detail": detail,
                }
            ],
        },
    }
    return materialize(
        raw_root,
        output_root,
        as_of=as_of,
        max_bytes=max_bytes,
        manifest=manifest,
        envelope=envelope,
        inputs=inputs,
        verify_inputs=verify_retained_inputs,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=ROOT / ".cache/feeds/raw")
    parser.add_argument("--output-root", type=Path, default=ROOT / ".cache/feeds/prepared")
    args = parser.parse_args()
    print(json.dumps(prepare(args.raw_root, args.output_root, as_of=datetime.now(UTC))))


if __name__ == "__main__":
    main()
