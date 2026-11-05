"""T003 acceptance: reject unknown source, bad CRS and paid-provider config; CLI help exits 0;
unimplemented commands exit 2."""

import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from atlas.cli import app
from atlas.config import Budgets, SourceConfig, StateConfig, load_budgets, load_state, to_display
from atlas.contracts import (
    Budget,
    DatasetManifest,
    FetchContext,
    ManifestFile,
    RawArtifact,
    SplitManifest,
)

ROOT = Path(__file__).resolve().parents[1]
GOOD = {
    "source_id": "S01",
    "name": "Open-Meteo weather forecast",
    "verify_task": "T009",
    "cost": "free",
    "storage_crs": "EPSG:4326",
}
SHA = "a" * 64
NOW = datetime(2026, 11, 5, 6, 30, tzinfo=UTC)


# --- shipped configs -------------------------------------------------------------------------


def test_ka_config_loads_with_every_source_disabled():
    ka = load_state(ROOT / "configs/states/ka.yaml")
    assert ka.state_id == "ka"
    assert (ka.storage_tz, ka.display_tz) == ("UTC", "Asia/Kolkata")
    assert ka.sources and all(not s.enabled for s in ka.sources)
    assert ka.source("S28").verify_task == "T008"


def test_budgets_load_and_match_plan_caps():
    b = load_budgets(ROOT / "configs/budgets.yaml")
    assert b.workers_ai.neurons_per_day == 8000
    assert b.open_meteo.calls_per_day == 2000
    assert (b.duckdb.memory_limit_gb, b.duckdb.threads) == (4, 4)


# --- rejections ------------------------------------------------------------------------------


@pytest.mark.parametrize("bad_id", ["S99", "S00", "X01", "S1"])
def test_rejects_unknown_source(bad_id):
    with pytest.raises(ValidationError, match="unknown source id"):
        SourceConfig.model_validate({**GOOD, "source_id": bad_id})


@pytest.mark.parametrize("crs", ["EPSG:3857", "EPSG:32643", "WGS84", "epsg:4326"])
def test_rejects_bad_storage_crs(crs):
    with pytest.raises(ValidationError):
        SourceConfig.model_validate({**GOOD, "storage_crs": crs})


@pytest.mark.parametrize("cost", ["paid", "trial", "billing"])
def test_rejects_paid_provider(cost):
    with pytest.raises(ValidationError):
        SourceConfig.model_validate({**GOOD, "cost": cost})


def test_rejects_unknown_keys():
    with pytest.raises(ValidationError, match="Extra inputs"):
        SourceConfig.model_validate({**GOOD, "api_key": "secret"})
    budgets = load_budgets(ROOT / "configs/budgets.yaml").model_dump()
    budgets["open_meteo"]["unlimited"] = True
    with pytest.raises(ValidationError):
        Budgets.model_validate(budgets)


def test_cannot_enable_without_verify_evidence():
    with pytest.raises(ValidationError, match="cannot be enabled"):
        SourceConfig.model_validate({**GOOD, "enabled": True})
    ok = SourceConfig.model_validate(
        {**GOOD, "enabled": True, "verified_by": "docs/sources/s01.md"}
    )
    assert ok.enabled


def test_keyed_source_needs_env_name_not_value():
    with pytest.raises(ValidationError, match="needs secret_env"):
        SourceConfig.model_validate({**GOOD, "cost": "free_with_key"})
    with pytest.raises(ValidationError, match="NAME"):
        SourceConfig.model_validate({**GOOD, "cost": "free_with_key", "secret_env": "abc123xyz"})


def test_rejects_duplicate_sources_in_state():
    raw = load_state(ROOT / "configs/states/ka.yaml").model_dump(mode="json")
    raw["sources"].append(raw["sources"][0])
    with pytest.raises(ValidationError, match="duplicate"):
        StateConfig.model_validate(raw)


# --- contracts -------------------------------------------------------------------------------


