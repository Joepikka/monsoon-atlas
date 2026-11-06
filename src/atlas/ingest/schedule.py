"""Local-only cadence/backoff admission. Cloud runners must use T233's D1 guard."""

import json
import math
import sqlite3
import subprocess
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

from atlas.ingest.base import FetchError
from atlas.ingest.http import RETRY_STATUS

REQUEST_SPACING_S = {"S01": 5.0, "S09": 1.0}


class Deferred(FetchError):
    """A provider cooldown was committed; stop without another request."""


class AdmittedTransport(httpx.BaseTransport):
    """Pace every HTTP attempt and retain cooldown before reading response bodies."""

    def __init__(self, inner, sleep, clock, database, *, source_id="S09"):
        self.inner, self.sleep = inner, sleep
        self.clock, self.database = clock, database
        self.source_id, self.spacing = source_id, REQUEST_SPACING_S[source_id]
        self.attempts = 0

    def handle_request(self, request):
        self.sleep(self.spacing)
        self.attempts += 1
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
        if response.status_code in RETRY_STATUS and retry_after:
            try:
                seconds = float(retry_after)
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
            defer(self.database, self.source_id, until)
            raise Deferred(f"{self.source_id}: provider Retry-After retained locally")


def open_control(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS local_admission (
            source TEXT PRIMARY KEY CHECK(source IN ('S01','S09')),
            admitted_at REAL, retry_at REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS cap_documents (
            identifier TEXT PRIMARY KEY, version TEXT NOT NULL,
            first_seen REAL NOT NULL, in_feed INTEGER NOT NULL,
            attempted_at REAL, validated_version TEXT, checked_at REAL,
            content_fetched_at TEXT, artifact_json TEXT, header_json TEXT
        );
    """)
    return db


def admit(db: sqlite3.Connection, source: str, now: datetime) -> str:
    cadence = {"S01": 21600, "S09": 900}[source]
    # BEGIN IMMEDIATE serializes competing processes before reading the clock.
    with db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM local_admission WHERE source=?", (source,)).fetchone()
        if row:
            if row["retry_at"] > now.timestamp():
                return "deferred"
            if row["admitted_at"] is not None and now.timestamp() < row["admitted_at"] + cadence:
                return "not_due"
        db.execute(
            "INSERT INTO local_admission(source,admitted_at) VALUES (?,?) "
            "ON CONFLICT(source) DO UPDATE SET admitted_at=excluded.admitted_at",
            (source, now.timestamp()),
        )
    return "admitted"


def defer(db: sqlite3.Connection, source: str, until: float) -> None:
    with db:
        db.execute(
            "INSERT INTO local_admission(source,retry_at) VALUES (?,?) "
            "ON CONFLICT(source) DO UPDATE SET retry_at=MAX(retry_at,excluded.retry_at)",
            (source, until),
        )


def run_bounded(command: list[str], *, timeout: float) -> dict:
    """Only for children with no descendants. A timeout kills and reaps the child."""
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
