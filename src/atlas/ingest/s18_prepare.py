"""S18 facilities for the Place Lens Nearby tab (F025, D175).

Turns S18 adapter rows into the browser's Facility shape: hospitals, police and fire stations only,
the nearest PER_KIND of each kind within MAX_KM of every place's representative point, so a state
release stays far below the one-megabyte snapshot limit. OSM `amenity=shelter` is left out: it
mostly marks bus and rain shelters, and no emergency-shelter status may be inferred from OSM (S43
holds official shelters). Names come from OSM; an unnamed object says so. Distances are
great-circle, as in the browser. Nothing here publishes: T045 adds the list to a release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa

KINDS = ("hospital", "police", "fire_station")
MAX_KM, PER_KIND = 25.0, 10
LABEL = {"hospital": "hospital", "police": "police station", "fire_station": "fire station"}
ROOT = Path(__file__).resolve().parents[3]


def km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def _name(tags: dict, kind: str) -> str:
    name = (tags.get("name:en") or tags.get("name") or "").strip()
    return name[:200] if name else f"Unnamed {LABEL[kind]} (OpenStreetMap)"


def facilities(table: pa.Table, places: list[dict]) -> list[dict]:
    """Facility rows near any place; `places` items carry longitude and latitude."""
    import shapely

    candidates = []
    for row in table.to_pylist():
        if row["feature_kind"] not in KINDS:
            continue
        point = shapely.from_wkb(row["geometry"]).centroid  # a way's outline gives its centre
        candidates.append((row, round(point.x, 6), round(point.y, 6)))
    keep: dict[str, dict] = {}
    for place in places:
        lon, lat = place["longitude"], place["latitude"]
        for kind in KINDS:
            near = sorted(
                (
                    (d, row, x, y)
                    for row, x, y in candidates
                    if row["feature_kind"] == kind and (d := km(lon, lat, x, y)) <= MAX_KM
                ),
                key=lambda t: (t[0], t[1]["osm_type"], t[1]["osm_id"]),  # ties: stable by id
            )
            for _d, row, x, y in near[:PER_KIND]:
                fid = f"osm:{row['osm_type']}:{row['osm_id']}"
                keep[fid] = {
                    "facility_id": fid,
                    "kind": kind,
                    "name": _name(json.loads(row["tags_json"]), kind),
                    "longitude": x,
                    "latitude": y,
                    "source_id": "S18",
                    "source_url": f"https://www.openstreetmap.org/{row['osm_type']}/{row['osm_id']}",
                    "fetched_at": row["fetched_at"]
                    .astimezone(UTC)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "verification_status": "source_checked",  # T021 passed on this extract
                }
    return [keep[k] for k in sorted(keep)]


def district_points(districts: pa.Table) -> list[dict]:
    """Representative points (inside each polygon) of S17 district rows."""
    import shapely

    out = []
    for row in districts.to_pylist():
        p = shapely.point_on_surface(shapely.from_wkb(row["geometry"]))
        out.append({"place_id": row["place_id"], "longitude": p.x, "latitude": p.y})
    return out


def main(argv: list[str] | None = None) -> Path:
    """Write data/prepared/S18/<state>/facilities-<sha12>.json from the local evidence."""
    import pyarrow.compute as pc
    import shapely

    from atlas.config import load_state
    from atlas.contracts import RawArtifact
    from atlas.ingest.discovery import load_manifest
    from atlas.ingest.s17 import S17
    from atlas.ingest.s18 import S18, owner_file

    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="ka")
    args = parser.parse_args(argv)
    raw = ROOT / "data" / "raw"
    state = load_state(ROOT / "configs" / "states" / f"{args.state}.yaml")

    def evidence(sid: str, eid: str) -> RawArtifact:
        e = next(
            x
            for x in load_manifest(ROOT / "tests" / "fixtures" / sid / "manifest.json").evidence
            if x.id == eid
        )
        path = raw / e.raw_path
        if sid == "s18":
            return owner_file(path, e.url, e.fetched_at)
        return RawArtifact(
            sha256=e.sha256,
            path=path,
            fetched_at=e.fetched_at,
            media_type=e.media_type,
            response_status=e.status,
            source_url=e.url,
            schema_mapping_version="s17-v1",
        )

    districts = S17(args.state).parse(
        evidence("s17", "e06"), state.source("S17"), adm1=evidence("s17", "e05")
    )
    area = shapely.union_all(shapely.from_wkb(districts["geometry"].to_pylist()))
    pbf = evidence("s18", "e05")
    adapter = S18(args.state, shapely.to_wkb(area))
    tables = [
        t.filter(pc.is_in(t["feature_kind"], pa.array(KINDS)))
        for t in adapter.parse_batches(pbf, state.source("S18"))
    ]
    rows = facilities(pa.concat_tables(tables), district_points(districts))
    body = {
        "schema_version": 1,
        "state": args.state,
        "source_id": "S18",
        "input_sha256": pbf.sha256,
        "prepared_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "rule": f"nearest {PER_KIND} per kind within {MAX_KM:g} km of each S17 district point",
        "facilities": rows,
    }
    text = json.dumps(body, ensure_ascii=False, indent=1) + "\n"
    digest = hashlib.sha256(text.encode()).hexdigest()
    out = ROOT / "data" / "prepared" / "S18" / args.state / f"facilities-{digest[:12]}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"written": str(out), "facilities": len(rows), "bytes": len(text)}))
    return out


if __name__ == "__main__":
    main()
