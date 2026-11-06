"""T234 bounded, local-only CAP capture. No publication or cloud operations."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

from atlas.config import load_budgets, load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.budget import ArchiveOnly, StorageQuota
from atlas.ingest.base import FetchError, IngestError
from atlas.ingest.http import RETRY_STATUS, Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s09 import BASE, FEED, HOSTS, MAPPING_VERSION, NS, S09, _time, feed_versions
from atlas.ingest.schedule import admit, defer, open_control

ROOT = Path(__file__).resolve().parents[3]


class Deferred(FetchError):
    """A provider cooldown was committed; stop this run without retrying."""


class CollectorTransport(httpx.BaseTransport):
    """Space every attempt and save cooldown headers before reading response bodies."""

    def __init__(self, inner, sleep, clock, database):
        self.inner, self.sleep = inner, sleep
        self.clock, self.database = clock, database

    def handle_request(self, request):
        self.sleep(1.0)
        response = self.inner.handle_request(request)
        try:
            self._respect_retry_after(response)
        except BaseException:
            response.close()
            raise
        return response

    def close(self):
        self.inner.close()

    def _respect_retry_after(self, response):
        retry_after = response.headers.get("retry-after")
        # Observe the actual response, including the last attempt. Fetcher._wait
        # is only invoked if there is still a retry available.
        if response.status_code in RETRY_STATUS and retry_after:
            try:
                seconds = float(retry_after)
                # Reject NaN/infinity instead of silently losing the cooldown.
                if not math.isfinite(seconds) or seconds < 0:
                    return
                until = self.clock().timestamp() + seconds
            except ValueError:
                try:
                    until = parsedate_to_datetime(retry_after)
                    if until.tzinfo is None:
                        raise ValueError
                    until = until.timestamp()
                except (TypeError, ValueError, OverflowError):
                    return
            defer(self.database, "S09", until)
            raise Deferred("S09: provider Retry-After retained locally")


def validate_cap(raw: RawArtifact) -> dict:
    """Validate all headers, even for other states; retain controls without fake info rows."""
    try:
        root = ET.fromstring(raw.path.read_bytes())
    except ET.ParseError as exc:
        raise IngestError("S09: CAP file is not XML") from exc
    if root.tag != f"{{{NS['cap']}}}alert":
        raise IngestError("S09: not a CAP 1.2 alert")
    header = {
        key: (root.findtext(f"cap:{key}", "", NS) or "").strip()
        for key in ("identifier", "sender", "sent", "msgType", "status", "scope", "references")
    }
    if not all(header[k] for k in ("identifier", "sender", "sent")):
        raise IngestError("S09: required CAP header missing")
    _time(header["sent"])
    if (
        header["msgType"] not in {"Alert", "Update", "Cancel", "Ack", "Error"}
        or header["status"] not in {"Actual", "Exercise", "System", "Test", "Draft"}
        or header["scope"] not in {"Public", "Restricted", "Private"}
    ):
        raise IngestError("S09: unsupported CAP lifecycle")
    if header["msgType"] in {"Update", "Cancel"} and not header["references"]:
        raise IngestError("S09: update/cancel references missing")
    for reference in header["references"].split():
        parts = reference.split(",")
        if len(parts) != 3 or not all(parts):
            raise IngestError("S09: malformed CAP reference")
        _time(parts[2])
    infos = root.findall("cap:info", NS)
    if header["msgType"] == "Alert" or (header["msgType"] == "Update" and infos):
        S09("ka").parse(raw, load_state(ROOT / "configs/states/ka.yaml").source("S09"))
    header["msg_type"] = header.pop("msgType")
    header["has_info"] = bool(infos)
    return header


def collect(
    root: Path,
    *,
    max_documents: int = 30,
    transport: httpx.BaseTransport | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    if not 1 <= max_documents <= 30:
        raise ValueError("max_documents must be between 1 and 30")
    now = clock()
    if now.utcoffset() != timedelta(0):
        raise ValueError("collector clock must be aware UTC")
    root = Path(root).resolve()
    db = open_control(root / "control.sqlite")
    result = {
        "status": "captured",
        "coverage": "partial",
        "validated": 0,
        "failed": 0,
        "pending": 0,
        "limit": "CAP-only; complete Karnataka coverage is unverified",
    }
    fetcher = None
    try:
        status = admit(db, "S09", now)
        if status != "admitted":
            result["status"] = status
            return result
        quota = StorageQuota.from_budget(
            [root, ROOT / "data"], load_budgets(ROOT / "configs/budgets.yaml").storage
        )
        quota.ensure_can_ingest()
        fetcher = Fetcher(
            RawStore(root / "raw", quota),
            HOSTS,
            transport=CollectorTransport(transport or httpx.HTTPTransport(), sleep, clock, db),
            clock=clock,
            sleep=sleep,
        )
        ctx = FetchContext(
            source_id="S09",
            state="ka",
            run_id=str(uuid.uuid4()),
            requested_at=now,
            budget=Budget(max_requests=1 + max_documents, max_bytes=2 * 1024**2),
            raw_root=root / "raw",
        )
        feed = fetcher.fetch_bytes(ctx, FEED, mapping_version=MAPPING_VERSION)
        if hashlib.sha256(feed.path.read_bytes()).hexdigest() != feed.sha256:
            raise IngestError("S09: RSS bytes failed hash verification")
        versions = feed_versions(feed)
        with db:
            db.execute("UPDATE cap_documents SET in_feed=0")
            db.executemany(
                "INSERT INTO cap_documents(identifier,version,first_seen,in_feed) VALUES (?,?,?,1) "
                "ON CONFLICT(identifier) DO UPDATE SET version=excluded.version,in_feed=1",
                [(ident, version, now.timestamp()) for ident, version in versions.items()],
            )
        eligible = list(
            db.execute(
                "SELECT * FROM cap_documents WHERE (in_feed=1 OR validated_version IS NULL "
                "OR version<>validated_version) AND (validated_version IS NULL "
                "OR version<>validated_version OR checked_at<=?) "
                "ORDER BY COALESCE(attempted_at,first_seen),first_seen,identifier",
                (now.timestamp() - 900,),
            )
        )
        # Split capacity between changed/new documents and oldest attempts. At limit=1,
        # oldest-first alone guarantees catch-up. Failed attempts also rotate fairly.
        priority = [r for r in eligible if r["validated_version"] != r["version"]]
        selected = priority[: max_documents // 2]
        chosen = {r["identifier"] for r in selected}
        selected += [r for r in eligible if r["identifier"] not in chosen][
            : max_documents - len(selected)
        ]
        for row in selected:
            ident = row["identifier"]
            with db:
                db.execute(
                    "UPDATE cap_documents SET attempted_at=? WHERE identifier=?",
                    (clock().timestamp(), ident),
                )
            try:
                raw = fetcher.fetch_bytes(
                    ctx,
                    f"{BASE}/FetchXMLFile",
                    mapping_version=MAPPING_VERSION,
                    params={"identifier": ident},
                )
                if hashlib.sha256(raw.path.read_bytes()).hexdigest() != raw.sha256:
                    raise IngestError("S09: raw bytes failed hash verification")
                header = validate_cap(raw)
                # Revalidation has a new check time, not a new content origin clock.
                origin = (
                    row["content_fetched_at"]
                    if row["artifact_json"]
                    and json.loads(row["artifact_json"])["sha256"] == raw.sha256
                    else None
                )
                if origin is None:
                    prior = fetcher.store.latest_ok(raw.source_url)
                    origin = prior["artifact"]["fetched_at"]
                retained = raw.model_copy(update={"fetched_at": datetime.fromisoformat(origin)})
                with db:
                    db.execute(
                        "UPDATE cap_documents SET validated_version=?,checked_at=?,"
                        "content_fetched_at=?,artifact_json=?,header_json=? WHERE identifier=?",
                        (
                            row["version"],
                            raw.fetched_at.timestamp(),
                            origin,
                            retained.model_dump_json(),
                            json.dumps(header),
                            ident,
                        ),
                    )
                result["validated"] += 1
            except Deferred:
                raise
            except (FetchError, IngestError):
                result["failed"] += 1
        return result
    except Deferred:
        result["status"] = "deferred"
        return result
    except (FetchError, IngestError, ArchiveOnly):
        result["status"] = "failed"
        result["failed"] += 1
        return result
    finally:
        result["pending"] = db.execute(
            "SELECT COUNT(*) FROM cap_documents WHERE validated_version IS NULL "
            "OR validated_version<>version"
        ).fetchone()[0]
        if fetcher:
            fetcher.client.close()
        db.close()


def run_bounded(command: list[str], *, timeout: float) -> dict:
    """Only for HTTP-only children with no descendants. Timeout kills and reaps the child."""
    try:
        completed = subprocess.run(
            command,
            shell=False,
            timeout=timeout,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "deadline", "coverage": "partial"}
    if completed.returncode != 0:
        return {"status": "failed", "coverage": "partial"}
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".cache/feeds")
    parser.add_argument("--max-documents", type=int, choices=range(1, 31), default=30)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        result = collect(args.root, max_documents=args.max_documents)
    else:
        result = run_bounded(
            [
                sys.executable,
                "-m",
                "atlas.ingest.s09_collect",
                "--child",
                "--root",
                str(args.root.resolve()),
                "--max-documents",
                str(args.max_documents),
            ],
            timeout=120,
        )
    print(json.dumps(result))
    if result["status"] in {"failed", "deadline"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
