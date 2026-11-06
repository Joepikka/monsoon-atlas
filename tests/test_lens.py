"""T040: source-backed places, frozen reports and browser-generated print views."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.discovery import load_manifest
from atlas.ingest.s17 import S17

ROOT = Path(__file__).resolve().parents[1]
PLACE = ROOT / "web/tests/fixtures/bangalore-place.json"


def test_place_fixture_cites_actual_versioned_source_evidence():
    place = json.loads(PLACE.read_text("utf-8"))
    provenance = json.loads(PLACE.with_suffix(".provenance.json").read_text("utf-8"))
    evidence = {e.id: e for e in load_manifest(ROOT / "tests/fixtures/s17/manifest.json").evidence}
    assert provenance["test_only"] is True
    assert place["source_id"] == provenance["source_id"] == "S17"
    assert place["kind"] == "district"
    assert not place["place_id"].startswith("h3:")
    assert place["source_url"] == evidence["e06"].url
    for eid, item in provenance["source_evidence"].items():
        assert item["sha256"] == evidence[eid].sha256
        assert item["url"] == evidence[eid].url
        assert item["raw_path"] == evidence[eid].raw_path


def test_print_warning_text_preserves_original_english_cap():
    ns = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
    raw = ET.fromstring((ROOT / "tests/fixtures/s09_sachet_cap_1793881986295019.xml").read_bytes())
    info = next(
        info
        for info in raw.findall("cap:info", ns)
        if info.findtext("cap:language", "", ns) == "en-IN"
    )
    record = json.loads((ROOT / "web/tests/fixtures/sachet-ka-point.json").read_text("utf-8"))
    assert record["warning_text"] == info.findtext("cap:headline", namespaces=ns)
    assert record["instruction"] == info.findtext("cap:instruction", namespaces=ns)


def test_place_fixture_matches_adapter_and_original_geometry():
    shapely = pytest.importorskip("shapely")
    provenance = json.loads(PLACE.with_suffix(".provenance.json").read_text("utf-8"))
    evidence = {e.id: e for e in load_manifest(ROOT / "tests/fixtures/s17/manifest.json").evidence}

    def artifact(eid):
        item = evidence[eid]
        path = ROOT / "data/raw" / item.raw_path
        if not path.exists():
            pytest.skip("Optional original S17 boundary files are not installed in core CI")
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest()
            == provenance["source_evidence"][eid]["sha256"]
        )
        return RawArtifact(
            sha256=item.sha256,
            path=path,
            fetched_at=item.fetched_at,
            media_type=item.media_type,
            response_status=item.status,
            source_url=item.url,
            schema_mapping_version="s17-v1",
        )

    place = json.loads(PLACE.read_text("utf-8"))
    rows = S17("ka").parse(
        artifact("e06"),
        load_state(ROOT / "configs/states/ka.yaml").source("S17"),
        adm1=artifact("e05"),
    )
    row = next(row for row in rows.to_pylist() if row["place_id"] == place["place_id"])
    point = shapely.from_wkb(row["geometry"]).representative_point()
    assert (place["longitude"], place["latitude"]) == (round(point.x, 6), round(point.y, 6))
    for field in ("place_id", "name", "boundary_version", "source_id", "source_url", "licence_id"):
        assert place[field] == row[field]


def test_place_lens_frozen_urls_distances_and_print_browser(web_check):
    web_check("run", "build")
    web_check("run", "test", "--", "src/report.test.ts")
    web_check("run", "test:e2e", "--", "lens.spec.ts")
