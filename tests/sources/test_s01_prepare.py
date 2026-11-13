"""T238: genuine paired weather evidence; edits below are failure/control copies."""

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

import atlas.ingest.s01_prepare as module
from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s01 import S01
from atlas.ingest.s01_collect import POINTS, collect_weather
from atlas.ingest.s01_prepare import prepare_weather

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests/fixtures"
NOW = datetime(2026, 11, 5, 14, tzinfo=UTC)


def capture(root, at=NOW, *, change=None):
    def respond(request):
        name = (
            "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
            if request.url.path.endswith("meta.json")
            else "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
        )
        body = (FIX / name).read_bytes()
        if change:
            body = change(name, body)
        if request.headers.get("if-none-match") and not change:
            return httpx.Response(304)
        return httpx.Response(
            200, content=body, headers={"etag": name, "content-type": "application/json"}
        )

    result = collect_weather(
        root, clock=lambda: at, sleep=lambda _: None, transport=httpx.MockTransport(respond)
    )
    return result, json.loads(Path(result["receipt_path"]).read_bytes())


def revise(root, result, pair, *, retain_original=False):
    """Archive an explicitly edited test-only receipt, retaining its originals."""
    encoded = json.dumps(pair, sort_keys=True, separators=(",", ":")).encode()
    at = datetime.fromisoformat(pair["captured_at"])
    path, digest = RawStore(root / "weather/pairs").put(encoded, "S01", at, "json")
    if not retain_original:
        Path(result["receipt_path"]).unlink()
    (root / "weather/latest-pair.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_id": "S01",
                "state": "ka",
                "path": path.relative_to(root).as_posix(),
                "sha256": digest,
            }
        ),
        "utf-8",
    )
    return path


def snapshot(result):
    encoded = Path(result["payload_path"]).read_bytes()
    assert hashlib.sha256(encoded).hexdigest() == result["sha256"]
    value = json.loads(encoded)["snapshot"]
    assert (
        hashlib.sha256(Path(result["inputs_path"]).read_bytes()).hexdigest()
        == value["data_revision"]
    )
    return value


def test_runner_reuses_weather_until_forecast_selection_changes(tmp_path):
    capture(tmp_path)
    start = NOW + timedelta(seconds=1)
    first = prepare_weather(tmp_path, as_of=start)
    first_snapshot = snapshot(first)
    output = tmp_path / "weather/prepared"
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    later = start + timedelta(seconds=1)
    assert prepare_weather(tmp_path, as_of=later, reuse_equivalent=True) == first
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    with pytest.raises(IngestError, match="byte cap"):
        prepare_weather(tmp_path, as_of=later, max_bytes=50, reuse_equivalent=True)

    standalone = prepare_weather(tmp_path, as_of=later)
    assert standalone["sha256"] != first["sha256"]
    validity = datetime.fromisoformat(first_snapshot["records"][0]["valid_at"])
    next_hour = prepare_weather(
        tmp_path, as_of=validity + timedelta(seconds=1), reuse_equivalent=True
    )
    assert next_hour["sha256"] != standalone["sha256"]
    assert snapshot(next_hour)["records"][0]["valid_at"] != first_snapshot["records"][0]["valid_at"]


def test_real_pair_matches_adapter_and_actual_browser_fixture_point(tmp_path):
    _, pair = capture(tmp_path)
    result = prepare_weather(tmp_path, as_of=NOW)
    value = snapshot(result)
    record = value["records"][0]
    raw = RawArtifact.model_validate(pair["requests"][1]["artifact"])
    meta = RawArtifact.model_validate(pair["requests"][2]["artifact"])
    rows = (
        S01("ka", POINTS)
        .parse(raw, load_state(ROOT / "configs/states/ka.yaml").source("S01"), meta=meta)
        .to_pylist()
    )
    row = next(r for r in rows if r["valid_at"] >= NOW and r["missing_reason"] is None)
    browser = json.loads(
        (ROOT / "web/tests/fixtures/openmeteo-temperature-point.json").read_bytes()
    )
    assert (
        (record["latitude"], record["longitude"])
        == (browser["latitude"], browser["longitude"])
        == (13.0, 77.5)
    )
    assert record["value"] == row["temperature_c"] and record["id"] == row["record_id"]
    assert record["unit"] == browser["unit"]
    assert record["issued_at"] == pair["model_initialization"]
    assert record["fetched_at"] == record["available_at"] == pair["captured_at"]
    assert (
        record["provenance"] == "model"
        and record["kind"] == "weather"
        and record["evidence"] == "forecast"
    )
    assert record.get("model_id") is None and record.get("model_status") is None
    assert "grid" in record["location_note"].lower()
    assert value["sources"][0]["status"] == "partial"
    assert value["sources"][0]["last_success_at"] == pair["captured_at"]
    assert "1 of 1 points" in value["sources"][0]["detail"]  # D206: T009 profile
    pointer = json.loads((tmp_path / "weather/prepared/prepared.json").read_bytes())
    assert pointer["status"] == "prepared_only" and "approval" not in pointer
    assert not list(tmp_path.rglob("*.approval.json"))


