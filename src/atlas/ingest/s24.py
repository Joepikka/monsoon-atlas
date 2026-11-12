"""S24 CPCB station pollution: T147 disabled contract after blocked T146 discovery."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S24 is blocked (T146): the data.gov.in resource ID and licence were not read, and units and "
    "averaging interval are unverified; retry the conditions in configs/sources/s24.yaml"
)


class S24:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
