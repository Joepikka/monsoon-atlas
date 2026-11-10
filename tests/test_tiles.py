"""T186: terrain and globe contract, checked from the source records and component files (D152).

The behaviour (world wrap, exaggeration default, missing imagery, WebGL and low-memory fallback,
reduced motion) is tested in web/src/map/Terrain.test.ts and Globe.test.ts. Here the constants
the components carry must equal what the S13, S14 and S15 records and adapters say. Not run: tile
reads against source geometry, because no PMTiles archive exists (D151).
"""

import re
import subprocess
from pathlib import Path

import pytest

from atlas.analysis.prices import load_record
from atlas.config import load_state
from atlas.spatial.tiles import SHARD_CAP

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "web/src/map"
TERRAIN = (MAP / "Terrain.tsx").read_text(encoding="utf-8")
GLOBE = (MAP / "Globe.tsx").read_text(encoding="utf-8")
RECORDS = {
    s: load_record(ROOT / f"configs/sources/{s.lower()}.yaml") for s in ("S13", "S14", "S15")
}


def const(text: str, name: str) -> str:
    return re.search(rf"{name} = '([^']+)'", text).group(1)


def test_the_three_sources_are_enabled_open_and_available():
    state = load_state(ROOT / "configs/states/ka.yaml")
    for source_id, record in RECORDS.items():
        assert state.source(source_id).enabled, source_id
        assert (record["outcome"], record["licence"]["status"]) == ("available", "open")


def test_terrain_tiles_and_encoding_are_the_s14_adapter_ones():
    s14 = (ROOT / "src/atlas/ingest/s14.py").read_text(encoding="utf-8")
    bucket = re.search(r'BUCKET = "([^"]+)"', s14).group(1)
    assert const(TERRAIN, "TERRAIN_TILES") == f"{bucket}/terrarium/{{z}}/{{x}}/{{y}}.png"
    assert "terrarium" in s14 and "encoding: 'terrarium'" in TERRAIN
    assert int(re.search(r"TERRAIN_MAX_ZOOM = (\d+)", TERRAIN).group(1)) == 15
    assert "0 <= z <= 15" in s14
    assert re.search(r"TERRAIN_EXAGGERATION = 1;", TERRAIN)  # the default
    credit = RECORDS["S14"]["licence"]["detail"]
    assert all(name in credit for name in ("Mapzen", "USGS", "NOAA"))
    assert all(name in const(TERRAIN, "TERRAIN_ATTRIBUTION") for name in ("Mapzen", "USGS", "NOAA"))


def test_imagery_matches_the_s13_adapter_and_names_nasa_gibs():
    s13 = (ROOT / "src/atlas/ingest/s13.py").read_text(encoding="utf-8")
    assert re.search(r'MATRIX_SET, ZOOM = "([^"]+)"', s13).group(1) == const(
        TERRAIN, "IMAGERY_MATRIX_SET"
    )
    assert const(TERRAIN, "IMAGERY_HOST") in s13
    assert "NASA GIBS" in RECORDS["S13"]["licence"]["detail"]
    assert "NASA GIBS" in const(TERRAIN, "IMAGERY_ATTRIBUTION")
    assert "VIIRS" in const(TERRAIN, "IMAGERY_ATTRIBUTION")
    assert "new Date" not in TERRAIN and "Date.now" not in TERRAIN  # the date comes from S13 data


def test_only_the_recorded_hosts_are_requested_and_nothing_is_stored_for_later():
    allowed = {"s3.amazonaws.com", "gibs.earthdata.nasa.gov"}
    for text in (TERRAIN, GLOBE):
        hosts = set(re.findall(r"https?://([^/'\"\s{]+)", text))
        assert hosts <= allowed, hosts
        assert not re.search(r"caches|serviceWorker|indexedDB|localStorage|sessionStorage", text)
    assert "tiles.openfreemap.org" not in TERRAIN  # S15 stays MapView's style and credit


def test_a_webgl_failure_shows_a_status_message_that_points_to_the_list():
    assert 'role="status"' in TERRAIN and "Dated records stay available in the list" in TERRAIN
    assert (
        "Globe unavailable in this build" in GLOBE and "Globe unavailable in this build" in TERRAIN
    )
    assert "prefers-reduced-motion: reduce" in TERRAIN


def test_large_file_budget_no_tracked_file_reaches_the_tile_cap():
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    files = [ROOT / p for p in out.split("\0") if p]
    assert not [p for p in files if p.suffix == ".pmtiles"]  # archives are built in CI
    assert [p.name for p in files if p.is_file() and p.stat().st_size >= SHARD_CAP] == []


def test_pmtiles_tile_reads_against_source_geometry_are_not_run():
    pytest.skip("not run: no PMTiles archive exists (D151); retry after tiles.yml builds one")
