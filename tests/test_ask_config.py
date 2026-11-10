"""T253 (child of T180): Ask quotas, disabled generation and no cloud secret (D88)."""

import os
import re
import subprocess
from pathlib import Path

import pytest

from atlas.config import load_budgets
from atlas.rag.corpus import tokens

ROOT = Path(__file__).resolve().parents[1]
ASK = (ROOT / "worker/src/ask.ts").read_text("utf-8")
NODE = ROOT / ".tools/node/node-v22.16.0-win-x64"


def limit(name: str) -> int:
    return int(re.search(rf"\b{name}: (\d+)", ASK).group(1))


def test_quotas_match_plan_and_project_budget():
    budget = load_budgets(ROOT / "configs/budgets.yaml").workers_ai
    assert limit("answersPerDay") == budget.ask_requests_per_day == 100
    assert limit("neuronsPerDay") == budget.neurons_per_day == 8000
    caps = (limit("requestsPerMinute"), limit("inputTokens"), limit("outputTokens"))
    assert caps == (6, 3000, 350)
    assert (limit("questionChars"), limit("timeoutMs")) == (500, 20000)


def test_generation_is_not_bound_and_no_secret_is_bundled():
    config = (ROOT / "worker/wrangler.toml").read_text("utf-8")
    assert 'CAPABILITY_GATE = "blocked"' in config
    assert not re.search(r"(?m)^\s*(\[+ai\]+|binding\s*=)", config)  # no Workers AI binding
    assert "env." not in ASK and "fetch(" not in ASK  # pure contract: no secrets or network
    assert not re.search(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*['\"]", ASK)
    route = (ROOT / "worker/src/index.ts").read_text("utf-8")
    assert "env.AI" not in route and "generate:" not in route  # T260 route stays extractive


def test_token_rule_matches_corpus_chunking():
    pattern = re.search(r"const TOKEN = /(.+)/gu;", ASK).group(1)
    assert pattern == r"[\p{L}\p{N}_]+|[^\p{L}\p{N}_\s]"
    assert tokens("SPI-3 < -1") == 6  # same sample as worker/tests/ask.test.mjs


def test_worker_ask_contract_runs_under_pinned_node():
    if not (NODE / "node.exe").exists() or not (ROOT / "worker/node_modules").exists():
        pytest.skip("Optional pinned Worker toolchain is not installed in core-only CI")
    env = os.environ | {"TEMP": str(ROOT / ".cache/tmp"), "TMP": str(ROOT / ".cache/tmp")}
    result = subprocess.run(
        [str(NODE / "node.exe"), "--experimental-strip-types", "--test", "tests/ask.test.mjs"],
        cwd=ROOT / "worker",
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# pass 5" in result.stdout and "# fail 0" in result.stdout


def coverage_rows() -> dict[str, tuple[str, str]]:
    text = (ROOT / "docs/ask.md").read_text("utf-8")
    section = text.split("## Plan coverage T179-T181", 1)[1]
    rows = re.findall(r"(?m)^\| (T\d{3}[^|]*)\| ([^|]+)\| ([^|]+)\|$", section)
    return {step.strip(): (status.strip(), evidence) for step, status, evidence in rows}


def test_plan_coverage_table_matches_the_repository():
    rows = coverage_rows()
    assert {step.split(" ")[0] for step in rows} >= {
        "T179.1",
        "T179.2",
        "T179.3",
        "T180.1",
        "T180.2",
    }
    allowed = ("done", "not adopted", "blocked", "deviation", "FTS done")
    assert all(status.startswith(allowed) for status, _ in rows.values())
    for _, evidence in rows.values():
        for path in re.findall(r"`([\w.-]+(?:/[\w.-]+)+\.\w+)`", evidence):
            assert (ROOT / path).exists(), path


def test_chunking_and_generation_gate_match_the_plan():
    rag = (ROOT / "configs/rag.yaml").read_text("utf-8")
    assert re.search(r"(?m)^chunk_tokens: 300$", rag) and re.search(
        r"(?m)^overlap_tokens: 50$", rag
    )
    assert re.search(r"(?m)^rerank_method: R0\b", rag)  # e5 tested in T264, not adopted
    model = "@cf/qwen/qwen3-30b-a3b-fp8"  # T180.1: named only after the H05 probe passes
    for folder in ("worker/src", "web/src", "configs"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and path.suffix in {".ts", ".tsx", ".yaml", ".toml", ".json"}:
                assert model not in path.read_text("utf-8"), path
    assert model not in (ROOT / "worker/wrangler.toml").read_text("utf-8")
