"""T089: M01 Bengaluru ward flood occurrence is blocked (no labels, S43). The plan's fallback is a
rainfall exposure index: forecast rain over the next 24 hours per ward, explicitly not a flood
probability. No labels, features or predictions of flooding are produced."""

from __future__ import annotations

from datetime import datetime, timedelta

import pyarrow as pa

from atlas.ingest.base import SourceUnavailable
from atlas.models import blocked

MODEL_ID = "M01"
SOURCES = ("S43",)
REASON = (
    "M01 blocked: no official dated ward-level inundation records or audited negatives exist "
    "(S43, T085), so labels, features and flood probabilities cannot be built (T089)."
)
EXPOSURE_LABEL = "Forecast rain in the next 24 h (exposure index, not a flood probability)"


def data_gate() -> dict:
    return blocked.data_gate(MODEL_ID, SOURCES, REASON)


def build_features(data):
    raise SourceUnavailable(REASON)


def export_predictions(predictions):
    raise SourceUnavailable(REASON)


def exposure_index(forecast: pa.Table, ward_cells: dict[str, str], issued_at: datetime) -> pa.Table:
    """Sum S01 hourly forecast rain over (issued_at, issued_at + 24 h] for each ward's grid cell.

    `forecast` is an S01 table from one model run; `ward_cells` maps ward IDs to S01 cell IDs.
    A ward whose cell lacks any of the 24 hours gets null with a reason, never a partial sum.
    """
    if not ward_cells:
        raise ValueError("at least one ward")
    runs = set(forecast["issued_at"].to_pylist())
    if len(runs) != 1:
        raise ValueError("the forecast must come from exactly one model run")
    end = issued_at + timedelta(hours=24)
    hourly: dict[str, dict[datetime, float | None]] = {}
    for cell, valid, rain in zip(
        forecast["cell_id"].to_pylist(),
        forecast["valid_at"].to_pylist(),
        forecast["rain_mm"].to_pylist(),
        strict=True,
    ):
        if issued_at < valid <= end:
            hourly.setdefault(cell, {})[valid] = rain
    wards, totals, reasons = [], [], []
    for ward, cell in sorted(ward_cells.items()):
        hours = hourly.get(cell, {})
        complete = len(hours) == 24 and all(v is not None for v in hours.values())
        wards.append(ward)
        totals.append(round(sum(hours.values()), 3) if complete else None)
        reasons.append(None if complete else "not_yet_available")
    n = len(wards)
    return pa.table(
        {
            "ward_id": wards,
            "issued_at": [issued_at] * n,
            "forecast_issued_at": [runs.pop()] * n,
            "rain_next_24h_mm": pa.array(totals, pa.float64()),
            "missing_reason": reasons,
            "label": [EXPOSURE_LABEL] * n,
            "probabilistic": [False] * n,
        }
    )