def test_storage_timestamps_must_be_utc():
    ist = timezone(timedelta(hours=5, minutes=30))
    with pytest.raises(ValidationError, match="UTC"):
        FetchContext(
            source_id="S01",
            state="ka",
            run_id="r1",
            requested_at=datetime(2026, 11, 5, 12, 0, tzinfo=ist),
            budget=Budget(max_requests=1, max_bytes=1),
            raw_root=Path("data/raw/ka"),
        )
    with pytest.raises(ValidationError, match="UTC"):
        RawArtifact(
            sha256=SHA,
            path=Path("x"),
            fetched_at=datetime(2026, 11, 5),
            media_type="application/json",
            response_status=200,
            source_url="https://api.open-meteo.com/v1/forecast",
            schema_mapping_version="1",
        )


def test_display_is_asia_kolkata():
    assert to_display(NOW).utcoffset() == timedelta(hours=5, minutes=30)
    with pytest.raises(ValueError):
        to_display(datetime(2026, 11, 5))


def test_secrets_never_serialized_and_urls_carry_no_keys():
    ctx = FetchContext(
        source_id="S25",
        state="ka",
        run_id="r1",
        requested_at=NOW,
        budget=Budget(max_requests=1, max_bytes=1),
        raw_root=Path("data/raw/ka"),
        secrets={"NASA_FIRMS_MAP_KEY": "do-not-leak"},
    )
    assert "do-not-leak" not in ctx.model_dump_json()
    assert "do-not-leak" not in repr(ctx)
    with pytest.raises(ValidationError, match="credentials"):
        RawArtifact(
            sha256=SHA,
            path=Path("x"),
            fetched_at=NOW,
            media_type="text/csv",
            response_status=200,
            source_url="https://firms.modaps.eosdis.nasa.gov/api/area/csv?MAP_KEY=abc",
            schema_mapping_version="1",
        )


def test_manifest_total_bytes_must_match_files():
    files = (ManifestFile(path="a.parquet", sha256=SHA, bytes=10, rows=1),)
    kw = dict(release_id="r1", schema_version=1, data_revision="d1", published_at=NOW, files=files)
    assert DatasetManifest(**kw, total_bytes=10).total_bytes == 10
    with pytest.raises(ValidationError, match="total_bytes"):
        DatasetManifest(**kw, total_bytes=11)


def test_split_must_be_time_ordered():
    def r(a, b):
        return {"start": date(*a), "end": date(*b)}

    SplitManifest.model_validate(
        {
            "train": r((2017, 1, 1), (2022, 12, 31)),
            "tune": r((2023, 1, 1), (2023, 6, 30)),
            "test": r((2024, 1, 1), (2024, 12, 31)),
        }  # fmt: skip
    )
    with pytest.raises(ValidationError, match="time-ordered"):
        SplitManifest.model_validate(
            {
                "train": r((2017, 1, 1), (2024, 6, 30)),
                "tune": r((2023, 1, 1), (2023, 6, 30)),
                "test": r((2024, 1, 1), (2024, 12, 31)),
            }  # fmt: skip
        )


# --- CLI -------------------------------------------------------------------------------------

COMMANDS = {
    "ingest": ["--source", "S01", "--state", "ka", "--as-of", "2026-11-05T00:00:00Z"],
    "validate": ["--manifest", "m.json"],
    "features": ["--model", "M06", "--as-of", "2026-11-05T00:00:00Z"],
    "train": ["--model", "M06", "--split", "s.json"],
    "evaluate": ["--run", "r1"],
    "publish": ["--manifest", "m.json"],
    "replay": ["--place", "in:ka:ward:1:v1", "--as-of", "2026-11-05T00:00:00Z"],
    "audit": ["--scope", "all"],
}
runner = CliRunner()


IMPLEMENTED = ["quota"]  # T006


def test_cli_help_exits_0():
    result = subprocess.run(  # pin the child's encoding: help text has box-drawing characters
        [sys.executable, "-m", "atlas", "--help"],
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert result.returncode == 0
    for name in [*COMMANDS, *IMPLEMENTED]:
        assert name in result.stdout


@pytest.mark.parametrize("name", COMMANDS)
def test_each_command_help_exits_0(name):
    assert runner.invoke(app, [name, "--help"]).exit_code == 0


@pytest.mark.parametrize("name,args", COMMANDS.items())
def test_unimplemented_commands_exit_2(name, args):
    result = runner.invoke(app, [name, *args])
    assert result.exit_code == 2
    assert "not implemented" in result.output
