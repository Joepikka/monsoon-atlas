"""T150: Delhi study registration. The page must match the S24/S38 records; no study start."""

import re
from pathlib import Path

import pytest

from atlas.config import load_state, load_yaml
from atlas.ingest.discovery import Discovery

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs/studies/delhi.md").read_text("utf-8")
S38 = load_yaml(ROOT / "configs/sources/s38.yaml", Discovery)
S24 = load_yaml(ROOT / "configs/sources/s24.yaml", Discovery)


@pytest.fixture
def dl():
    return load_state(ROOT / "configs/states/dl.yaml")


def registration() -> dict[str, tuple[str, str]]:
    section = PAGE.split("\n## Registration", 1)[1].split("\n## ", 1)[0]
    rows = [[c.strip() for c in line.strip("|").split("|")] for line in section.splitlines()]
    return {
        r[0]: (r[1], r[2]) for r in rows if len(r) == 3 and r[0] != "Item" and "---" not in r[0]
    }


def study_ready(state) -> tuple[bool, str]:
    """The study may start only when S38 is enabled, verified and its record is not blocked."""
    s38 = state.source("S38")
    if not s38.enabled:
        return False, "S38 is disabled in dl.yaml"
    if S38.outcome != "available":
        return False, f"S38 outcome is {S38.outcome}"
    return True, ""


def test_delhi_is_isolated_from_the_other_states(dl):
    ka, kl = (load_state(ROOT / f"configs/states/{s}.yaml") for s in ("ka", "kl"))
    assert (dl.state_id, dl.name, dl.storage_tz, dl.display_tz) == (
        "dl",
        "Delhi",
        "UTC",
        "Asia/Kolkata",
    )
    for kind in ("raw_root", "clean_root", "publish_root"):
        path = getattr(dl.paths, kind)
        assert not path.is_absolute() and ".." not in path.parts and path.parts[-1] == "dl"
        assert path not in (getattr(ka.paths, kind), getattr(kl.paths, kind))
    with pytest.raises(KeyError):
        dl.source("S28")  # Karnataka reservoir source
    with pytest.raises(KeyError):
        dl.source("S32")  # Kerala dam source


def test_no_delhi_source_is_enabled_and_blocked_ones_point_at_their_records(dl):
    assert not any(s.enabled for s in dl.sources)
    for source, record in ((dl.source("S24"), S24), (dl.source("S38"), S38)):
        assert record.state == "dl" and record.outcome == "blocked"
        assert (source.verify_task, source.verified_by) == (
            record.verify_task,
            f"configs/sources/{record.source_id.lower()}.yaml",
        )
        assert record.retry_condition
    assert dl.source("S38").secret_env == "OTD_API_KEY"  # a name, never a value


def test_study_cannot_start_and_says_why(dl):
    ready, why = study_ready(dl)
    assert not ready and "disabled" in why
    assert S38.access.status == "form_and_key_required_owner_step"
    assert "H04" in S38.retry_condition


def test_registration_page_matches_the_source_records():
    rows = registration()
    assert list(rows) == [
        "Access approval",
        "Protobuf schema",
        "Trip linkage",
        "Selected routes",
        "Study dates",
        "Decoder (`worker/src/protobuf.ts`)",
    ]
    assert rows["Access approval"][0] == "none" and "H04" in rows["Access approval"][1]
    assert S38.units.status == "unlabelled"
    assert all(f.upstream is None for f in S38.field_map)  # no upstream field was read
    assert rows["Protobuf schema"][0] == "not published, not read"
    assert rows["Trip linkage"][0] == "unknown"
    assert rows["Selected routes"][0] == "none"
    assert rows["Study dates"][0] == "not frozen"
    # The only route counts on the page are the public counts the S38 record holds.
    assert "543 bus, 36 DMRC" in rows["Selected routes"][1]
    detail = " ".join(S38.history.detail.split())
    assert "543 routes" in detail and "36 routes" in detail


def test_no_route_selection_dates_or_decoder_exist():
    assert not (ROOT / "worker/src/protobuf.ts").exists()
    assert not list((ROOT / "docs/studies").glob("*manifest*"))
    assert not (ROOT / "data/manifests/dl").exists()
    worker = ROOT / "worker/package.json"
    assert "protobufjs" not in worker.read_text("utf-8")
    # No calendar date is frozen on the page except the plan's assumption, which it labels.
    dates = re.findall(r"\b20\d\d-\d\d-\d\d\b", PAGE)
    assert dates == ["2028-01-17"] and "assumed approval" in PAGE
