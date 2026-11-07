"""T114 acceptance on real, attributed KSEB title/table excerpts (no live network)."""

import hashlib
import json
import re
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
from atlas.ingest.s32 import HOSTS, MEASURES, S32

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests/fixtures"
SAMPLES = json.loads((FIX / "s32_samples.json").read_text("utf-8"))
CONFIG = (
    load_state(ROOT / "configs/states/kl.yaml").source("S32").model_copy(update={"enabled": True})
)


def artifact(eid="e02", path=None):
    sample = next(s for s in SAMPLES if s["evidence_id"] == eid)
    path = path or FIX / sample["file"]
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=datetime.fromisoformat(sample["fetched_at"].replace("Z", "+00:00")),
        media_type="text/html",
        response_status=200,
        source_url=sample["source_url"],
        schema_mapping_version="s32-v1",
    )


def edit(tmp_path, transform):
    path = tmp_path / "edited.html"
    path.write_text(transform(artifact().path.read_text("utf-8")), encoding="utf-8")
    return artifact(path=path)


def replace_cell(page, index, value):
    cells = list(re.finditer(r"(?is)(<td\b[^>]*>)(.*?)(</td>)", page))
    match = cells[index]
    return page[: match.start(2)] + value + page[match.end(2) :]


def test_roundtrip_preserves_source_units_ids_and_observation_time(tmp_path):
    raw = artifact()
    table = S32(CONFIG).parse(raw, CONFIG)
    pq.write_table(table, tmp_path / "s32.parquet")
    assert pq.read_table(tmp_path / "s32.parquet").equals(table)
    validate_table(table, measures=["level_m", "storage_mcm", "capacity_mcm"])
    assert read_mapping(table)["provider_to_canonical"]["Today's Water level (metre)"] == "level_m"
    assert table.num_rows == 16 and len(set(table["record_id"].to_pylist())) == 16
    row = table.to_pylist()[0]
    assert row["reservoir_id"] == "kseb:idk:idukki"
    assert (row["operator"], row["reservoir_name"], row["district_code"]) == (
        "KSEB",
        "IDUKKI",
        "IDK",
    )
    assert (row["level_m"], row["storage_mcm"], row["capacity_mcm"]) == (722.029, 918.774, 1459.49)
    assert row["date_local"] == date(2026, 11, 5)
    assert row["observed_at"] == row["valid_at"] == datetime(2026, 11, 5, 1, 30, tzinfo=UTC)
    assert row["available_at"] == row["fetched_at"] == raw.fetched_at
    assert row["issued_at"] is None and row["provenance"] == "official"
    assert row["missing_reason"] is None
    assert row["inflow_m3s"] is None and row["inflow_missing_reason"] == "not_reported"
    assert row["vertical_datum"] is None and row["datum_missing_reason"] == "not_reported"
    assert "MU is energy" in row["quality_details"]
    assert set(table["date_local"].to_pylist()) == {date(2026, 11, 5)}


@pytest.mark.parametrize("eid", ["e03", "e09"])
def test_early_unit_or_percentage_contradictions_are_quarantined(eid):
    rows = S32(CONFIG).parse(artifact(eid), CONFIG).to_pylist()
    assert len(rows) == 16
    first = rows[0]
    assert first["missing_reason"] == "quality_rejected"
    assert first["level_m"] is first["storage_mcm"] is first["capacity_mcm"] is None
    assert "out_of_range" in first["quality_flags"]
    assert "storage percentage mismatch" in first["quality_details"]


def test_missing_storage_is_not_zero_and_inconsistencies_remain_visible():
    rows = {r["reservoir_name"]: r for r in S32(CONFIG).parse(artifact(), CONFIG).to_pylist()}
    assert rows["MOOZHIYAR"]["missing_reason"] == "not_reported"
    assert rows["MOOZHIYAR"]["level_m"] is rows["MOOZHIYAR"]["storage_mcm"] is None
    assert rows["KALLARKUTTY"]["missing_reason"] == "quality_rejected"
    assert rows["KALLARKUTTY"]["capacity_mcm"] is None


def test_valid_header_only_report_is_empty_not_a_synthetic_observation():
    table = S32(CONFIG, day=date(2023, 10, 25)).parse(artifact("e04"), CONFIG)
    assert table.num_rows == 0
    assert table.schema.field("level_m").type == MEASURES.field("level_m").type
    validate_table(table, measures=["level_m", "storage_mcm", "capacity_mcm"])


@pytest.mark.parametrize(
    "transform",
    [
        lambda p: "",
        lambda p: "<html>upstream unavailable</html>",
        lambda p: p[:-50],
        lambda p: p.replace("Today's Water level (metre)", "Today's Water level (ft)"),
        lambda p: p.replace("District</th>", "Region</th>"),
        lambda p: p.replace("<td>IDUKKI</td>", ""),
        lambda p: p.replace("7.00 AM.", "8.00 AM."),
        lambda p: p.replace("05-Nov-2026", "04-Nov-2026"),
        lambda p: p + p,
    ],
)
def test_empty_malformed_changed_or_mismatched_report_fails(tmp_path, transform):
    with pytest.raises(IngestError):
        S32(CONFIG, day=date(2026, 11, 5)).parse(edit(tmp_path, transform), CONFIG)


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "2353.98", "722kg"])
def test_invalid_or_unlabelled_level_is_not_rescaled(tmp_path, value):
    raw = edit(tmp_path, lambda p: replace_cell(p, 2, value))
    row = S32(CONFIG).parse(raw, CONFIG).to_pylist()[0]
    assert row["missing_reason"] == "quality_rejected" and row["level_m"] is None


