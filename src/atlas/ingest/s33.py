"""S33 KSEB monthly statistics (T116): blocked adapter after T115 discovery.

The published archive pages currently return error content and no reservoir file
has been verified. A config flag cannot override that missing source contract.
"""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

SOURCE_ID = "S33"
REASON = (
    "S33 is blocked (T115): no verified reservoir artifact, units, history or file licence; "
    "retry the conditions in configs/sources/s33.yaml"
)


class S33:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
