"""T244: restore, capture one admitted source and save under one deadline."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from atlas.data.budget import ArchiveOnly
from atlas.ingest.admission import SOURCES, capture_admitted
from atlas.ingest.base import IngestError
from atlas.ingest.runner_checkpoint import commit_checkpoint, resume_checkpoint
from atlas.ingest.schedule import run_bounded
from atlas.ingest.upload import ROOT, signing_key

DEADLINE_S = 150
COMPLETE = {"captured", "not_due", "deferred", "older_run"}


def run_cycle(
    root: Path, store: Path, *, source_id: str, origin: str, max_documents: int = 30
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
        digest = prior
        if capture["stage"] == "capture":
            # Even a failed capture can have committed cadence, cooldown or evidence.
            stage = "checkpoint"
            digest = commit_checkpoint(root, store, expected_head=prior)
        return {
            "status": capture["status"],
            "stage": capture["stage"],
            "manifest_sha256": digest,
            **progress,
        }
    except (IngestError, ArchiveOnly, OSError, ValueError, sqlite3.Error) as error:
        return {"status": "failed", "stage": stage, "error_type": type(error).__name__, **progress}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".cache/feeds")
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--source", required=True, choices=SOURCES)
    parser.add_argument("--max-documents", type=int, choices=range(1, 31), default=30)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        result = run_cycle(
            args.root,
            args.store,
            source_id=args.source,
            origin=args.origin,
            max_documents=args.max_documents,
        )
    else:
        try:
            result = run_bounded(
                [
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
                ],
                timeout=DEADLINE_S,
            )
        except (OSError, ValueError) as error:
            result = {"status": "failed", "error_type": type(error).__name__}
        result.setdefault("stage", "cycle")
    print(json.dumps(result))
    if not args.child and result["status"] not in COMPLETE:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
