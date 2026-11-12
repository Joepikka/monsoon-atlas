"""T242: request signed loopback Worker admission before one local capture."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from atlas.config import load_state
from atlas.data.budget import ArchiveOnly
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.s01_collect import collect_weather
from atlas.ingest.s09_collect import collect
from atlas.ingest.schedule import run_bounded
from atlas.ingest.upload import ROOT, post_local_signed, signing_key

ADMISSION_PATH = "/internal/feed-check"
DEADLINE_S = 150
SOURCES = ("S09", "S01")


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    value = dict(pairs)
    if len(pairs) != len(value):
        raise IngestError("Duplicate fields in Worker acknowledgement")
    return value


def capture_admitted(
    root: Path,
    *,
    source_id: str,
    origin: str,
    max_documents: int = 30,
    admission_transport: httpx.BaseTransport | None = None,
    provider_transport: httpx.BaseTransport | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Claim once and leave local cadence, cooldown and quota to the collector."""
    stage = "admission"
    try:
        key = signing_key(origin)
        if source_id not in SOURCES or not 1 <= max_documents <= 30:
            raise ValueError("Invalid capture source or document bound")
        if not load_state(ROOT / "configs/states/ka.yaml").source(source_id).enabled:
            raise SourceUnavailable("Source is disabled")
        identity = {"state": "ka", "source_id": source_id}
        body = json.dumps(identity, separators=(",", ":")).encode("utf-8")
        status, reply = post_local_signed(
            origin,
            ADMISSION_PATH,
            body,
            "application/json",
            key=key,
            transport=admission_transport,
        )
        if status not in {200, 201}:
            return {"status": "failed", "stage": stage, "http_status": status}
        value = json.loads(reply.decode("utf-8"), object_pairs_hook=unique_object)
        if (
            status == 200
            and isinstance(value, dict)
            and value.get("admitted") is False
            and value == {**identity, "admitted": False, "reason": "not_due"}
        ):
            return {"status": "not_due", "stage": stage, "source_id": source_id}
        if (
            status != 201
            or not isinstance(value, dict)
            or value.get("admitted") is not True
            or value != {**identity, "admitted": True}
        ):
            raise IngestError("Invalid Worker admission acknowledgement")

        stage = "capture"
        options = {"transport": provider_transport, "clock": clock, "sleep": sleep}
        collection = (
            collect(root, max_documents=max_documents, **options)
            if source_id == "S09"
            else collect_weather(root, **options)
        )
        return collection | {"stage": stage, "source_id": source_id}
    except (
        IngestError,
        ArchiveOnly,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        httpx.HTTPError,
        sqlite3.Error,
    ) as error:
        return {"status": "failed", "stage": stage, "error_type": type(error).__name__}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".cache/feeds")
    parser.add_argument("--source", required=True, choices=SOURCES)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--max-documents", type=int, choices=range(1, 31), default=30)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        result = capture_admitted(
            args.root, source_id=args.source, origin=args.origin, max_documents=args.max_documents
        )
    else:
        try:
            signing_key(args.origin)
        except ValueError:
            result = {"status": "failed", "stage": "admission", "error_type": "ValueError"}
        else:
            result = run_bounded(
                [
                    sys.executable,
                    "-m",
                    "atlas.ingest.admission",
                    "--child",
                    "--root",
                    str(args.root.resolve()),
                    "--source",
                    args.source,
                    "--origin",
                    args.origin,
                    "--max-documents",
                    str(args.max_documents),
                ],
                timeout=DEADLINE_S,
            )
    print(json.dumps(result))
    if not args.child and result["status"] not in {"captured", "not_due", "deferred", "older_run"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
