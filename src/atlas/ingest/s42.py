"""S42 Sentinel-1 / NDVI quantitative imagery: T128 disabled contract after blocked T127."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S42 is blocked (T127): Copernicus Data Space product download needs a registered account and "
    "access token (owner step); retry the conditions in configs/sources/s42.yaml"
)


class S42:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
