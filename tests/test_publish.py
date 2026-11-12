"""T045 acceptance: a release joins verified hot snapshots, places and facilities into immutable
bytes named by their SHA-256; the pointer stays "pending" without the owner's approval; a source
failure cannot replace a good pointer; replay by snapshot ID returns exactly what was known at the
cutoff; the release passes the browser's own validator (vitest, committed fixture)."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas.publish import (
    PublishError,
    build_release,
    canonical,
    hot_snapshots,
    places,
    write_release,
)
from atlas.replay import ReplayError, replay

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "web/tests/fixtures"
CAP = json.loads((FIX / "sachet-ka-point.json").read_text("utf-8"))
WEATHER = json.loads((FIX / "openmeteo-temperature-point.json").read_text("utf-8"))
PLACE = json.loads((FIX / "bangalore-place.json").read_text("utf-8"))
FACILITIES = json.loads((FIX / "s18-facilities-bengaluru.json").read_text("utf-8"))
NOW = datetime(2026, 11, 12, 6, 0, tzinfo=UTC)
RELEASE_FIXTURE = FIX / "release-ka.json"


def hot(source_id: str, record: dict) -> dict:
    snapshot = {
        "schema_version": 1,
        "state": "ka",
        "release_id": f"{source_id}-test",
        "data_revision": "a" * 64,
        "as_of": record["fetched_at"],
        "published_at": record["fetched_at"],
        "records": [record],
        "places": [],
        "facilities": [],
        "sources": [
            {
                "source_id": source_id,
                "status": "partial",
                "last_success_at": record["fetched_at"],
                "detail": "test",
            }
        ],
    }
    wire = json.dumps(
        {"source_id": source_id, "snapshot": snapshot}, ensure_ascii=False, separators=(",", ":")
    )
    return {
        "source_id": source_id,
        "sha256": "b" * 64,
        "wire_sha256": hashlib.sha256(wire.encode()).hexdigest(),
        "snapshot": snapshot,
    }


CURRENT = {"sources": [hot("S09", CAP), hot("S01", WEATHER)]}
DISTRICT = PLACE | {"name": PLACE["name"]}


def release() -> dict:
    district = {
        k: DISTRICT[k] for k in ("place_id", "name", "boundary_version", "longitude", "latitude")
    }
    return build_release(
        hot_snapshots(CURRENT), places([district], PLACE["source_url"]), FACILITIES, NOW
    )


def test_release_joins_sources_places_and_facilities():
    r = release()
    assert {h["source_id"] for h in r["sources"]} == {"S01", "S09"}
    assert len(r["records"]) == 2 and r["places"] == [PLACE]
    assert len(r["facilities"]) == len(FACILITIES) and r["as_of"] == "2026-11-12T06:00:00.000Z"
    assert (
        r["data_revision"]
        == hashlib.sha256(
            canonical({k: v for k, v in r.items() if k not in ("release_id", "data_revision")})
        ).hexdigest()
    )


def test_browser_fixture_is_the_python_release():
    assert json.loads(RELEASE_FIXTURE.read_text("utf-8")) == release()


def test_tampered_wire_digest_and_empty_hot_store_are_refused():
    bad = {"sources": [dict(CURRENT["sources"][0], wire_sha256="0" * 64)]}
    with pytest.raises(PublishError, match="wire digest"):
        hot_snapshots(bad)
    with pytest.raises(PublishError, match="no hot snapshot"):
        hot_snapshots({"sources": []})


def test_pointer_is_pending_releases_are_immutable_and_replay_matches(tmp_path):
    r = release()
    pointer = write_release(tmp_path, r, "pending")
    assert pointer["approval"] == "pending"
    data = (tmp_path / pointer["manifest_url"].lstrip("/")).read_bytes()
    assert hashlib.sha256(data).hexdigest() == pointer["sha256"]
    assert (tmp_path / f"api/v1/snapshots/{pointer['sha256']}.json").read_bytes() == data
    current = json.loads((tmp_path / "api/v1/current.json").read_text("utf-8"))
    assert current["sha256"] == pointer["sha256"] and len(current["sources"]) == 2
    assert replay(tmp_path, pointer["sha256"]) == r
    with pytest.raises(PublishError, match="approval"):
        write_release(tmp_path, r, "yes")
    (tmp_path / pointer["manifest_url"].lstrip("/")).write_bytes(data + b" ")
    with pytest.raises(ReplayError, match="do not match"):
        replay(tmp_path, pointer["sha256"])
    with pytest.raises(PublishError, match="immutable"):
        write_release(tmp_path, r, "pending")


def test_source_failure_keeps_the_previous_pointer(tmp_path):
    pointer = write_release(tmp_path, release(), "pending")
    before = (tmp_path / "data/ka/latest.json").read_bytes()
    with pytest.raises(PublishError):
        build_release(hot_snapshots({"sources": []}), [], [], NOW)
    assert (tmp_path / "data/ka/latest.json").read_bytes() == before
    assert json.loads(before)["sha256"] == pointer["sha256"]


def test_replay_refuses_data_from_after_the_cutoff(tmp_path):
    late = release()
    late["records"][0] = late["records"][0] | {"fetched_at": "2026-11-13T00:00:00Z"}
    pointer = write_release(tmp_path, late, "pending")
    with pytest.raises(ReplayError, match="not known"):
        replay(tmp_path, pointer["sha256"])
    with pytest.raises(ReplayError, match="64-character"):
        replay(tmp_path, "abc")


def test_static_inputs_and_api_description_are_committed():
    static = ROOT / "data/static/ka"
    rows = json.loads((static / "places.json").read_text("utf-8"))["rows"]
    assert len(rows) == 30 and all(
        r["kind"] == "district" and r["source_id"] == "S17" for r in rows
    )
    facilities = json.loads((static / "facilities.json").read_text("utf-8"))["rows"]
    assert len(facilities) == 433 and {f["kind"] for f in facilities} == {
        "hospital",
        "police",
        "fire_station",
    }
    spec = json.loads((ROOT / "docs/api/openapi.json").read_text("utf-8"))
    assert {"/api/v1/current.json", "/api/v1/snapshots/{id}.json"} <= set(spec["paths"])


def test_daily_workflow_archives_privately_and_never_deploys():
    import yaml

    text = (ROOT / ".github/workflows/daily.yml").read_text("utf-8")
    flow = yaml.safe_load(text)
    assert flow[True]["schedule"] == [{"cron": "17 2 * * *"}]
    assert flow["permissions"] == {"contents": "read"}
    assert "--approval pending" in text and "::add-mask::$HF_ARCHIVE_REPO" in text
    assert "wrangler" not in text and "pages deploy" not in text
