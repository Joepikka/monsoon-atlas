"""T056 acceptance: the S07 adapter round trip preserves units, IDs and source timestamps on real
NASA POWER responses (no use restrictions, committed fixtures); -999 is decoded to null with a
reason; mixed products are split by fetch and refused by parse; malformed, empty and changed
responses fail; a disabled source fails closed."""

import hashlib
import json
from datetime import UTC, date, datetime
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
from atlas.ingest.s07 import HOSTS, MEASURES, PAUSE_S, S07

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
JULY = FIX / "s07_nasa_power_bengaluru_2024-07.json"  # T055 e16: MERRA2, SYN1DEG
JAN_1990 = FIX / "s07_nasa_power_bengaluru_1990-01.json"  # T055 e20: MERRA2, SRB
MIXED = FIX / "s07_nasa_power_bengaluru_2026-09_11.json"  # T055 e21: MERRA2 and GEOSIT
FETCHED = datetime(2026, 11, 9, 6, 47, 5, 330842, tzinfo=UTC)  # retrieval of JULY (e16)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S07")
POINT = (12.97, 77.59)
ADAPTER = S07("ka", POINT, date(2024, 7, 1), date(2024, 7, 31))
FILL = -999.0


def artifact(path: Path) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url="https://power.larc.nasa.gov/api/temporal/daily/point",
        schema_mapping_version="s07-v1",
    )


def edited(tmp_path: Path, edit, source: Path = JULY) -> RawArtifact:
    out = tmp_path / source.name
    out.write_text(json.dumps(edit(json.loads(source.read_text("utf-8")))), encoding="utf-8")
    return artifact(out)


def parse(raw: RawArtifact):
    return ADAPTER.parse(raw, CONFIG)


def row(table, day: date) -> dict:
    return table.filter(pc.equal(table["date_local"], day)).to_pylist()[0]


def test_roundtrip_preserves_units_ids_products_and_timestamps(tmp_path):
    table = parse(artifact(JULY))
    pq.write_table(table, tmp_path / "s07.parquet")
    back = pq.read_table(tmp_path / "s07.parquet")
    assert back.equals(table)
    validate_table(back, measures=["rain_mm", "tmean_c"])
    assert read_mapping(back)["provider_to_canonical"]["ALLSKY_SFC_SW_DWN"] == "solar_mj_m2"
    assert back.num_rows == 31 and len(set(back["record_id"].to_pylist())) == 31
    first = row(back, date(2024, 7, 1))
    assert first["cell_id"] == "power_12.9700N_77.5900E"
    assert (first["met_product"], first["solar_product"], first["api_version"]) == (
        "MERRA2",
        "SYN1DEG",
        "v2.10.3",
    )
    assert (first["rain_mm"], first["tmean_c"], first["solar_mj_m2"]) == (1.07, 22.5, 12.11)
    assert first["provenance"] == "model" and first["issued_at"] is None
    assert first["available_at"] == FETCHED == first["fetched_at"]
    assert first["valid_at"] == datetime(2024, 7, 2, tzinfo=UTC)  # end of the UTC day
    assert first["missing_reason"] is None and first["solar_missing_reason"] is None


def test_older_solar_product_is_recorded():
    table = S07("ka", POINT, date(1990, 1, 1), date(1990, 1, 31)).parse(artifact(JAN_1990), CONFIG)
    assert set(table["met_product"].to_pylist()) == {"MERRA2"}
    assert set(table["solar_product"].to_pylist()) == {"SRB"}


def test_mixed_products_are_refused():
    with pytest.raises(IngestError, match="split"):
        parse(artifact(MIXED))


def test_fill_values_decode_to_null_with_reasons(tmp_path):
    def gaps(body):
        p = body["properties"]["parameter"]
        for day in ("20240729", "20240730", "20240731"):
            p["ALLSKY_SFC_SW_DWN"][day] = FILL  # solar lags months behind
        p["T2M"]["20240731"] = FILL  # newest day not yet out
        p["PRECTOTCORR"]["20240710"] = FILL  # a gap inside the record
        return body

    table = parse(edited(tmp_path, gaps))
    lag = row(table, date(2024, 7, 29))
    assert (lag["solar_mj_m2"], lag["solar_missing_reason"]) == (None, "not_yet_available")
    assert lag["rain_mm"] is not None and lag["missing_reason"] is None  # rain and T2M kept
    last = row(table, date(2024, 7, 31))
    assert (last["rain_mm"], last["tmean_c"], last["missing_reason"]) == (
        None,
        None,
        "not_yet_available",
    )
    gap = row(table, date(2024, 7, 10))
    assert (gap["rain_mm"], gap["tmean_c"], gap["missing_reason"]) == (
        None,
        None,
        "out_of_coverage",
    )
    assert gap["quality_flags"] == ["missing"] and gap["solar_mj_m2"] is not None
    assert FILL not in table["rain_mm"].to_pylist() + table["solar_mj_m2"].to_pylist()


