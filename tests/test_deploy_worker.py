"""D180: the committed Worker config stays disabled; only the git-ignored deploy config, built from
.env at deploy time, carries the D1 binding, workers.dev and the verified free/no-card gate."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("deploy_worker", ROOT / "scripts/deploy_worker.py")
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


def test_deploy_config_enables_only_the_generated_copy():
    base = (ROOT / "worker/wrangler.toml").read_text("utf-8")
    out = deploy.deploy_config(base, "00000000-0000-0000-0000-000000000000")
    assert 'CAPABILITY_GATE = "verified_free_no_card"' in out and "workers_dev = true" in out
    assert 'binding = "DB"' in out and 'database_name = "monsoon-atlas-hot"' in out
    assert 'CAPABILITY_GATE = "blocked"' in base and "database_id" not in base
    with pytest.raises(SystemExit, match="changed"):
        deploy.deploy_config(base.replace("workers_dev = false", "workers_dev = maybe"), "x")


def test_generated_config_and_env_are_ignored():
    for path in ("worker/wrangler.deploy.toml", ".env"):
        assert subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0, path
