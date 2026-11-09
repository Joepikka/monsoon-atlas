"""T088 acceptance: the S44 adapter keeps registered-case counts per published police unit on real
public-domain tables (2024 offence heads, 2023 totals); unit kinds separate districts,
commissionerates, subtotals and no-area units; malformed, empty and changed tables fail; a
disabled source fails closed."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.s44 import FILES, MEASURES, S44, unit_kind

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
HEADS = FIX / "s44_opencity_ksp_district_ipc_2024.csv"  # T087 e04
TOTALS = FIX / "s44_opencity_ksp_totals_2023.csv"  # T087 e05
FETCHED = datetime(2026, 11, 9, 11, 7, 0, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S44")
ADAPTER = S44("ka")


def artifact(path: Path, year: int) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="text/csv",
        response_status=200,
        source_url=FILES[year],
        schema_mapping_version="s44-v1",
    )


def edited(tmp_path: Path, source: Path, year: int, edit) -> RawArtifact:
    out = tmp_path / "edited.csv"
    out.write_text(edit(source.read_bytes().decode("utf-8-sig")), encoding="utf-8")
    return artifact(out, year)


def cell(table, unit: str, head: str) -> dict:
    keep = pc.and_(pc.equal(table["district_id"], unit), pc.equal(table["offence_category"], head))
    return table.filter(keep).to_pylist()[0]


def test_roundtrip_keeps_units_heads_and_counts(tmp_path):
    table = ADAPTER.parse(artifact(HEADS, 2024), CONFIG, year=2024)
    pq.write_table(table, tmp_path / "s44.parquet")
    back = pq.read_table(tmp_path / "s44.parquet")
    assert back.equals(table)
    validate_table(back, measures=["count"])
    assert read_mapping(back)["provider_to_canonical"]["cell value"] == "count"
    assert back.num_rows == 41 * 21 and len(set(back["record_id"].to_pylist())) == 41 * 21
    murder = cell(back, "Bengaluru City", "MURDER")
    assert (murder["count"], murder["unit_kind"], murder["year"]) == (176, "commissionerate", 2024)
    assert cell(back, "Total", "MURDER")["count"] == 1209
    assert murder["provenance"] == "official" and murder["population_year"] is None
    assert murder["valid_at"] == datetime(2024, 12, 31, 18, 30, tzinfo=UTC)
    units = set(back["district_id"].to_pylist())
    assert not {"Commissionerates", "Central Range"} & units  # empty heading rows skipped


def test_unit_kinds():
    kinds = {
        "Bengaluru Dist": "district",
        "Mysuru City": "commissionerate",
        "Central Range": "range_subtotal",
        "Karnataka Railways": "no_area",
        "KRailways": "no_area",
        "CID": "no_area",
        "TOTAL": "state_total",
    }
    assert {name: unit_kind(name) for name in kinds} == kinds


def test_totals_layout_2023():
    table = ADAPTER.parse(artifact(TOTALS, 2023), CONFIG, year=2023)
    assert set(table["offence_category"].to_pylist()) == {"IPC Cases", "SLL Cases", "Total"}
    total = cell(table, "TOTAL", "Total")
    assert (total["count"], total["unit_kind"]) == (214234, "state_total")
    assert cell(table, "Shimoga", "IPC Cases")["unit_kind"] == "district"


def test_blank_count_stays_null(tmp_path):
    raw = edited(tmp_path, TOTALS, 2023, lambda t: t.replace("Bagalkot,2317,", "Bagalkot,,", 1))
    row = cell(ADAPTER.parse(raw, CONFIG, year=2023), "Bagalkot", "IPC Cases")
    assert (row["count"], row["missing_reason"]) == (None, "not_reported")


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s44.json").read_text("utf-8"))
    names = {"string": "string", "int64": "int64"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_empty_malformed_and_changed_tables_rejected(tmp_path):
    for edit, match in (
        (lambda t: t.splitlines(keepends=True)[0], "empty"),
        (lambda t: t.replace("IPC Cases", "IPC", 1), "columns changed"),
        (lambda t: t.replace("Bagalkot,2317,", "Bagalkot,2.3k,", 1), "not a case count"),
        (lambda t: t.replace("Bagalkot,2317,985,3302", "Bagalkot,2317", 1), "short row"),
    ):
        with pytest.raises(IngestError, match=match):
            ADAPTER.parse(edited(tmp_path, TOTALS, 2023, edit), CONFIG, year=2023)


def test_disabled_source_fails_closed_and_years_checked():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(TOTALS, 2023), off, year=2023)
    with pytest.raises(ValueError, match="2021"):
        ADAPTER.fetch(None, 2021)
