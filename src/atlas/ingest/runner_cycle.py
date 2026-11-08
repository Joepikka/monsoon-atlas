"""T244: restore, capture one admitted source and save under one deadline."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from atlas.data.budget import ArchiveOnly
from atlas.ingest.admission import SOURCES, capture_admitted
from atlas.ingest.base import IngestError
from atlas.ingest.checkpoint_bundle import OUTPUT
from atlas.ingest.runner_checkpoint import commit_checkpoint, resume_checkpoint
from atlas.ingest.s01_prepare import prepare_weather
from atlas.ingest.s09_prepare import prepare
from atlas.ingest.schedule import run_bounded
from atlas.ingest.upload import ROOT, signing_key, upload_local

DEADLINE_S = 150
COMPLETE = {"captured", "not_due", "deferred", "older_run", "stored", "unchanged"}
STATE_ERRORS = (IngestError, ArchiveOnly, OSError, ValueError, sqlite3.Error)


def run_cycle(
    root: Path,
    store: Path,
    *,
    source_id: str,
    origin: str,
    max_documents: int = 30,
    upload: bool = False,
) -> dict:
    """Keep the working root and seal verified state against the restored head."""
    stage = "preflight"
    progress = {}
    try:
        signing_key(origin)
        if source_id not in SOURCES or not 1 <= max_documents <= 30:
            raise ValueError("Invalid capture source or document bound")

        stage = "restore"
        prior = resume_checkpoint(root, store)
        progress["restored_sha256"] = prior

        stage = "capture"
        capture = capture_admitted(
            root, source_id=source_id, origin=origin, max_documents=max_documents
        )
        progress["capture"] = capture
        preparation = None
        if upload and capture["status"] == "captured":
            stage = "prepare"
            try:
                cutoff = datetime.now(UTC)
                preparation = (
                    prepare_weather(root, as_of=cutoff)
                    if source_id == "S01"
                    else prepare(root / "raw", root / OUTPUT[source_id], as_of=cutoff)
                )
            except STATE_ERRORS as error:
                preparation = {"status": "failed", "error_type": type(error).__name__}
            progress["prepare"] = preparation

        digest = prior
        if capture["stage"] == "capture":
            # Even a failed capture can have committed cadence, cooldown or evidence.
            stage = "checkpoint"
            digest = commit_checkpoint(root, store, expected_head=prior)
        progress["manifest_sha256"] = digest
        if preparation is not None and preparation["status"] == "failed":
            return {"status": "failed", "stage": "prepare", **progress}

        frozen = store / "objects" / digest / "files"
        if upload and (
            preparation is not None
            or (
                capture["status"] == "not_due"
                and (frozen / OUTPUT[source_id] / "prepared.json").is_file()
            )
        ):
            stage = "upload"
            sent = upload_local(frozen, source_id=source_id, origin=origin)
            return {"status": sent["status"], "stage": stage, "upload": sent, **progress}
        return {
            "status": capture["status"],
            "stage": capture["stage"],
            **progress,
        }
    except STATE_ERRORS as error:
        return {"status": "failed", "stage": stage, "error_type": type(error).__name__, **progress}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".cache/feeds")
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--source", required=True, choices=SOURCES)
    parser.add_argument("--max-documents", type=int, choices=range(1, 31), default=30)
    parser.add_argument("--upload-local", action="store_true", help="Prepare and send after save")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        result = run_cycle(
            args.root,
            args.store,
            source_id=args.source,
            origin=args.origin,
            max_documents=args.max_documents,
            upload=args.upload_local,
        )
    else:
        command = [
            sys.executable,
            "-m",
            "atlas.ingest.runner_cycle",
            "--child",
            "--root",
            str(args.root),
            "--store",
            str(args.store),
            "--origin",
            args.origin,
            "--source",
            args.source,
            "--max-documents",
            str(args.max_documents),
        ]
        if args.upload_local:
            command.append("--upload-local")
        try:
            result = run_bounded(command, timeout=DEADLINE_S)
        except (OSError, ValueError) as error:
            result = {"status": "failed", "error_type": type(error).__name__}
        result.setdefault("stage", "cycle")
    print(json.dumps(result))
    if not args.child and result["status"] not in COMPLETE:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
