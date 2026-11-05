"""State, source and budget configuration. YAML in, strict pydantic models out.

Unknown keys are rejected everywhere. Secret values never live in YAML: a source names the
environment variable that holds its key, and code reads only that name.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

import yaml
from pydantic import AfterValidator, BaseModel, Field, model_validator

from atlas.contracts import SourceId, StateId, Strict, UtcDatetime

STORAGE_TZ = "UTC"
DISPLAY_TZ = "Asia/Kolkata"


def _task_id(value: str) -> str:
    if not re.fullmatch(r"T\d{3}", value):
        raise ValueError(f"task id {value!r} must look like T008")
    return value


def _env_name(value: str) -> str:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
        raise ValueError("secret_env must be an environment variable NAME, never a secret value")
    return value


TaskId = Annotated[str, AfterValidator(_task_id)]
EnvName = Annotated[str, AfterValidator(_env_name)]


class SourceConfig(Strict):
    source_id: SourceId
    name: str = Field(min_length=1)
    verify_task: TaskId
    # Rs 0 rule: only free sources. Anything paid or billing-gated fails validation.
    cost: Literal["free", "free_with_key"]
    # Stored vector coordinates are always EPSG:4326 (plan section 4); None for non-spatial data.
    storage_crs: Literal["EPSG:4326"] | None = None
    secret_env: EnvName | None = None
    # None until the source's verify task records the real cadence.
    schedule: str | None = None
    enabled: bool = False
    # Path to the verify task's evidence. A source cannot be enabled without it.
    verified_by: str | None = None

    @model_validator(mode="after")
    def _gates(self) -> SourceConfig:
        if self.enabled and not self.verified_by:
            raise ValueError(f"{self.source_id} cannot be enabled before {self.verify_task} passes")
        if self.cost == "free_with_key" and not self.secret_env:
            raise ValueError(f"{self.source_id} needs secret_env for its free key")
        return self


class StatePaths(Strict):
    raw_root: Path
    clean_root: Path
    publish_root: Path


class StateConfig(Strict):
    state_id: StateId
    name: str
    storage_tz: Literal["UTC"]
    display_tz: Literal["Asia/Kolkata"]
    paths: StatePaths
    sources: tuple[SourceConfig, ...]

    @model_validator(mode="after")
    def _unique_sources(self) -> StateConfig:
        ids = [s.source_id for s in self.sources]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate source ids: {dupes}")
        return self

    def source(self, source_id: str) -> SourceConfig:
        for s in self.sources:
            if s.source_id == source_id:
                return s
        raise KeyError(f"source {source_id} is not configured for state {self.state_id}")


# Project caps from plan section 5 ("Free tiers, budgets and zero-cost fallbacks").
class PagesBudget(Strict):
    builds_per_month: int = Field(gt=0)
    max_files: int = Field(gt=0)
    max_file_mib: int = Field(gt=0)


class WorkersBudget(Strict):
    requests_per_day: int = Field(gt=0)
    cron_triggers: int = Field(gt=0)


class WorkersAiBudget(Strict):
    neurons_per_day: int = Field(gt=0)
    ask_requests_per_day: int = Field(gt=0)


class D1Budget(Strict):
    reads_per_day: int = Field(gt=0)
    writes_per_day: int = Field(gt=0)
    database_mb: int = Field(gt=0)
    hot_retention_days: int = Field(gt=0)


class HuggingFaceBudget(Strict):
    public_gb: int = Field(gt=0)
    files_per_repo: int = Field(gt=0)
    shard_mb: int = Field(gt=0)


class ActionsBudget(Strict):
    daily_pipeline_minutes: int = Field(gt=0)
    feed_job_minutes_per_hour: int = Field(gt=0)
    artifacts_mb: int = Field(gt=0)
    artifact_retention_days: int = Field(gt=0)


class OpenMeteoBudget(Strict):
    calls_per_day: int = Field(gt=0)
    calls_per_hour: int = Field(gt=0)
    calls_per_minute: int = Field(gt=0)
    calls_per_month: int = Field(gt=0)


class ColabBudget(Strict):
    checkpoint_every_hours: int = Field(gt=0)


class DuckDbBudget(Strict):
    memory_limit_gb: int = Field(gt=0)
    threads: int = Field(gt=0)


class StorageBudget(Strict):
    preflight_min_free_gb: int = Field(gt=0)
    archive_only_at_fraction: float = Field(gt=0, le=1)


class Budgets(Strict):
    cloudflare_pages: PagesBudget
    cloudflare_workers: WorkersBudget
    workers_ai: WorkersAiBudget
    cloudflare_d1: D1Budget
    hugging_face: HuggingFaceBudget
    github_actions: ActionsBudget
    open_meteo: OpenMeteoBudget
    colab: ColabBudget
    duckdb: DuckDbBudget
    storage: StorageBudget


def load_yaml[M: BaseModel](path: Path, model: type[M]) -> M:
    with open(path, encoding="utf-8") as f:
        return model.model_validate(yaml.safe_load(f))


def load_state(path: Path) -> StateConfig:
    return load_yaml(path, StateConfig)


def load_budgets(path: Path) -> Budgets:
    return load_yaml(path, Budgets)


def to_display(value: UtcDatetime | datetime) -> datetime:
    """Convert a stored UTC timestamp to Asia/Kolkata for display only."""
    if value.tzinfo is None:
        raise ValueError("naive datetime: storage timestamps must be UTC-aware")
    return value.astimezone(ZoneInfo(DISPLAY_TZ))
