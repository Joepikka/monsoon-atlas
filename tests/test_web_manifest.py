"""T038: the pinned shell builds and passes real browser loading checks when installed."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.discovery import load_manifest
from atlas.ingest.s09 import S09

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
NODE_DIR = ROOT / ".tools/node/node-v22.16.0-win-x64"


def test_public_cap_fixture_matches_the_existing_source_adapter():
    fixture_dir = WEB / "tests/fixtures"
    record = json.loads((fixture_dir / "sachet-ka-point.json").read_text("utf-8"))
    provenance = json.loads((fixture_dir / "sachet-ka-point.provenance.json").read_text("utf-8"))
    for name, sha in provenance["source_files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    evidence = {e.id: e for e in load_manifest(ROOT / "tests/fixtures/s09/manifest.json").evidence}

    def artifact(eid, filename):
        item = evidence[eid]
        return RawArtifact(
            sha256=item.sha256,
            path=ROOT / "tests/fixtures" / filename,
            fetched_at=item.fetched_at,
            media_type=item.media_type,
            response_status=200,
            source_url=item.url,
            schema_mapping_version="s09-v1",
        )

    raw = artifact("e03", "s09_sachet_cap_1793881986295019.xml")
    polygon = artifact("e04", "s09_sachet_polygon_1793881986295019.xml")
    row = (
        S09("ka")
        .parse(raw, load_state(ROOT / "configs/states/ka.yaml").source("S09"), polygon=polygon)
        .to_pylist()[0]
    )
    assert (
        record["id"] == row["record_id"] and record["provenance"] == row["provenance"] == "official"
    )
    assert record["source_url"] == row["source_url"]
    assert record["title"] == row["event"] + " — " + row["area_text"]
    for field in ("issued_at", "valid_at", "fetched_at", "expires_at", "available_at"):
        assert record[field] == row[field].isoformat().replace("+00:00", "Z")


def test_exact_web_dependencies_and_no_seeded_production_data():
    path = WEB / "package.json"
    assert path.exists(), "T038 web shell missing"
    package = json.loads(path.read_text("utf-8"))
    assert package["engines"]["node"] == "22.16.0"
    assert package["dependencies"]["react"] == "19.3.1"
    assert package["dependencies"]["maplibre-gl"] == "6.16.0"
    assert {"build", "test", "test:e2e"} <= package["scripts"].keys()
    lock_path = WEB / "package-lock.json"
    assert lock_path.exists(), "Web lock is missing"
    lock = json.loads(lock_path.read_text("utf-8"))
    for group in ("dependencies", "devDependencies"):
        for name, version in package[group].items():
            assert lock["packages"][f"node_modules/{name}"]["version"] == version
    assert not list((WEB / "public/data").rglob("*.json"))


def test_web_build_unit_and_browser_contracts():
    node = NODE_DIR / "node.exe"
    npm = NODE_DIR / "node_modules/npm/bin/npm-cli.js"
    if not node.exists() or not (WEB / "node_modules").exists():
        pytest.skip("Optional pinned web toolchain is not installed in this core-only environment")
    env = os.environ.copy()
    env.update(
        {
            "TEMP": str(ROOT / ".cache/tmp"),
            "TMP": str(ROOT / ".cache/tmp"),
            "npm_config_cache": str(ROOT / ".cache/npm"),
            "PLAYWRIGHT_BROWSERS_PATH": str(ROOT / ".cache/ms-playwright"),
            "PATH": str(NODE_DIR) + os.pathsep + env.get("PATH", ""),
        }
    )
    for args in (["run", "build"], ["run", "test"], ["run", "test:e2e", "--", "shell.spec.ts"]):
        result = subprocess.run(
            [str(node), str(npm), *args],
            cwd=WEB,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        assert result.returncode == 0, result.stdout[-7000:] + result.stderr[-3000:]
