"""S11 OpenSky flight fallback: T062 disabled contract after blocked T061 discovery."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S11 is blocked (T061): using the OpenSky API means accepting terms the agent could not read "
    "(HTTP 403) and may not accept; retry the owner step in configs/sources/s11.yaml"
)


class S11:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
