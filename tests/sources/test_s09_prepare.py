"""T235 real captured CAPs; mutations are test-only controls/clock/error cases."""

import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest import s09_collect, s09_prepare
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.discovery import load_manifest
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s09 import BASE, NS, S09
from atlas.ingest.s09_prepare import prepare

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures"
KA = "1793881986295019"
AP = "1793880856139008"
CUTOFF = datetime(2026, 11, 5, 14, tzinfo=UTC)


def captured(store, ident=KA):
    path = FIXTURES / f"s09_sachet_cap_{ident}.xml"
    evidence = next(
        e
        for e in load_manifest(FIXTURES / "s09/manifest.json").evidence
        if e.url == f"{BASE}/FetchXMLFile?identifier={ident}"
    )
    raw_path, digest = store.put(path.read_bytes(), "S09", evidence.fetched_at, "xml")
    assert digest == evidence.sha256
    raw = RawArtifact(
        sha256=digest,
        path=raw_path,
        fetched_at=evidence.fetched_at,
        media_type=evidence.media_type,
        response_status=200,
        source_url=evidence.url,
        schema_mapping_version="s09-v1",
    )
    store.record(raw, {"status": 200})
    return raw


def payload(result):
    path = Path(result["payload_path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == result["sha256"]
    return json.loads(path.read_text("utf-8"))


def english_info(root):
    return next(
        info
        for info in root.findall("cap:info", NS)
        if info.findtext("cap:language", "", NS) == "en-IN"
    )


def control(store, original, *, mismatch=None, message_type="Cancel"):
    # Header-only control derived from the actual fixture, never used as an observation.
    root = ET.fromstring(original.path.read_bytes())
    get = lambda tag: root.find(f"cap:{tag}", NS)  # noqa: E731
    sender, ident, sent = (get(t).text for t in ("sender", "identifier", "sent"))
    get("identifier").text += ".test-control-copy"
    get("msgType").text = message_type
    for info in root.findall("cap:info", NS):
        root.remove(info)
    if mismatch == "sender":
        sender += ".unmatched-test-copy"
    if mismatch == "sent":
        sent = "2026-11-05T18:35:11+05:30"
    get("references").text = f"{sender},{ident},{sent}"
    if mismatch == "ack":
        get("msgType").text = "Ack"
    if mismatch == "test":
        get("status").text = "Test"
    if mismatch == "private":
        get("scope").text = "Private"
    at = CUTOFF - timedelta(minutes=1)
    path, digest = store.put(ET.tostring(root), "S09", at, "xml")
    raw = original.model_copy(update={"path": path, "sha256": digest, "fetched_at": at})
    store.record(raw, {"status": 200})
    return raw


def test_prepared_warning_matches_real_adapter_and_keeps_original_clocks(tmp_path):
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    result = prepare(store.root, tmp_path / "prepared", as_of=CUTOFF)
    snapshot = payload(result)["snapshot"]
    row = (
        S09("ka")
        .parse(raw, load_state(ROOT / "configs/states/ka.yaml").source("S09"))
        .to_pylist()[0]
    )
    record = snapshot["records"][0]
    assert record["id"] == row["record_id"]
    info = english_info(ET.fromstring(raw.path.read_bytes()))
    assert record["warning_text"] == info.findtext("cap:headline", namespaces=NS)
    assert record["area_text"] == row["area_text"]
    assert record["instruction"] == row["instruction"]
    assert record["longitude"] is None and record["latitude"] is None
    for field in ("issued_at", "valid_at", "fetched_at", "available_at", "expires_at"):
        assert record[field] == row[field].isoformat().replace("+00:00", "Z")
    assert snapshot["sources"][0]["status"] == "partial"
    pointer = json.loads((tmp_path / "prepared/prepared.json").read_text("utf-8"))
    assert pointer["status"] == "prepared_only" and "approval" not in pointer
    inputs = Path(result["inputs_path"]).read_bytes()
    assert hashlib.sha256(inputs).hexdigest() == snapshot["data_revision"]
    assert json.loads(inputs)["mapping_version"] == "s09-prepared-v2"
    assert not list(tmp_path.rglob("*.approval.json"))


@pytest.mark.parametrize("field", ["description", "event", "first_info"])
def test_warning_text_follows_selected_info_and_falls_back_within_it(tmp_path, field):
    original = captured(RawStore(tmp_path / "original"))
    root = ET.fromstring(original.path.read_bytes())
    english = english_info(root)
    root.remove(english)
    root.append(english)  # The retained Kannada block now comes first.
    if field == "first_info":
        english.remove(english.find("cap:language", NS))
        expected = root.findtext("cap:info/cap:headline", namespaces=NS)
    else:
        headline = english.find("cap:headline", NS)
        english.remove(headline)
        if field == "description":
            english.find("cap:description", NS).text = headline.text
        expected = english.findtext(f"cap:{field}", namespaces=NS)
    store = RawStore(tmp_path / "raw")
    path, digest = store.put(ET.tostring(root), "S09", original.fetched_at, "xml")
    store.record(original.model_copy(update={"path": path, "sha256": digest}), {"status": 200})
    result = prepare(store.root, tmp_path / "prepared", as_of=CUTOFF)
    assert payload(result)["snapshot"]["records"][0]["warning_text"] == expected


def test_304_advances_exact_document_check_clock_without_changing_content_clock(tmp_path):
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    store.record(
        raw.model_copy(update={"fetched_at": CUTOFF, "response_status": 304}), {"status": 304}
    )
    snapshot = payload(prepare(store.root, tmp_path / "prepared", as_of=CUTOFF))["snapshot"]
    assert snapshot["sources"][0]["last_success_at"] == CUTOFF.isoformat().replace("+00:00", "Z")
    assert snapshot["records"][0]["fetched_at"] == raw.fetched_at.isoformat().replace("+00:00", "Z")


def test_runner_reuses_cap_until_new_check_or_expiry(tmp_path):
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    output = tmp_path / "prepared"
    first = prepare(store.root, output, as_of=CUTOFF)
    original_head = (output / "prepared.json").read_bytes()
    before = {p.name for p in output.iterdir()}
    later = CUTOFF + timedelta(seconds=1)
    assert prepare(store.root, output, as_of=later, reuse_equivalent=True) == first
    assert (output / "prepared.json").read_bytes() == original_head
    assert {p.name for p in output.iterdir()} == before

    store.record(
        raw.model_copy(update={"fetched_at": later, "response_status": 304}), {"status": 304}
    )
    checked = prepare(store.root, output, as_of=later, reuse_equivalent=True)
    assert checked["sha256"] != first["sha256"]
    snapshot = payload(checked)["snapshot"]
    assert datetime.fromisoformat(snapshot["sources"][0]["last_success_at"]) == later
    expiry = datetime.fromisoformat(snapshot["records"][0]["expires_at"])
    expired = prepare(store.root, output, as_of=expiry, reuse_equivalent=True)
    assert expired["sha256"] != checked["sha256"]
    assert payload(expired)["snapshot"]["records"] == []


def test_runner_rejects_corrupt_equivalent_cap_head(tmp_path):
    store = RawStore(tmp_path / "raw")
    captured(store)
    output = tmp_path / "prepared"
    first = prepare(store.root, output, as_of=CUTOFF)
    head = (output / "prepared.json").read_bytes()
    Path(first["payload_path"]).write_bytes(b"damaged")
    with pytest.raises(IngestError, match="hash verification"):
        prepare(store.root, output, as_of=CUTOFF + timedelta(seconds=1), reuse_equivalent=True)
    assert (output / "prepared.json").read_bytes() == head


@pytest.mark.parametrize("message_type", ["Cancel", "Update"])
def test_header_only_control_applies_exact_reference_without_fake_warning_row(
    tmp_path, message_type
):
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    cancelled = control(store, raw, message_type=message_type)
    result = prepare(store.root, tmp_path / "prepared", as_of=CUTOFF)
    assert payload(result)["snapshot"]["records"] == []
    assert raw.path.exists() and cancelled.path.exists()


@pytest.mark.parametrize("evidence", ["Cancel", "Update", "out-of-state", "damaged-ledger"])
def test_disabled_source_refuses_before_reading_ledger_and_keeps_pointer(
    tmp_path, monkeypatch, evidence
):
    store = RawStore(tmp_path / "raw")
    if evidence in {"Cancel", "Update"}:
        original = captured(RawStore(tmp_path / "original"))
        control(store, original, message_type=evidence)
    else:
        captured(store, AP)
    output = tmp_path / "prepared"
    first = prepare(store.root, output, as_of=CUTOFF)
    assert payload(first)["snapshot"]["records"] == []
    files = {path.name: path.read_bytes() for path in output.iterdir()}
    if evidence == "damaged-ledger":
        (store.root / "ledger.jsonl").write_bytes(b"{damaged-ledger\n")

    state = load_state(ROOT / "configs/states/ka.yaml")
    disabled = state.model_copy(
        update={
            "sources": tuple(
                source.model_copy(update={"enabled": False})
                if source.source_id == "S09"
                else source
                for source in state.sources
            )
        }
    )
    monkeypatch.setattr(s09_prepare, "load_state", lambda _: disabled)
    monkeypatch.setattr(s09_collect, "load_state", lambda _: disabled)
    with pytest.raises(SourceUnavailable, match="S09 is disabled"):
        prepare(store.root, output, as_of=CUTOFF + timedelta(minutes=1))
    assert {path.name: path.read_bytes() for path in output.iterdir()} == files


@pytest.mark.parametrize("damage", ["malformed_entry", "missing_entry", "retargeted_entry"])
def test_damaged_control_ledger_cannot_resurrect_warning_or_advance_head(tmp_path, damage):
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    control(store, raw)
    output = tmp_path / "prepared"
    first = prepare(store.root, output, as_of=CUTOFF)
    assert payload(first)["snapshot"]["records"] == []
    pointer = (output / "prepared.json").read_bytes()
    ledger = store.root / "ledger.jsonl"
    lines = ledger.read_bytes().splitlines(keepends=True)
    if damage == "malformed_entry":
        lines[-1] = b"{damaged-completed-cancellation-entry\n"
    elif damage == "missing_entry":
        lines.pop()
    else:
        entry = json.loads(lines[-1])
        entry["artifact"]["source_url"] = f"{BASE}/rss/rss_india.xml"
        lines[-1] = json.dumps(entry).encode("utf-8") + b"\n"
    ledger.write_bytes(b"".join(lines))  # Test-only ledger damage, not observation editing.
    with pytest.raises(IngestError, match="ledger|evidence|retained|input"):
        prepare(store.root, output, as_of=CUTOFF + timedelta(minutes=1))
    assert (output / "prepared.json").read_bytes() == pointer
    assert payload(first)["snapshot"]["records"] == []


@pytest.mark.parametrize("mismatch", ["sender", "sent", "ack", "test", "private"])
def test_unmatched_or_non_public_control_cannot_erase_warning(tmp_path, mismatch):
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    control(store, raw, mismatch=mismatch)
    assert (
        len(
            payload(prepare(store.root, tmp_path / "prepared", as_of=CUTOFF))["snapshot"]["records"]
        )
        == 1
    )


@pytest.mark.parametrize("ident,at", [(AP, CUTOFF), (KA, CUTOFF + timedelta(days=1))])
def test_empty_state_or_expired_result_stays_partial_and_keeps_raw_history(tmp_path, ident, at):
    store = RawStore(tmp_path / "raw")
    raw = captured(store, ident)
    snapshot = payload(prepare(store.root, tmp_path / "prepared", as_of=at))["snapshot"]
    assert snapshot["records"] == [] and snapshot["sources"][0]["status"] == "partial"
    assert raw.path.exists()


def test_same_message_byte_revision_is_selected_only_after_its_actual_fetch(tmp_path):
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    at = CUTOFF + timedelta(minutes=10)
    path, digest = store.put(raw.path.read_bytes() + b"\n", "S09", at, "xml")
    changed = raw.model_copy(update={"path": path, "sha256": digest, "fetched_at": at})
    store.record(changed, {"status": 200})  # Whitespace-only revision test copy.
    first = prepare(store.root, tmp_path / "prepared", as_of=CUTOFF)
    old_bytes = Path(first["payload_path"]).read_bytes()
    second = prepare(store.root, tmp_path / "prepared", as_of=at)
    one, two = payload(first)["snapshot"]["records"], payload(second)["snapshot"]["records"]
    assert len(one) == len(two) == 1 and one[0]["id"] != two[0]["id"]
    assert Path(first["payload_path"]).read_bytes() == old_bytes


@pytest.mark.parametrize("failure", ["corrupt", "oversized"])
def test_failed_prepare_preserves_last_pointer_and_immutable_payload(tmp_path, failure):
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    output = tmp_path / "prepared"
    result = prepare(store.root, output, as_of=CUTOFF)
    pointer = (output / "prepared.json").read_bytes()
    original = Path(result["payload_path"]).read_bytes()
    if failure == "corrupt":
        raw.path.write_bytes(b"corrupt-test-copy")
    with pytest.raises(IngestError):
        prepare(
            store.root, output, as_of=CUTOFF, max_bytes=1 if failure == "oversized" else 1048576
        )
    assert (output / "prepared.json").read_bytes() == pointer
    assert Path(result["payload_path"]).read_bytes() == original


def test_no_cap_evidence_cannot_prepare_an_available_feed(tmp_path):
    with pytest.raises(SourceUnavailable):
        prepare(tmp_path / "raw", tmp_path / "prepared", as_of=CUTOFF)


def test_old_or_competing_preparation_cannot_roll_the_head_back(tmp_path):
    store = RawStore(tmp_path / "raw")
    captured(store)
    output = tmp_path / "prepared"
    later = CUTOFF + timedelta(minutes=1)

    def attempt(at):
        try:
            return prepare(store.root, output, as_of=at)
        except IngestError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(attempt, [later, CUTOFF]))
    pointer = json.loads((output / "prepared.json").read_text("utf-8"))
    assert json.loads((output / pointer["payload"]).read_text("utf-8"))["snapshot"][
        "as_of"
    ] == later.isoformat().replace("+00:00", "Z")
    with pytest.raises(IngestError, match="older|back"):
        prepare(store.root, output, as_of=CUTOFF)


def test_repeat_preparation_is_content_addressed_and_idempotent(tmp_path):
    store = RawStore(tmp_path / "raw")
    captured(store)
    one = prepare(store.root, tmp_path / "prepared", as_of=CUTOFF)
    two = prepare(store.root, tmp_path / "prepared", as_of=CUTOFF)
    assert one["sha256"] == two["sha256"]


def test_preparation_time_is_real_even_for_a_historical_cutoff(tmp_path):
    store = RawStore(tmp_path / "raw")
    captured(store)
    started = datetime.now(UTC)
    snapshot = payload(prepare(store.root, tmp_path / "prepared", as_of=CUTOFF))["snapshot"]
    assert datetime.fromisoformat(snapshot["published_at"]) >= started
    assert snapshot["as_of"] == CUTOFF.isoformat().replace("+00:00", "Z")


def test_same_cutoff_with_different_inputs_cannot_replace_prepared_head(tmp_path):
    store = RawStore(tmp_path / "raw")
    captured(store)
    output = tmp_path / "prepared"
    prepare(store.root, output, as_of=CUTOFF)
    pointer = (output / "prepared.json").read_bytes()
    captured(store, AP)
    with pytest.raises(IngestError, match="conflict|cutoff"):
        prepare(store.root, output, as_of=CUTOFF)
    assert (output / "prepared.json").read_bytes() == pointer


def test_malformed_new_download_keeps_dated_warning_without_refreshing_success_clock(tmp_path):
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    path, digest = store.put(b"<broken", "S09", CUTOFF, "xml")
    store.record(
        raw.model_copy(update={"path": path, "sha256": digest, "fetched_at": CUTOFF}),
        {"status": 200},
    )
    result = prepare(store.root, tmp_path / "prepared", as_of=CUTOFF)
    snapshot = payload(result)["snapshot"]
    assert len(snapshot["records"]) == 1
    assert snapshot["sources"][0]["last_success_at"] == raw.fetched_at.isoformat().replace(
        "+00:00", "Z"
    )
    assert "could not be validated" in snapshot["sources"][0]["detail"]


def test_python_prepared_bytes_round_trip_through_actual_worker_validator(tmp_path):
    node = ROOT / ".tools/node/node-v22.16.0-win-x64/node.exe"
    if not node.is_file():
        pytest.skip("Optional pinned local Node toolchain is absent in core-only CI")
    store = RawStore(tmp_path / "raw")
    raw = captured(store)
    result = prepare(store.root, tmp_path / "prepared", as_of=CUTOFF)
    validator_uri = (ROOT / "worker/src/ingest.ts").as_uri()
    script = (
        "import { readFileSync } from 'node:fs'; import { gzipSync } from 'node:zlib';"
        f"import {{decodeUpload,restoreUpload}} from {json.dumps(validator_uri)};"
        "const input=readFileSync(process.argv[1]);"
        "const clean=await decodeUpload(gzipSync(input),Date.parse(process.argv[2]));"
        "const restored=await restoreUpload(clean.compressed,clean.sha256,"
        "Date.parse(process.argv[2]));"
        "if(restored.snapshot.sources[0].status!=='partial'||restored.snapshot.records.length!==1)"
        "throw new Error('Prepared source/coverage mismatch');"
        "console.log(JSON.stringify([clean.snapshot.records[0].warning_text,"
        "restored.snapshot.records[0].warning_text]));"
    )
    env = os.environ.copy()
    env.update({"TEMP": str(ROOT / ".cache/tmp"), "TMP": str(ROOT / ".cache/tmp")})
    checked = subprocess.run(
        [
            str(node),
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            script,
            result["payload_path"],
            datetime.now(UTC).isoformat(),
        ],
        env=env,
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert checked.returncode == 0, checked.stderr
    headline = english_info(ET.fromstring(raw.path.read_bytes())).findtext(
        "cap:headline", namespaces=NS
    )
    assert json.loads(checked.stdout) == [headline, headline]
