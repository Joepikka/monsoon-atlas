"""T074 acceptance: the S21 adapter keeps the pinned 2016 timetable for stops at Karnataka
stations (real CC0 subsets: three Karnataka trains plus one other, and their stations); "None"
times stay null; stop order is derived and flagged when ids disagree; malformed, empty and
changed files fail; a disabled source fails closed; fetch reads only the pinned commit."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s21 import BASE, COMMIT, HOSTS, MEASURES, S21

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
STOPS = FIX / "s21_datameet_schedules_4_trains.json"  # subset of T073 e08 (CC0)
STATIONS = FIX / "s21_datameet_stations_subset.json"  # subset of T073 e06 (CC0)
FETCHED = datetime(2026, 11, 9, 9, 46, 43, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S21")
ADAPTER = S21("ka", "Karnataka")


def artifact(path: Path, name: str) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url=f"{BASE}/{name}",
        schema_mapping_version="s21-v1",
    )


def stations() -> RawArtifact:
    return artifact(STATIONS, "stations.json")


def edited(tmp_path: Path, edit) -> RawArtifact:
    out = tmp_path / "schedules.json"
    out.write_text(json.dumps(edit(json.loads(STOPS.read_text("utf-8")))), encoding="utf-8")
    return artifact(out, "schedules.json")


def parse(raw: RawArtifact):
    return ADAPTER.parse(raw, CONFIG, stations=stations())


def test_roundtrip_keeps_ids_times_and_positions(tmp_path):
    table = parse(artifact(STOPS, "schedules.json"))
    pq.write_table(table, tmp_path / "s21.parquet")
    back = pq.read_table(tmp_path / "s21.parquet")
    assert back.equals(table)
    validate_table(back)
    assert read_mapping(back)["provider_to_canonical"]["day"] == "journey_day"
    assert back.num_rows == 28 and len(set(back["record_id"].to_pylist())) == 28
    trains = {t: c for t, c in zip(*pc.value_counts(back["train_id"]).flatten(), strict=True)}
    assert {str(k): v.as_py() for k, v in trains.items()} == {"56646": 10, "56656": 3, "51462": 15}
    first = back.filter(pc.equal(back["train_id"], "56646")).to_pylist()[0]
    assert (first["stop_sequence"], first["arrival_text"]) == (1, None)  # first stop: "None"
    assert first["departure_text"] is not None and first["journey_day"] == 1
    assert first["provenance"] == "reconstructed" and first["valid_at"] is None
    assert first["published_at"] == datetime(2016, 8, 8, 7, 20, tzinfo=UTC)


def test_other_states_are_dropped_and_missing_positions_stay_null():
    table = parse(artifact(STOPS, "schedules.json"))
    assert "04853" not in table["train_id"].to_pylist()
    assert table["lat"].null_count == table["lon"].null_count


def test_stop_order_is_flagged_when_ids_disagree(tmp_path):
    def swap(stops):
        rows = [s for s in stops if s["train_number"] == "56646"]
        rows[0]["id"], rows[1]["id"] = rows[1]["id"], rows[0]["id"]
        return stops

    table = parse(edited(tmp_path, swap))
    flagged = table.filter(pc.equal(table["train_id"], "56646"))["quality_flags"].to_pylist()
    assert flagged == [["imputed"]] * 10
    other = table.filter(pc.equal(table["train_id"], "51462"))["quality_flags"].to_pylist()
    assert other == [[]] * 15


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s21.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "int64": "int64"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_and_empty_files_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(STOPS.read_bytes()[:300])
    with pytest.raises(IngestError, match="not JSON"):
        parse(artifact(broken, "schedules.json"))
    with pytest.raises(IngestError, match="empty"):
        parse(edited(tmp_path, lambda s: []))
    with pytest.raises(IngestError, match="positions"):
        ADAPTER.parse(artifact(STOPS, "schedules.json"), CONFIG)


@pytest.mark.parametrize(
    "change",
    [
        lambda s: [s[0] | {"platform": "1"}, *s[1:]],
        lambda s: [s[0] | {"departure": "7.55"}, *s[1:]],
        lambda s: [s[0] | {"day": 0}, *s[1:]],
        lambda s: [s[0] | {"station_code": "NOPE"}, *s[1:]],
    ],
    ids=["new column", "time format", "day", "unknown station"],
)
def test_changed_files_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        parse(edited(tmp_path, change))


def test_unpinned_files_and_disabled_source_fail_closed():
    unpinned = artifact(STOPS, "schedules.json").model_copy(
        update={
            "source_url": "https://raw.githubusercontent.com/datameet/railways/master/schedules.json"
        }
    )
    with pytest.raises(IngestError, match="pinned"):
        parse(unpinned)
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(STOPS, "schedules.json"), off, stations=stations())


def test_fetch_reads_the_pinned_commit(tmp_path):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        path = STATIONS if request.url.path.endswith("stations.json") else STOPS
        return httpx.Response(200, content=path.read_bytes())

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S21",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=2, max_bytes=200 * 1024**2),
        raw_root=tmp_path,
    )
    stations_raw, stops_raw = S21("ka", "Karnataka", fetcher).fetch(ctx)
    assert seen == [f"{BASE}/stations.json", f"{BASE}/schedules.json"]
    assert all(COMMIT in u for u in seen)
    assert ADAPTER.parse(stops_raw, CONFIG, stations=stations_raw).num_rows == 28
