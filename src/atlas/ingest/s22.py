"""S22 India Data Portal: T024 disabled contract after blocked T023 discovery."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S22 is blocked (T023): no verified download, field mapping, units or dataset licence; "
    "retry the conditions in configs/sources/s22.yaml"
)


class S22:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
