"""T238: offline prepared-only temperature at the single verified model grid point."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.prepared import MAX_BYTES, canonical, materialize, utc
from atlas.ingest.s01 import API, MAPPING_VERSION, S01, SETTLE, meta_url
from atlas.ingest.s01_collect import POINTS, RETURNED_POINT, ROLES, latest_pair

ROOT = Path(__file__).resolve().parents[3]
PROFILE = "bengaluru-ecmwf_ifs025-v1"
MODEL = "ecmwf_ifs025"


def receipt_time(value: str) -> datetime:
    value = datetime.fromisoformat(value)
    if value.utcoffset() != timedelta(0):
        raise ValueError("Receipt clocks must be aware UTC")
    return value


def verify_retained_inputs(previous: dict, output_root: Path, inputs: list[dict]) -> None:
    """Every previously used immutable receipt (and thus its raw identities) survives."""
    try:
        revision = previous["inputs_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", revision):
            raise ValueError("Invalid input identity")
        encoded = (output_root / f"{revision}.inputs.json").read_bytes()
        if hashlib.sha256(encoded).hexdigest() != revision:
            raise ValueError("Invalid prior input manifest")
        current = {item["receipt_sha256"]: item for item in inputs}
        for item in json.loads(encoded)["inputs"]:
            if current[item["receipt_sha256"]] != item:
                raise ValueError("Changed retained receipt")
    except (OSError, KeyError, TypeError, ValueError):
        raise IngestError(
            "Previously retained weather input evidence is missing or changed"
        ) from None


def qualified_receipts(root: Path, as_of: datetime, config) -> list[tuple]:
    """Read complete archived attempts; a head is a checked hint, never independent inputs."""
    latest_pair(root)  # A present pointer must be intact even for an historical cutoff.
    head = root / "weather/latest-pair.json"
    if head.exists():
        pointer = json.loads(head.read_bytes())
        if (
            pointer.get("schema_version") != 1
            or pointer.get("source_id") != "S01"
            or pointer.get("state") != "ka"
            or Path(pointer["path"]).stem != pointer["sha256"]
        ):
            raise IngestError("Weather paired-capture pointer has invalid identity")
    adapter = S01("ka", POINTS, model=MODEL)
    urls = (
        meta_url(MODEL),
        f"{API}/v1/forecast?{urlencode(sorted(adapter.params().items()))}",
        meta_url(MODEL),
    )
    eligible = []
    for path in sorted((root / "weather/pairs").rglob("*.json")):
        try:
            encoded = path.read_bytes()
            digest = hashlib.sha256(encoded).hexdigest()
            if path.stem != digest or not path.resolve().is_relative_to(root / "weather/pairs"):
                raise ValueError("Receipt hash/path mismatch")
            pair = json.loads(encoded)
            if (
                pair["schema_version"] != 1
                or pair["source_id"] != "S01"
                or pair["state"] != "ka"
                or pair["profile"] != PROFILE
                or pair["requested_model"] != MODEL
                or pair["requested_points"] != [list(point) for point in POINTS]
            ):
                raise ValueError("Receipt source/profile mismatch")
            captured = receipt_time(pair["captured_at"])
            started = receipt_time(pair["capture_started_at"])
            if started > captured:
                raise ValueError("Receipt capture clocks regressed")
            if pair["outcome"] != "validated" or captured > as_of:
                continue
            if pair["returned_points"] != [list(RETURNED_POINT)]:
                raise ValueError("Returned grid changed")
            if [item["role"] for item in pair["requests"]] != list(ROLES):
                raise ValueError("Receipt requires exactly three ordered input roles")
            artifacts = [RawArtifact.model_validate(item["artifact"]) for item in pair["requests"]]
            if any(raw.fetched_at > as_of for raw in artifacts):
                continue
            for raw, url in zip(artifacts, urls, strict=True):
                raw_path = raw.path.resolve()
                if (
                    raw.source_url != url
                    or raw.schema_mapping_version != MAPPING_VERSION
                    or raw.response_status not in {200, 304}
                    or not raw_path.is_relative_to(root / "weather/raw/S01")
                    or raw_path.stem != raw.sha256
                    or hashlib.sha256(raw_path.read_bytes()).hexdigest() != raw.sha256
                    or not started <= raw.fetched_at <= captured
                ):
                    raise ValueError("Raw evidence hash/path/source/clock mismatch")
            before, forecast, after = artifacts
            if not before.fetched_at <= forecast.fetched_at <= after.fetched_at:
                raise ValueError("Input HTTP clocks are out of order")
            metadata = [json.loads(raw.path.read_bytes()) for raw in (before, after)]
            issued = receipt_time(pair["model_initialization"])
            for info in metadata:
                if (
                    datetime.fromtimestamp(info["last_run_initialisation_time"], UTC) != issued
                    or issued > forecast.fetched_at
                    or datetime.fromtimestamp(info["last_run_availability_time"], UTC) + SETTLE
                    > forecast.fetched_at
                ):
                    raise ValueError("Weather model run mismatched or unsettled at retrieval")
            body = json.loads(forecast.path.read_bytes())
            locations = body if isinstance(body, list) else [body]
            if (
                len(locations) != 1
                or not isinstance(locations[0], dict)
                or (locations[0]["latitude"], locations[0]["longitude"]) != RETURNED_POINT
                or not isinstance(locations[0].get("hourly"), dict)
                or not isinstance(locations[0].get("hourly_units"), dict)
            ):
                raise ValueError("Actual returned grid or forecast shape changed")
            rows = adapter.parse(forecast, config, meta=after).to_pylist()
            if not any(usable(row, captured) for row in rows):
                raise SourceUnavailable("S01: validated receipt has no usable future temperature")
            item = {
                "receipt_sha256": digest,
                "receipt_path": path.relative_to(root).as_posix(),
                "captured_at": utc(captured),
                "requests": [
                    {
                        "role": role,
                        "sha256": raw.sha256,
                        "source_url": raw.source_url,
                        "path": raw.path.resolve().relative_to(root).as_posix(),
                        "fetched_at": utc(raw.fetched_at),
                    }
                    for role, raw in zip(ROLES, artifacts, strict=True)
                ],
            }
            eligible.append((issued, captured, forecast, rows, locations[0], item))
        except (OSError, KeyError, TypeError, ValueError, OverflowError) as error:
            raise IngestError(
                "Weather receipt or raw input failed integrity verification"
            ) from error
    return eligible


def usable(row: dict, cutoff: datetime) -> bool:
    return (
        row["valid_at"] >= cutoff
        and row["available_at"] <= cutoff
        and not row["missing_reason"]
        and not row["quality_flags"]
        and row["temperature_c"] is not None
        and math.isfinite(row["temperature_c"])
    )


def prepare_weather(root: Path, *, as_of: datetime, max_bytes: int = MAX_BYTES) -> dict:
    if as_of.utcoffset() != timedelta(0) or as_of > datetime.now(UTC):
        raise ValueError("Preparation cutoff must be aware UTC and cannot be in the future")
    if not 1 <= max_bytes <= MAX_BYTES:
        raise ValueError("Preparation byte bound must be between 1 and 1048576")
    config = load_state(ROOT / "configs/states/ka.yaml").source("S01")
    if not config.enabled:
        raise SourceUnavailable("S01 is disabled; preparation unavailable")
    root = Path(root).resolve()
    output_root = root / "weather/prepared"
    receipts = qualified_receipts(root, as_of, config)
    inputs = [receipt[-1] for receipt in receipts]
    head = output_root / "prepared.json"
    if head.exists():
        verify_retained_inputs(json.loads(head.read_bytes()), output_root, inputs)
    if not receipts:
        raise SourceUnavailable("S01: no complete validated weather receipt at this cutoff")
    selected = max(receipts, key=lambda receipt: (receipt[0], receipt[1]))
    issued, _, forecast, rows, location, _ = selected
    cohort = [
        r
        for r in receipts
        if r[0] == issued
        and (r[2].source_url, r[2].sha256) == (forecast.source_url, forecast.sha256)
    ]
    first_fetch = min(r[2].fetched_at for r in cohort)
    available = min(r[1] for r in cohort)
    if available < first_fetch:
        raise IngestError("Weather availability precedes retrieval")
    row = next(
        (row for row in sorted(rows, key=lambda r: r["valid_at"]) if usable(row, as_of)), None
    )
    if row is None or available > as_of:
        raise SourceUnavailable("S01: no quality-passed future temperature at this cutoff")
    record = {
        "id": row["record_id"],
        "title": "ECMWF IFS temperature — Bengaluru grid cell",
        "source_id": "S01",
        "source_url": row["source_url"],
        "provenance": "model",
        "kind": "weather",
        "spatial_scope": "point",
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "issued_at": utc(issued),
        "valid_at": utc(row["valid_at"]),
        "fetched_at": utc(first_fetch),
        "available_at": utc(available),
        "expires_at": None,
        "severity": None,
        "value": row["temperature_c"],
        "unit": location["hourly_units"]["temperature_2m"],
        "missing_reason": None,
        "evidence": "forecast",
        "location_note": "ECMWF IFS 0.25-degree model grid-cell centre; not a station observation.",
    }
    manifest = canonical(
        {
            "schema_version": 1,
            "mapping_version": "s01-prepared-v1",
            "source_id": "S01",
            "state": "ka",
            "as_of": utc(as_of),
            "coverage": "partial",
            "inputs": inputs,
        }
    )
    revision = hashlib.sha256(manifest.encode()).hexdigest()
    envelope = {
        "source_id": "S01",
        "snapshot": {
            "schema_version": 1,
            "state": "ka",
            "release_id": f"S01-{revision[:20]}",
            "data_revision": revision,
            "as_of": utc(as_of),
            "records": [record],
            "places": [],
            "facilities": [],
            "sources": [
                {
                    "source_id": "S01",
                    "status": "partial",
                    "last_success_at": utc(max(r[1] for r in cohort)),
                    "detail": (
                        "Single-point Bengaluru model-grid temperature only; "
                        "statewide coverage is unverified."
                    ),
                }
            ],
        },
    }
    return materialize(
        root,
        output_root,
        as_of=as_of,
        max_bytes=max_bytes,
        manifest=manifest,
        envelope=envelope,
        inputs=inputs,
        verify_inputs=verify_retained_inputs,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".cache/feeds")
    args = parser.parse_args()
    print(json.dumps(prepare_weather(args.root, as_of=datetime.now(UTC))))


if __name__ == "__main__":
    main()
