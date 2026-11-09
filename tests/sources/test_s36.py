"""T122 acceptance: the S36 adapter keeps the district totals of three real KSDMA memorandum tables
(flooded area as on 16-7-2018, fatalities for two periods) with document and page; malformed,
empty and changed PDFs fail; a disabled source fails closed. The PDFs are all rights reserved, so
they stay in data/raw and the real-PDF tests skip when that copy is absent (CI)."""

import json
from datetime import UTC, date, datetime
from functools import cache
from pathlib import Path

import httpx
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest import s36
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s36 import HOSTS, S36, TABLES

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CONFIG = load_state(ROOT / "configs" / "states" / "kl.yaml").source("S36")
EVIDENCE = {
    e["id"]: e
    for e in json.loads((ROOT / "tests/fixtures/s36/manifest.json").read_text("utf-8"))["evidence"]
}
FETCHED = datetime(2026, 11, 9, tzinfo=UTC)


def artifact(eid: str = "e06", path: Path | None = None) -> RawArtifact:
    e = EVIDENCE[eid]
    real = RAW / e["raw_path"]
    if path is None and not real.exists():
        pytest.skip("raw evidence is local only")
    return RawArtifact(
        sha256=e["sha256"],
        path=path or real,
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="s36-v1",
    )


@cache
def parsed(eid: str):
    return S36().parse(artifact(eid), CONFIG)


def cell(table, claim: str, district: str) -> dict:
    keep = pc.and_(pc.equal(table["claim_type"], claim), pc.equal(table["district_id"], district))
    return table.filter(keep).to_pylist()[0]


def test_memorandum1_roundtrip_keeps_published_districts(tmp_path):
    table = parsed("e06")
    pq.write_table(table, tmp_path / "s36.parquet")
    back = pq.read_table(tmp_path / "s36.parquet")
    assert back.equals(table)
    validate_table(back, measures=["value"])
    assert read_mapping(back)["provider_to_canonical"]["table header"] == "claim_type"
    assert back.num_rows == 7 + 14 and len(set(back["record_id"].to_pylist())) == 21
    area = cell(back, "flooded_area_ha", "Alleppey")  # published spelling kept, not mapped
    assert (area["value"], area["unit"], area["page"]) == (21799, "ha", 9)
    assert (area["event_date"], area["date_basis"]) == (date(2018, 7, 16), "as_on")
    assert area["valid_at"] == datetime(2018, 7, 15, 18, 30, tzinfo=UTC) == area["observed_at"]
    deaths = cell(back, "human_fatalities", "Kannur")
    assert (deaths["value"], deaths["unit"], deaths["page"]) == (22, "persons", 14)
    assert (deaths["event_date"], deaths["date_basis"]) == (None, "period_total")
    assert (deaths["period_start"], deaths["period_end"]) == (date(2018, 5, 29), date(2018, 7, 31))
    assert deaths["valid_at"] == datetime(2018, 7, 31, 18, 30, tzinfo=UTC)
    assert deaths["excerpt"] == "Kannur 22 88" and deaths["observed_at"] is None
    assert area["place_id"] is None and area["boundary_version"] is None
    assert area["provenance"] == "official" and area["redistribution_allowed"] is False
    assert area["published_at"] == datetime(2018, 8, 6, 18, 30, tzinfo=UTC)
    flooded = back.filter(pc.equal(back["claim_type"], "flooded_area_ha"))
    assert pc.sum(flooded["value"]).as_py() == 55007
    assert (
        pc.sum(
            pc.filter(back["value"], pc.not_equal(back["claim_type"], "flooded_area_ha"))
        ).as_py()
        == 138
    )


def test_memorandum2_fatalities_use_its_own_period():
    table = parsed("e07")
    assert table.num_rows == 14 and set(table["claim_type"].to_pylist()) == {"human_fatalities"}
    assert pc.sum(table["value"]).as_py() == 339
    thrissur = cell(table, "human_fatalities", "Thrissur")
    assert (thrissur["value"], thrissur["page"], thrissur["document_id"]) == (
        72,
        20,
        "Memorandum2-Floods-2018.pdf",
    )
    assert (thrissur["period_start"], thrissur["period_end"]) == (
        date(2018, 8, 1),
        date(2018, 8, 30),
    )
    assert "Kasaragode" in table["district_id"].to_pylist()  # spelling differs from memorandum 1


def test_malformed_and_empty_pdfs_fail(tmp_path):
    for name, data in (("bad.pdf", b"%PDF-1.4 not really"), ("empty.pdf", b"")):
        path = tmp_path / name
        path.write_bytes(data)
        with pytest.raises(IngestError):
            S36().parse(artifact("e06", path), CONFIG)


GOOD = "9\nDistrict Flooded Area (ha)\nAlleppey 10\nErnakulam 20\nTotal 30\n"


@pytest.fixture
def one_table(monkeypatch):
    monkeypatch.setattr(s36, "TABLES", (TABLES[0]._replace(rows=2),))

    def set_text(text):
        monkeypatch.setattr(s36, "page_text", lambda path, page: text)

    return set_text


def test_text_layer_edits_fail_closed(tmp_path, one_table):
    raw = artifact("e06", tmp_path / "x.pdf")
    one_table(GOOD)
    assert S36().parse(raw, CONFIG).num_rows == 2
    for bad in (
        GOOD.replace("Flooded Area (ha)", "Flooded Area (sq km)"),  # changed column
        GOOD.replace("Total 30", "Total 31"),  # rows no longer sum
        GOOD.replace("Total 30\n", ""),  # no Total row
        GOOD.replace("Ernakulam 20", "Ernakulam 2O"),  # unreadable row
        GOOD.replace("Ernakulam 20", "Alleppey 20"),  # duplicate district
        "",  # blank page
    ):
        one_table(bad)
        with pytest.raises(IngestError):
            S36().parse(raw, CONFIG)


def test_disabled_source_and_unknown_url_fail(tmp_path):
    raw = artifact("e06", tmp_path / "x.pdf")
    with pytest.raises(SourceUnavailable):
        S36().parse(raw, CONFIG.model_copy(update={"enabled": False}))
    with pytest.raises(IngestError):
        S36().parse(raw.model_copy(update={"source_url": "https://sdma.kerala.gov.in/x"}), CONFIG)


def test_fetch_gets_each_memorandum_once(tmp_path):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=b"%PDF-1.4", headers={"content-type": "application/pdf"})

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S36",
        state="kl",
        run_id="test",
        requested_at=FETCHED,
        budget=Budget(max_requests=2, max_bytes=1024),
        raw_root=tmp_path,
    )
    S36(fetcher=fetcher).fetch(ctx)
    assert seen == [EVIDENCE["e06"]["url"], EVIDENCE["e07"]["url"]]
    with pytest.raises(IngestError):
        S36().fetch(ctx)
