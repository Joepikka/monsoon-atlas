"""T252: permission-filtered Ask corpus of committed project documents (D87)."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "configs/rag.yaml"
# shortcut: words and punctuation stand in for e5 subword tokens until the pinned
# tokenizer is installed (D87); switch to the tokenizer count with the embedding child.
TOKEN = re.compile(r"\w+|[^\w\s]")
HEADING = re.compile(r"(#{1,6})\s+(.*)")
DIVIDER = re.compile(r":?-{3,}:?")


class CorpusError(ValueError):
    """The corpus configuration or a listed document cannot be indexed safely."""


@dataclass(frozen=True)
class Document:
    doc_id: str
    path: str
    kind: str
    states: tuple[str, ...]
    licence: str
    language: str
    text: str
    sha256: str
    available_at: str  # UTC commit time of the indexed content, "YYYY-MM-DDTHH:MM:SSZ"
    commit: str
    expires_at: str | None = None


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    section: str
    heading: str  # document title and section heading; indexed but outside the token window
    ordinal: int
    text: str
    tokens: int
    sha256: str


def tokens(text: str) -> int:
    return len(TOKEN.findall(text))


def utc_text(value: datetime) -> str:
    if value.utcoffset() is None:
        raise CorpusError("Corpus times must be timezone-aware")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "top"


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        raise CorpusError(f"git {args[0]} failed for the corpus")
    return completed.stdout.strip()


def load_config(path: Path = CONFIG) -> dict:
    config = yaml.safe_load(path.read_text("utf-8"))
    ids = [entry["doc_id"] for entry in config["documents"]]
    if len(ids) != len(set(ids)):
        raise CorpusError("Corpus document IDs must be unique")
    return config


def committed_documents(config: dict, root: Path = ROOT) -> list[Document]:
    """Read listed documents exactly as committed; uncommitted edits cannot enter the index."""
    allowed = set(config["licences"])
    documents = []
    for entry in config["documents"]:
        licence = entry.get("licence", "project-mit")
        if licence not in allowed:
            raise CorpusError(f"{entry['doc_id']} has an unapproved licence")
        path = entry["path"]
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise CorpusError("Corpus paths must stay inside the repository")
        if _git(root, "status", "--porcelain", "--", path):
            raise CorpusError(f"{path} has uncommitted changes; commit it before indexing")
        found = _git(root, "log", "-1", "--format=%H %cI", "--", path).split()
        if len(found) != 2:
            raise CorpusError(f"{path} is not a committed document")
        commit, stamp = found
        text = _git(root, "show", f"{commit}:{path}") + "\n"
        documents.append(
            Document(
                doc_id=entry["doc_id"],
                path=path,
                kind=entry["kind"],
                states=tuple(entry["states"]),
                licence=licence,
                language=entry.get("language", "en"),
                text=text,
                sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                available_at=utc_text(datetime.fromisoformat(stamp)),
                commit=commit,
                expires_at=entry.get("expires_at"),
            )
        )
    return documents


def units(text: str) -> tuple[list[tuple[str, str, bool]], dict[str, str]]:
    """Return (section, text, is_table_row) units and each section's heading line.

    Level 1-2 headings name sections; deeper headings stay in the prose. Each table row
    becomes one self-describing unit.
    """
    found: list[tuple[str, str, bool]] = []
    headings: dict[str, str] = {}
    title, section, header, paragraph, fenced = "", "top", None, [], False

    def flush() -> None:
        if paragraph:
            found.append((section, " ".join(paragraph), False))
            paragraph.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            flush()
            fenced = not fenced
        elif fenced:
            if line:
                found.append((section, line, False))
        elif (heading := HEADING.fullmatch(line)) and len(heading.group(1)) <= 2:
            flush()
            header = None
            name = heading.group(2).strip()
            title = title or name
            section = slug(name)
            headings.setdefault(section, name if name == title else f"{title} - {name}")
        elif line.startswith("|") and line.endswith("|") and len(line) > 1:
            flush()
            cells = [cell.strip() for cell in line[1:-1].split("|")]
            if all(DIVIDER.fullmatch(cell) for cell in cells):
                continue
            if header is None:
                header = cells
            else:
                pairs = zip(header, cells, strict=False)
                found.append((section, "; ".join(f"{k}: {v}" for k, v in pairs), True))
        else:
            header = None
            if not line or line.startswith(("- ", "* ", "#")) or re.match(r"\d+\. ", line):
                flush()
            if line:
                paragraph.append(line.lstrip("#").strip() + ("." if line[0] == "#" else ""))
    flush()
    headings.setdefault("top", title)
    return found, headings


def _windows(words: list[str], limit: int, overlap: int) -> list[str]:
    """Split one long prose unit into overlapping word windows."""
    pieces, start = [], 0
    while start < len(words):
        end, size = start, 0
        while end < len(words) and (end == start or size + tokens(words[end]) <= limit):
            size += tokens(words[end])
            end += 1
        pieces.append(" ".join(words[start:end]))
        if end == len(words):
            break
        back, kept = end, 0
        while back > start + 1 and kept + tokens(words[back - 1]) <= overlap:
            back -= 1
            kept += tokens(words[back])
        start = back
    return pieces


def chunk(document: Document, *, limit: int = 300, overlap: int = 50) -> list[Chunk]:
    """Pack heading-scoped units into windows of at most `limit` tokens with unit overlap.

    Prose longer than the limit is split by words; a table row is never split.
    """
    sections: dict[str, list[str]] = {}
    found, headings = units(document.text)
    for section, text, row in found:
        pieces = [text] if row or tokens(text) <= limit else _windows(text.split(), limit, overlap)
        sections.setdefault(section, []).extend(pieces)

    chunks: list[Chunk] = []
    for section, parts in sections.items():
        index = ordinal = 0
        while index < len(parts):
            first, size, window = index, 0, []
            while index < len(parts) and (not window or size + tokens(parts[index]) <= limit):
                window.append(parts[index])
                size += tokens(parts[index])
                index += 1
            text = "\n".join(window)
            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}#{section}:{ordinal}",
                    doc_id=document.doc_id,
                    section=section,
                    heading=headings[section],
                    ordinal=ordinal,
                    text=text,
                    tokens=tokens(text),
                    sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                )
            )
            ordinal += 1
            if index == len(parts):
                break
            back, kept = index, 0
            while back > first + 1 and kept + tokens(parts[back - 1]) <= overlap:
                back -= 1
                kept += tokens(parts[back])
            index = back
    return chunks
