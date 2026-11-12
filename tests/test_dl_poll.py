"""T151: Delhi live poll stays fail-closed while S38 is blocked (H04); no feed, URL or key."""

import os
import re
import subprocess
from pathlib import Path

import pytest

from atlas.config import load_budgets, load_yaml
from atlas.ingest.discovery import Discovery

ROOT = Path(__file__).resolve().parents[1]
TRANSIT = (ROOT / "worker/src/transit.ts").read_text("utf-8")
BUDGETS = load_budgets(ROOT / "configs/budgets.yaml")


def const(name: str) -> int:
    return int(re.search(rf"export const {name} = (\d+);", TRANSIT)[1])


def shipped_text(*roots: str):
    for root in roots:
        for path in (ROOT / root).rglob("*"):
            if path.is_file() and not {"node_modules", "dist"} & set(path.parts):
                if path.suffix in {".ts", ".tsx", ".mjs", ".js", ".html", ".toml", ".json"}:
                    if path.name not in {"package-lock.json", "transit.test.mjs"}:
                        yield path, path.read_text("utf-8")


def test_poll_budget_fits_the_configured_caps():
    ticks = const("STUDY_HOURS") * 3600 // const("POLL_SECONDS")
    assert ticks == 960
    # One upstream call and one stored snapshot per tick.
    assert ticks <= BUDGETS.cloudflare_d1.writes_per_day
    assert ticks <= BUDGETS.cloudflare_workers.requests_per_day
    assert BUDGETS.cloudflare_workers.cron_triggers >= 1  # the one 60 s trigger, once enabled
    assert const("STALE_SECONDS") == 120


def test_live_mode_is_unavailable_and_says_why():
    assert "available: false" in TRANSIT
    assert "transit live mode unavailable: S38 blocked (H04)" in TRANSIT
    record = load_yaml(ROOT / "configs/sources/s38.yaml", Discovery)
    assert record.outcome == "blocked"


def test_no_poller_upstream_url_cron_or_key_binding_exists():
    assert not (ROOT / "worker/src/cron.ts").exists()
    assert "fetch(" not in TRANSIT and "http" not in TRANSIT
    assert "crons" not in (ROOT / "worker/wrangler.toml").read_text("utf-8")
    for path, text in shipped_text("worker", "web"):
        assert "otd.delhi.gov.in" not in text, path
        assert "transit.ts" not in text, path  # nothing wires the module in yet


def test_credential_name_is_absent_from_client_and_worker_code():
    for path, text in shipped_text("worker", "web"):
        assert "OTD_API_KEY" not in text, path
        assert not re.search(r"VehiclePositions", text), path


def test_worker_transit_rules_run_under_node():
    node_dir = ROOT / ".tools/node/node-v22.16.0-win-x64"
    if not (node_dir / "node.exe").exists():
        pytest.skip("Optional pinned Worker toolchain is not installed in core-only CI")
    result = subprocess.run(
        [
            str(node_dir / "node.exe"),
            "--experimental-strip-types",
            "--test",
            "tests/transit.test.mjs",
        ],
        cwd=ROOT / "worker",
        env={**os.environ, "TEMP": str(ROOT / ".cache/tmp"), "TMP": str(ROOT / ".cache/tmp")},
        capture_output=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
