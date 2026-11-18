"""T026/T269/T270: S23 is enabled for Karnataka onion only; other commodities refuse before I/O."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s23 import MAPPING_VERSION, S23, day_params

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_state(ROOT / "configs/states/ka.yaml").source("S23")


def test_source_and_schema_are_enabled_for_onion():
    schema = json.loads((ROOT / "schemas/s23.json").read_text("utf-8"))
    assert CONFIG.enabled and CONFIG.verified_by == "configs/sources/s23.yaml"
    assert CONFIG.verify_task == "T269" and CONFIG.secret_env == "DATA_GOV_IN_API_KEY"
    assert (schema["source_id"], schema["status"], schema["mapping_version"]) == (
        "S23",
        "enabled",
        MAPPING_VERSION,
    )
    names = [f["name"] for f in schema["fields"]]
    assert "modal_inr_quintal" in names and "market_id" in names


@pytest.mark.parametrize("commodity", ["Tomato", "Potato", "onion"])
def test_other_commodities_refuse_before_any_io(tmp_path, monkeypatch, commodity):
    def no_network(*args, **kwargs):
        pytest.fail("S23 attempted network access for an unverified commodity")

    monkeypatch.setattr(httpx.Client, "send", no_network)
    with pytest.raises(SourceUnavailable, match="H16"):
        S23(commodity=commodity)
    with pytest.raises(SourceUnavailable, match="H16"):
        day_params(date(2019, 1, 2), commodity)
    url = (
        "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24?"
        f"filters%5BArrival_Date%5D=02%2F01%2F2019&filters%5BCommodity%5D={commodity}"
        "&filters%5BState%5D=Karnataka&format=json&limit=1000&offset=0"
    )
    raw = RawArtifact(
        sha256="0" * 64,
        path=tmp_path / "absent.json",
        fetched_at=datetime.now(UTC),
        media_type="application/json",
        response_status=200,
        source_url=url,
        schema_mapping_version=MAPPING_VERSION,
    )
    with pytest.raises(SourceUnavailable, match="H16"):
        S23().parse(raw, CONFIG)
    assert not raw.path.exists()


def test_only_karnataka_is_in_scope():
    with pytest.raises(SourceUnavailable, match="Karnataka"):
        S23(state="kl")


def test_fetch_without_the_key_sends_nothing(tmp_path):
    from atlas.ingest.http import Fetcher
    from atlas.ingest.raw_store import RawStore

    ctx = FetchContext(
        source_id="S23",
        state="ka",
        run_id="no-key",
        requested_at=datetime.now(UTC),
        raw_root=tmp_path,
        budget=Budget(max_requests=1, max_bytes=1024),
    )
    fetcher = Fetcher(RawStore(tmp_path), {"api.data.gov.in"})
    with pytest.raises(SourceUnavailable, match="secret not configured"):
        S23([date(2019, 1, 2)], fetcher=fetcher).fetch(ctx)
    assert not any(tmp_path.iterdir())
