"""Chronological rolling-origin and spatial-block splits with purging (T033).

Training data ends `purge_days` before the test period starts, where purge_days is the
largest forecast horizon plus the source publication lag, so no training target overlaps a
test-period event. Manifests are saved as JSON with their dates and a SHA256 of the content.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path

from pydantic import Field, model_validator

from atlas.contracts import Strict
from atlas.features.base import LeakageError


class DatasetSplit(Strict):
    name: str = Field(min_length=1)
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    purge_days: int = Field(ge=0)
    test_blocks: tuple[str, ...] = ()  # spatial blocks held out; empty = all units

    @model_validator(mode="after")
    def _ordered(self) -> DatasetSplit:
        if not self.train_start <= self.train_end < self.test_start <= self.test_end:
            raise ValueError(f"{self.name}: dates must run train -> test")
        if (self.test_start - self.train_end).days <= self.purge_days:
            raise ValueError(
                f"{self.name}: train must end more than {self.purge_days} days before test"
            )
        return self


def rolling_origin(
    start: date,
    first_origin: date,
    end: date,
    *,
    step_days: int,
    horizon_days: int,
    publication_lag_days: int,
) -> list[DatasetSplit]:
    """Expanding-window splits: train from `start` to origin - purge - 1, test one step."""
    purge = horizon_days + publication_lag_days
    splits, origin = [], first_origin
    while origin <= end:
        test_end = min(origin + timedelta(days=step_days - 1), end)
        splits.append(
            DatasetSplit(
                name=f"origin-{origin.isoformat()}",
                train_start=start,
                train_end=origin - timedelta(days=purge + 1),
                test_start=origin,
                test_end=test_end,
                purge_days=purge,
            )
        )
        origin = test_end + timedelta(days=1)
    return splits


def spatial_blocks(unit_block: Mapping[str, str], folds: int) -> list[tuple[str, ...]]:
    """Assign whole blocks (never single units) to folds, round robin by sorted block name."""
    blocks = sorted(set(unit_block.values()))
    if folds < 2 or folds > len(blocks):
        raise ValueError(f"need 2 to {len(blocks)} folds")
    return [tuple(blocks[i::folds]) for i in range(folds)]


def check_events(
    train: Sequence[tuple[str, date, date]], test: Sequence[tuple[str, date, date]], purge_days: int
) -> None:
    """Fail if a training event (id, start, end) overlaps a test event or its purge window."""
    for t_id, t_start, t_end in test:
        for r_id, r_start, r_end in train:
            if r_id == t_id or (r_start <= t_end and t_start <= r_end + timedelta(days=purge_days)):
                raise LeakageError(f"training event {r_id} overlaps test event {t_id}")


def write_manifest(splits: Sequence[DatasetSplit], path: Path) -> str:
    """Save splits as JSON with their SHA256; return the hash."""
    body = [s.model_dump(mode="json") for s in splits]
    content = json.dumps(body, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(content.encode()).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"sha256": digest, "splits": body}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return digest


class TrainOnlyScaler:
    """Standardiser whose mean and spread come only from training rows."""

    def __init__(self) -> None:
        self.mean: float | None = None
        self.std: float | None = None

    def fit(
        self, values: Sequence[float | None], dates: Sequence[date], split: DatasetSplit
    ) -> TrainOnlyScaler:
        train = [
            v
            for v, d in zip(values, dates, strict=True)
            if v is not None and split.train_start <= d <= split.train_end
        ]
        if len(train) < 2:
            raise ValueError("need at least two training values")
        self.mean = sum(train) / len(train)
        self.std = (sum((v - self.mean) ** 2 for v in train) / (len(train) - 1)) ** 0.5 or 1.0
        return self

    def transform(self, values: Sequence[float | None]) -> list[float | None]:
        if self.mean is None:
            raise ValueError("fit on training rows first")
        return [None if v is None else (v - self.mean) / self.std for v in values]
