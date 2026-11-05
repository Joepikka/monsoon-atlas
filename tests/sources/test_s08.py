"""T058 acceptance: the S08 adapter round trip preserves units, IDs and source timestamps on the
real 2024 year file; malformed, empty and changed files fail; a disabled source fails closed.
Raw year files are local only (IMD forbids reproduction), so real-file tests skip in CI."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest import s08 as s08_mod
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s08 import MEASURES, S08

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S08")
CELLS = 540  # land cells in the Karnataka box 11.5-18.5N, 74-78.75E


def artifact(eid: str, path: Path | None = None) -> RawArtifact:
    manifest = json.loads((ROOT / "tests/fixtures/s08/manifest.json").read_text("utf-8"))
    e = next(e for e in manifest["evidence"] if e["id"] == eid)
    real = RAW / e["raw_path"]
    if path is None and not real.exists():
        pytest.skip("raw year files are local only (not redistributed)")
    return RawArtifact(
        sha256=e["sha256"],
        path=path or real,
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="discovery",
    )


def edited_copy(tmp_path: Path, eid: str, edit) -> RawArtifact:
    grid = np.fromfile(artifact(eid).path, dtype="<f4").copy()
    out = tmp_path / f"{eid}.grd"
    edit(grid).tofile(out)
    return artifact(eid, out)


def test_roundtrip_preserves_units_ids_and_timestamps(tmp_path):
    raw = artifact("e04")  # 2024, 366 days
    table = S08("ka", [2024]).parse(raw, CONFIG)
    pq.write_table(table, tmp_path / "s08.parquet")
    back = pq.read_table(tmp_path / "s08.parquet")
    assert back.equals(table) and back.schema.equals(table.schema)
    validate_table(back, measures=["rain_mm"])
    assert read_mapping(back)["provider_to_canonical"]["rf"] == "rain_mm"
    assert back.num_rows == CELLS * 366
    assert len(set(back["record_id"].to_pylist())) == back.num_rows
    assert set(back["fetched_at"].to_pylist()) == {raw.fetched_at}
    assert set(back["raw_sha256"].to_pylist()) == {raw.sha256}
    assert set(back["grid_resolution_deg"].to_pylist()) == {0.25}
    rows = back.filter(pc.equal(back["cell_id"], "imd025_13.00N_77.50E"))  # Bengaluru cell
    assert round(sum(rows["rain_mm"].to_pylist()), 1) == 990.0  # T057 total, read independently


def test_valid_at_is_the_latest_possible_end_of_the_day():
    table = S08("ka", [2024]).parse(artifact("e04"), CONFIG)
    first = table.slice(0, 1).to_pylist()[0]
    assert first["date_local"] == date(2024, 1, 1)
    assert first["valid_at"] == datetime(2024, 1, 2, 3, tzinfo=UTC)  # 08:30 IST next day
    last = table.slice(table.num_rows - 1, 1).to_pylist()[0]
    assert last["valid_at"] - timedelta(hours=27) == datetime(2024, 12, 31, tzinfo=UTC)


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s08.json").read_text("utf-8"))
    assert [(f["name"], str(f["type"]), f["nullable"]) for f in spec["fields"]] == [
        (
            f.name,
            str(f.type).replace("double", "float64").replace("date32[day]", "date32"),
            f.nullable,
        )
        for f in MEASURES
    ]


def test_negative_value_becomes_null_with_reason(tmp_path):
    def poison(grid):
        g = grid.reshape(366, 129, 135)
        g[0, round((13.0 - 6.5) / 0.25), round((77.5 - 66.5) / 0.25)] = -5.0
        return g

    table = S08("ka", [2024]).parse(edited_copy(tmp_path, "e04", poison), CONFIG)
    bad = table.filter(pc.equal(table["missing_reason"], "quality_rejected")).to_pylist()
    assert len(bad) == 1 and bad[0]["rain_mm"] is None
    assert bad[0]["quality_flags"] == ["out_of_range"] and bad[0]["date_local"] == date(2024, 1, 1)


def test_malformed_copy_rejected(tmp_path):
    raw = edited_copy(tmp_path, "e04", lambda g: g[: -129 * 135])  # one day short
    with pytest.raises(IngestError, match="expected 366 days"):
        S08("ka", [2024]).parse(raw, CONFIG)


def test_changed_land_mask_rejected(tmp_path):
    def hole(grid):
        g = grid.reshape(366, 129, 135)
        g[100, round((13.0 - 6.5) / 0.25), round((77.5 - 66.5) / 0.25)] = -999.0
        return g

    with pytest.raises(IngestError, match="land mask"):
        S08("ka", [2024]).parse(edited_copy(tmp_path, "e04", hole), CONFIG)


def test_empty_response_rejected(tmp_path):
    empty = tmp_path / "empty.grd"
    empty.write_bytes(b"")
    with pytest.raises(IngestError, match="0 bytes"):
        S08("ka", [2024]).parse(artifact("e04", empty), CONFIG)


def test_disabled_source_fails_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        S08("ka", [2024]).parse(artifact("e04", ROOT / "README.md"), off)
    with pytest.raises(SourceUnavailable):
        S08("kl", [2024])  # no cell box yet: Kerala is added in P3


def test_fetch_requests_each_year_and_parses(tmp_path, monkeypatch):
    body = artifact("e04").path.read_bytes()
    seen = []

    def serve(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200, content=body, headers={"content-type": "application/octet-stream"}
        )

    monkeypatch.setattr(s08_mod.time, "sleep", lambda s: None)
    fetcher = Fetcher(RawStore(tmp_path), s08_mod.HOSTS, transport=httpx.MockTransport(serve))
    ctx = FetchContext(
        source_id="S08",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=4, max_bytes=60 * 1024**2),
        raw_root=tmp_path,
    )
    (raw,) = S08("ka", [2024], fetcher).fetch(ctx)
    assert seen == ["https://www.imdpune.gov.in/cmpg/Griddata/rainfall.php?rain=2024"]
    assert S08("ka", [2024]).parse(raw, CONFIG).num_rows == CELLS * 366
