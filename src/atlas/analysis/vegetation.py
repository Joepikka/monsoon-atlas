"""T145: NDVI method and layer status. S42 imagery is blocked on an owner account (H15), so no
NDVI is computed from real scenes; this code is tested on small hand-checkable arrays only.

Missing is NaN and is never filled: nodata, a cloud-masked pixel, a negative reflectance or a
zero denominator all stay missing, so every value that remains lies in [-1, 1].
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import numpy as np
import yaml

GREENNESS = "vegetation greenness"
CROP_HEALTH = "crop health"


def ndvi(nir, red, *, cloud=None, nodata: float | None = None) -> np.ndarray:
    """(NIR - red) / (NIR + red) as float64; missing pixels are NaN."""
    nir, red = np.asarray(nir, dtype=np.float64), np.asarray(red, dtype=np.float64)
    bad = ~np.isfinite(nir) | ~np.isfinite(red) | (nir < 0) | (red < 0)
    if nodata is not None:
        bad |= (nir == nodata) | (red == nodata)
    if cloud is not None:
        bad |= np.asarray(cloud, dtype=bool)
    denom = nir + red
    bad |= denom == 0
    return np.where(bad, np.nan, (nir - red) / np.where(bad, 1.0, denom))


def dekad(day: date) -> tuple[int, int, int]:
    """(year, month, 1..3): days 1-10, 11-20 and 21-end of a month."""
    return day.year, day.month, min((day.day - 1) // 10, 2) + 1


def dekad_median(days: Sequence[date], stack) -> dict[tuple[int, int, int], np.ndarray]:
    """10-day median of the valid pixels of a (time, ...) stack; all-missing stays NaN."""
    stack = np.asarray(stack, dtype=np.float64)
    groups: dict[tuple[int, int, int], list[int]] = {}
    for i, d in enumerate(days):
        groups.setdefault(dekad(d), []).append(i)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN slices are the missing case
        return {k: np.nanmedian(stack[idx], axis=0) for k, idx in sorted(groups.items())}


def wording(crop_mask_verified: bool) -> str:
    """Crop-health wording needs a verified crop mask; otherwise it is only greenness."""
    return CROP_HEALTH if crop_mask_verified else GREENNESS


def layer_status(config: Path, crop_mask_verified: bool = False) -> dict:
    """Layer status from the S42 source record: blocked means unavailable, never synthetic."""
    outcome = yaml.safe_load(config.read_text("utf-8"))["outcome"]
    ok = outcome == "available"
    return {
        "status": "ready" if ok else "unavailable",
        "reason": None if ok else f"S42 {outcome} (H15: owner account needed for imagery)",
        "wording": wording(crop_mask_verified),
    }
