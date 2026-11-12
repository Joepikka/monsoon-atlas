# ruff: noqa: E501
"""Build one combined handoff document for another agent (for example ChatGPT).

Run from the repository root: .venv/Scripts/python scripts/build_handoff.py
Writes handoff/MONSOON_ATLAS_FULL_HANDOFF.md from the committed docs, configs and git history.
No raw data, keys or .env content is read.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "handoff" / "MONSOON_ATLAS_FULL_HANDOFF.md"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout


def section(title: str, path: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8").strip()
    return f"\n\n---\n\n# {title}\n\nSource file: `{path}`\n\n{text}\n"


def code_block(title: str, path: str, lang: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8").strip()
    return f"\n\n---\n\n# {title}\n\nSource file: `{path}`\n\n```{lang}\n{text}\n```\n"


def main() -> None:
    head = git("rev-parse", "--short", "HEAD").strip()
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    files = git("ls-files").split()
    sizes = [(f, (ROOT / f).stat().st_size) for f in files if (ROOT / f).exists()]
    parts = [
        "# Monsoon Atlas: full handoff package",
        "",
        f"Generated {now} from commit `{head}` of https://github.com/Joepikka/monsoon-atlas",
        "",
        "## How to use this with Claude (or any agent)",
        "",
        "1. Upload this file, `docs/plan.pdf` (ChatGPT's original 263-page plan) and, if the tool allows,",
        "   the current code ZIP (tracked code, tests, configs and docs from `p1/gate-core`).",
        "2. Paste the starter prompt from section 12 of the handoff guide below.",
        "3. The agent works in `D:\\monsoon-atlas` on Joe's laptop (Windows, everything on drive D),",
        "   one task at a time: acceptance test, commit with the task ID, push, update `docs/HANDOFF.md`.",
        "4. Human-only steps (accounts, terms, passwords, keys, approvals) stay with Joe.",
        "",
        "Contents: continuation guide; handoff; agent rules; current decisions; amendments; GATE-CORE; M05",
        "model report; every source discovery report; state and model configs; file inventory; full",
        "commit history. Local raw data and `.env` are excluded from this portable bundle and never",
        "committed.",
    ]
    parts.append(section("0. Claude continuation guide", "docs/CLAUDE_HANDOFF.md"))
    parts.append(section("1. Handoff guide", "docs/HANDOFF.md"))
    parts.append(section("2. Rules for AI agents", "AGENTS.md"))
    parts.append(section("3. Decisions log", "docs/decisions.md"))
    parts.append(section("4. Plan amendments v1 (win over the plan)", "docs/amendments.md"))
    parts.append(section("5. GATE-CORE report (T222, D17, D29)", "docs/gates/core_data_gate.md"))
    parts.append(section("6. M05 drought model result (T103)", "reports/models/m05.md"))
    for i, path in enumerate(sorted(p for p in files if p.startswith("docs/sources/")), start=1):
        name = Path(path).stem.upper()
        parts.append(section(f"7.{i} Source report {name}", path))
    parts.append(
        code_block(
            "8. Karnataka state config (sources and enabled flags)",
            "configs/states/ka.yaml",
            "yaml",
        )
    )
    parts.append(code_block("9. M05 model config", "configs/models/m05.yaml", "yaml"))
    parts.append(
        "\n\n---\n\n# 10. Repository file inventory\n\n"
        + f"{len(sizes)} tracked files (raw data and secrets are git-ignored).\n\n| File | Bytes |\n|---|---|\n"
        + "\n".join(f"| `{f}` | {s:,} |" for f, s in sizes)
        + "\n"
    )
    log = git("log", "--reverse", "--format=%h %ad %s", "--date=short")
    parts.append(
        f"\n\n---\n\n# 11. Full commit history (oldest first)\n\n```text\n{log.strip()}\n```\n"
    )
    parts.append(section("12. Feed and checkpoint operations", "docs/feeds.md"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")
    print(OUT, f"{OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
