"""T014 acceptance: the S09 adapter round trip preserves IDs and source timestamps on real Sachet
CAP files (public domain, committed fixtures); updates and cancels supersede old alerts; missing
geometry stays area text; malformed, empty and changed files fail; disabled fails closed."""

import hashlib
import struct
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest import s09 as s09_mod
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s09 import HOSTS, MEASURES, S09, feed_identifiers, supersede

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
KA_CAP = FIX / "s09_sachet_cap_1793881986295019.xml"
KA_POLY = FIX / "s09_sachet_polygon_1793881986295019.xml"
AP_CAP = FIX / "s09_sachet_cap_1793880856139008.xml"
KL_CAP = FIX / "s09_sachet_cap_1793871793334006.xml"
FEED = FIX / "s09_sachet_rss_india_2026-11-05.xml"
FETCHED = datetime(2026, 11, 5, 13, 5, 40, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S09")
ADAPTER = S09("ka")


def artifact(path: Path) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="text/xml",
        response_status=200,
        source_url="https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1",
        schema_mapping_version="s09-v1",
    )


def edited(tmp_path: Path, name: str, *swaps: tuple[str, str]) -> RawArtifact:
    text = KA_CAP.read_text("utf-8")
    for old, new in swaps:
        assert old in text
        text = text.replace(old, new)
    out = tmp_path / name
    out.write_text(text, encoding="utf-8")
    return artifact(out)


def test_roundtrip_preserves_ids_and_timestamps(tmp_path):
    table = ADAPTER.parse(artifact(KA_CAP), CONFIG, polygon=artifact(KA_POLY))
    pq.write_table(table, tmp_path / "s09.parquet")
    back = pq.read_table(tmp_path / "s09.parquet")
    assert back.equals(table)
    validate_table(back)
    assert read_mapping(back)["provider_to_canonical"]["cap:identifier"] == "alert_id"
    row = back.to_pylist()[0]
    assert (row["alert_id"], row["sender"], row["msg_type"]) == (
        "IN-1793881986295019_19",
        "Karnataka-SNDMC",
        "Update",
    )
    assert row["sent_at"] == datetime(2026, 11, 5, 12, 35, 10, tzinfo=UTC)  # 18:05:10+05:30
    assert row["expires_at"] == datetime(2026, 11, 5, 15, 30, tzinfo=UTC)
    assert (
        row["event"] == "Thunderstorm with Lightning"
        and row["area_text"] == "5 districts of Karnataka"
    )
    assert row["issued_at"] == row["sent_at"] and row["provenance"] == "official"


def test_geometry_is_wkb_multipolygon_in_lon_lat():
    row = ADAPTER.parse(artifact(KA_CAP), CONFIG, polygon=artifact(KA_POLY)).to_pylist()[0]
    wkb = row["geometry"]
    order, kind, parts = struct.unpack_from("<BII", wkb)
    assert (order, kind, parts) == (1, 6, 7)  # 14 rings in the file, each listed twice
    _, _, _, points = struct.unpack_from("<BIII", wkb, 9)
    lon, lat = struct.unpack_from("<dd", wkb, 22)
    assert points > 3 and 74 < lon < 79 and 11 < lat < 19


def test_missing_geometry_stays_area_text():
    row = ADAPTER.parse(artifact(KA_CAP), CONFIG).to_pylist()[0]
    assert row["geometry"] is None and row["area_text"] == "5 districts of Karnataka"


def test_alerts_outside_the_state_give_no_rows():
    for path in (AP_CAP, KL_CAP):
        table = ADAPTER.parse(artifact(path), CONFIG)
        assert table.num_rows == 0 and table.schema.names[-len(MEASURES) :] == MEASURES.names


