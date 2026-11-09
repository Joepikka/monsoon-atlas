"""T080 acceptance: the S29 adapter keeps annual KSNDMC rainfall by level and name path on real
public-domain subsets (2020 seasonal layout, 2021 and 2024 annual layouts with region and State
totals, 2023 stations); the unmarked 2025 layout is refused; malformed, empty and changed files
fail; a disabled source fails closed; fetch waits 10 seconds between files."""

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
from atlas.ingest.s29 import FILES, HOSTS, MEASURES, PAUSE_S, S29

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
FETCHED = datetime(2026, 11, 9, 10, 46, 10, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S29")
ADAPTER = S29("ka")


def sample(name: str) -> Path:
    return FIX / f"s29_opencity_ksndmc_{name}_subset.csv"  # subsets of T079 e04-e09


def artifact(path: Path, year: int) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="text/csv",
        response_status=200,
        source_url=FILES[year],
        schema_mapping_version="s29-v1",
    )


def parse(name: str, year: int):
    return ADAPTER.parse(artifact(sample(name), year), CONFIG, year=year)


def edited(tmp_path: Path, name: str, year: int, edit) -> RawArtifact:
    out = tmp_path / "edited.csv"
    out.write_text(edit(sample(name).read_text("utf-8")), encoding="utf-8")
    return artifact(out, year)


def row(table, area_id: str) -> dict:
    return table.filter(pc.equal(table["area_id"], area_id)).to_pylist()[0]


def test_roundtrip_keeps_levels_paths_and_totals(tmp_path):
    table = parse("2021", 2021)
    pq.write_table(table, tmp_path / "s29.parquet")
    back = pq.read_table(tmp_path / "s29.parquet")
    assert back.equals(table)
    validate_table(back, measures=["rain_mm"])
    assert read_mapping(back)["provider_to_canonical"]["% DEP / Departure (%)"] == "departure_pct"
    levels = {d["values"]: d["counts"] for d in pc.value_counts(back["area_level"]).to_pylist()}
    assert levels == {"district": 1, "taluk": 3, "hobli": 21, "region": 4, "state": 1}
    hobli = row(back, "BENGALURU URBAN / Anekal / Anekal_1")
    assert (hobli["rain_mm"], hobli["normal_mm"], hobli["departure_pct"]) == (848.0, 902.0, -6.0)
    assert (hobli["year"], hobli["coverage"], hobli["provenance"]) == (2021, None, "official")
    assert hobli["valid_at"] == datetime(2021, 12, 31, 18, 30, tzinfo=UTC)  # end of 2021, IST
    assert row(back, "State")["rain_mm"] == 1337.0 and row(back, "COASTAL")["normal_mm"] == 3518.0


def test_seasonal_2020_uses_annual_columns_and_2024_keeps_decimals():
    district = row(parse("2020", 2020), "BENGALURU URBAN")
    assert (district["normal_mm"], district["rain_mm"], district["departure_pct"]) == (
        846,
        1082,
        28,
    )
    assert row(parse("2024", 2024), "BENGALURU URBAN")["normal_mm"] == 845.6


def test_station_totals_are_a_separate_level():
    stations = parse("2023_stations", 2023)
    assert set(stations["area_level"].to_pylist()) == {"station"} and stations.num_rows == 15
    assert row(stations, "BAGALKOTE / BADAMI / ADAGAL (GP)")["rain_mm"] == 356.0


def test_unmarked_2025_layout_is_refused():
    with pytest.raises(IngestError, match="unmarked"):
        parse("2025", 2025)


def test_repeated_paths_are_flagged_and_blank_values_kept_null(tmp_path):
    def repeat(text):
        lines = text.splitlines(keepends=True)
        return "".join(lines[:4] + [lines[3]] + lines[4:])  # Anekal_1 twice

    table = ADAPTER.parse(edited(tmp_path, "2021", 2021, repeat), CONFIG, year=2021)
    flags = table.filter(pc.equal(table["area_id"], "BENGALURU URBAN / Anekal / Anekal_1"))
    assert flags["quality_flags"].to_pylist() == [["duplicate"], ["duplicate"]]

    def blank(text):
        return text.replace("Anekal_1,902,848", "Anekal_1,902,", 1)

    missing = row(
        ADAPTER.parse(edited(tmp_path, "2021", 2021, blank), CONFIG, year=2021),
        "BENGALURU URBAN / Anekal / Anekal_1",
    )
    assert (missing["rain_mm"], missing["missing_reason"]) == (None, "not_reported")


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s29.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "int64": "int64"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_empty_and_changed_files_rejected(tmp_path):
    for edit, match in (
        (lambda t: t.splitlines(keepends=True)[0], "empty"),
        (lambda t: t.replace("Normal (mm)", "Normal (cm)", 1), "columns changed"),
        (lambda t: t.replace("\nT,Anekal", "\nX,Anekal", 1), "marker"),
        (lambda t: t.replace("Anekal_1,902,848", "Anekal_1,902,lots", 1), "not a number"),
        (lambda t: t.replace("Anekal_1,902,848", "Anekal_1,902,-5", 1), "negative"),
    ):
        with pytest.raises(IngestError, match=match):
            ADAPTER.parse(edited(tmp_path, "2021", 2021, edit), CONFIG, year=2021)


def test_disabled_source_fails_closed_and_years_checked():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(sample("2021"), 2021), off, year=2021)
    with pytest.raises(ValueError, match="2017"):
        S29("ka", years=(2017,))


def test_fetch_waits_between_published_files(tmp_path):
    seen: list[str] = []
    pauses: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=sample("2021").read_bytes())

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S29",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=3, max_bytes=1024**2),
        raw_root=tmp_path,
    )
    S29("ka", years=(2021, 2022), fetcher=fetcher, pause=pauses.append).fetch(ctx)
    assert seen == [FILES[2021], FILES[2022]] and pauses == [PAUSE_S]
