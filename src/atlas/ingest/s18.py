"""S18 Geofabrik OSM extracts (T022): disabled adapter.

T021 found S18 blocked: Geofabrik's robots.txt disallows *.osm.pbf for all user agents (D34).
Until a retry condition in configs/sources/s18.yaml is met, every call raises SourceUnavailable
and no rows are produced.
"""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

SOURCE_ID = "S18"
REASON = f"{SOURCE_ID} is blocked (T021, D34): robots.txt disallows automated extract downloads"


class S18:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