def test_negative_values_are_rejected(tmp_path):
    def bad(body):
        p = body["properties"]["parameter"]
        p["PRECTOTCORR"]["20240705"] = -0.4
        p["ALLSKY_SFC_SW_DWN"]["20240706"] = -1.0
        return body

    table = parse(edited(tmp_path, bad))
    rain = row(table, date(2024, 7, 5))
    assert (rain["rain_mm"], rain["missing_reason"], rain["quality_flags"]) == (
        None,
        "quality_rejected",
        ["out_of_range"],
    )
    sun = row(table, date(2024, 7, 6))
    assert (sun["solar_mj_m2"], sun["solar_missing_reason"]) == (None, "quality_rejected")
    assert sun["rain_mm"] is not None


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s07.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "date32[day]": "date32"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_copy_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(JULY.read_bytes()[:500])
    with pytest.raises(IngestError, match="not JSON"):
        parse(artifact(broken))


def test_empty_response_rejected(tmp_path):
    with pytest.raises(IngestError, match="empty"):
        parse(edited(tmp_path, lambda b: b["properties"].update(parameter={}) or b))


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["parameters"]["ALLSKY_SFC_SW_DWN"].update(units="kW-hr/m^2/day") or b,
        lambda b: b["properties"]["parameter"].pop("T2M") and b,
        lambda b: b["header"].update(time_standard="LST") or b,
        lambda b: b["header"].update(sources=["MERRA2", "FLASHFlux"]) or b,
        lambda b: b["header"].pop("fill_value") and b,
    ],
    ids=["unit", "missing column", "not utc", "unknown product", "no fill value"],
)
def test_changed_columns_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        parse(edited(tmp_path, change))


def test_disabled_source_fails_closed_and_dates_checked():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(JULY), off)
    with pytest.raises(ValueError, match="1981"):
        S07("ka", POINT, date(1980, 12, 31), date(1981, 1, 31))


def context(tmp_path) -> FetchContext:
    return FetchContext(
        source_id="S07",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=40, max_bytes=4 * 1024**2),
        raw_root=tmp_path,
    )


def switching_power(switch: str, seen: list[dict]):
    """Serves slices of the real Sep-Nov 2026 response (T055 e21); the header names MERRA2 before
    `switch` and GEOSIT from it, both when a range spans it (a test switch day, not a claim)."""
    real = json.loads(MIXED.read_text("utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        q = {k: v[0] for k, v in parse_qs(urlsplit(str(request.url)).query).items()}
        seen.append(q)
        body = json.loads(json.dumps(real))
        body["header"].update(start=q["start"], end=q["end"])
        for values in body["properties"]["parameter"].values():
            for day in list(values):
                if not q["start"] <= day <= q["end"]:
                    del values[day]
        body["header"]["sources"] = [
            name
            for name, used in (("MERRA2", q["start"] < switch), ("GEOSIT", q["end"] >= switch))
            if used
        ]
        return httpx.Response(200, json=body)

    return handler


def test_fetch_splits_ranges_until_each_names_one_product(tmp_path):
    seen: list[dict] = []
    pauses: list[float] = []
    fetcher = Fetcher(
        RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(switching_power("20261005", seen))
    )
    adapter = S07("ka", POINT, date(2026, 9, 1), date(2026, 11, 7), fetcher, pauses.append)
    parts = adapter.fetch(context(tmp_path))
    assert seen[0]["community"] == "AG" and seen[0]["time-standard"] == "UTC"
    assert seen[0]["parameters"] == "PRECTOTCORR,T2M,ALLSKY_SFC_SW_DWN"
    assert pauses == [PAUSE_S] * (len(seen) - 1)  # D106: spaced calls
    tables = [adapter.parse(p, CONFIG) for p in parts]
    days = sorted(d for t in tables for d in t["date_local"].to_pylist())
    assert days[0] == date(2026, 9, 1) and days[-1] == date(2026, 11, 7)
    assert len(days) == len(set(days)) == 68  # every day once, no overlap
    for t in tables:
        assert len(set(t["met_product"].to_pylist())) == 1
    switch = next(t for t in tables if date(2026, 10, 5) in t["date_local"].to_pylist())
    assert set(switch["met_product"].to_pylist()) == {"GEOSIT"}


def test_fetch_refuses_a_single_day_that_names_two_products(tmp_path):
    def always_mixed(request: httpx.Request) -> httpx.Response:
        body = json.loads(MIXED.read_text("utf-8"))
        return httpx.Response(200, json=body)

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(always_mixed))
    adapter = S07("ka", POINT, date(2026, 10, 1), date(2026, 10, 2), fetcher, lambda _: None)
    with pytest.raises(IngestError, match="two products"):
        adapter.fetch(context(tmp_path))