def test_update_and_cancel_supersede(tmp_path):
    # Mutated CAP copies test reference semantics; predecessors are not observed rows.
    update = ADAPTER.parse(artifact(KA_CAP), CONFIG)
    ref = "IMD-Bengaluru,IN-1793881986295019_51,2026-11-05T18:01:57+05:30"
    refs = f"<cap:references>{ref}</cap:references>"
    original = ADAPTER.parse(
        edited(
            tmp_path,
            "original.xml",
            ("IN-1793881986295019_19", "IN-1793881986295019_51"),
            ("<cap:msgType>Update", "<cap:msgType>Alert"),
            ("<cap:sender>Karnataka-SNDMC", "<cap:sender>IMD-Bengaluru"),
            ("<cap:sent>2026-11-05T18:05:10+05:30", "<cap:sent>2026-11-05T18:01:57+05:30"),
            (refs, "<cap:references/>"),
        ),
        CONFIG,
    )
    both = pa.concat_tables([original, update])
    assert supersede(both)["alert_id"].to_pylist() == ["IN-1793881986295019_19"]
    cancel = ADAPTER.parse(
        edited(
            tmp_path,
            "cancel.xml",
            ("<cap:identifier>IN-1793881986295019_19", "<cap:identifier>IN-1793881986295019_77"),
            ("<cap:msgType>Update", "<cap:msgType>Cancel"),
            (ref, "Karnataka-SNDMC,IN-1793881986295019_19,2026-11-05T18:05:10+05:30"),
        ),
        CONFIG,
    )
    assert supersede(pa.concat_tables([original, update, cancel])).num_rows == 0


@pytest.mark.parametrize("mismatch", ["sender", "time", "naive_reference", "malformed_reference"])
def test_reference_mismatch_cannot_remove_an_unrelated_warning(tmp_path, mismatch):
    update = ADAPTER.parse(artifact(KA_CAP), CONFIG)
    ref = "IMD-Bengaluru,IN-1793881986295019_51,2026-11-05T18:01:57+05:30"
    original = edited(
        tmp_path,
        "reference-target-copy.xml",
        ("<cap:identifier>IN-1793881986295019_19", "<cap:identifier>IN-1793881986295019_51"),
        ("<cap:msgType>Update", "<cap:msgType>Alert"),
        ("<cap:sender>Karnataka-SNDMC", "<cap:sender>IMD-Bengaluru"),
        ("<cap:sent>2026-11-05T18:05:10+05:30", "<cap:sent>2026-11-05T18:01:57+05:30"),
        (f"<cap:references>{ref}</cap:references>", "<cap:references/>"),
    )
    target = ADAPTER.parse(original, CONFIG)
    if mismatch == "sender":
        target = target.set_column(
            target.schema.get_field_index("sender"),
            target.schema.field("sender"),
            pa.array(["Karnataka-SNDMC"]),
        )
    elif mismatch == "time":
        target = target.set_column(
            target.schema.get_field_index("sent_at"),
            target.schema.field("sent_at"),
            update["sent_at"],
        )
    else:
        text = (
            "IMD-Bengaluru,IN-1793881986295019_51,2026-11-05T12:31:57"
            if mismatch == "naive_reference"
            else "IN-1793881986295019_51"
        )
        update = update.set_column(
            update.schema.get_field_index("references"),
            update.schema.field("references"),
            pa.array([text]),
        )
    assert supersede(pa.concat_tables([target, update])).num_rows == 2


def test_equivalent_reference_timezone_matches_the_actual_target_instant(tmp_path):
    ref = "IMD-Bengaluru,IN-1793881986295019_51,2026-11-05T18:01:57+05:30"
    update = ADAPTER.parse(artifact(KA_CAP), CONFIG)
    update = update.set_column(
        update.schema.get_field_index("references"),
        update.schema.field("references"),
        pa.array([ref.replace("18:01:57+05:30", "12:31:57Z")]),
    )
    original = ADAPTER.parse(
        edited(
            tmp_path,
            "utc-reference-target-copy.xml",
            ("<cap:identifier>IN-1793881986295019_19", "<cap:identifier>IN-1793881986295019_51"),
            ("<cap:msgType>Update", "<cap:msgType>Alert"),
            ("<cap:sender>Karnataka-SNDMC", "<cap:sender>IMD-Bengaluru"),
            ("<cap:sent>2026-11-05T18:05:10+05:30", "<cap:sent>2026-11-05T18:01:57+05:30"),
            (f"<cap:references>{ref}</cap:references>", "<cap:references/>"),
        ),
        CONFIG,
    )
    assert supersede(pa.concat_tables([original, update]))["alert_id"].to_pylist() == [
        "IN-1793881986295019_19"
    ]


