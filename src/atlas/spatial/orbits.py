"""T187: rules behind the movement overlays (aircraft, satellites, earthquakes, ships) (D153).

Per layer: which sources may feed it (enabled, available, licence open), one shared region key and
poll gate so a fallback source cannot add a second upstream poll, the stale thresholds, and the
labelling of satellite positions as predicted. Propagation itself is unavailable: the `sgp4`
package is not in any lock, and a propagator is never written by hand here (D153). CelesTrak
serves OMM JSON, so the "TLE epoch" of the plan is the OMM `EPOCH` (D109).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from atlas.config import load_state
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s10 import MAX_AGE_S as AIRCRAFT_MAX_AGE_S
from atlas.ingest.s12 import MAX_AGE as ELEMENT_MAX_AGE
from atlas.spatial.context import _discovery

ROOT = Path(__file__).resolve().parents[3]
PREDICTED_LABEL = "Predicted position (propagated from orbit elements), not observed"
PROPAGATION_REASON = (
    "sgp4 not in the lock (add to requirements/geo.in with pip-tools in a follow-up)"
)
# layer -> (source, title, note); further sources are fallbacks in `FALLBACKS`
LAYERS = {
    "aircraft": (
        "S10",
        "Aircraft",
        "Community receiver reports, not an official air-traffic feed: never use for safety. "
        "Positions older than 5 minutes are hidden. No callsign, registration or owner is shown.",
    ),
    "satellite": (
        "S12",
        "Satellites (predicted)",
        "Positions are predicted from published orbit elements, not observed; the element "
        "date is shown. Elements older than 7 days are hidden.",
    ),
    "earthquake": (
        "S20",
        "Earthquakes",
        "USGS events are revised after first report; the revision time and the source link are "
        "shown with each event.",
    ),
    "vessel": (
        "S26",
        "Ships",
        "Ship positions are not shown: the AIS feed is blocked.",
    ),
}
FALLBACKS = {"aircraft": ("S11",)}
# minimum seconds between upstream polls of one region; ships have no recorded interval
POLL_SECONDS = {"aircraft": AIRCRAFT_MAX_AGE_S, "satellite": 7200, "earthquake": 3600}
KA_STATE = ROOT / "configs/states/ka.yaml"


def propagation_status(requirements: Path = ROOT / "requirements") -> dict:
    """Propagation is available only when an SGP4 package is pinned in a lock and importable."""
    pinned = any(
        re.search(r"(?mi)^sgp4==", p.read_text(encoding="utf-8"))
        for p in requirements.glob("*.txt")
    )
    if not pinned:
        return {"available": False, "reason": PROPAGATION_REASON}
    return {"available": False, "reason": "sgp4 is pinned but propagation is not written yet"}


def predict(omm: dict, at: datetime) -> dict:
    """Latitude and longitude of one satellite at `at`; unavailable until sgp4 is pinned."""
    raise SourceUnavailable(propagation_status()["reason"])


def omm_epoch(value: str) -> datetime:
    """An OMM EPOCH (UTC, usually without a zone designator) as an aware UTC datetime."""
    epoch = datetime.fromisoformat(value)
    return epoch.replace(tzinfo=UTC) if epoch.tzinfo is None else epoch.astimezone(UTC)


def element_status(epoch: datetime, now: datetime) -> str:
    """'fresh' within 7 days of the epoch, 'stale' beyond, 'future' for an epoch after now."""
    age = now - epoch
    if age < timedelta(0):
        return "future"
    return "fresh" if age <= ELEMENT_MAX_AGE else "stale"


def predicted_label(epoch: datetime) -> str:
    return f"{PREDICTED_LABEL}; elements dated {epoch.astimezone(UTC):%Y-%m-%d %H:%M} UTC"


def aircraft_visible(position_at: datetime, now: datetime) -> bool:
    """Shown for ages 0 to 300 s; older (as the S10 adapter drops them) and future ones are not."""
    return 0 <= (now - position_at).total_seconds() <= AIRCRAFT_MAX_AGE_S


def region_key(lat: float, lon: float, radius_nm: int) -> str:
    """One key for flights and ships: centre on a 0.5 degree grid, radius up to a 25 nm step."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 0 < radius_nm <= 250):
        raise ValueError("latitude, longitude or radius out of range")
    wrapped = ((round(lon * 2) / 2 + 180) % 360) - 180  # +180 rounds onto -180
    return (
        f"{round(lat * 2) / 2 + 0.0:g}:{wrapped + 0.0:g}:{-(-radius_nm // 25) * 25}"  # +0.0: no -0
    )


def upstreams(layer: str, state_file: Path = KA_STATE) -> list[str]:
    """Enabled, available sources for a layer, primary first. S11 and S26 are blocked: absent."""
    state = load_state(state_file)
    out = []
    for source_id in (LAYERS[layer][0], *FALLBACKS.get(layer, ())):
        try:
            enabled = state.source(source_id).enabled
        except KeyError:
            enabled = False
        if enabled and _discovery(source_id)["outcome"] == "available":
            out.append(source_id)
    return out


class PollGate:
    """One poll slot per layer and region, whichever source uses it, so a fallback shares it."""

    def __init__(self) -> None:
        self._last: dict[tuple[str, str], datetime] = {}

    def claim(self, layer: str, key: str, now: datetime) -> bool:
        if layer not in LAYERS:
            raise ValueError(f"unknown movement layer {layer!r}")
        if layer not in POLL_SECONDS:
            raise SourceUnavailable(f"{layer} has no enabled upstream: {movement_reason(layer)}")
        last = self._last.get((layer, key))
        if last is not None and (now - last).total_seconds() < POLL_SECONDS[layer]:
            return False
        self._last[(layer, key)] = now
        return True


def movement_reason(layer: str) -> str:
    return next(s["reason"] for s in movement_status() if s["layer"] == layer)


def movement_status(state_file: Path = KA_STATE) -> list[dict]:
    """One entry per layer: available, or disabled with the reason and the evidence page."""
    state = load_state(state_file)
    out = []
    for layer, (source_id, title, note) in LAYERS.items():
        d = _discovery(source_id)
        try:
            enabled = state.source(source_id).enabled
        except KeyError:
            enabled = False
        licence = d["licence"]["status"]
        reasons = []
        if d["outcome"] == "blocked":
            reasons.append(" ".join(d["retry_condition"].split()))
        else:
            if not enabled:
                reasons.append("Source contract not enabled.")
            if licence != "open":
                reasons.append(f"Licence {licence}: waits for the owner's review (H11).")
        if layer == "satellite" and not propagation_status()["available"]:
            reasons.append(f"Orbit propagation unavailable: {PROPAGATION_REASON}.")
        out.append(
            {
                "layer": layer,
                "source_id": source_id,
                "title": title,
                "note": note,
                "available": not reasons,
                "reason": " ".join(reasons) or None,
                "evidence": f"docs/sources/{source_id.lower()}.md",
                "landing_url": d["landing_url"],
            }
        )
    return out
