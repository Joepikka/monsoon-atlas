"""T187: movement overlays: source gating, stale thresholds, one shared poll gate (D153).

Rendering is tested in web/src/map/Movement.test.ts. Not run: SGP4 propagation of a known
example against its published answer, because the sgp4 package is not in any lock and a
propagator is never written by hand here; satellites therefore show no position at all.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from atlas.ingest import s10
from atlas.ingest.base import SourceUnavailable
from atlas.spatial.orbits import (
    AIRCRAFT_MAX_AGE_S,
    ELEMENT_MAX_AGE,
    POLL_SECONDS,
    PREDICTED_LABEL,
    PROPAGATION_REASON,
    PollGate,
    aircraft_visible,
    element_status,
    movement_status,
    omm_epoch,
    predict,
    predicted_label,
    propagation_status,
    region_key,
    upstreams,
)

ROOT = Path(__file__).resolve().parents[1]
MOVEMENT = (ROOT / "web/src/map/Movement.tsx").read_text(encoding="utf-8")
T0 = datetime(2026, 11, 11, 6, 0, tzinfo=UTC)  # TEST INPUT time, not an observation
STATUS = {s["layer"]: s for s in movement_status()}


def test_only_enabled_licensed_layers_are_available_and_the_web_copy_matches():
    assert STATUS["aircraft"]["available"] and STATUS["aircraft"]["reason"] is None
    assert "Licence restricted" in STATUS["satellite"]["reason"]
    assert PROPAGATION_REASON in STATUS["satellite"]["reason"]
    assert "Licence restricted" in STATUS["earthquake"]["reason"]  # S20 waits for H11 (D110)
    assert "H12" in STATUS["vessel"]["reason"]  # S26 blocked: no ship layer
    assert [s["available"] for s in movement_status()] == [True, False, False, False]
    fixture = json.loads((ROOT / "web/tests/fixtures/movement-layers.json").read_text("utf-8"))
    assert fixture == movement_status()


def test_aircraft_has_exactly_one_upstream_and_ships_have_none():
    assert upstreams("aircraft") == ["S10"]  # S11 (OpenSky) is blocked and disabled
    assert upstreams("vessel") == []
    assert upstreams("satellite") == ["S12"] and upstreams("earthquake") == ["S20"]


def test_flights_and_ships_share_one_region_key():
    assert region_key(13.0, 77.5, 100) == region_key(13.2, 77.6, 90)  # same 0.5 degree cell
    assert region_key(13.0, 77.5, 100) != region_key(13.0, 77.5, 101)  # next 25 nm radius step
    assert region_key(13.0, 77.5, 100) != region_key(13.5, 77.5, 100)
    assert region_key(14.5, 179.8, 10) == region_key(14.5, -180.0, 10)  # antimeridian
    assert region_key(-0.1, -0.1, 10) == "0:0:25"  # no negative zero
    for bad in ((91, 0, 10), (0, 181, 10), (0, 0, 0), (0, 0, 251)):
        with pytest.raises(ValueError):
            region_key(*bad)


def test_a_fallback_cannot_double_the_upstream_poll_of_a_region():
    gate, key = PollGate(), region_key(13.0, 77.5, 100)
    assert gate.claim("aircraft", key, T0)  # primary polls
    assert not gate.claim("aircraft", key, T0 + timedelta(seconds=1))  # a fallback finds no slot
    assert not gate.claim("aircraft", key, T0 + timedelta(seconds=POLL_SECONDS["aircraft"] - 1))
    assert gate.claim("aircraft", key, T0 + timedelta(seconds=POLL_SECONDS["aircraft"]))
    assert gate.claim("aircraft", region_key(20, 80, 100), T0)  # other region
    assert gate.claim("satellite", key, T0)  # other layer
    with pytest.raises(SourceUnavailable, match="H12"):
        gate.claim("vessel", key, T0)
    with pytest.raises(ValueError, match="unknown"):
        gate.claim("train", key, T0)


def test_aircraft_stale_threshold_matches_the_adapter_and_the_web_copy():
    assert AIRCRAFT_MAX_AGE_S == s10.MAX_AGE_S == 300
    assert aircraft_visible(T0 - timedelta(seconds=300), T0)
    assert not aircraft_visible(T0 - timedelta(seconds=301), T0)
    assert not aircraft_visible(T0 + timedelta(seconds=1), T0)  # a future time is never live
    assert re.search(r"AIRCRAFT_MAX_AGE_S = 300;", MOVEMENT)
    assert re.search(r"ELEMENT_MAX_AGE_S = 7 \* 86400;", MOVEMENT) and ELEMENT_MAX_AGE.days == 7
    assert s10.MEASURES.names == re.findall(
        r"'(\w+)'", re.search(r"AIRCRAFT_FIELDS = \[(.*?)\]", MOVEMENT).group(1)
    )  # the allowlist is the adapter's columns: no callsign, registration or owner


def test_orbit_element_age_rule_and_epoch_parsing():
    epoch = omm_epoch("2026-11-04T06:00:00.000000")  # OMM EPOCH has no zone: UTC
    assert epoch == T0 - timedelta(days=7) and epoch.tzinfo is not None
    assert element_status(epoch, T0) == "fresh"
    assert element_status(epoch, T0 + timedelta(seconds=1)) == "stale"
    assert element_status(T0 + timedelta(seconds=1), T0) == "future"
    assert omm_epoch("2026-11-04T11:30:00+05:30") == epoch


def test_satellite_positions_are_labelled_predicted_and_unavailable_without_sgp4(tmp_path):
    assert PREDICTED_LABEL in MOVEMENT and "not observed" in PREDICTED_LABEL
    assert "2026-11-11 05:00 UTC" in predicted_label(T0 - timedelta(hours=1))
    locks = list((ROOT / "requirements").glob("*.txt"))
    assert locks and not any("sgp4==" in p.read_text("utf-8").lower() for p in locks)
    assert propagation_status() == {"available": False, "reason": PROPAGATION_REASON}
    with pytest.raises(SourceUnavailable, match="sgp4 not in the lock"):
        predict({"NORAD_CAT_ID": 25544}, T0)
    (tmp_path / "geo.txt").write_text("sgp4==2.25 \\\n    --hash=sha256:0\n", encoding="utf-8")
    assert "pinned but propagation is not written" in propagation_status(tmp_path)["reason"]


def test_the_movement_component_makes_no_request_and_names_only_usgs():
    assert not re.search(r"fetch\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon", MOVEMENT)
    assert set(re.findall(r"https?://([^/'\"\s]+)", MOVEMENT)) == set()
    assert (
        "earthquake.usgs.gov" in MOVEMENT and "updated_at" in MOVEMENT and "source_url" in MOVEMENT
    )


def test_sgp4_known_example_propagation_is_not_run():
    pytest.skip("not run: sgp4 not in any lock (D153); add the pin, then test a published example")
