"""S31 Karnataka RERA: T082 disabled contract after blocked T081 discovery (permission needed)."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S31 is blocked (T081): K-RERA allows reproduction only after emailed permission; retry the "
    "conditions in configs/sources/s31.yaml"
)


class S31:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
