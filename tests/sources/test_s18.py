"""T022 acceptance: S18 is blocked (T021), so the adapter fails closed and produces zero records."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s18 import S18

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S18")


def test_source_is_disabled_in_config():
    assert not CONFIG.enabled and CONFIG.verified_by is None


def test_fetch_and_parse_fail_closed(tmp_path):
    ctx = FetchContext(
        source_id="S18",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=1, max_bytes=1),
        raw_root=tmp_path,
    )
    with pytest.raises(SourceUnavailable, match="robots.txt"):
        S18().fetch(ctx)
    raw = RawArtifact(
        sha256="0" * 64,
        path=tmp_path / "none.pbf",
        fetched_at=datetime.now(UTC),
        media_type="application/octet-stream",
        response_status=200,
        source_url="https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf",
        schema_mapping_version="s18-v1",
    )
    with pytest.raises(SourceUnavailable):
        S18().parse(raw, CONFIG)
    assert not raw.path.exists()  # nothing was downloaded or written
