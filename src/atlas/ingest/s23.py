"""S23 data.gov.in: disabled contract until the T270 adapter; T269 verified onion units only."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S23 is blocked for ingestion until the T270 adapter: only Onion has a verified price unit "
    "(Rs./Quintal, T269); other commodities stay disabled until H16 (configs/sources/s23.yaml)"
)


class S23:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
