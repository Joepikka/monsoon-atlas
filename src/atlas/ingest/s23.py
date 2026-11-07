"""S23 data.gov.in: T026 disabled contract while T025 price units are unverified."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S23 is blocked (T025): price units/denominator are unverified despite the open GODL licence; "
    "retry the conditions in configs/sources/s23.yaml"
)


class S23:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