def test_original_browser_fixture_value_and_identity_are_reproducible(tmp_path):
    expected = json.loads(
        (ROOT / "web/tests/fixtures/openmeteo-temperature-point.json").read_bytes()
    )
    cutoff = datetime.fromisoformat(expected["fetched_at"])
    result, _ = capture(tmp_path, cutoff)
    assert result["status"] == "captured"
    record = snapshot(prepare_weather(tmp_path, as_of=cutoff))["records"][0]
    for field in (
        "id",
        "value",
        "unit",
        "latitude",
        "longitude",
        "issued_at",
        "valid_at",
        "fetched_at",
        "available_at",
    ):
        assert record[field] == expected[field]


def test_complete_receipt_and_each_input_are_fenced_at_cutoff(tmp_path):
    result, pair = capture(tmp_path)
    pair["captured_at"] = (NOW + timedelta(seconds=2)).isoformat()
    pair["requests"][2]["artifact"]["fetched_at"] = (NOW + timedelta(seconds=1)).isoformat()
    revise(tmp_path, result, pair)
    with pytest.raises(SourceUnavailable):
        prepare_weather(tmp_path, as_of=NOW)
    value = snapshot(prepare_weather(tmp_path, as_of=NOW + timedelta(seconds=2)))
    assert datetime.fromisoformat(value["records"][0]["fetched_at"]) == NOW
    assert datetime.fromisoformat(value["records"][0]["available_at"]) == NOW + timedelta(seconds=2)


@pytest.mark.parametrize("prepare_first", [True, False])
def test_revalidation_preserves_first_cohort_clocks_and_latest_actual_check(
    tmp_path, prepare_first
):
    _, first = capture(tmp_path)
    if prepare_first:
        prepare_weather(tmp_path, as_of=NOW)
    later = NOW + timedelta(hours=6)
    _, checked = capture(tmp_path, later)
    value = snapshot(prepare_weather(tmp_path, as_of=later))
    assert checked["requests"][1]["artifact"]["response_status"] == 304
    assert value["records"][0]["fetched_at"] == first["requests"][1]["artifact"]["fetched_at"]
    assert value["records"][0]["available_at"] == first["captured_at"]
    assert value["sources"][0]["last_success_at"] == checked["captured_at"]


@pytest.mark.parametrize(
    "damage",
    [
        "receipt_hash",
        "raw_hash",
        "missing_raw",
        "mapping",
        "url",
        "roles",
        "profile",
        "grid",
        "run",
        "settle",
        "source",
        "point",
        "schema",
        "pointer",
    ],
)
def test_corrupt_or_mismatched_evidence_never_moves_head(tmp_path, damage):
    result, pair = capture(tmp_path)
    prepare_weather(tmp_path, as_of=NOW)
    head = tmp_path / "weather/prepared/prepared.json"
    original = head.read_bytes()
    raw = pair["requests"][1]["artifact"]
    if damage == "receipt_hash":
        Path(result["receipt_path"]).write_bytes(b"{}")
    elif damage == "raw_hash":
        Path(raw["path"]).write_bytes(b"corrupt test copy")
    elif damage == "missing_raw":
        Path(raw["path"]).unlink()
    elif damage == "pointer":
        (tmp_path / "weather/latest-pair.json").write_bytes(b"{}")
    else:
        if damage == "mapping":
            raw["schema_mapping_version"] = "unknown-test"
        if damage == "url":
            raw["source_url"] += "&models=best_match"
        if damage == "roles":
            pair["requests"][0]["role"] = "forecast"
        if damage == "profile":
            pair["profile"] = "unknown-test"
        if damage == "grid":
            pair["returned_points"] = [[12.97, 77.59]]
        if damage == "run":
            pair["model_initialization"] = "2026-11-04T00:00:00Z"
        if damage == "settle":
            raw["fetched_at"] = "2026-11-05T00:00:00Z"
        if damage == "source":
            pair["source_id"] = "S09"
        if damage == "point":
            pair["requested_points"] = [[13.0, 77.5]]
        if damage == "schema":
            pair["schema_version"] = 2
        revise(tmp_path, result, pair)
    with pytest.raises(IngestError):
        prepare_weather(tmp_path, as_of=NOW + timedelta(minutes=1))
    assert head.read_bytes() == original


