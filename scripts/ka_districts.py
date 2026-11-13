"""D209: simplified outlines of the 30 Karnataka districts for the Overview 3D map.

Reads the local S17 geoBoundaries IND ADM2 file (ODbL; the same boundary version as
configs/static/ka/places.json), keeps the 30 Karnataka place IDs, simplifies each outline
(about 1 km) and writes web/src/ka-districts.json. Run once after the boundary version changes:
    .venv/Scripts/python scripts/ka_districts.py
"""

from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]
RAW = (
    ROOT
    / "data/raw/S17/2026-11-05/8bef6929fd65432e7dc775e7c44473e84efff064ebddbfd6b834e6291546db40.bin"
)
OUT = ROOT / "web/src/ka-districts.json"
TOLERANCE = 0.01  # degrees, about 1 km: outlines stay recognisable at state zoom


def rounded(value):
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, (list, tuple)):
        return [rounded(v) for v in value]
    return value


def build() -> dict:
    places = json.loads((ROOT / "configs/static/ka/places.json").read_text("utf-8"))["rows"]
    wanted = {p["place_id"]: p["name"] for p in places}
    source = json.loads(RAW.read_text("utf-8"))
    features = []
    for f in source["features"]:
        pid = "gb-IND-ADM2-" + f["properties"]["shapeID"]  # place_id prefix (S17 adapter)
        if pid not in wanted:
            continue
        geom = shape(f["geometry"]).simplify(TOLERANCE, preserve_topology=True)
        features.append(
            {
                "type": "Feature",
                "properties": {"place_id": pid, "name": wanted[pid]},
                "geometry": {
                    "type": geom.geom_type,
                    "coordinates": rounded(mapping(geom)["coordinates"]),
                },
            }
        )
    assert len(features) == len(wanted) == 30, len(features)
    features.sort(key=lambda f: f["properties"]["name"])
    return {
        "type": "FeatureCollection",
        "attribution": "District outlines: geoBoundaries IND ADM2 (ODbL), simplified about 1 km",
        "boundary_version": places[0]["boundary_version"],
        "features": features,
    }


if __name__ == "__main__":
    text = json.dumps(build(), separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(text) // 1024} KB")
