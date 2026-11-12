"""S39 Telegram Bot API: T084 disabled contract after blocked T083 discovery (owner step H08)."""

from __future__ import annotations

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.ingest.base import SourceUnavailable

REASON = (
    "S39 is blocked (T083): the bot token, public channel and terms are owner step H08; retry "
    "the conditions in configs/sources/s39.yaml"
)


class S39:
    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(REASON)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        raise SourceUnavailable(REASON)
