"""T237 paired weather capture at verified model grid points (D206: all 30 districts)."""

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
# D206: the 30 district representative points (configs/static/ka/places.json, 2 dp) and the
# ecmwf_ifs025 grid centre Open-Meteo returned for each on 13 Nov 2026 (30 distinct cells, all
# within 18.6 km of their point, inside the Place Lens 25 km radius).
DISTRICTS = (
    ("Bagalkot", (16.29, 75.58), (16.25, 75.5)),
    ("Bangalore", (12.94, 77.53), (13, 77.5)),
    ("Bangalore Rural", (13.18, 77.34), (13.25, 77.25)),
    ("Belgaum", (16.16, 74.89), (16.25, 75)),
    ("Bellary", (15.2, 76.74), (15.25, 76.75)),
    ("Bidar", (18.02, 77.26), (18, 77.25)),
    ("Bijapur", (16.82, 75.89), (16.75, 76)),
    ("Chamarajanagar", (11.95, 77.1), (12, 77)),
    ("Chikkaballapura", (13.6, 77.78), (13.5, 77.75)),
    ("Chikmagalur", (13.43, 75.65), (13.5, 75.75)),
    ("Chitradurga", (14.31, 76.53), (14.25, 76.5)),
    ("Dakshina Kannada", (12.82, 75.26), (12.75, 75.25)),
    ("Davanagere", (14.37, 75.89), (14.25, 76)),
    ("Dharwad", (15.37, 75.13), (15.25, 75.25)),
    ("Gadag", (15.42, 75.68), (15.5, 75.75)),
    ("Gulbarga", (17.24, 76.77), (17.25, 76.75)),
    ("Hassan", (13.03, 76.17), (13, 76.25)),
    ("Haveri", (14.72, 75.39), (14.75, 75.5)),
    ("Kodagu", (12.38, 75.66), (12.5, 75.75)),
    ("Kolar", (13.18, 78.26), (13.25, 78.25)),
    ("Koppal", (15.57, 76.31), (15.5, 76.25)),
    ("Mandya", (12.64, 76.73), (12.75, 76.75)),
    ("Mysore", (12.17, 76.5), (12.25, 76.5)),
    ("Raichur", (16.05, 76.9), (16, 77)),
    ("Ramanagara", (12.72, 77.32), (12.75, 77.25)),
    ("Shimoga", (14.06, 75.12), (14, 75)),
    ("Tumkur", (13.42, 76.88), (13.5, 77)),
    ("Udupi", (13.56, 74.88), (13.5, 75)),
    ("Uttara Kannada", (14.73, 74.64), (14.75, 74.75)),
    ("Yadgir", (16.57, 76.93), (16.5, 77)),
)
# profile -> (names, requested points, returned grid centres, forecast days). The T009 Bengaluru
# profile stays valid so receipts already in the relayed checkpoint keep verifying.
PROFILES = {
    "bengaluru-ecmwf_ifs025-v1": (("Bengaluru",), ((12.97, 77.59),), ((13.0, 77.5),), 16),
    "ka-districts-ecmwf_ifs025-v1": (
        tuple(d[0] for d in DISTRICTS),
        tuple(d[1] for d in DISTRICTS),
        tuple(d[2] for d in DISTRICTS),
        3,
    ),
}
PROFILE = "ka-districts-ecmwf_ifs025-v1"
NAMES, POINTS, RETURNED_POINTS, FORECAST_DAYS = PROFILES[PROFILE]
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
    profile = PROFILE  # read at call time, so tests can pin the T009 Bengaluru profile
    _, points, cells, days = PROFILES[profile]
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
        adapter = S01("ka", points, fetcher=fetcher, forecast_days=days)
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
            if [tuple(point) for point in returned] != list(cells):
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
                    "No quality-passed future temperature at the verified points"
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
            "profile": profile,
            "requested_model": adapter.model,
            "requested_points": [list(point) for point in points],
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
