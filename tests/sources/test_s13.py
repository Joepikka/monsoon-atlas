"""T066 acceptance: the S13 adapter picks the newest listed, non-blank imagery date over the state
from real GIBS evidence (NOAA-20 layer subset of the capabilities and two real tiles, NASA open
data); blank, unlisted, malformed and changed inputs fail; a disabled source fails closed."""

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s13 import CAPABILITIES, HOSTS, MEASURES, S13, _layer, listed_dates, tile_index

pytest.importorskip("PIL")  # blank-tile check needs pillow (geo lock, D35)

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
CAPS = FIX / "s13_gibs_capabilities_noaa20_2026-11-09.xml"  # T065 e06, NOAA-20 layer only
TILE_8 = FIX / "s13_gibs_noaa20_bengaluru_z6_2026-11-08.jpeg"  # T065 e07, imagery with cloud
TILE_9 = FIX / "s13_gibs_noaa20_bengaluru_z6_2026-11-09_blank.jpeg"  # T065 e08, all black
FETCHED = datetime(2026, 11, 9, 7, 39, 24, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S13")
ADAPTER = S13("ka", (12.97, 77.59))


def artifact(path: Path, url: str) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/octet-stream",
        response_status=200,
        source_url=url,
        schema_mapping_version="s13-v1",
    )


def tile(path: Path, day: str) -> RawArtifact:
    layer = _layer(artifact(CAPS, CAPABILITIES))
    return artifact(path, ADAPTER.tile_url(layer, date.fromisoformat(day)))


def test_tile_index_and_listed_dates():
    assert tile_index(12.97, 77.59) == (29, 45)  # T065 e07/e08
    layer = _layer(artifact(CAPS, CAPABILITIES))
    assert listed_dates(layer, 3) == [date(2026, 11, 9), date(2026, 11, 8), date(2026, 11, 7)]
    assert date(2022, 1, 13) not in listed_dates(layer, 10_000)  # a gap between ranges


def test_roundtrip_records_layer_date_template_and_bounds(tmp_path):
    table = ADAPTER.parse(artifact(CAPS, CAPABILITIES), CONFIG, tile=tile(TILE_8, "2026-11-08"))
    pq.write_table(table, tmp_path / "s13.parquet")
    back = pq.read_table(tmp_path / "s13.parquet")
    assert back.equals(table)
    validate_table(back)
    assert read_mapping(back)["provider_to_canonical"]["ResourceURL@template"] == "tile_template"
    row = back.to_pylist()[0]
    assert (row["layer_id"], row["imagery_date"], row["crs"]) == (
        "VIIRS_NOAA20_CorrectedReflectance_TrueColor",
        date(2026, 11, 8),
        "EPSG:3857",
    )
    assert row["tile_template"].endswith(
        "/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg"
    )
    assert row["bounds"] == "-180 -85.051129 180 85.051129"
    assert row["valid_at"] == datetime(2026, 11, 9, tzinfo=UTC)
    assert row["source_url"].endswith("/2026-11-08/GoogleMapsCompatible_Level9/6/29/45.jpeg")


def test_blank_or_unlisted_tile_is_not_imagery():
    caps = artifact(CAPS, CAPABILITIES)
    with pytest.raises(IngestError, match="blank"):
        ADAPTER.parse(caps, CONFIG, tile=tile(TILE_9, "2026-11-09"))
    with pytest.raises(IngestError, match="not a listed date"):
        ADAPTER.parse(caps, CONFIG, tile=tile(TILE_8, "2022-01-13"))
    with pytest.raises(IngestError, match="unknown"):
        ADAPTER.parse(caps, CONFIG)


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s13.json").read_text("utf-8"))
    names = {"string": "string", "date32[day]": "date32"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


@pytest.mark.parametrize(
    "body",
    [b"<Capabilities", CAPS.read_bytes().replace(b"VIIRS_NOAA20", b"VIIRS_OTHER")],
    ids=["malformed", "layer missing"],
)
def test_malformed_or_changed_capabilities_rejected(tmp_path, body):
    bad = tmp_path / "caps.xml"
    bad.write_bytes(body)
    with pytest.raises(IngestError):
        ADAPTER.parse(artifact(bad, CAPABILITIES), CONFIG, tile=tile(TILE_8, "2026-11-08"))


def test_disabled_source_fails_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(CAPS, CAPABILITIES), off, tile=tile(TILE_8, "2026-11-08"))


def run_fetch(tmp_path, tiles: dict[str, bytes]):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        seen.append(url)
        if url == CAPABILITIES:
            return httpx.Response(200, content=CAPS.read_bytes())
        day = url.split("/default/")[1].split("/")[0]
        return httpx.Response(200, content=tiles[day], headers={"content-type": "image/jpeg"})

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S13",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=6, max_bytes=8 * 1024**2),
        raw_root=tmp_path,
    )
    return S13("ka", (12.97, 77.59), fetcher).fetch(ctx), seen


def test_fetch_skips_the_blank_default_date(tmp_path):
    tiles = {"2026-11-09": TILE_9.read_bytes(), "2026-11-08": TILE_8.read_bytes()}
    (caps, probe), seen = run_fetch(tmp_path, tiles)
    assert len(seen) == 3 and "/2026-11-09/" in seen[1] and "/2026-11-08/" in seen[2]
    assert ADAPTER.parse(caps, CONFIG, tile=probe)["imagery_date"][0].as_py() == date(2026, 11, 8)


def test_fetch_fails_when_every_probe_is_blank(tmp_path):
    blank = TILE_9.read_bytes()
    with pytest.raises(IngestError, match="all blank"):
        run_fetch(tmp_path, {d: blank for d in ("2026-11-09", "2026-11-08", "2026-11-07")})