def test_missing_pointer_recovers_receipt_but_removed_known_receipt_fails(tmp_path):
    result, _ = capture(tmp_path)
    pointer = tmp_path / "weather/latest-pair.json"
    pointer.unlink()
    prepare_weather(tmp_path, as_of=NOW)
    head = (tmp_path / "weather/prepared/prepared.json").read_bytes()
    Path(result["receipt_path"]).unlink()
    with pytest.raises(IngestError):
        prepare_weather(tmp_path, as_of=NOW + timedelta(minutes=1))
    assert (tmp_path / "weather/prepared/prepared.json").read_bytes() == head


@pytest.mark.parametrize("damage", ["missing", "quality", "empty", "exhausted"])
def test_no_eligible_future_row_preserves_previous_output(tmp_path, damage, monkeypatch):
    capture(tmp_path)
    prepare_weather(tmp_path, as_of=NOW)
    head = (tmp_path / "weather/prepared/prepared.json").read_bytes()
    if damage == "exhausted":
        cutoff = NOW + timedelta(days=30)

        class LaterClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cutoff + timedelta(days=1)

        monkeypatch.setattr(module, "datetime", LaterClock)
    else:

        def change(name, body):
            if "forecast" not in name:
                return body
            value = json.loads(body)
            hourly = value["hourly"]
            if damage == "empty":
                value["hourly"] = {key: [] for key in hourly}
            elif damage == "missing":
                hourly["temperature_2m"] = [None] * len(hourly["time"])
            else:
                hourly["relative_humidity_2m"] = [101] * len(hourly["time"])
            return json.dumps(value).encode()

        cutoff = NOW + timedelta(hours=6)
        result, pair = capture(tmp_path, cutoff, change=change)
        # Deliberately false outcome control: preparation must independently qualify it.
        pair["outcome"] = "validated"
        pair["model_initialization"] = "2026-11-05T00:00:00Z"
        pair["returned_points"] = [[13.0, 77.5]]
        revise(tmp_path, result, pair)
    with pytest.raises(IngestError):
        prepare_weather(tmp_path, as_of=cutoff)
    assert (tmp_path / "weather/prepared/prepared.json").read_bytes() == head


def test_idempotent_replay_and_older_cutoff_and_size_and_quota(tmp_path, monkeypatch):
    capture(tmp_path)
    first = prepare_weather(tmp_path, as_of=NOW)
    published = snapshot(first)["published_at"]
    assert datetime.fromisoformat(published) > NOW
    assert prepare_weather(tmp_path, as_of=NOW) == first
    head = (tmp_path / "weather/prepared/prepared.json").read_bytes()
    with pytest.raises(IngestError):
        prepare_weather(tmp_path, as_of=NOW - timedelta(seconds=1))
    with pytest.raises(IngestError):
        prepare_weather(tmp_path, as_of=NOW, max_bytes=1)
    from atlas.data.budget import ArchiveOnly, StorageQuota

    def full(*_):
        raise ArchiveOnly("test quota full")

    monkeypatch.setattr(StorageQuota, "ensure_can_ingest", full)
    with pytest.raises(ArchiveOnly):
        prepare_weather(tmp_path, as_of=NOW + timedelta(seconds=1))
    assert (tmp_path / "weather/prepared/prepared.json").read_bytes() == head


def test_disabled_source_and_absent_evidence(tmp_path, monkeypatch):
    with pytest.raises(SourceUnavailable):
        prepare_weather(tmp_path, as_of=NOW)
    capture(tmp_path)
    state = load_state(ROOT / "configs/states/ka.yaml")
    disabled = state.model_copy(
        update={
            "sources": tuple(
                s.model_copy(update={"enabled": False}) if s.source_id == "S01" else s
                for s in state.sources
            )
        }
    )
    monkeypatch.setattr(module, "load_state", lambda _: disabled)
    with pytest.raises(SourceUnavailable):
        prepare_weather(tmp_path, as_of=NOW)
    assert not (tmp_path / "weather/prepared/prepared.json").exists()


