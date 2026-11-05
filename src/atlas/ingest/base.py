"""Adapter contract and ingestion errors (plan section 4 "Module contracts")."""

from __future__ import annotations

from typing import Protocol

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact


class IngestError(Exception):
    """Base class for ingestion failures."""


class SourceUnavailable(IngestError):
    """Source is disabled or blocked. Adapters raise this; they never return synthetic rows."""


class FetchError(IngestError):
    """A request failed after its allowed retries."""


class HostNotAllowed(FetchError):
    """URL or redirect target is outside the allowlist."""


class TooLarge(FetchError):
    """Response exceeded the byte budget."""


class BudgetExceeded(FetchError):
    """Run exceeded its request budget."""


class CircuitOpen(FetchError):
    """Too many consecutive failures for this source; no request is sent."""


class Adapter(Protocol):
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]: ...

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table: ...
