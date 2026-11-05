"""Append-only JSON Lines files that survive interrupted writes.

An interrupted append can leave a torn final line. The next append first terminates it, so new
entries never merge into the torn bytes, and readers skip any line that is not valid JSON.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def append(path: Path, entry: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry) + "\n"
    with open(path, "ab+") as f:
        f.seek(0, os.SEEK_END)
        if f.tell():
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                line = "\n" + line  # close a torn line left by a crash
        f.write(line.encode("utf-8"))  # one write per entry
        f.flush()
        os.fsync(f.fileno())


def read(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # torn line from an interrupted append
    return out
