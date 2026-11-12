"""S43 official shelters and flood impact labels: T086 disabled contract after blocked T085."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S43 is blocked (T085): no official dated ward-level flood incidents; complaint logs are not "
    "ground truth; retry the conditions in configs/sources/s43.yaml"
)


class S43:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
