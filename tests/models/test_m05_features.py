"""T101 acceptance: M05 target and lag rules hold on real IMD rain (S08 1981-2024, local raw;
skipped in CI); a future-data mutation cannot change a feature; a blocked model exports nothing."""

import json
from datetime import date
from functools import cache
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pytest

pytest.importorskip("shapely")
pytest.importorskip("scipy")

from atlas.config import load_state  # noqa: E402
from atlas.contracts import RawArtifact  # noqa: E402
from atlas.features import m05  # noqa: E402
from atlas.ingest.base import SourceUnavailable  # noqa: E402
from atlas.ingest.s17 import S17  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
KA = load_state(ROOT / "configs" / "states" / "ka.yaml")


def artifact(source: str, eid: str) -> RawArtifact:
    manifest = json.loads((ROOT / f"tests/fixtures/{source}/manifest.json").read_text("utf-8"))
    e = next(x for x in manifest["evidence"] if x["id"] == eid)
    if not (RAW / e["raw_path"]).exists():
        pytest.skip("raw evidence is local only")
    return RawArtifact(
        sha256=e["sha256"],
        path=RAW / e["raw_path"],
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="test",
    )


@cache
def monthly() -> pa.Table:
    try:
        raws = m05.year_artifacts(RAW, range(1981, 2025))
    except SourceUnavailable:
        pytest.skip("S08 1981-2024 year files are local only")
    districts = S17("ka").parse(
        artifact("s17", "e06"), KA.source("S17"), adm1=artifact("s17", "e05")
    )
    return m05.district_monthly_rain(raws, districts)


@cache
def spi() -> pa.Table:
    return m05.spi_table(monthly())


@cache
def features() -> pa.Table:
    return m05.feature_rows(spi())


def test_monthly_rain_covers_30_districts_and_44_years():
    t = monthly()
    assert t.num_rows == 30 * 44 * 12
    assert len(set(t["place_id"].to_pylist())) == 30
    assert pc.min(t["rain_mm"]).as_py() >= 0
    blr = t.filter(
        pc.and_(pc.equal(t["name"], "Bangalore"), pc.equal(t["month"], pa.scalar(date(2024, 1, 1))))
    )
    yearly = t.filter(pc.equal(t["name"], "Bangalore")).to_pylist()
    total_2024 = sum(r["rain_mm"] for r in yearly if r["month"].year == 2024)
    assert blr.num_rows == 1 and 700 < total_2024 < 1400  # IMD 2024, Bengaluru Urban


def test_spi3_is_standard_normal_in_the_reference_period():
    t = spi().to_pylist()
    ref = np.array(
        [r["spi3"] for r in t if 1981 <= r["month"].year <= 2010 and r["spi3"] is not None]
    )
    assert abs(ref.mean()) < 0.1 and 0.85 < ref.std() < 1.15
    assert all(r["spi3"] is None for r in t if r["month"] < date(1981, 3, 1))  # needs 3 months


def test_target_and_lag_rules():
    f = features().to_pylist()
    assert f and all(r["known_until"] < r["target_month"] for r in f)
    assert all(r["target_drought"] == (r["target_spi3"] < -1.0) for r in f)
    by_key = {(r["place_id"], r["target_month"]): r for r in f}
    for r in f[:500]:
        prev = by_key.get((r["place_id"], r["known_until"]))
        if prev:
            assert (
                r["spi3_lag1"] == prev["target_spi3"]
            )  # last month's SPI-3 is this month's feature
    issue = f[0]["issue_at"]
    assert issue.hour == 18 and issue.minute == 30  # 00:00 IST on day 1, in UTC


def test_future_data_mutation_cannot_change_features():
    base = spi()
    month = date(2020, 6, 1)
    rain = base["rain_mm"].to_pylist()
    hit = [
        i
        for i, (p, m) in enumerate(
            zip(base["place_id"].to_pylist(), base["month"].to_pylist(), strict=True)
        )
        if m == month
    ]
    for i in hit:
        rain[i] = rain[i] * 10 + 500  # a wild June 2020
    mutated = m05.spi_table(
        base.select(["place_id", "name", "month", "rain_mm"]).set_column(
            3, "rain_mm", pa.array(rain)
        )
    )
    before = {(r["place_id"], r["target_month"]): r for r in m05.feature_rows(base).to_pylist()}
    after = {(r["place_id"], r["target_month"]): r for r in m05.feature_rows(mutated).to_pylist()}
    key = next(k for k in before if k[1] == month)
    assert after[key]["spi3_lag1"] == before[key]["spi3_lag1"]  # features end in May
    assert after[key]["target_spi3"] != before[key]["target_spi3"]  # only the target moves


def test_gate_and_blocked_export(tmp_path):
    ok = m05.gate(monthly(), verified_taluks=False)
    assert (
        ok["status"] == "ok" and ok["years"] == [1981, 2024] and ok["unit"].startswith("district")
    )
    short = monthly().filter(pc.greater_equal(monthly()["month"], pa.scalar(date(2000, 1, 1))))
    blocked = m05.gate(short, verified_taluks=False)
    assert blocked["status"] == "blocked"
    with pytest.raises(SourceUnavailable, match="blocked"):
        m05.export_predictions(blocked, pa.table({"place_id": ["x"], "spi3": [0.0]}))
    digest = m05.write_split_manifest(tmp_path / "m05_splits.json")
    saved = json.loads((tmp_path / "m05_splits.json").read_text("utf-8"))
    assert saved["sha256"] == digest
    assert [s["test_start"] for s in saved["splits"]] == ["2017-01-01", "2019-01-01", "2020-01-01"]
    assert all(s["train_end"] == "2016-09-30" for s in saved["splits"])
