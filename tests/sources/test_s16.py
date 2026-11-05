"""T018 acceptance: the S16 adapter keeps native WorldPop cells inside the S17 state polygon, so
the state total equals an independent masked sum (counts conserved); malformed, empty and
changed files fail; a disabled source fails closed. Needs rasterio (geo lock) and local raw."""

import json
from datetime import UTC, datetime
from functools import cache
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s16 import HOSTS, S16

rasterio = pytest.importorskip("rasterio")

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S16")


def artifact(source: str, eid: str, path: Path | None = None) -> RawArtifact:
    manifest = json.loads((ROOT / f"tests/fixtures/{source}/manifest.json").read_text("utf-8"))
    e = next(x for x in manifest["evidence"] if x["id"] == eid)
    real = RAW / e["raw_path"]
    if path is None and not real.exists():
        pytest.skip("raw evidence is local only")
    return RawArtifact(
        sha256=e["sha256"],
        path=path or real,
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="s16-v1",
    )


def boundary() -> RawArtifact:
    return artifact("s17", "e05")  # S17 ADM1 simplified GeoJSON


@cache
def karnataka_2025():
    return S16("ka", 2025).parse(artifact("s16", "e05"), CONFIG, boundary=boundary())


def test_roundtrip_and_counts_are_conserved(tmp_path):
    from rasterio.features import geometry_mask

    table = karnataka_2025()
    pq.write_table(table, tmp_path / "s16.parquet")
    back = pq.read_table(tmp_path / "s16.parquet")
    assert back.equals(table)
    validate_table(back, measures=["population"])
    assert back.num_rows == 203_344 and len(set(back["cell_id"].to_pylist())) == 203_344
    assert set(back["raster_id"].to_pylist()) == {"WP00840-R2025A-2025-IND-1km"}
    total = sum(back["population"].to_pylist())

    shape = next(
        f["geometry"]
        for f in json.loads(boundary().path.read_text("utf-8"))["features"]
        if f["properties"]["shapeISO"] == "IN-KA"
    )
    with rasterio.open(
        artifact("s16", "e05").path
    ) as src:  # whole raster, independent of the window
        data = src.read(1)
        keep = ~geometry_mask([shape], data.shape, src.transform) & (data != src.nodata)
    assert abs(float(data[keep].astype("float64").sum()) - total) < 1e-3
    assert 60e6 < total < 80e6  # Karnataka, 2025


def test_malformed_empty_and_changed_rejected(tmp_path):
    good = artifact("s16", "e05")
    broken = tmp_path / "broken.tif"
    broken.write_bytes(good.path.read_bytes()[:4096])
    empty = tmp_path / "empty.tif"
    empty.write_bytes(b"")
    for path in (broken, empty):
        with pytest.raises(IngestError):
            S16("ka", 2025).parse(artifact("s16", "e05", path), CONFIG, boundary=boundary())
    renamed = good.model_copy(update={"source_url": "https://data.worldpop.org/other/file.tif"})
    with pytest.raises(IngestError, match="unexpected file URL"):
        S16("ka", 2025).parse(renamed, CONFIG, boundary=boundary())
    with pytest.raises(IngestError, match="boundary"):
        S16("ka", 2025).parse(good, CONFIG)


def test_disabled_source_fails_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        S16("ka", 2025).parse(artifact("s16", "e05"), off, boundary=boundary())


def test_fetch_follows_the_catalogue_link(tmp_path):
    listing, tif = (
        artifact("s16", "e03").path.read_bytes(),
        artifact("s16", "e05").path.read_bytes(),
    )
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        body, kind = (
            (tif, "image/tiff")
            if request.url.path.endswith(".tif")
            else (listing, "application/json")
        )
        return httpx.Response(200, content=body, headers={"content-type": kind})

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S16",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=3, max_bytes=40 * 1024**2),
        raw_root=tmp_path,
    )
    _, raw = S16("ka", 2025, fetcher).fetch(ctx)
    assert seen[0].endswith("G2_CN_POP_R25A_1km?iso3=IND")
    assert seen[1].endswith(
        "/R2025A/2025/IND/v1/1km_ua/constrained/ind_pop_2025_CN_1km_R2025A_UA_v1.tif"
    )
    assert raw.sha256 == artifact("s16", "e05").sha256
