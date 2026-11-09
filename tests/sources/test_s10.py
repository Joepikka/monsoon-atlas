"""T060 acceptance: the S10 adapter round trip preserves units, IDs and source timestamps on a
real adsb.lol response (ODbL; callsign, registration and type removed, D108); stale, private and
position-less aircraft are dropped; malformed, empty and changed responses fail; a disabled source
fails closed."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s10 import HOSTS, MEASURES, S10

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "tests" / "fixtures" / "s10_adsb_lol_bengaluru_100nm_2026-11-09.json"  # T059 e10
FETCHED = datetime(2026, 11, 9, 7, 7, 33, 431558, tzinfo=UTC)  # retrieval of the sample (e10)
NOW = datetime(2026, 11, 9, 7, 7, 34, tzinfo=UTC)  # the sample's "now", 1794208054000 ms
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S10")
ADAPTER = S10("ka", (12.97, 77.59))


def artifact(path: Path) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url="https://api.adsb.lol/v2/point/12.97/77.59/100",
        schema_mapping_version="s10-v1",
    )


def edited(tmp_path: Path, edit) -> RawArtifact:
    out = tmp_path / SAMPLE.name
    out.write_text(json.dumps(edit(json.loads(SAMPLE.read_text("utf-8")))), encoding="utf-8")
    return artifact(out)


def parse(raw: RawArtifact):
    return ADAPTER.parse(raw, CONFIG)


def source() -> list[dict]:
    return json.loads(SAMPLE.read_text("utf-8"))["ac"]


def test_roundtrip_preserves_units_ids_and_timestamps(tmp_path):
    table = parse(artifact(SAMPLE))
    pq.write_table(table, tmp_path / "s10.parquet")
    back = pq.read_table(tmp_path / "s10.parquet")
    assert back.equals(table)
    validate_table(back, measures=["lat", "lon"])
    assert read_mapping(back)["provider_to_canonical"]["hex"] == "aircraft_id"
    assert back.num_rows == 20 and len(set(back["record_id"].to_pylist())) == 20
    first, ac = back.slice(0, 1).to_pylist()[0], source()[0]
    assert first["aircraft_id"] == ac["hex"] == "77170d"
    assert first["position_at"] == NOW - timedelta(seconds=ac["seen_pos"])
    assert first["valid_at"] == first["observed_at"] == first["position_at"]
    assert first["published_at"] == NOW and first["available_at"] == FETCHED
    assert first["altitude_m"] == pytest.approx(35000 * 0.3048)
    assert first["speed_ms"] == pytest.approx(476.4 * 1852 / 3600)
    assert (first["lat"], first["lon"]) == (ac["lat"], ac["lon"])
    assert (first["provenance"], first["position_type"], first["on_ground"]) == (
        "inferred",
        "adsb_icao",
        False,
    )


def test_ground_and_unreported_values_stay_null_never_zero():
    table = parse(artifact(SAMPLE))
    rows = table.to_pylist()
    ground = [r for r in rows if r["on_ground"]]
    assert len(ground) == 5 and all(r["altitude_m"] is None for r in ground)
    assert sum(r["speed_ms"] is None for r in rows) == 3
    assert 0.0 not in table["altitude_m"].to_pylist()


def test_private_stale_and_positionless_aircraft_are_dropped(tmp_path):
    def mark(body):
        ac = body["ac"]
        ac[0]["dbFlags"] = 8  # LADD
        ac[1]["dbFlags"] = 4  # PIA
        ac[2]["dbFlags"] = 1  # military only: kept
        ac[3]["seen_pos"] = 301  # stale at fetch
        ac[4].pop("lat")  # no position and no lastPosition
        ac[5].pop("lat")
        ac[5]["lastPosition"] = {"lat": 13.1, "lon": 77.6, "nic": 8, "rc": 186, "seen_pos": 90.0}
        return body

    table = parse(edited(tmp_path, mark))
    ids = table["aircraft_id"].to_pylist()
    hexes = [a["hex"] for a in source()]
    assert table.num_rows == 16 and hexes[2] in ids
    assert not {hexes[0], hexes[1], hexes[3], hexes[4]} & set(ids)
    last = table.to_pylist()[ids.index(hexes[5])]
    assert (last["lat"], last["position_at"]) == (13.1, NOW - timedelta(seconds=90))


def test_no_aircraft_is_an_empty_table_not_an_error(tmp_path):
    table = parse(edited(tmp_path, lambda b: b.update(ac=[], total=0) or b))
    assert table.num_rows == 0 and set(MEASURES.names) <= set(table.column_names)


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s10.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "bool": "bool"}
    names["timestamp[us, tz=UTC]"] = "timestamp"
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_copy_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(SAMPLE.read_bytes()[:500])
    with pytest.raises(IngestError, match="not JSON"):
        parse(artifact(broken))


def test_empty_response_rejected(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    with pytest.raises(IngestError, match="empty"):
        parse(artifact(empty))


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b.update(now=b["now"] // 1000) or b,  # seconds, as the readsb reference says
        lambda b: b["ac"][0].pop("hex") and b,
        lambda b: b["ac"][0].update(alt_baro="unknown") or b,
        lambda b: b["ac"][0].update(lat=95.0) or b,
    ],
    ids=["clock in seconds", "missing hex", "altitude text", "latitude out of range"],
)
def test_changed_columns_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        parse(edited(tmp_path, change))


def test_disabled_source_fails_closed_and_radius_checked():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(SAMPLE), off)
    with pytest.raises(ValueError, match="250"):
        S10("ka", (12.97, 77.59), radius_nm=251)


def test_fetch_uses_the_documented_point_route(tmp_path):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=SAMPLE.read_bytes())

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S10",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=1, max_bytes=1024**2),
        raw_root=tmp_path,
    )
    [raw] = S10("ka", (12.97, 77.59), 100, fetcher).fetch(ctx)
    assert urlsplit(seen[0]).path == "/v2/point/12.97/77.59/100"
    assert raw.sha256 == hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
