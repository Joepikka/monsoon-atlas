"""S25 NASA FIRMS: T076 disabled contract after blocked T075 discovery (owner step H09)."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S25 is blocked (T075): the FIRMS API needs a MAP_KEY (owner step H09) and no key-free link "
    "was readable; retry the conditions in configs/sources/s25.yaml"
)


class S25:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
