"""T183: Telegram channel message from a brief. Sending is blocked until owner step H08 (D149).

`format_message` is a pure function. `send_message` raises `SourceUnavailable` before any I/O: no
bot token is read, no channel exists and nothing is posted. There is one public channel per state,
owned by the project owner; no direct messages, and nothing about readers is kept.
"""

from __future__ import annotations

from atlas.alerts.brief import SECTIONS, Brief, Line, ist
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s39 import REASON

MAX_CHARS = 4096  # Telegram's limit for one text message
TITLES = {
    "official": "OFFICIAL (NDMA Sachet alerts and official records)",
    "model": "MODEL ESTIMATES (not official)",
    "inferred": "INFERRED (not official)",
}
NOTICE = "Not an emergency service. For warnings use https://sachet.ndma.gov.in/"


def _entry(line: Line) -> str:
    return f"- {line.text}\n  Source: {line.source_url} (as of {ist(line.as_of)})"


def format_message(brief: Brief) -> str:
    head = [
        f"Monsoon Atlas daily brief, {brief.state.upper()}, {brief.run_date.isoformat()}",
        f"Published {brief.published_label}. {NOTICE}",
    ]
    blocks: list[str] = []
    for section in SECTIONS:
        entries = [_entry(x) for x in brief.lines if x.provenance == section]
        if entries:
            blocks.append("\n".join([TITLES[section], *entries]))
    if not any(x.provenance == "official" for x in brief.lines):
        blocks.insert(0, "No active official alerts in the records used for this brief.")
    text = "\n\n".join(["\n".join(head), *blocks])
    dropped = 0
    while len(text) > MAX_CHARS and blocks:
        last = blocks[-1].split("\n- ")
        if len(last) > 2:  # drop the last entry of the last block
            blocks[-1] = "\n- ".join(last[:-1])
        else:
            blocks.pop()
        dropped += 1
        text = "\n\n".join(["\n".join(head), *blocks, f"{dropped} more entries not shown."])
    return text


def send_message(text: str) -> None:
    """Post to the state channel. Blocked: raises before reading a token or opening a connection."""
    raise SourceUnavailable(REASON)
