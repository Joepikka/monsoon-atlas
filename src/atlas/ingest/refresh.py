"""T236: one bounded local KA CAP capture/preparation run, without cloud activity."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from atlas.data.budget import ArchiveOnly
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.s09_collect import ROOT, collect, run_bounded
from atlas.ingest.s09_prepare import prepare

DEADLINE_S = 150


def refresh(
    root: Path,
    *,
    max_documents: int = 30,
    transport: httpx.BaseTransport | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Prepare retained evidence even if a new provider check is deferred/not due.

    This recovers a captured control after interruption. It never advances a
    source validation clock merely because a new report was prepared.
    """
    root = Path(root).resolve()
    try:
        collection = collect(
            root, max_documents=max_documents, transport=transport, clock=clock, sleep=sleep
        )
    except (SourceUnavailable, ValueError) as error:
        return {
            "status": "failed",
            "coverage": "partial",
            "stage": "capture",
            "error_type": type(error).__name__,
        }
    except (IngestError, ArchiveOnly, OSError) as error:
        collection = {
            "status": "failed",
            "coverage": "partial",
            "stage": "capture",
            "error_type": type(error).__name__,
        }
    try:
        prepared = prepare(root / "raw", root / "prepared", as_of=clock())
    except (IngestError, ArchiveOnly, OSError, ValueError) as error:
        return {
            "status": "failed",
            "coverage": "partial",
            "stage": "prepare",
            "error_type": type(error).__name__,
            "collection": collection,
        }
    return {
        "status": "prepared",
        "coverage": "partial",
        "collection": collection,
        "prepared": prepared,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".cache/feeds")
    parser.add_argument("--max-documents", type=int, choices=range(1, 31), default=30)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        result = refresh(args.root, max_documents=args.max_documents)
    else:
        result = run_bounded(
            [
                sys.executable,
                "-m",
                "atlas.ingest.refresh",
                "--child",
                "--root",
                str(args.root.resolve()),
                "--max-documents",
                str(args.max_documents),
            ],
            timeout=DEADLINE_S,
        )
    print(json.dumps(result))
    # Handled child errors are returned as structured JSON to the parent. The
    # public launcher supplies the failing exit status after retaining that detail.
    if not args.child and result["status"] in {"failed", "deadline"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
