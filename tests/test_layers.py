"""T039 acceptance: real forecast projection, source clocks, layers and browser controls."""

import hashlib
import json
from pathlib import Path

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.discovery import load_manifest
from atlas.ingest.s01 import S01

ROOT = Path(__file__).resolve().parents[1]


def test_forecast_fixture_preserves_source_value_units_grid_and_times():
    path = ROOT / "web/tests/fixtures/openmeteo-temperature-point.json"
    assert path.exists(), "T039 source fixture missing"
    record = json.loads(path.read_text("utf-8"))
    provenance = json.loads(path.with_suffix(".provenance.json").read_text("utf-8"))
    for name, sha in provenance["source_files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    evidence = {e.id: e for e in load_manifest(ROOT / "tests/fixtures/s01/manifest.json").evidence}

    def artifact(eid, filename):
        item = evidence[eid]
        return RawArtifact(
            sha256=item.sha256,
            path=ROOT / "tests/fixtures" / filename,
            fetched_at=item.fetched_at,
            media_type=item.media_type,
            response_status=200,
            source_url=item.url,
            schema_mapping_version="s01-v1",
        )

    raw = artifact("e08", "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json")
    meta = artifact("e09", "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json")
    table = S01("ka", [(12.97, 77.59)]).parse(
        raw,
        load_state(ROOT / "configs/states/ka.yaml").source("S01"),
        meta=meta,
    )
    row = next(row for row in table.to_pylist() if row["record_id"] == record["id"])
    source = json.loads(raw.path.read_text("utf-8"))
    assert record["provenance"] == row["provenance"] == "model"
    assert record["value"] == row["temperature_c"]
    assert record["unit"] == source["hourly_units"]["temperature_2m"]
    assert (record["longitude"], record["latitude"]) == (source["longitude"], source["latitude"])
    assert record["source_url"] == row["source_url"]
    for field in ("issued_at", "valid_at", "fetched_at", "available_at"):
        assert record[field] == row[field].isoformat().replace("+00:00", "Z")


def test_layer_contracts_and_browser_controls(web_check):
    web_check("run", "build")
    web_check("run", "test", "--", "src/map/Layers.test.ts")
    web_check("run", "test:e2e", "--", "layers.spec.ts")
