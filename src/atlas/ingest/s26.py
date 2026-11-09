"""S26 aisstream ships: T112 disabled contract after blocked T111 discovery (owner step H12)."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S26 is blocked (T111): the API key is owner step H12 and the data terms are unpublished; "
    "retry the conditions in configs/sources/s26.yaml"
)


class S26:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