def test_python_weather_bytes_round_trip_actual_worker(tmp_path):
    node = ROOT / ".tools/node/node-v22.16.0-win-x64/node.exe"
    if not node.is_file():
        pytest.skip("Optional pinned Node absent")
    capture(tmp_path)
    result = prepare_weather(tmp_path, as_of=NOW)
    validator_uri = (ROOT / "worker/src/ingest.ts").as_uri()
    script = (
        "import {readFileSync} from 'node:fs';import {gzipSync} from 'node:zlib';"
        f"import {{decodeUpload,restoreUpload}} from {json.dumps(validator_uri)};"
        "const c=await decodeUpload(gzipSync(readFileSync(process.argv[1])),"
        "Date.parse(process.argv[2]));"
        "const r=await restoreUpload(c.compressed,c.sha256,Date.parse(process.argv[2]));"
        "if(r.snapshot.records[0].latitude!==13||r.snapshot.sources[0].status!=='partial')"
        "throw Error('weather mismatch');"
    )
    env = os.environ.copy() | {"TEMP": str(ROOT / ".cache/tmp"), "TMP": str(ROOT / ".cache/tmp")}
    result = subprocess.run(
        [
            str(node),
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            script,
            result["payload_path"],
            datetime.now(UTC).isoformat(),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("new_cohort", ["model", "content"])
def test_new_model_or_content_has_its_own_first_clocks(tmp_path, new_cohort):
    _, first = capture(tmp_path)
    prepare_weather(tmp_path, as_of=NOW)
    later = NOW + timedelta(hours=6)

    def change(name, body):
        if new_cohort == "model" and "meta" in name:
            info = json.loads(body)
            info["last_run_initialisation_time"] += 21600
            return json.dumps(info).encode()  # Explicit model-run selection control.
        if new_cohort == "content" and "forecast" in name:
            return body + b"\n"  # Whitespace-only revision of genuine source bytes.
        return body

    result, second = capture(tmp_path, later, change=change)
    assert result["status"] == "captured"
    value = snapshot(prepare_weather(tmp_path, as_of=later))
    record = value["records"][0]
    assert record["issued_at"] == second["model_initialization"]
    assert record["fetched_at"] == record["available_at"] == second["captured_at"]
    assert record["fetched_at"] != first["captured_at"]
    if new_cohort == "model":
        # A later capture of an older run is archived, but never selected over the newer run.
        older, _ = capture(tmp_path, later + timedelta(hours=6), change=lambda _, body: body)
        assert older["status"] == "older_run"
        current = snapshot(prepare_weather(tmp_path, as_of=later + timedelta(hours=6)))
        assert current["records"][0]["issued_at"] == second["model_initialization"]
        assert current["sources"][0]["last_success_at"] == second["captured_at"]


def test_same_cutoff_new_receipt_and_changed_bytes_conflict(tmp_path, monkeypatch):
    result, pair = capture(tmp_path)
    prepare_weather(tmp_path, as_of=NOW)
    head = tmp_path / "weather/prepared/prepared.json"
    original = head.read_bytes()
    # An additional identity at the same cutoff cannot replace an already prepared manifest.
    pair["test_only_control"] = "same-cutoff additional receipt"
    revise(tmp_path, result, pair, retain_original=True)
    with pytest.raises(IngestError, match="conflict"):
        prepare_weather(tmp_path, as_of=NOW)
    assert head.read_bytes() == original


@pytest.mark.parametrize("role", [0, 1, 2])
def test_each_input_validation_time_must_be_at_cutoff(tmp_path, role):
    result, pair = capture(tmp_path)
    pair["requests"][role]["artifact"]["fetched_at"] = (NOW + timedelta(seconds=1)).isoformat()
    revise(tmp_path, result, pair)
    with pytest.raises(SourceUnavailable):
        prepare_weather(tmp_path, as_of=NOW)
    assert not (tmp_path / "weather/prepared/prepared.json").exists()


def test_missing_and_quality_rows_are_skipped_using_adapter_policy(tmp_path):
    def change(name, body):
        if "forecast" not in name:
            return body
        value = json.loads(body)
        index = value["hourly"]["time"].index("2026-11-05T14:00")
        value["hourly"]["temperature_2m"][index] = None
        value["hourly"]["relative_humidity_2m"][index + 1] = 101
        return json.dumps(value).encode()  # Test-only missing/quality controls.

    result, _ = capture(tmp_path, change=change)
    assert result["status"] == "captured"
    value = snapshot(prepare_weather(tmp_path, as_of=NOW))
    assert value["records"][0]["valid_at"] == "2026-11-05T16:00:00Z"


def test_unavailable_early_attempt_cannot_be_certified_by_later_cutoff(tmp_path):
    def early(name, body):
        if "meta" not in name:
            return body
        info = json.loads(body)
        info["last_run_availability_time"] = int(NOW.timestamp())
        return json.dumps(info).encode()

    result, pair = capture(tmp_path, change=early)
    assert result["status"] == "unavailable" and pair["outcome"] == "unavailable"
    with pytest.raises(SourceUnavailable):
        prepare_weather(tmp_path, as_of=NOW + timedelta(minutes=20))
    pair["outcome"] = "validated"
    pair["model_initialization"] = "2026-11-05T00:00:00Z"
    pair["returned_points"] = [[13.0, 77.5]]
    revise(tmp_path, result, pair)
    with pytest.raises(IngestError):
        prepare_weather(tmp_path, as_of=NOW + timedelta(minutes=20))


@pytest.mark.parametrize("body", [b"not JSON", b"[]", b"null", b'{"hourly":null}'])
def test_malformed_rehashed_forecast_cannot_be_promoted(tmp_path, body):
    result, pair = capture(tmp_path)
    prepare_weather(tmp_path, as_of=NOW)
    head = tmp_path / "weather/prepared/prepared.json"
    original = head.read_bytes()
    path, digest = RawStore(tmp_path / "weather/raw").put(body, "S01", NOW, "json")
    pair["requests"][1]["artifact"].update({"path": str(path), "sha256": digest})
    revise(tmp_path, result, pair)
    with pytest.raises(IngestError):
        prepare_weather(tmp_path, as_of=NOW + timedelta(minutes=1))
    assert head.read_bytes() == original


def test_transport_gzip_bound_and_same_input_changed_bytes_preserve_head(tmp_path, monkeypatch):
    import atlas.ingest.prepared as shared

    capture(tmp_path)
    first = prepare_weather(tmp_path, as_of=NOW)
    head = tmp_path / "weather/prepared/prepared.json"
    original = head.read_bytes()
    with monkeypatch.context() as patch:
        patch.setattr(shared.gzip, "compress", lambda *_, **__: b"x" * (1048576 + 1))
        with pytest.raises(IngestError, match="byte cap"):
            prepare_weather(tmp_path, as_of=NOW + timedelta(seconds=1))
    with monkeypatch.context() as patch:
        # Same receipt manifest, changed projection: same-cutoff bytes must also be immutable.
        original_materialize = module.materialize

        def altered(*args, **kwargs):
            kwargs["envelope"]["snapshot"]["records"][0]["location_note"] += (
                " test-only byte conflict"
            )
            return original_materialize(*args, **kwargs)

        patch.setattr(module, "materialize", altered)
        with pytest.raises(IngestError, match="bytes conflict"):
            prepare_weather(tmp_path, as_of=NOW)
    assert head.read_bytes() == original
    assert snapshot(first)["records"][0]["latitude"] == 13.0


@pytest.mark.parametrize("field", ["hourly", "hourly_units"])
def test_malformed_nested_forecast_is_an_ingest_error(tmp_path, field):
    result, pair = capture(tmp_path)
    raw = pair["requests"][1]["artifact"]
    body = json.loads(Path(raw["path"]).read_bytes())
    body[field] = None  # Test-only malformed source-shape control.
    path, digest = RawStore(tmp_path / "weather/raw").put(
        json.dumps(body).encode(), "S01", NOW, "json"
    )
    raw.update({"path": str(path), "sha256": digest})
    revise(tmp_path, result, pair)
    with pytest.raises(IngestError):
        prepare_weather(tmp_path, as_of=NOW)


def test_validated_json_uses_existing_adapter_contract_when_content_type_is_absent(tmp_path):
    result, pair = capture(tmp_path)
    # Fetcher records this default when an upstream omits Content-Type; S01 validates JSON itself.
    for item in pair["requests"]:
        item["artifact"]["media_type"] = "application/octet-stream"
    revise(tmp_path, result, pair)
    assert snapshot(prepare_weather(tmp_path, as_of=NOW))["records"][0]["latitude"] == 13.0
