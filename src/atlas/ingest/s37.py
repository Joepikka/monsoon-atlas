"""S37 2018 landslide inventory / ISRO Atlas: T124 disabled contract after blocked T123."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S37 is blocked (T123): NRSC publishes no downloadable landslide inventory, only atlas counts; "
    "retry the conditions in configs/sources/s37.yaml"
)


class S37:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
