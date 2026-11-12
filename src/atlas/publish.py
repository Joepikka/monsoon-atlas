"""T045: static Karnataka release snapshots and the project-owned JSON API (D185).

One release joins, for one state and cutoff:
- the current S09 and S01 snapshots from the hot Worker (records and source health, as stored);
- S17 district places (representative points inside each boundary, D59);
- S18 facilities (hospitals, police and fire stations near each district, D175).

The release bytes are canonical JSON named by their SHA-256 and never rewritten. A pointer
`data/<state>/latest.json` names the newest release and carries `approval`: "pending" unless the
owner's public-release approval is recorded (H11); the browser refuses a pending pointer. The API
copies are `api/v1/current.json` (the pointer plus source health) and
`api/v1/snapshots/<sha256>.json` (the release bytes). A failed or empty hot fetch raises before any
pointer is written, so a source failure never replaces a good release. Nothing here deploys.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 1024 * 1024  # the browser's snapshot limit (web/src/data.ts)
APPROVALS = ("pending", "approved")
PLACE_NOTE = "Representative point within the source district boundary; not a street address."
PLACE_LICENCE = "odbl-1.0-geoboundaries-pathways"


class PublishError(Exception):
    pass


def utc(t: datetime) -> str:
    return t.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def hot_snapshots(current: dict) -> list[dict]:
    """The Worker's /api/v1/current reply: verified per-source snapshots, S01 and S09 only."""
    sources = current.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PublishError("no hot snapshot is available")
    out = []
    for s in sources:
        if s.get("source_id") not in ("S01", "S09"):
            raise PublishError("unexpected hot source")
        wire = hashlib.sha256(
            json.dumps(
                {"source_id": s["source_id"], "snapshot": s["snapshot"]},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        if wire != s.get("wire_sha256"):
            raise PublishError(f"{s['source_id']} wire digest does not match")
        out.append(s["snapshot"])
    return out


def places(districts: list[dict], source_url: str) -> list[dict]:
    """Browser Place rows from S17 district rows with a representative point."""
    return [
        {
            "place_id": d["place_id"],
            "name": d["name"],
            "kind": "district",
            "state": "ka",
            "boundary_version": d["boundary_version"],
            "longitude": round(d["longitude"], 6),
            "latitude": round(d["latitude"], 6),
            "source_id": "S17",
            "source_url": source_url,
            "licence_id": PLACE_LICENCE,
            "location_note": PLACE_NOTE,
        }
        for d in sorted(districts, key=lambda d: d["place_id"])
    ]


def build_release(
    snapshots: list[dict], place_rows: list[dict], facility_rows: list[dict], now: datetime
) -> dict:
    as_of = utc(now)
    records, health = [], []
    for snap in snapshots:
        records.extend(snap["records"])
        health.extend(snap["sources"])
    records.sort(key=lambda r: (r["source_id"], r["id"]))
    health.sort(key=lambda h: h["source_id"])
    known = [
        f
        for f in facility_rows
        if datetime.fromisoformat(f["fetched_at"].replace("Z", "+00:00")) <= now
    ]
    facilities = known
    body = {
        "schema_version": 1,
        "state": "ka",
        "as_of": as_of,
        "published_at": as_of,
        "records": records,
        "sources": health,
        "places": place_rows,
        "facilities": sorted(facilities, key=lambda f: f["facility_id"]),
    }
    revision = hashlib.sha256(canonical(body)).hexdigest()
    return body | {"release_id": f"ka-{revision[:20]}", "data_revision": revision}


def write_release(out: Path, release: dict, approval: str) -> dict:
    """Immutable release + pointer + API copies; returns the pointer."""
    if approval not in APPROVALS:
        raise PublishError("approval must be pending or approved")
    data = canonical(release)
    if len(data) > MAX_BYTES:
        raise PublishError(f"release is {len(data)} bytes, over the 1 MiB browser limit")
    digest = hashlib.sha256(data).hexdigest()
    state = release["state"]
    files = {
        f"data/{state}/releases/{digest}.json": data,
        f"api/v1/snapshots/{digest}.json": data,
    }
    pointer = {
        "schema_version": 1,
        "state": state,
        "approval": approval,
        "sha256": digest,
        "manifest_url": f"/data/{state}/releases/{digest}.json",
        "as_of": release["as_of"],
    }
    files[f"data/{state}/releases/{digest}.approval.json"] = canonical(pointer)
    files[f"data/{state}/latest.json"] = canonical(pointer)
    files["api/v1/current.json"] = canonical(pointer | {"sources": release["sources"]})
    files["api/v1/openapi.json"] = (ROOT / "docs/api/openapi.json").read_bytes()
    for path, content in files.items():
        p = out / path
        if p.exists() and "/releases/" in path and p.read_bytes() != content:
            raise PublishError(f"immutable {path} would change")
    for path, content in files.items():  # releases first, pointers last
        p = out / path
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(content)
        tmp.replace(p)
    return pointer


STATIC = ROOT / "configs/static/ka"


def write_static_inputs(facilities: Path) -> None:  # pragma: no cover - needs data/raw
    """Committed derived inputs, so CI needs no raw files: S17 district points, S18 facilities."""
    import shapely

    from atlas.config import load_state
    from atlas.ingest.s17 import S17
    from atlas.ingest.s18_prepare import evidence

    state = load_state(ROOT / "configs/states/ka.yaml")
    adm1, adm2 = evidence("s17", "e05"), evidence("s17", "e06")
    districts = []
    for row in S17("ka").parse(adm2, state.source("S17"), adm1=adm1).to_pylist():
        p = shapely.point_on_surface(shapely.from_wkb(row["geometry"]))
        districts.append(row | {"longitude": p.x, "latitude": p.y})
    STATIC.mkdir(parents=True, exist_ok=True)
    note = "Derived from S17 geoBoundaries (ODbL) and S18 OpenStreetMap (ODbL); see D185."
    for name, rows in (
        ("places.json", places(districts, adm2.source_url)),
        ("facilities.json", json.loads(facilities.read_text("utf-8"))["facilities"]),
    ):
        text = json.dumps({"note": note, "rows": rows}, ensure_ascii=False, indent=1) + "\n"
        (STATIC / name).write_text(text, encoding="utf-8", newline="\n")


def archive_release(out: Path, pointer: dict, repo: str, token: str) -> str:  # pragma: no cover
    """Commit the release and pointers to the private HF dataset, then read them back."""
    from atlas.data.hot_export import HfArchive

    archive = HfArchive(repo, token)
    state, digest = pointer["state"], pointer["sha256"]
    paths = [
        f"data/{state}/releases/{digest}.json",
        f"data/{state}/releases/{digest}.approval.json",
        f"data/{state}/latest.json",
        "api/v1/current.json",
    ]
    files = {f"releases/{p}": (out / p).read_bytes() for p in paths}
    revision = archive.commit(files, f"release {digest[:12]} as of {pointer['as_of']}")
    for path, data in files.items():
        if archive.read_at(path, revision) != data:
            raise PublishError(f"read-back of {path} does not match")
    return revision


def write_alert_archive(out: Path, origin: str) -> int:  # pragma: no cover - live Worker
    """data/ka/alerts/archive.json from every stored S09 snapshot (D189)."""
    from atlas.alerts.archive import archive_body, warnings_from_rows
    from atlas.data.hot_export import fetch_new
    from atlas.ingest.upload import signing_key

    key = signing_key(origin)
    with httpx.Client(
        trust_env=False,
        follow_redirects=False,
        timeout=httpx.Timeout(30.0, connect=5.0),
        headers={"User-Agent": "monsoon-atlas-publish/1", "Accept-Encoding": "identity"},
    ) as client:
        rows, _, _ = fetch_new(client, origin, key, {"after_ms": -1, "after_id": ""})
    s09 = [r for r in rows if r["source_id"] == "S09"]
    since = utc(min(r["as_of"] for r in s09)) if s09 else None
    body = archive_body(warnings_from_rows(s09), since, datetime.now(UTC))
    path = out / "data/ka/alerts/archive.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(body))
    return body["count"]


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - needs the live Worker
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", help="hot Worker origin (ATLAS_HOT_ORIGIN)")
    parser.add_argument("--out", type=Path, default=ROOT / ".cache/publish")
    parser.add_argument("--approval", choices=APPROVALS, default="pending")
    parser.add_argument("--hf-repo", help="also archive the release to this private dataset")
    parser.add_argument("--write-static", type=Path, metavar="FACILITIES_JSON")
    parser.add_argument(
        "--alerts", action="store_true", help="add the warning archive (signed Worker export)"
    )
    args = parser.parse_args(argv)
    if args.write_static:
        write_static_inputs(args.write_static)
        print(json.dumps({"status": "static_written", "dir": str(STATIC)}))
        return 0
    try:
        if not args.origin:
            raise PublishError("--origin is required")
        with httpx.Client(
            timeout=30,
            trust_env=False,
            follow_redirects=False,
            headers={"User-Agent": "monsoon-atlas-publish/1"},
        ) as client:
            r = client.get(args.origin + "/api/v1/current", params={"state": "ka"})
        if r.status_code != 200:
            raise PublishError(f"hot Worker returned HTTP {r.status_code}")
        snaps = hot_snapshots(r.json())
        place_rows = json.loads((STATIC / "places.json").read_text("utf-8"))["rows"]
        facility_rows = json.loads((STATIC / "facilities.json").read_text("utf-8"))["rows"]
        release = build_release(snaps, place_rows, facility_rows, datetime.now(UTC))
        pointer = write_release(args.out, release, args.approval)
        result = {"status": "published_locally", **pointer, "bytes": len(canonical(release))}
        if args.alerts:
            result["alerts"] = write_alert_archive(args.out, args.origin)
        if args.hf_repo:
            result["archive_revision"] = archive_release(
                args.out, pointer, args.hf_repo, os.environ["HF_TOKEN"]
            )
    except Exception as error:  # noqa: BLE001 - one bounded report; logs are public (D184)
        detail = str(error)[:200] if isinstance(error, PublishError) else None
        result = {"status": "failed", "error_type": type(error).__name__, "detail": detail}
    print(json.dumps(result))
    return 0 if result["status"] == "published_locally" else 1


if __name__ == "__main__":
    sys.exit(main())