@pytest.mark.parametrize("message_type", ["Alert", "Ack", "Error"])
def test_only_update_or_cancel_can_supersede_a_reference(tmp_path, message_type):
    update = ADAPTER.parse(artifact(KA_CAP), CONFIG)
    target = update.set_column(
        update.schema.get_field_index("alert_id"),
        update.schema.field("alert_id"),
        pa.array(["IN-1793881986295019_51"]),
    )
    target = target.set_column(
        target.schema.get_field_index("sender"),
        target.schema.field("sender"),
        pa.array(["IMD-Bengaluru"]),
    )
    target = target.set_column(
        target.schema.get_field_index("sent_at"),
        target.schema.field("sent_at"),
        pa.array(
            [datetime(2026, 11, 5, 12, 31, 57, tzinfo=UTC)],
            type=target.schema.field("sent_at").type,
        ),
    )
    target = target.set_column(
        target.schema.get_field_index("references"),
        target.schema.field("references"),
        pa.array([None], type=pa.string()),
    )
    control = ADAPTER.parse(
        edited(
            tmp_path,
            "message-type-copy.xml",
            ("<cap:msgType>Update", f"<cap:msgType>{message_type}"),
        ),
        CONFIG,
    )
    ids = supersede(pa.concat_tables([target, control]))["alert_id"].to_pylist()
    assert "IN-1793881986295019_51" in ids
    assert ("IN-1793881986295019_19" in ids) == (message_type == "Alert")


@pytest.mark.parametrize(
    "field,before,after",
    [
        ("status", "Actual", "Test"),
        ("status", "Actual", "Exercise"),
        ("scope", "Public", "Restricted"),
        ("scope", "Public", "Private"),
    ],
)
def test_non_actual_or_non_public_messages_are_not_public_warnings(tmp_path, field, before, after):
    raw = edited(
        tmp_path, "non-public-copy.xml", (f"<cap:{field}>{before}", f"<cap:{field}>{after}")
    )
    assert ADAPTER.parse(raw, CONFIG).num_rows == 0


@pytest.mark.parametrize("field", ["status", "scope", "msgType"])
def test_unknown_lifecycle_fields_fail_closed(tmp_path, field):
    before = {"status": "Actual", "scope": "Public", "msgType": "Update"}[field]
    raw = edited(
        tmp_path,
        "unknown-lifecycle-copy.xml",
        (f"<cap:{field}>{before}", f"<cap:{field}>unsupported-test-copy"),
    )
    with pytest.raises(IngestError):
        ADAPTER.parse(raw, CONFIG)


def test_naive_sent_timestamp_cannot_be_interpreted_in_the_host_timezone(tmp_path):
    raw = edited(
        tmp_path,
        "naive-date-copy.xml",
        ("<cap:sent>2026-11-05T18:05:10+05:30", "<cap:sent>2026-11-05T18:05:10"),
    )
    with pytest.raises(IngestError, match="time|UTC|offset"):
        ADAPTER.parse(raw, CONFIG)


def test_self_reference_does_not_erase_its_own_update_warning():
    update = ADAPTER.parse(artifact(KA_CAP), CONFIG)
    row = update.to_pylist()[0]
    reference = f"{row['sender']},{row['alert_id']},{row['sent_at'].isoformat()}"
    update = update.set_column(
        update.schema.get_field_index("references"),
        update.schema.field("references"),
        pa.array([reference]),
    )
    assert supersede(update)["alert_id"].to_pylist() == [row["alert_id"]]


def test_empty_source_table_stays_typed_during_supersession():
    empty = ADAPTER.parse(artifact(AP_CAP), CONFIG)
    assert supersede(empty).equals(empty)


def test_schema_file_matches_measure_columns():
    import json

    spec = json.loads((ROOT / "schemas" / "s09.json").read_text("utf-8"))
    names = {"string": "string", "binary": "binary", "timestamp[us, tz=UTC]": "timestamp"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_empty_and_changed_files_rejected(tmp_path):
    broken = tmp_path / "broken.xml"
    broken.write_bytes(KA_CAP.read_bytes()[:300])
    empty = tmp_path / "empty.xml"
    empty.write_bytes(b"")
    for path in (broken, empty):
        with pytest.raises(IngestError, match="not XML"):
            ADAPTER.parse(artifact(path), CONFIG)
    no_event = edited(
        tmp_path,
        "no_event.xml",
        ("<cap:event>", "<cap:eventType>"),
        ("</cap:event>", "</cap:eventType>"),
    )
    with pytest.raises(IngestError, match="event"):
        ADAPTER.parse(no_event, CONFIG)
    with pytest.raises(IngestError, match="not a CAP"):
        ADAPTER.parse(artifact(FEED), CONFIG)


def test_disabled_source_fails_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(KA_CAP), off)
    with pytest.raises(SourceUnavailable):
        S09("kl")


