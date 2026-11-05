# AGENTS.md: rules for AI coding agents

This repository is built by an AI coding agent following a fixed plan. Read this file before every task.

## Source of truth

1. `docs/plan.pdf`: the full plan (263 pages, 4 Nov 2026). Tasks T001 to T221, model cards M01 to M20, source catalogue S01 onwards, decisions D01 to D16.
2. `docs/amendments.md` and `docs/amendments.yaml`: amendments v1 (5 Nov 2026). **Where they conflict with the plan, the amendments win.** New tasks are T222 to T225.
3. `docs/decisions.md`: the decisions log. Record every deviation from the plan here before you make it.

## Hard constraints (never break)

- **Cost Rs 0.** Free tiers and open data only. No paid API, no paid hosting, no card on file. The Claude API is paid, so Ask uses a free tier (Cloudflare Workers AI) with an extractive fallback.
- **Build order:** Karnataka (P0 to P2), then Kerala (P3), then Delhi (P4), then cross-state work (P5). Follow the session order in amendments A8.
- **Real data only.** Never invent rows, labels, URLs, endpoints or API fields. Unverified sources stay disabled until their verify task passes. A disabled source raises `SourceUnavailable`; it never returns synthetic rows.
- **Honest ML.** Time-based (and, where stated, spatial) splits only. Features must be available at issue time. Always compare with the strongest simple baseline. Promote a model only if the lower 95% paired bootstrap CI of the improvement is above 0. Otherwise publish it as research-only.
- **Not an emergency service.** Official alerts, model outputs and inferred items stay visibly separate. No routing is promised to be safe.
- **No KW Live reuse.** Do not copy the KW Live name, logo, visual identity or website text.
- **Privacy.** No personal data. No accounts or subscriber databases.

## Environment

- Windows 10, 15.7 GB RAM, 4 cores, NVIDIA MX450 (2 GB, too small for deep learning; train on Kaggle or Colab).
- **Python 3.12 only** (never 3.14) in `.venv`. **DuckDB 1.x only** (2.0.0 corrupted files in an earlier project).
- Repository lives on drive D (drive C has under 20 GB free).
- DuckDB settings: `memory_limit=4GB`, `threads=4` (amendment A2).

## How to work on a task

1. Pick the next task in the amendments A8 order. Check that its dependencies are done.
2. Do only that task. Keep it within one session (about 3 hours). If it grows, split it into a child task recorded in both the task list and the YAML.
3. Run the task's acceptance command and show its output. A task is done only when the acceptance test passes.
4. Commit with the task ID in the message, for example `T002: Python 3.12 environment, linting and tests`.
5. Record any deviation in `docs/decisions.md`.

## Human-only steps (amendments A5)

The agent never creates accounts, accepts terms, enters passwords or types keys into web forms. When a task needs one of the H01 to H14 steps, stop and ask the owner. Keys live in `.env` (ignored by git) or in GitHub Actions secrets; code reads only the variable names.

## Commands

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
```
