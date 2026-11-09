"""S35 Kerala 2018 flood dataset: T120 disabled contract after blocked T119 discovery."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S35 is blocked (T119): Kaggle needs a sign-in and no licence is published; "
    "retry the conditions in configs/sources/s35.yaml"
)


class S35:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
