"""Optional local web checks share the pinned runtime and drive-D cache policy."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE_DIR = ROOT / ".tools/node/node-v22.16.0-win-x64"


@pytest.fixture
def web_check():
    node = NODE_DIR / "node.exe"
    npm = NODE_DIR / "node_modules/npm/bin/npm-cli.js"
    if not node.exists() or not (ROOT / "web/node_modules").exists():
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

    def run(*args):
        result = subprocess.run(
            [str(node), str(npm), *args],
            cwd=ROOT / "web",
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        assert result.returncode == 0, result.stdout[-7000:] + result.stderr[-3000:]
        return result.stdout

    return run
