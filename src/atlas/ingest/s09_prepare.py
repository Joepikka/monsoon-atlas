"""T235: local CAP projection and immutable prepared transport; never publication."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from atlas.config import load_budgets, load_state
from atlas.contracts import RawArtifact
from atlas.data.budget import StorageQuota
from atlas.data.manifest import _atomic_write
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.raw_store import LEDGER
from atlas.ingest.s09 import BASE, S09, _time, superseded_identities
from atlas.ingest.s09_collect import validate_cap

ROOT = Path(__file__).resolve().parents[3]
MAX_BYTES = 1024**2
CAP_URL = re.compile(re.escape(BASE) + r"/FetchXMLFile\?identifier=\d+$")


def canonical(value) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def immutable(path: Path, text: str) -> None:
    if path.exists():
        if path.read_bytes() != text.encode("utf-8"):
            raise IngestError("Prepared immutable file failed content verification")
        return
    _atomic_write(path, text)


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


def warning(row: dict) -> dict:
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
        "warning_text": row["event"],
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
    config = load_state(ROOT / "configs/states/ka.yaml").source("S09")
    records = []
    for identity, (raw, header, _) in sorted(selected.items()):
        if (
            identity in replaced
            or header["msg_type"] not in {"Alert", "Update"}
            or not header["has_info"]
        ):
            continue
        for row in S09("ka").parse(raw, config).to_pylist():
            if row["expires_at"] is None or row["expires_at"] > as_of:
                records.append(warning(row))
    manifest = canonical(
        {
            "schema_version": 1,
            "mapping_version": "s09-prepared-v1",
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
    # SQLite serializes competing head updates; the atomic JSON pointer remains the
    # authority after a crash. Repeated input reuses its actual first preparation
    # time, rather than fabricating a past publication clock or changing identity.
    output_root.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(output_root / "prepared-control.sqlite", timeout=5)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS prepare_guard(id INTEGER PRIMARY KEY)")
        db.execute("BEGIN IMMEDIATE")
        head = output_root / "prepared.json"
        prepared_at, previous_same = utc(datetime.now(UTC)), None
        if head.exists():
            previous = json.loads(head.read_text("utf-8"))
            if datetime.fromisoformat(previous["as_of"]) > as_of:
                raise IngestError("An older preparation cannot roll the local head back")
            verify_retained_inputs(previous, output_root, inputs)
            if datetime.fromisoformat(previous["as_of"]) == as_of:
                if previous["inputs_sha256"] != revision:
                    raise IngestError(
                        "Different prepared inputs conflict at the same source cutoff"
                    )
                if not re.fullmatch(r"[0-9a-f]{64}", previous["sha256"]):
                    raise IngestError("Prepared head has no valid content identity")
                prior_bytes = (output_root / f"{previous['sha256']}.json").read_bytes()
                if hashlib.sha256(prior_bytes).hexdigest() != previous["sha256"]:
                    raise IngestError("Prepared head payload failed hash verification")
                prepared_at = json.loads(prior_bytes)["snapshot"]["published_at"]
                previous_same = previous["sha256"]
        envelope["snapshot"]["published_at"] = prepared_at
        text = canonical(envelope)
        encoded = text.encode("utf-8")
        if max(len(encoded), len(gzip.compress(encoded, mtime=0))) > max_bytes:
            raise IngestError("Prepared CAP snapshot exceeds the transport byte cap")
        digest = hashlib.sha256(encoded).hexdigest()
        if previous_same is not None and previous_same != digest:
            raise IngestError("Different prepared bytes conflict at the same source cutoff")
        payload_path, inputs_path = (
            output_root / f"{digest}.json",
            output_root / f"{revision}.inputs.json",
        )
        roots = {ROOT / "data", raw_root, output_root}
        quota_roots = [p for p in roots if not any(p != q and p.is_relative_to(q) for q in roots)]
        incoming = sum(
            len(body.encode("utf-8"))
            for path, body in ((payload_path, text), (inputs_path, manifest))
            if not path.exists()
        )
        StorageQuota.from_budget(
            quota_roots, load_budgets(ROOT / "configs/budgets.yaml").storage
        ).ensure_can_ingest(incoming)
        immutable(inputs_path, manifest)
        immutable(payload_path, text)
        pointer = {
            "schema_version": 1,
            "status": "prepared_only",
            "state": "ka",
            "source_id": "S09",
            "as_of": utc(as_of),
            "sha256": digest,
            "payload": payload_path.name,
            "inputs_sha256": revision,
            "inputs": inputs_path.name,
        }
        _atomic_write(head, canonical(pointer))
    return {
        "status": "prepared",
        "coverage": "partial",
        "sha256": digest,
        "payload_path": str(payload_path),
        "inputs_path": str(inputs_path),
        "records": len(records),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=ROOT / ".cache/feeds/raw")
    parser.add_argument("--output-root", type=Path, default=ROOT / ".cache/feeds/prepared")
    args = parser.parse_args()
    print(json.dumps(prepare(args.raw_root, args.output_root, as_of=datetime.now(UTC))))


if __name__ == "__main__":
    main()
