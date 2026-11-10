"""T152: Delhi readiness gate. Failed: no real sample, so nothing is measured or claimed."""

import re
from pathlib import Path

from atlas.config import load_budgets, load_state, load_yaml
from atlas.ingest.discovery import Discovery

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs/studies/delhi-readiness.md").read_text("utf-8")
BUDGETS = load_budgets(ROOT / "configs/budgets.yaml")
S38 = load_yaml(ROOT / "configs/sources/s38.yaml", Discovery)
TRANSIT = (ROOT / "worker/src/transit.ts").read_text("utf-8")


def table(heading: str) -> list[list[str]]:
    section = PAGE.split(f"\n## {heading}", 1)[1].split("\n## ", 1)[0]
    rows = [[c.strip() for c in ln.strip("|").split("|")] for ln in section.splitlines()]
    return [r for r in rows if len(r) > 1 and r[0] and "---" not in r[0]][1:]


def test_gate_failed_and_nothing_is_measured():
    assert "**Gate result: failed (not run).**" in PAGE
    assert "Continuous capture: unavailable. Live mode:\ndisabled." in PAGE
    rows = table("Benchmark with a real sample")
    assert [r[0] for r in rows] == [
        "Worker CPU per request",
        "Worker memory",
        "Compressed snapshot blob",
        "Compressed daily history",
        "Hot, archive, replay counts",
    ]
    assert {r[2] for r in rows} == {"not measured", "not run"}
    assert S38.outcome == "blocked" and S38.access.status == "form_and_key_required_owner_step"


def test_chronology_is_not_frozen_and_no_dates_or_manifest_exist():
    assert {r[1] for r in table("Chronology")} == {"not frozen", "not written"}
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b", PAGE)
    assert not list((ROOT / "docs/studies").glob("*manifest*"))


def test_quota_simulation_is_within_the_configured_caps():
    ticks = 16 * 3600 // 60
    d1, workers = BUDGETS.cloudflare_d1, BUDGETS.cloudflare_workers
    expected = {
        "Polls per day (16 h at one per 60 s)": (ticks, 960),
        "D1 writes per day (one snapshot per tick)": (ticks, d1.writes_per_day),
        "Worker requests per day (one per tick)": (ticks, workers.requests_per_day),
        "Hot history, 7 days at 40 MB per day": (
            d1.hot_retention_days * 40,
            d1.database_mb,
        ),
    }
    rows = table("Quota simulation (arithmetic from `configs/budgets.yaml`; no feed involved)")
    assert [r[0] for r in rows] == list(expected)
    for (simulated, cap), row in zip(expected.values(), rows, strict=True):
        assert simulated <= cap
        assert [int(re.match(r"\d+", c)[0]) for c in row[1:]] == [simulated, cap]
    assert d1.hot_retention_days == 7
    assert "MAX_BLOB = 1024 * 1024" in (ROOT / "worker/src/ingest.ts").read_text("utf-8")


def test_live_mode_disabled_no_browser_key_and_time_zones():
    assert "available: false" in TRANSIT
    for path in [*(ROOT / "web/src").rglob("*"), ROOT / "web/index.html"]:
        if path.is_file():
            assert "OTD_API_KEY" not in path.read_text("utf-8"), path
    dl = load_state(ROOT / "configs/states/dl.yaml")
    assert (dl.storage_tz, dl.display_tz) == ("UTC", "Asia/Kolkata")
    # No GTFS file was read, so no trip ID exists to validate and none is claimed.
    assert next(f for f in S38.field_map if f.canonical == "trip_id").upstream is None
    assert "Owner-run capture windows with narrower claims, available only after H04" in PAGE
