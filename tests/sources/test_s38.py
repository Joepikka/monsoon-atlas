"""T149: blocked Delhi Open Transit Data cannot fetch, parse or publish rows."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from atlas.config import SourceConfig
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s38 import S38

ROOT = Path(__file__).resolve().parents[2]
CONFIG = SourceConfig(
    source_id="S38",
    name="Delhi Open Transit Data",
    verify_task="T148",
    cost="free_with_key",
    secret_env="OTD_API_KEY",
)


def test_source_and_schema_remain_disabled():
    schema = json.loads((ROOT / "schemas/s38.json").read_text("utf-8"))
    assert not CONFIG.enabled
    assert (schema["source_id"], schema["status"], schema["fields"]) == ("S38", "disabled", [])


@pytest.mark.parametrize("force_enabled", [False, True])
def test_no_io_even_if_config_is_force_enabled(tmp_path, monkeypatch, force_enabled):
    def no_network(*args, **kwargs):
        pytest.fail("Blocked S38 attempted network access")

    monkeypatch.setattr(httpx.Client, "send", no_network)
    ctx = FetchContext(
        source_id="S38",
        state="dl",
        run_id="blocked-s38",
        requested_at=datetime.now(UTC),
        raw_root=tmp_path / "absent",
        budget=Budget(max_requests=1, max_bytes=1),
    )
    raw = RawArtifact(
        sha256="0" * 64,
        path=tmp_path / "absent.pb",
        fetched_at=datetime.now(UTC),
        media_type="application/x-protobuf",
        response_status=200,
        source_url="https://otd.delhi.gov.in/api/realtime/VehiclePositions.pb",
        schema_mapping_version="s38-v1",
    )
    config = CONFIG.model_copy(update={"enabled": force_enabled})
    with pytest.raises(SourceUnavailable, match="T148"):
        S38().fetch(ctx)
    with pytest.raises(SourceUnavailable, match="T148"):
        S38().parse(raw, config)
    assert not ctx.raw_root.exists() and not raw.path.exists()
