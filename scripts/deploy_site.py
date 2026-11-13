"""Deploy the public Karnataka site to Cloudflare Pages (D187; owner approved public release).

Steps: an approved release from the live Worker (`atlas.publish --approval approved`), the Ask
release files (`atlas.rag.manifest --public`), the web build, both copied into `web/dist`, then
`wrangler pages deploy` with `web/functions` (forwarding /api/v1/current and /api/v1/ask to the
Worker). Account values come from the ignored .env; nothing is printed or committed.
Usage: .venv/Scripts/python scripts/deploy_site.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import deploy_worker as worker  # noqa: E402

ORIGIN = "https://monsoon-atlas-hot.monsoon-atlas.workers.dev"
PROJECT = "monsoon-atlas"


def step(cmd: list[str], cwd: Path, env: dict) -> None:
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True)
    tail = (result.stdout + result.stderr).decode("utf-8", "replace").splitlines()[-3:]
    print(ascii(" | ".join(t for t in tail if "token" not in t.lower())))
    if result.returncode:
        raise SystemExit(f"step failed: {cmd[1:3]}")


def main() -> int:
    pairs = worker.env_file()
    env = os.environ | {
        "CLOUDFLARE_API_TOKEN": pairs["CLOUDFLARE_API_TOKEN"],
        "CLOUDFLARE_ACCOUNT_ID": pairs["CLOUDFLARE_ACCOUNT_ID"],
        "HF_TOKEN": pairs["HF_TOKEN"],
        "ATLAS_INGEST_HMAC_KEY": pairs["ATLAS_INGEST_HMAC_KEY"],
        "ATLAS_HOT_ORIGIN": ORIGIN,
        "HF_HUB_DISABLE_PROGRESS_BARS": "1",
        "WRANGLER_SEND_METRICS": "false",
        "FORCE_COLOR": "0",
        "TEMP": str(ROOT / ".cache/tmp"),
        "TMP": str(ROOT / ".cache/tmp"),
        "XDG_CONFIG_HOME": str(ROOT / ".cache/wrangler"),
        "XDG_CACHE_HOME": str(ROOT / ".cache"),
        "npm_config_cache": str(ROOT / ".cache/npm"),
        "PATH": str(worker.NODE) + os.pathsep + os.environ.get("PATH", ""),
    }
    py, node = sys.executable, str(worker.NODE / "node.exe")
    data, ask = ROOT / ".cache/site-data", ROOT / ".cache/site-ask"
    for d in (data, ask):
        shutil.rmtree(d, ignore_errors=True)
    step(
        [
            py,
            "-m",
            "atlas.publish",
            "--origin",
            ORIGIN,
            "--out",
            str(data),
            "--approval",
            "approved",
            "--hf-repo",  # every public release is archived privately first (rollback, D187)
            pairs["HF_ARCHIVE_REPO"],
            "--alerts",  # warning archive from the signed Worker export (D189)
        ],
        ROOT,
        env,
    )
    if (ROOT / "configs/static/ka/monsoon-normals.json").exists():  # D192
        out = str(data / "data/ka/monsoon.json")
        step([py, "-m", "atlas.analysis.district_monsoon", "current", "--out", out], ROOT, env)
    step([py, "-m", "atlas.models.accuracy", "--publish", str(data)], ROOT, env)  # D207
    step([py, "-m", "atlas.rag.index"], ROOT, env)
    step([py, "-m", "atlas.rag.manifest", "--public", str(ask / "data/ask")], ROOT, env)
    worker.DEPLOY.write_text(
        worker.deploy_config(
            (ROOT / "worker/wrangler.toml").read_text("utf-8"), pairs["CLOUDFLARE_D1_DATABASE_ID"]
        ),
        encoding="utf-8",
        newline="\n",
    )
    sql = str(ROOT / "data/rag/ask-release.sql")  # new rows, then the pointer, then old rows go
    d1 = [node, str(worker.WRANGLER), "d1", "execute", "monsoon-atlas-hot", "--remote"]
    step([*d1, "--file", sql, "--config", worker.DEPLOY.name, "--yes"], ROOT / "worker", env)
    npm = str(worker.NODE / "node_modules/npm/bin/npm-cli.js")
    step([node, npm, "run", "build"], ROOT / "web", env)
    dist = ROOT / "web/dist"
    for src in (data / "data", data / "api"):
        shutil.copytree(src, dist / src.name, dirs_exist_ok=True)
    shutil.copytree(ask / "data/ask", dist / "data/ask", dirs_exist_ok=True)
    deploy = [node, str(worker.WRANGLER), "pages", "deploy", "dist", "--project-name", PROJECT]
    step([*deploy, "--branch", "main", "--commit-dirty=true"], ROOT / "web", env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
