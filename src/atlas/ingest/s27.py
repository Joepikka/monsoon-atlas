"""S27 KSNDMC gauges: T078 disabled contract after blocked T077 discovery (no HTTPS, D112)."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S27 is blocked (T077): ksndmc.org refuses HTTPS and publishes only undocumented template "
    "endpoints; retry the conditions in configs/sources/s27.yaml"
)


class S27:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