@pytest.mark.parametrize("changed_version", [False, True])
def test_fetch_skips_only_known_rss_versions(tmp_path, monkeypatch, changed_version):
    idents = feed_identifiers(artifact(FEED))
    assert len(idents) == 100 and idents[0] == "1793881986295019"
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        path = request.url.path
        body = FEED if path.endswith(".xml") else KA_POLY if "Polygon" in path else KA_CAP
        return httpx.Response(200, content=body.read_bytes(), headers={"content-type": "text/xml"})

    monkeypatch.setattr(s09_mod.time, "sleep", lambda s: None)
    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S09",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=5, max_bytes=5 * 1024**2),
        raw_root=tmp_path,
    )
    known = s09_mod.feed_versions(artifact(FEED))
    if changed_version:
        known[idents[0]] = "0" * 64  # Technical stale-cache token; no observation invented.
    else:
        known.pop(idents[0])
    raws = S09("ka", fetcher).fetch(ctx, known=known)
    assert len(raws) == 3 and seen[1].endswith("FetchXMLFile?identifier=1793881986295019")
    assert seen[2].endswith("FetchPolygonXMLFile?identifier=1793881986295019")


def test_identifier_only_cache_is_rejected_before_network(tmp_path, monkeypatch):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, content=FEED.read_bytes(), headers={"content-type": "text/xml"})

    monkeypatch.setattr(s09_mod.time, "sleep", lambda s: None)
    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S09",
        state="ka",
        run_id="legacy-cache",
        requested_at=FETCHED,
        budget=Budget(max_requests=5, max_bytes=5 * 1024**2),
        raw_root=tmp_path,
    )
    with pytest.raises(IngestError, match="version|fingerprint"):
        S09("ka", fetcher).fetch(ctx, known=set(feed_identifiers(artifact(FEED))))
    assert not seen


def test_item_versions_ignore_channel_clock_but_detect_an_item_change(tmp_path):
    import xml.etree.ElementTree as ET

    original = s09_mod.feed_versions(artifact(FEED))
    root = ET.fromstring(FEED.read_bytes())
    root.find("channel/pubDate").text = "Thu, 05 Nov 2026 12:35:12 GMT"
    path = tmp_path / "channel-clock-copy.xml"
    path.write_bytes(ET.tostring(root))
    assert s09_mod.feed_versions(artifact(path)) == original
    first = root.find("channel/item/pubDate")
    first.text = first.text.replace("12:35:12", "12:35:13")  # Mutated version-marker test copy.
    path.write_bytes(ET.tostring(root))
    changed = s09_mod.feed_versions(artifact(path))
    assert changed["1793881986295019"] != original["1793881986295019"]
    assert {k: v for k, v in changed.items() if k != "1793881986295019"} == {
        k: v for k, v in original.items() if k != "1793881986295019"
    }


def test_empty_rss_channel_is_distinct_from_changed_or_malformed_schema(tmp_path):
    import xml.etree.ElementTree as ET

    with pytest.raises(IngestError, match="RSS"):
        s09_mod.feed_versions(artifact(KA_CAP))
    root = ET.fromstring(FEED.read_bytes())
    root.find("channel/item").remove(root.find("channel/item/link"))
    bad = tmp_path / "missing-link-copy.xml"
    bad.write_bytes(ET.tostring(root))
    with pytest.raises(IngestError, match="CAP link"):
        s09_mod.feed_versions(artifact(bad))
    channel = root.find("channel")
    for item in channel.findall("item"):
        channel.remove(item)
    empty = tmp_path / "empty-channel-copy.xml"
    empty.write_bytes(ET.tostring(root))
    assert s09_mod.feed_versions(artifact(empty)) == {}
