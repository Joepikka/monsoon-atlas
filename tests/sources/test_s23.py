"""T026: an open licence does not enable prices whose units are unknown."""

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_state(ROOT / "configs/states/ka.yaml").source("S23")


def test_source_and_schema_remain_disabled():
    path = ROOT / "schemas/s23.json"
    assert path.exists(), "T026 source contract is missing"
    schema = json.loads(path.read_text("utf-8"))
    assert not CONFIG.enabled
    assert (schema["source_id"], schema["status"], schema["fields"]) == ("S23", "disabled", [])


@pytest.mark.parametrize("force_enabled", [False, True])
def test_no_io_even_if_config_is_force_enabled(tmp_path, monkeypatch, force_enabled):
    assert importlib.util.find_spec("atlas.ingest.s23") is not None, "T026 adapter is missing"
    adapter = importlib.import_module("atlas.ingest.s23").S23()

    def no_network(*args, **kwargs):
        pytest.fail("Blocked S23 attempted network access")

    monkeypatch.setattr(httpx.Client, "send", no_network)
    ctx = FetchContext(
        source_id="S23",
        state="ka",
        run_id="blocked-s23",
        requested_at=datetime.now(UTC),
        raw_root=tmp_path / "absent",
        budget=Budget(max_requests=1, max_bytes=1),
    )
    raw = RawArtifact(
        sha256="0" * 64,
        path=tmp_path / "absent.json",
        fetched_at=datetime.now(UTC),
        media_type="application/json",
        response_status=200,
        source_url="https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070",
        schema_mapping_version="s23-v1",
    )
    config = CONFIG.model_copy(update={"enabled": force_enabled})
    with pytest.raises(SourceUnavailable, match="unit"):
        adapter.fetch(ctx)
    with pytest.raises(SourceUnavailable, match="unit"):
        adapter.parse(raw, config)
    assert not ctx.raw_root.exists() and not raw.path.exists()
