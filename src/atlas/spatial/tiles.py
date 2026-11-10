"""T185: the parts of the PMTiles city-layer build that run without Tippecanoe (D151).

Tippecanoe runs only in Linux CI (`.github/workflows/tiles.yml`). Here: a layer is clipped to one
versioned boundary before tiling (the T105 clipper, not a second one), only sources whose licence
is open and whose credit is registered may enter a tile build, features are planned into shards
below the 20 MiB cap, and delivery defaults to the smaller GeoJSON unless a hosted PMTiles probe
returned HTTP 206 with a CORS header. Reading tiles back from an archive is not built: no archive
exists yet.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from atlas.ingest.base import SourceUnavailable
from atlas.spatial.context import _discovery, buildings_in_place

TIPPECANOE_VERSION = "2.79.0"
SHARD_CAP = 20 * 1024 * 1024  # bytes per PMTiles archive (plan T185)
RESERVE = 1024 * 1024  # planning margin for the header, directories and metadata
ATTRIBUTION = {"S19": "Google Research Open Buildings v3 (CC BY 4.0)"}


def require_tile_source(source_id: str) -> str:
    """The credit line for a source that may be redistributed in tiles, else SourceUnavailable."""
    d = _discovery(source_id)
    if d["outcome"] != "available" or d["licence"]["status"] != "open":
        raise SourceUnavailable(
            f"{source_id} cannot enter a tile build: outcome {d['outcome']}, "
            f"licence {d['licence']['status']}"
        )
    if source_id not in ATTRIBUTION:
        raise SourceUnavailable(f"{source_id} has no registered attribution for tiles")
    return ATTRIBUTION[source_id]


def clipped_buildings(buildings, place: dict, *, boundary_version: str) -> dict:
    """S19 footprints (confidence 0.75 or more) clipped to the place, as a GeoJSON collection."""
    credit = require_tile_source("S19")
    features = buildings_in_place(buildings, place, boundary_version=boundary_version)
    for f in features:
        f["properties"]["attribution"] = credit
    return {"type": "FeatureCollection", "attribution": credit, "features": features}


def plan_shards(
    sizes: Sequence[tuple[str, int]], cap: int = SHARD_CAP, reserve: int = RESERVE
) -> list[list[str]]:
    """Pack (id, source bytes) in order into shards whose sum stays within cap minus reserve.

    shortcut: source bytes only bound the archive size roughly; the real check is
    `check_shard_sizes` on the built files.
    """
    limit = cap - reserve
    shards: list[list[str]] = []
    used = limit + 1
    for key, size in sizes:
        if size > limit:
            raise ValueError(f"{key} alone ({size} bytes) exceeds a shard ({limit} bytes)")
        if used + size > limit:
            shards.append([])
            used = 0
        shards[-1].append(key)
        used += size
    return shards


def shard_collection(collection: dict, cap: int = SHARD_CAP, reserve: int = RESERVE) -> list[dict]:
    """Split a feature collection (features carry `building_id`) into collections under the cap."""
    by_id = {f["properties"]["building_id"]: f for f in collection["features"]}
    sizes = [(k, len(json.dumps(f, separators=(",", ":")))) for k, f in by_id.items()]
    return [
        collection | {"features": [by_id[k] for k in shard]}
        for shard in plan_shards(sizes, cap, reserve)
    ]


def check_shard_sizes(paths: Sequence[Path], cap: int = SHARD_CAP) -> None:
    """Fail when any built archive reaches the cap."""
    big = [f"{p.name} ({p.stat().st_size} bytes)" for p in paths if p.stat().st_size >= cap]
    if big:
        raise ValueError(f"over the {cap} byte cap: {', '.join(big)}")


def tippecanoe_args(geojson: Path, out: Path, layer: str, attribution: str, max_zoom: int) -> list:
    """Arguments for one shard. Unverified until the first CI run, since it cannot run here."""
    return [
        "tippecanoe", "-f", "-o", str(out), "-l", layer, "-Z", "0", "-z", str(max_zoom),
        "--attribution", attribution, "--use-attribute-for-id", "building_id", str(geojson),
    ]  # fmt: skip


def delivery(range_status: int | None, allow_origin: str | None, site_origin: str) -> str:
    """'pmtiles' only after a probe saw 206 and a CORS header for the site; else GeoJSON."""
    cors_ok = allow_origin in ("*", site_origin)
    return "pmtiles" if range_status == 206 and cors_ok else "geojson"
