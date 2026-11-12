"""T105: context layers (fire hotspots, RERA projects, building footprints, registered crime).

Availability comes from the source contracts: a layer is shown only when its source is enabled,
its discovery outcome is available and its licence is open. Otherwise the web control is disabled
with the recorded reason and the evidence page. A FIRMS hotspot is a satellite thermal anomaly,
never a confirmed (structure) fire; RERA rows keep only the discovery's public fields; building
footprints are clipped to one versioned place boundary; crime is district-year totals of
registered cases, with no map join until a police-unit crosswalk exists (D114).
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import yaml

from atlas.config import load_state
from atlas.ingest.base import SourceUnavailable

ROOT = Path(__file__).resolve().parents[3]
LAYERS = {
    "fire": (
        "S25",
        "Satellite thermal anomalies",
        "A FIRMS hotspot is a satellite-detected thermal anomaly with a confidence and an "
        "acquisition time; it is not a confirmed fire and never a confirmed structure fire.",
    ),
    "rera": (
        "S31",
        "Registered real-estate projects",
        "Public project records only; promoter names and personal contacts are never shown.",
    ),
    "buildings": (
        "S19",
        "Building footprints",
        "Machine-detected footprints (Open Buildings v3, May 2023 imagery) with model confidence, "
        "0.75 or more by default; not a building register.",
    ),
    "crime": (
        "S44",
        "Registered crime, district-year totals",
        "Registered cases, not crime incidence: under-reporting varies by offence, place and "
        "year. Police units are not revenue districts, so the totals are listed, not mapped.",
    ),
}
FIRE_KIND = "thermal_anomaly"
MIN_CONFIDENCE = 0.75
PLACE_KINDS = ("district", "ward", "h3")


def _discovery(source_id: str) -> dict:
    return yaml.safe_load((ROOT / f"configs/sources/{source_id.lower()}.yaml").read_text("utf-8"))


def layer_status(state_file: Path = ROOT / "configs/states/ka.yaml") -> list[dict]:
    """One entry per context layer: available or disabled with the reason and evidence."""
    state = load_state(state_file)
    out = []
    for layer, (source_id, title, note) in LAYERS.items():
        d = _discovery(source_id)
        enabled = state.source(source_id).enabled
        licence = d["licence"]["status"]
        available = enabled and d["outcome"] == "available" and licence == "open"
        if available:
            reason = None
        elif d["outcome"] == "blocked":
            reason = " ".join(d["retry_condition"].split())
        elif licence != "open":
            reason = f"Licence {licence}: waits for the owner's review (H11)."
        else:
            reason = "Source contract not enabled."
        out.append(
            {
                "layer": layer,
                "source_id": source_id,
                "title": title,
                "note": note,
                "available": available,
                "reason": reason,
                "evidence": f"docs/sources/{source_id.lower()}.md",
                "landing_url": d["landing_url"],
            }
        )
    return out


def require(layer: str) -> None:
    status = next(s for s in layer_status() if s["layer"] == layer)
    if not status["available"]:
        raise SourceUnavailable(f"{layer} layer unavailable: {status['reason']}")


def fire_kind(layer_category: str) -> str:
    """Hotspots map only to thermal anomalies; any confirmed-fire category is refused."""
    if layer_category != FIRE_KIND:
        raise ValueError(f"a FIRMS hotspot is a {FIRE_KIND}, never {layer_category!r}")
    return FIRE_KIND


def rera_public(row: dict) -> dict:
    """Keep only the canonical public fields recorded in the S31 discovery (T081)."""
    allowed = {f["canonical"] for f in _discovery("S31")["field_map"]}
    return {k: v for k, v in row.items() if k in allowed}


def buildings_in_place(
    buildings: pa.Table,
    place: dict,
    *,
    boundary_version: str,
    min_confidence: float = MIN_CONFIDENCE,
) -> list[dict]:
    """S19 footprints clipped to one place boundary of the expected version, as GeoJSON features."""
    import shapely

    if set(buildings["source_id"].to_pylist()) - {"S19"}:
        raise ValueError("building footprints come from S19 only")
    if place.get("kind") not in PLACE_KINDS:
        raise ValueError(f"place kind must be one of {PLACE_KINDS}")
    if not place.get("boundary_version") or place["boundary_version"] != boundary_version:
        raise ValueError(
            f"boundary version {place.get('boundary_version')!r} is not {boundary_version!r}"
        )
    versions = set(buildings["boundary_version"].drop_null().to_pylist())
    if versions - {boundary_version}:
        raise ValueError(f"buildings joined to other boundary versions: {sorted(versions)}")
    boundary = shapely.from_wkb(place["geometry"])
    if not boundary.is_valid or boundary.area == 0:
        raise ValueError(f"invalid boundary for {place['place_id']}")
    keep = buildings.filter(pc.greater_equal(buildings["confidence"], min_confidence))
    features = []
    for row in keep.select(
        ["building_id", "source_release", "geometry", "area_m2", "confidence"]
    ).to_pylist():
        clipped = shapely.intersection(shapely.from_wkb(row["geometry"]), boundary)
        if clipped.is_empty or clipped.area == 0:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": shapely.geometry.mapping(clipped),
                "properties": {
                    "building_id": row["building_id"],
                    "source_release": row["source_release"],
                    "confidence": row["confidence"],
                    "area_m2": row["area_m2"],
                    "clipped": not clipped.equals(shapely.from_wkb(row["geometry"])),
                    "place_id": place["place_id"],
                    "boundary_version": boundary_version,
                },
            }
        )
    return features


def crime_totals(table: pa.Table) -> list[dict]:
    """District-year totals of registered cases (published Total column, district units only)."""
    require("crime")
    if set(table["source_id"].to_pylist()) != {"S44"}:
        raise ValueError("crime totals come from S44 only")
    rows = table.filter(
        pc.and_(
            pc.equal(table["unit_kind"], "district"), pc.equal(table["offence_category"], "Total")
        )
    )
    note = LAYERS["crime"][2]
    return [
        r | {"measure": "registered cases", "note": note, "map_join": None}
        for r in rows.select(["district_id", "year", "count"]).to_pylist()
    ]
