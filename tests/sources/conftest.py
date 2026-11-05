"""Shared helpers for source discovery tests (one test file per discovery task)."""

import hashlib
from pathlib import Path

import pytest

from atlas.config import load_state, load_yaml
from atlas.ingest.discovery import Discovery, check, load_manifest

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"


def enabled(source_id: str) -> bool:
    ka = load_state(ROOT / "configs" / "states" / "ka.yaml")
    return next(s for s in ka.sources if s.source_id == source_id).enabled


class Record:
    def __init__(self, source_id: str):
        n = source_id.lower()
        self.discovery = load_yaml(ROOT / "configs" / "sources" / f"{n}.yaml", Discovery)
        self.fixture_dir = ROOT / "tests" / "fixtures" / n
        self.manifest = load_manifest(self.fixture_dir / "manifest.json")
        self.source_id = source_id

    def problems(self) -> list[str]:
        return check(self.discovery, self.manifest, source_enabled=enabled(self.source_id))

    def committed_files(self) -> list[str]:
        return sorted(p.name for p in self.fixture_dir.iterdir())

    def raw(self, evidence_id: str) -> Path:
        e = next(e for e in self.manifest.evidence if e.id == evidence_id)
        path = RAW / e.raw_path
        if not path.exists():
            pytest.skip("raw evidence is local only (not redistributed)")
        return path

    def check_local_hashes(self) -> None:
        if not RAW.exists():
            pytest.skip("raw evidence is local only (not redistributed)")
        for e in self.manifest.evidence:
            path = RAW / e.raw_path
            assert path.exists(), e.id
            assert hashlib.sha256(path.read_bytes()).hexdigest() == e.sha256, e.id


@pytest.fixture
def record():
    return Record
