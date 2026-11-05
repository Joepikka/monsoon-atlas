"""Typed module contracts from plan section 4 (FetchContext, RawArtifact) and section 7
(archive_manifest), plus the model release record used by the registry."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

STATE_IDS = ("ka", "kl", "dl")
StateId = Literal["ka", "kl", "dl"]
SOURCE_ID_RE = re.compile(r"^S\d{2}$")
MODEL_ID_RE = re.compile(r"^M\d{2}$")
# Plan section 6 catalogue: S01..S44. A source outside it is unknown and rejected.
CATALOGUE_SOURCE_IDS = frozenset(f"S{i:02d}" for i in range(1, 45))
_SECRET_QUERY_RE = re.compile(r"[?&](api[_-]?key|key|token|access_token|map_key)=", re.I)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamps are stored in UTC and must be timezone-aware UTC")
    return value


def _source_id(value: str) -> str:
    if not SOURCE_ID_RE.match(value) or value not in CATALOGUE_SOURCE_IDS:
        raise ValueError(f"unknown source id {value!r}; must be in the plan catalogue S01..S44")
    return value


def _model_id(value: str) -> str:
    if not MODEL_ID_RE.match(value):
        raise ValueError(f"model id {value!r} must look like M01")
    return value


def _sha256(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("sha256 must be 64 lowercase hex characters")
    return value


def _no_secret_url(value: str) -> str:
    if _SECRET_QUERY_RE.search(value):
        raise ValueError("source_url must not contain credentials or keys")
    return value


UtcDatetime = Annotated[datetime, AfterValidator(_utc)]
SourceId = Annotated[str, AfterValidator(_source_id)]
ModelId = Annotated[str, AfterValidator(_model_id)]
Sha256 = Annotated[str, AfterValidator(_sha256)]
SafeUrl = Annotated[str, AfterValidator(_no_secret_url)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Budget(Strict):
    """Per-run fetch budget handed to an adapter."""

    max_requests: int = Field(gt=0)
    max_bytes: int = Field(gt=0)


class FetchContext(Strict):
    source_id: SourceId
    state: StateId
    run_id: str = Field(min_length=1)
    requested_at: UtcDatetime
    budget: Budget
    raw_root: Path
    # Ephemeral: never serialized, never shown in repr or logs.
    secrets: Mapping[str, str] = Field(default_factory=dict, exclude=True, repr=False)


class RawArtifact(Strict):
    sha256: Sha256
    path: Path
    fetched_at: UtcDatetime
    upstream_issued_at: UtcDatetime | None = None
    media_type: str
    response_status: int = Field(ge=100, le=599)
    source_url: SafeUrl
    schema_mapping_version: str


class ManifestFile(Strict):
    path: str
    sha256: Sha256
    bytes: int = Field(ge=0)


class DatasetManifest(Strict):
    """Release manifest (section 7 archive_manifest). Published last, atomically."""

    release_id: str = Field(min_length=1)
    schema_version: int = Field(ge=1)
    data_revision: str = Field(min_length=1)
    published_at: UtcDatetime
    parent_release_id: str | None = None
    files: tuple[ManifestFile, ...]
    source_versions: Mapping[SourceId, str] = Field(default_factory=dict)
    model_versions: Mapping[ModelId, str] = Field(default_factory=dict)
    total_bytes: int = Field(ge=0)

    @model_validator(mode="after")
    def _total_matches(self) -> DatasetManifest:
        if self.total_bytes != sum(f.bytes for f in self.files):
            raise ValueError("total_bytes must equal the sum of file bytes")
        return self


class DateRange(Strict):
    start: date
    end: date

    @model_validator(mode="after")
    def _ordered(self) -> DateRange:
        if self.end < self.start:
            raise ValueError("end must not be before start")
        return self


class SplitManifest(Strict):
    """Frozen dated split. The test period is never passed to fit."""

    train: DateRange
    tune: DateRange
    calibrate: DateRange | None = None
    test: DateRange

    @model_validator(mode="after")
    def _time_ordered(self) -> SplitManifest:
        parts = [p for p in (self.train, self.tune, self.calibrate, self.test) if p is not None]
        for earlier, later in zip(parts, parts[1:], strict=False):
            if later.start <= earlier.end:
                raise ValueError("split periods must be time-ordered and non-overlapping")
        return self


class ModelRelease(Strict):
    model_id: ModelId
    model_version: str = Field(min_length=1)
    state: StateId | Literal["all"]
    data_revision: str = Field(min_length=1)
    dataset_sha256: Sha256
    split: SplitManifest
    baseline_id: str = Field(min_length=1)
    status: Literal["champion", "research_only", "blocked"]
    trained_at: UtcDatetime
    artifact_sha256: Sha256
    seeds: tuple[int, ...] = (42, 43, 44)
