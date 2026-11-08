"""Bounded immutable prepared-only envelopes shared by source projections."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from atlas.config import load_budgets
from atlas.data.budget import StorageQuota
from atlas.data.manifest import _atomic_write
from atlas.ingest.base import IngestError

ROOT = Path(__file__).resolve().parents[3]
MAX_BYTES = 1024**2
DERIVED_FIELDS = {"as_of", "published_at", "release_id", "data_revision"}


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


def materialize(
    raw_root: Path,
    output_root: Path,
    *,
    as_of: datetime,
    max_bytes: int,
    manifest: str,
    envelope: dict,
    inputs: list[dict],
    verify_inputs: Callable[[dict, Path, list[dict]], dict],
    reuse_equivalent: bool = False,
) -> dict:
    revision = hashlib.sha256(manifest.encode("utf-8")).hexdigest()
    source_id = envelope["source_id"]
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
            previous_cutoff = datetime.fromisoformat(previous["as_of"])
            if previous_cutoff > as_of:
                raise IngestError("An older preparation cannot roll the local head back")
            retained = verify_inputs(previous, output_root, inputs)
            same_cutoff = previous_cutoff == as_of
            if same_cutoff and previous["inputs_sha256"] != revision:
                raise IngestError("Different prepared inputs conflict at the same source cutoff")
            same_evidence = (
                reuse_equivalent
                and not same_cutoff
                and retained.get("as_of") == previous["as_of"]
                and canonical(retained | {"as_of": utc(as_of)}) == manifest
            )
            if same_cutoff or same_evidence:
                if not re.fullmatch(r"[0-9a-f]{64}", previous["sha256"]):
                    raise IngestError("Prepared head has no valid content identity")
                prior_path = output_root / f"{previous['sha256']}.json"
                with prior_path.open("rb") as stream:
                    prior_bytes = stream.read(MAX_BYTES + 1)
                if (
                    len(prior_bytes) > MAX_BYTES
                    or hashlib.sha256(prior_bytes).hexdigest() != previous["sha256"]
                ):
                    raise IngestError("Prepared head payload failed hash verification")
                prior_envelope = json.loads(prior_bytes)
                prior_snapshot = prior_envelope["snapshot"]
                if same_cutoff:
                    prepared_at = prior_snapshot["published_at"]
                    previous_same = previous["sha256"]
                else:
                    prior_inputs = output_root / f"{previous['inputs_sha256']}.inputs.json"
                    if (
                        previous.get("schema_version") != 1
                        or previous.get("status") != "prepared_only"
                        or previous.get("source_id") != source_id
                        or previous.get("state") != "ka"
                        or previous.get("payload") != prior_path.name
                        or previous.get("inputs") != prior_inputs.name
                        or prior_envelope["source_id"] != source_id
                        or prior_snapshot["as_of"] != previous["as_of"]
                        or prior_snapshot["data_revision"] != previous["inputs_sha256"]
                    ):
                        raise IngestError("Prepared payload disagrees with its pointer")
                    old = {k: v for k, v in prior_snapshot.items() if k not in DERIVED_FIELDS}
                    new = {k: v for k, v in envelope["snapshot"].items() if k not in DERIVED_FIELDS}
                    if old == new:
                        if (
                            max(len(prior_bytes), len(gzip.compress(prior_bytes, mtime=0)))
                            > max_bytes
                        ):
                            raise IngestError("Prepared snapshot exceeds the transport byte cap")
                        return {
                            "status": "prepared",
                            "coverage": "partial",
                            "sha256": previous["sha256"],
                            "payload_path": str(prior_path),
                            "inputs_path": str(prior_inputs),
                            "records": len(prior_snapshot["records"]),
                        }
        envelope["snapshot"]["published_at"] = prepared_at
        text = canonical(envelope)
        encoded = text.encode("utf-8")
        if max(len(encoded), len(gzip.compress(encoded, mtime=0))) > max_bytes:
            raise IngestError("Prepared snapshot exceeds the transport byte cap")
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
            "source_id": source_id,
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
        "records": len(envelope["snapshot"]["records"]),
    }
