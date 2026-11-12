"""T120: blocked Kerala 2018 flood dataset cannot fetch, parse or publish rows."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s35 import S35

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_state(ROOT / "configs/states/kl.yaml").source("S35")


def test_source_and_schema_remain_disabled():
    schema = json.loads((ROOT / "schemas/s35.json").read_text("utf-8"))
    assert not CONFIG.enabled
    assert (schema["source_id"], schema["status"], schema["fields"]) == ("S35", "disabled", [])


@pytest.mark.parametrize("force_enabled", [False, True])
def test_no_io_even_if_config_is_force_enabled(tmp_path, monkeypatch, force_enabled):
    def no_network(*args, **kwargs):
        pytest.fail("Blocked S35 attempted network access")

    monkeypatch.setattr(httpx.Client, "send", no_network)
    ctx = FetchContext(
        source_id="S35",
        state="kl",
        run_id="blocked-s35",
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
        source_url="https://www.kaggle.com/datasets",
        schema_mapping_version="s35-v1",
    )
    config = CONFIG.model_copy(update={"enabled": force_enabled})
    with pytest.raises(SourceUnavailable, match="T119"):
        S35().fetch(ctx)
    with pytest.raises(SourceUnavailable, match="T119"):
        S35().parse(raw, config)
    assert not ctx.raw_root.exists() and not raw.path.exists()
