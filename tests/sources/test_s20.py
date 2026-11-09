"""T072 acceptance: the S20 adapter round trip keeps IDs, units and timestamps on real USGS
responses (local raw files, skipped in CI: licence not yet recorded, D110); automatic and
reviewed events stay distinct; missing magnitudes stay null; malformed, empty and changed
responses fail; a disabled source fails closed."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

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
from atlas.ingest.s20 import FEED, HOSTS, MEASURES, QUERY, S20

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "S20" / "2026-11-09"
HISTORY = RAW / "3b5e16e8307d7287ad8977373856e55395bd1e29953139ccc2b35724969137dc.json"  # e09
DAY = RAW / "ffe000ffb89ffc9af98a6ea4e4a2bc9036e68863b7b43e3a7a18840bdbf83ae5.json"  # e07
pytestmark = pytest.mark.skipif(not HISTORY.exists(), reason="USGS raw files are local only")

FETCHED = datetime(2026, 11, 9, 8, 9, 19, 704438, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S20")
SOUTH_INDIA = (72.0, 8.0, 81.0, 19.0)
WORLD = (-180.0, -90.0, 180.0, 90.0)


def artifact(path: Path, url: str = QUERY) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url=url,
        schema_mapping_version="s20-v1",
    )


def edited(tmp_path: Path, edit, source: Path = HISTORY) -> RawArtifact:
    out = tmp_path / "events.json"
    out.write_text(json.dumps(edit(json.loads(source.read_text("utf-8")))), encoding="utf-8")
    return artifact(out)


def parse(raw: RawArtifact, box=SOUTH_INDIA):
    return S20("ka", box).parse(raw, CONFIG)


def test_roundtrip_keeps_ids_units_and_timestamps(tmp_path):
    table = parse(artifact(HISTORY))
    pq.write_table(table, tmp_path / "s20.parquet")
    back = pq.read_table(tmp_path / "s20.parquet")
    assert back.equals(table)
    validate_table(back, measures=["magnitude"])
    assert read_mapping(back)["provider_to_canonical"]["properties.updated"] == "updated_at"
    assert back.num_rows == 95 and len(set(back["record_id"].to_pylist())) == 95
    first = back.filter(pc.equal(back["event_id"], "us7000nvs3")).to_pylist()[0]
    assert first["origin_at"] == datetime(2024, 12, 4, 1, 56, 58, 775000, tzinfo=UTC)
    assert first["updated_at"] == first["published_at"]
    assert (first["magnitude"], first["review_status"], first["provenance"]) == (
        5.0,
        "reviewed",
        "official",
    )
    assert first["redistribution_allowed"] is False and first["valid_at"] == first["origin_at"]


def test_missing_magnitude_stays_null_with_reason():
    table = parse(artifact(HISTORY))
    missing = table.filter(pc.is_null(table["magnitude"]))
    assert missing.num_rows == 16
    assert set(missing["missing_reason"].to_pylist()) == {"not_reported"}


def test_feed_keeps_automatic_and_reviewed_apart_and_clips_the_box():
    day = parse(artifact(DAY, FEED), WORLD)
    statuses = pc.value_counts(day["review_status"]).to_pylist()
    assert {s["values"]: s["counts"] for s in statuses} == {"automatic": 136, "reviewed": 50}
    assert parse(artifact(DAY, FEED), SOUTH_INDIA).num_rows == 0  # no event near India that day


def test_new_version_only_with_a_later_update(tmp_path):
    def bump(body):
        body["features"][0]["properties"]["updated"] += 60_000
        return body

    old = set(parse(artifact(HISTORY))["record_id"].to_pylist())
    new = set(parse(edited(tmp_path, bump))["record_id"].to_pylist())
    assert len(old - new) == len(new - old) == 1  # same event id, new version


def test_other_types_and_deleted_events_are_dropped(tmp_path):
    def mark(body):
        body["features"][0]["properties"]["type"] = "quarry blast"
        body["features"][1]["properties"]["status"] = "deleted"
        return body

    assert parse(edited(tmp_path, mark)).num_rows == 93


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s20.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "timestamp[us, tz=UTC]": "timestamp"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_and_empty_responses_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(HISTORY.read_bytes()[:400])
    with pytest.raises(IngestError, match="not JSON"):
        parse(artifact(broken))
    with pytest.raises(IngestError, match="empty"):
        parse(edited(tmp_path, lambda b: {}))
    assert parse(edited(tmp_path, lambda b: b | {"features": []})).num_rows == 0


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["features"][0]["properties"].pop("updated") and b,
        lambda b: b["features"][0]["properties"].update(time="2024-12-04") or b,
        lambda b: b["features"][0]["properties"].update(status="final") or b,
        lambda b: b["features"][0].pop("id") and b,
    ],
    ids=["missing updated", "time text", "unknown status", "missing id"],
)
def test_changed_columns_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        parse(edited(tmp_path, change))


def test_disabled_source_fails_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        S20("ka", SOUTH_INDIA).parse(artifact(HISTORY), off)


@pytest.mark.parametrize("starttime", [None, "1900-01-01"])
def test_fetch_uses_the_feed_or_a_dated_query(tmp_path, starttime):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=HISTORY.read_bytes())

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S20",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=2, max_bytes=1024**2),
        raw_root=tmp_path,
    )
    S20("ka", SOUTH_INDIA, starttime, fetcher).fetch(ctx)
    if starttime is None:
        assert seen == [FEED]
    else:
        query = parse_qs(urlsplit(seen[0]).query)
        assert query["starttime"] == ["1900-01-01"] and query["limit"] == ["1000"]
        assert query["minlatitude"] == ["8"] and query["maxlongitude"] == ["81"]
