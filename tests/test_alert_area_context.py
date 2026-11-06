"""T230: real CAP area-only fallback remains official, readable and unlocated."""

import hashlib
import json
from pathlib import Path

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.discovery import load_manifest
from atlas.ingest.s09 import S09

ROOT = Path(__file__).resolve().parents[1]


def test_area_only_fixture_matches_original_cap_adapter_without_supplemental_geometry():
    path = ROOT / "web/tests/fixtures/sachet-ka-area.json"
    record = json.loads(path.read_text("utf-8"))
    provenance = json.loads(path.with_suffix(".provenance.json").read_text("utf-8"))
    for name, sha in provenance["source_files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    evidence = next(
        e
        for e in load_manifest(ROOT / "tests/fixtures/s09/manifest.json").evidence
        if e.id == "e03"
    )
    raw = RawArtifact(
        sha256=evidence.sha256,
        path=ROOT / "tests/fixtures/s09_sachet_cap_1793881986295019.xml",
        fetched_at=evidence.fetched_at,
        media_type=evidence.media_type,
        response_status=200,
        source_url=evidence.url,
        schema_mapping_version="s09-v1",
    )
    row = (
        S09("ka")
        .parse(raw, load_state(ROOT / "configs/states/ka.yaml").source("S09"))
        .to_pylist()[0]
    )
    assert row["geometry"] is None
    assert record["id"] == row["record_id"]
    assert record["area_text"] == row["area_text"]
    assert record["provenance"] == row["provenance"] == "official"
    assert record["source_url"] == row["source_url"]
    assert record["longitude"] is None and record["latitude"] is None
    for field in ("issued_at", "valid_at", "fetched_at", "available_at", "expires_at"):
        assert record[field] == row[field].isoformat().replace("+00:00", "Z")


def test_area_only_browser_contract(web_check):
    web_check("run", "build")
    web_check("run", "test", "--", "src/area.test.ts")
    web_check("run", "test:e2e", "--", "area.spec.ts")
