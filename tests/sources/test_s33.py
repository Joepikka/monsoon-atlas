"""T116: unavailable S33 never reads files, fetches data or produces observations."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s33 import S33

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_state(ROOT / "configs/states/kl.yaml").source("S33")


def test_blocked_source_and_schema_stay_disabled():
    spec = json.loads((ROOT / "schemas/s33.json").read_text("utf-8"))
    assert not CONFIG.enabled
    assert (spec["source_id"], spec["status"]) == ("S33", "disabled")
    assert spec["fields"] == []  # no unverified upstream schema is invented


@pytest.mark.parametrize("force_enabled", [False, True])
def test_fetch_and_parse_fail_before_network_or_file_access(tmp_path, monkeypatch, force_enabled):
    def no_request(*args, **kwargs):
        pytest.fail("A blocked source attempted a network request")

    monkeypatch.setattr(httpx.Client, "send", no_request)
    raw_root = tmp_path / "not-created"
    ctx = FetchContext(
        source_id="S33",
        state="kl",
        run_id="blocked-s33",
        requested_at=datetime.now(UTC),
        raw_root=raw_root,
        budget=Budget(max_requests=1, max_bytes=1),
    )
    raw = RawArtifact(
        sha256="0" * 64,
        path=tmp_path / "absent.pdf",
        fetched_at=datetime.now(UTC),
        media_type="application/pdf",
        response_status=200,
        source_url="https://dams.kseb.in/",
        schema_mapping_version="s33-v1",
    )
    config = CONFIG.model_copy(update={"enabled": force_enabled})
    with pytest.raises(SourceUnavailable, match="T115"):
        S33().fetch(ctx)
    with pytest.raises(SourceUnavailable, match="T115"):
        S33().parse(raw, config)
    assert not raw_root.exists() and not raw.path.exists()