def test_explicit_feet_are_converted_but_datum_remains_unknown(tmp_path):
    feet = 722.029 / 0.3048
    raw = edit(tmp_path, lambda p: replace_cell(p, 2, f"{feet:.10f}ft"))
    row = S32(CONFIG).parse(raw, CONFIG).to_pylist()[0]
    assert row["level_m"] == pytest.approx(722.029)
    assert row["vertical_datum"] is None
    assert "explicit feet converted to metres" in row["quality_details"]


def test_duplicate_dam_rows_rejected(tmp_path):
    def duplicate(page):
        row = re.search(r"(?is)<tr>\s*<td>IDUKKI</td>.*?</tr>", page).group(0)
        return page.replace("</tbody>", row + "</tbody>")

    with pytest.raises(IngestError, match="duplicate"):
        S32(CONFIG).parse(edit(tmp_path, duplicate), CONFIG)


def test_same_artifact_is_stable_and_revisions_are_distinct(tmp_path):
    adapter = S32(CONFIG)
    original = adapter.parse(artifact(), CONFIG)
    assert adapter.parse(artifact(), CONFIG).equals(original)
    revised = adapter.parse(edit(tmp_path, lambda p: replace_cell(p, 2, "722.030")), CONFIG)
    assert original["reservoir_id"].to_pylist() == revised["reservoir_id"].to_pylist()
    assert original["record_id"].to_pylist() != revised["record_id"].to_pylist()


def context(tmp_path, **updates):
    values = dict(
        source_id="S32",
        state="kl",
        run_id="s32-test",
        requested_at=artifact().fetched_at,
        raw_root=tmp_path,
        budget=Budget(max_requests=2, max_bytes=1000000),
    )
    return FetchContext(**(values | updates))


def test_fetch_uses_verified_date_form_and_shared_ledger(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200, content=artifact().path.read_bytes(), headers={"content-type": "text/html"}
        )

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    adapter = S32(CONFIG, day=date(2026, 11, 5), fetcher=fetcher)
    raws = adapter.fetch(context(tmp_path))
    assert len(raws) == 1 and adapter.parse(raws[0], CONFIG).num_rows == 16
    assert requests[0].url.host == "kseb.in"
    assert requests[0].url.params["date"] == "2026-11-05"
    assert raws[0].path.exists()


def test_disabled_fetch_and_parse_fail_before_accessing_raw_or_network(tmp_path):
    disabled = CONFIG.model_copy(update={"enabled": False})
    adapter = S32(disabled)
    with pytest.raises(SourceUnavailable):
        adapter.fetch(context(tmp_path))
    with pytest.raises(SourceUnavailable):
        adapter.parse(artifact().model_copy(update={"path": tmp_path / "absent"}), disabled)


@pytest.mark.parametrize("updates", [{"state": "ka"}, {"source_id": "S34"}])
def test_wrong_fetch_context_is_rejected_before_network(tmp_path, updates):
    with pytest.raises(IngestError):
        S32(CONFIG).fetch(context(tmp_path, **updates))


def test_schema_and_fixture_provenance():
    schema = json.loads((ROOT / "schemas/s32.json").read_text("utf-8"))
    assert [f["name"] for f in schema["fields"]] == MEASURES.names
    discovery = json.loads((FIX / "s32/manifest.json").read_text("utf-8"))
    for sample in SAMPLES:
        assert (
            hashlib.sha256((FIX / sample["file"]).read_bytes()).hexdigest()
            == sample["excerpt_sha256"]
        )
        evidence = next(e for e in discovery["evidence"] if e["id"] == sample["evidence_id"])
        assert sample["raw_sha256"] == evidence["sha256"]
        assert sample["source_url"] == evidence["url"]


def test_only_completed_s32_is_enabled_in_kerala():
    source = load_state(ROOT / "configs/states/kl.yaml").source("S32")
    assert source.enabled and source.verified_by == "configs/sources/s32.yaml"


@pytest.mark.parametrize(
    "updates",
    [
        {"sha256": "0" * 64},
        {"source_url": "https://kseb.in/dashboard/view/waterlevel?date=2026-11-04"},
        {"source_url": "https://example.invalid/dashboard/view/waterlevel"},
        {"fetched_at": datetime(2026, 11, 4, tzinfo=UTC)},
        {"media_type": "application/json"},
        {"response_status": 503},
    ],
)
def test_untrusted_artifact_metadata_cannot_change_provenance(updates):
    with pytest.raises(IngestError):
        S32(CONFIG).parse(artifact().model_copy(update=updates), CONFIG)
