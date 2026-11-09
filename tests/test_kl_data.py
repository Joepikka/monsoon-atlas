"""T226 (T129 bootstrap): state isolation and fail-closed Kerala source registration.

These checks do not certify the full T129 label audit or M07 training readiness.
"""

from pathlib import Path

import pytest

from atlas.config import load_state, load_yaml
from atlas.ingest.discovery import Discovery

ROOT = Path(__file__).resolve().parents[1]


def test_kerala_config_exists():
    assert (ROOT / "configs/states/kl.yaml").is_file(), "T226 Kerala bootstrap is missing"


@pytest.fixture
def kl():
    path = ROOT / "configs/states/kl.yaml"
    assert path.is_file(), "T226 Kerala bootstrap is missing"
    return load_state(path)


def test_state_paths_cannot_mix_karnataka_and_kerala(kl):
    ka = load_state(ROOT / "configs/states/ka.yaml")
    assert (ka.state_id, kl.state_id, kl.name) == ("ka", "kl", "Kerala")
    assert (kl.storage_tz, kl.display_tz) == ("UTC", "Asia/Kolkata")
    for kind in ("raw_root", "clean_root", "publish_root"):
        ka_path, kl_path = getattr(ka.paths, kind), getattr(kl.paths, kind)
        assert not kl_path.is_absolute()
        assert ".." not in kl_path.parts
        assert kl_path.parts[-1] == "kl"
        assert ka_path != kl_path and ka_path not in kl_path.parents
        assert kl_path not in ka_path.parents


def test_kerala_does_not_enable_unimplemented_or_ka_only_adapters(kl):
    assert {"S32", "S33", "S34", "S35", "S36", "S37", "S40", "S41", "S43"} <= {
        source.source_id for source in kl.sources
    }
    assert {source.source_id for source in kl.sources if source.enabled} == {"S32", "S36"}
    # Karnataka discovery is not evidence for Kerala wards or flood labels.
    assert kl.source("S40").verified_by is None
    assert kl.source("S43").verified_by is None
    with pytest.raises(KeyError):
        kl.source("S28")  # Karnataka reservoir source must not leak into Kerala.


@pytest.mark.parametrize("source_id", ["S32", "S34", "S35", "S36", "S37", "S41"])
def test_existing_discovery_references_belong_to_kerala(kl, source_id):
    source = kl.source(source_id)
    discovery = load_yaml(ROOT / source.verified_by, Discovery)
    assert discovery.source_id == source_id
    assert discovery.state == "kl"
    assert discovery.verify_task == source.verify_task
    # Only T114 (S32) and T122 (S36) are completed Kerala adapters; discovery alone enables nothing.
    assert source.enabled == (source_id in {"S32", "S36"})
    if source_id in {"S35", "S37", "S41"}:
        assert discovery.outcome == "blocked"
