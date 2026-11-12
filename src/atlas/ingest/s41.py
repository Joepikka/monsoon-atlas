"""S41 permitted news RSS sources: T126 disabled contract after blocked T125."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S41 is blocked (T125): publisher terms limit RSS use to personal reading and grant no licence "
    "to store or classify items; retry the conditions in configs/sources/s41.yaml"
)


class S41:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
