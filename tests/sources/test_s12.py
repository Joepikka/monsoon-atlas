"""T064 acceptance: the S12 adapter round trip preserves units, IDs and epochs on a real CelesTrak
OMM response (local raw file, skipped in CI: element sets are not republished, D109); 6-digit
catalog numbers survive; stale elements are flagged; malformed, empty and changed responses
fail; a disabled source fails closed; fetch never retries."""

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
from atlas.ingest.base import FetchError, IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s12 import HOSTS, MEASURES, S12

ROOT = Path(__file__).resolve().parents[2]
# T063 e08, local only: no licence is published, so the response is not committed (D109).
SAMPLE = (
    ROOT
    / "data"
    / "raw"
    / "S12"
    / "2026-11-09"
    / ("9caeaaa6a63aff21151db059d56fcbef87cd01e9a0b07d76142f9d0e7b9f975e.json")
)
pytestmark = pytest.mark.skipif(not SAMPLE.exists(), reason="CelesTrak raw data is local only")
FETCHED = datetime(2026, 11, 9, 7, 32, 28, 652987, tzinfo=UTC)  # retrieval of the sample
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S12")
ADAPTER = S12("ka")


def artifact(path: Path, fetched: datetime = FETCHED) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=fetched,
        media_type="application/json",
        response_status=200,
        source_url="https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json",
        schema_mapping_version="s12-v1",
    )


def edited(tmp_path: Path, edit) -> RawArtifact:
    out = tmp_path / SAMPLE.name
    out.write_text(json.dumps(edit(json.loads(SAMPLE.read_text("utf-8")))), encoding="utf-8")
    return artifact(out)


def parse(raw: RawArtifact):
    return ADAPTER.parse(raw, CONFIG)


def test_roundtrip_preserves_units_ids_and_epochs(tmp_path):
    table = parse(artifact(SAMPLE))
    pq.write_table(table, tmp_path / "s12.parquet")
    back = pq.read_table(tmp_path / "s12.parquet")
    assert back.equals(table)
    validate_table(back)
    assert read_mapping(back)["provider_to_canonical"]["NORAD_CAT_ID"] == "norad_id"
    assert back.num_rows == 19 and len(set(back["record_id"].to_pylist())) == 19
    iss = back.filter(pc.equal(back["norad_id"], 25544)).to_pylist()[0]
    assert (iss["name"], iss["object_id"]) == ("ISS (ZARYA)", "1998-067A")
    assert iss["epoch_at"] == datetime(2026, 11, 8, 4, 12, 35, 430048, tzinfo=UTC)
    assert iss["valid_at"] == iss["epoch_at"] and iss["available_at"] == FETCHED
    assert (iss["mean_motion_rev_day"], iss["inclination_deg"]) == (15.49256954, 51.632)
    assert (iss["provenance"], iss["redistribution_allowed"]) == ("official", False)
    assert iss["tle_line1"] is None and iss["tle_line2"] is None
    assert back["quality_flags"].to_pylist() == [[]] * 19


def test_six_digit_catalog_numbers_are_kept():
    names = parse(artifact(SAMPLE)).filter(pc.greater(pc.field("norad_id"), 99999))["name"]
    assert sorted(names.to_pylist()) == [
        "CREW DRAGON 13",
        "DRAGON CRS-35",
        "PROGRESS-MS 35",
        "SOYUZ-MS 29",
    ]


def test_elements_older_than_seven_days_are_flagged_stale():
    later = artifact(SAMPLE, datetime(2026, 11, 15, 3, 12, 35, tzinfo=UTC))
    flags = dict(
        zip(*(parse(later)[c].to_pylist() for c in ("name", "quality_flags")), strict=True)
    )
    assert flags["ISS (ZARYA)"] == []  # epoch 8 Nov 04:12: 6 days 23 hours old
    assert flags["KNACKSAT-2"] == ["stale"]  # epoch 7 Nov 05:33: more than 7 days old


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s12.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "int64": "int64"}
    names["timestamp[us, tz=UTC]"] = "timestamp"
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_copy_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(SAMPLE.read_bytes()[:500])
    with pytest.raises(IngestError, match="not JSON"):
        parse(artifact(broken))


def test_empty_response_rejected(tmp_path):
    with pytest.raises(IngestError, match="empty"):
        parse(edited(tmp_path, lambda b: []))


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b[0].pop("MEAN_MOTION") and b,
        lambda b: b[0].update(ECCENTRICITY=1.2) or b,
        lambda b: b[0].update(INCLINATION=181.0) or b,
    ],
    ids=["missing element", "eccentricity", "inclination"],
)
def test_changed_columns_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        parse(edited(tmp_path, change))


def test_disabled_source_fails_closed_and_group_checked():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(SAMPLE), off)
    with pytest.raises(ValueError, match="GROUP"):
        S12("ka", group="stations&FORMAT=tle")


def context(tmp_path) -> FetchContext:
    return FetchContext(
        source_id="S12",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=5, max_bytes=1024**2),
        raw_root=tmp_path,
    )


def fetcher(tmp_path, handler, **kwargs) -> Fetcher:
    return Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler), **kwargs)


def test_fetch_requires_a_fetcher_without_retries(tmp_path):
    def ok(request):
        return httpx.Response(200, content=SAMPLE.read_bytes())

    with pytest.raises(ValueError, match="retries"):
        S12("ka", fetcher=fetcher(tmp_path, ok)).fetch(context(tmp_path))


def test_fetch_uses_omm_json_and_stops_on_the_first_error(tmp_path):
    seen: list[str] = []

    def ok(request):
        seen.append(str(request.url))
        return httpx.Response(200, content=SAMPLE.read_bytes())

    [raw] = S12("ka", fetcher=fetcher(tmp_path, ok, retry_delays=())).fetch(context(tmp_path))
    assert parse_qs(urlsplit(seen[0]).query) == {"GROUP": ["stations"], "FORMAT": ["json"]}
    assert ADAPTER.parse(raw, CONFIG).num_rows == 19

    calls: list[int] = []

    def busy(request):
        calls.append(1)
        return httpx.Response(503)

    adapter = S12("ka", fetcher=fetcher(tmp_path / "b", busy, retry_delays=()))
    with pytest.raises(FetchError, match="503"):
        adapter.fetch(context(tmp_path / "b"))
    assert calls == [1]  # D109: no retry after a non-200 response
