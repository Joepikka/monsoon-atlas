"""S38 Delhi Open Transit Data: T149 disabled contract after blocked T148 (owner step H04)."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S38 is blocked (T148): the static GTFS forms and the realtime key are owner step H04, and the "
    "feed fields and units are unread; retry the conditions in configs/sources/s38.yaml"
)


class S38:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
