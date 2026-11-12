"""T237 paired weather capture for one verified Bengaluru model grid point."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from atlas.config import load_budgets, load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.budget import ArchiveOnly, StorageQuota
from atlas.data.manifest import _atomic_write
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s01 import HOSTS, S01
from atlas.ingest.schedule import AdmittedTransport, Deferred, admit, open_control, run_bounded

ROOT = Path(__file__).resolve().parents[3]
POINTS = ((12.97, 77.59),)  # T009 verified query, not a statewide sampling grid.
RETURNED_POINT = (13.0, 77.5)  # Actual ecmwf_ifs025 grid centre in the captured response.
ROLES = ("metadata_before", "forecast", "metadata_after")


def stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


class RecordingFetcher(Fetcher):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.artifacts: list[RawArtifact] = []

    def fetch_bytes(self, *args, **kwargs):
        raw = super().fetch_bytes(*args, **kwargs)
        self.artifacts.append(raw)
        return raw


def latest_pair(root: Path) -> dict | None:
    head = root / "weather/latest-pair.json"
    if not head.exists():
        return None
    try:
        pointer = json.loads(head.read_bytes())
        if not re.fullmatch(r"[0-9a-f]{64}", pointer["sha256"]):
            raise ValueError
        path = (root / pointer["path"]).resolve()
        if not path.is_relative_to((root / "weather/pairs").resolve()):
            raise ValueError
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != pointer["sha256"]:
            raise ValueError
        pair = json.loads(body)
        if pair["source_id"] != "S01" or pair["state"] != "ka" or pair["outcome"] != "validated":
            raise ValueError
        return pair
    except (OSError, KeyError, TypeError, ValueError):
        raise IngestError("Weather paired-capture head failed integrity verification") from None


def collect_weather(
    root: Path,
    *,
    transport: httpx.BaseTransport | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    now = clock()
    if now.utcoffset() != timedelta(0):
        raise ValueError("weather clock must be aware UTC")
    config = load_state(ROOT / "configs/states/ka.yaml").source("S01")
    if not config.enabled:
        raise SourceUnavailable("S01 is disabled; no provider request is allowed")
    root = Path(root).resolve()
    database = open_control(root / "control.sqlite")
    fetcher = None
    result = {"status": "failed", "coverage": "partial", "raw_capture_only": True}
    try:
        status = admit(database, "S01", now)
        if status != "admitted":
            return result | {"status": status, "http_attempts": 0}
        quota = StorageQuota.from_budget(
            [root, ROOT / "data"], load_budgets(ROOT / "configs/budgets.yaml").storage
        )
        quota.ensure_can_ingest()
        paced = AdmittedTransport(
            transport or httpx.HTTPTransport(), sleep, clock, database, source_id="S01"
        )
        fetcher = RecordingFetcher(
            RawStore(root / "weather/raw", quota), HOSTS, transport=paced, clock=clock, sleep=sleep
        )
        adapter = S01("ka", POINTS, fetcher=fetcher)
        context = FetchContext(
            source_id="S01",
            state="ka",
            run_id=str(uuid.uuid4()),
            requested_at=now,
            raw_root=root / "weather/raw",
            budget=Budget(max_requests=5, max_bytes=2 * 1024**2),
        )
        outcome, issued, returned = "failed", None, []
        error_type = None
        try:
            meta, forecast = adapter.fetch(context)
            for artifact in fetcher.artifacts:
                if (
                    not artifact.path.resolve().is_relative_to((root / "weather/raw").resolve())
                    or hashlib.sha256(artifact.path.read_bytes()).hexdigest() != artifact.sha256
                ):
                    raise IngestError("Weather raw evidence failed hash/path verification")
            table = adapter.parse(forecast, config, meta=meta)
            rows = table.to_pylist()
            if not rows:
                raise SourceUnavailable("Weather forecast contains no rows")
            # Settling is judged at the actual forecast request, not at a later
            # preparation clock. An early cache response cannot become a verified
            # vintage just by waiting.
            if (
                rows[0]["available_at"] > forecast.fetched_at
                or rows[0]["issued_at"] > forecast.fetched_at
            ):
                raise SourceUnavailable("Named model data was not settled when retrieved")
            body = json.loads(forecast.path.read_bytes())
            locations = body if isinstance(body, list) else [body]
            returned = [[location["latitude"], location["longitude"]] for location in locations]
            if len(returned) != 1 or tuple(returned[0]) != RETURNED_POINT:
                raise SourceUnavailable("Verified weather grid mapping changed")
            checked = clock()
            if checked < max(raw.fetched_at for raw in fetcher.artifacts):
                raise SourceUnavailable("Weather capture clock regressed")
            if not any(
                row["valid_at"] >= checked
                and row["available_at"] <= checked
                and not row["missing_reason"]
                and not row["quality_flags"]
                and row["temperature_c"] is not None
                and math.isfinite(row["temperature_c"])
                for row in rows
            ):
                raise SourceUnavailable(
                    "No quality-passed future temperature at the verified point"
                )
            issued, outcome = rows[0]["issued_at"], "validated"
        except Deferred as error:
            outcome, error_type = "deferred", type(error).__name__
        except SourceUnavailable as error:
            outcome, error_type = "unavailable", type(error).__name__
        except (IngestError, OSError, ValueError, TypeError, KeyError, OverflowError) as error:
            outcome, error_type = "failed", type(error).__name__
        checked = clock()
        pair = {
            "schema_version": 1,
            "source_id": "S01",
            "state": "ka",
            "profile": "bengaluru-ecmwf_ifs025-v1",
            "requested_model": adapter.model,
            "requested_points": [list(point) for point in POINTS],
            "returned_points": returned,
            "capture_started_at": stamp(now),
            "captured_at": stamp(checked),
            "model_initialization": stamp(issued) if issued is not None else None,
            "outcome": outcome,
            "error_type": error_type,
            "http_attempts": paced.attempts,
            "requests": [
                {"role": role, "artifact": raw.model_dump(mode="json")}
                for role, raw in zip(ROLES, fetcher.artifacts, strict=False)
            ],
        }
        text = json.dumps(
            pair, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        path, digest = RawStore(root / "weather/pairs", quota).put(
            text.encode("utf-8"), "S01", checked, "json"
        )
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise IngestError("Weather capture receipt failed content verification")
        result |= {
            "http_attempts": paced.attempts,
            "receipt_path": str(path),
            "receipt_sha256": digest,
        }
        with database:
            database.execute("BEGIN IMMEDIATE")
            previous = latest_pair(root) if outcome == "validated" else None
            advanced = outcome == "validated" and (
                previous is None
                or (
                    issued >= datetime.fromisoformat(previous["model_initialization"])
                    and checked >= datetime.fromisoformat(previous["captured_at"])
                )
            )
            if advanced:
                _atomic_write(
                    root / "weather/latest-pair.json",
                    json.dumps(
                        {
                            "schema_version": 1,
                            "source_id": "S01",
                            "state": "ka",
                            "sha256": digest,
                            "path": path.relative_to(root).as_posix(),
                        }
                    ),
                )
        return result | {
            "status": "captured"
            if advanced
            else "older_run"
            if outcome == "validated"
            else outcome,
            "http_attempts": paced.attempts,
            "receipt_path": str(path),
            "receipt_sha256": digest,
        }
    except (IngestError, ArchiveOnly, OSError, ValueError, TypeError) as error:
        return result | {"error_type": type(error).__name__}
    finally:
        if fetcher:
            fetcher.client.close()
        database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".cache/feeds")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    result = (
        collect_weather(args.root)
        if args.child
        else run_bounded(
            [
                sys.executable,
                "-m",
                "atlas.ingest.s01_collect",
                "--child",
                "--root",
                str(args.root.resolve()),
            ],
            timeout=120,
        )
    )
    print(json.dumps(result))
    if not args.child and result["status"] in {"failed", "unavailable", "deadline"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
