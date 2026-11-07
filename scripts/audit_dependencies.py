"""Dependency audit and source policy checker (plan T007).

  python scripts/audit_dependencies.py --policy   offline checks; exit 1 on any violation
  python scripts/audit_dependencies.py --report   query PyPI; write docs/dependency-audit.md

Policy checks:
  - every direct requirement is an exact == pin and appears in its hash lock at that version
  - every lock entry carries hashes; torch never appears outside the dl lock
  - no secret values in configs/ or .github/ (keys live in .env or Actions secrets only)
  - no paid services referenced from code, configs or workflows
  - state configs pass validation (free sources only, sources disabled until verified)
  - workflow actions pinned to full commit SHAs, read-only token, no secrets on pull requests
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("core", "dev", "geo", "ml", "dl", "ocr")
NO_TORCH_GROUPS = ("core", "dev", "geo", "ml", "ocr")
PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)")
PAID_HOSTS = (
    "api.anthropic.com",
    "api.openai.com",
    "api.mapbox.com",
    "maps.googleapis.com",
    "r2.cloudflarestorage.com",
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),  # Telegram bot token
    re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password|map_key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"
    ),
)


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def pins(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-c", "-r", "--")):
            continue
        m = PIN_RE.match(line)
        out[norm(m.group(1)) if m else line] = m.group(2) if m else ""
    return out


def check_locks(req_dir: Path) -> list[str]:
    problems = []
    for group in GROUPS:
        src, lock = req_dir / f"{group}.in", req_dir / f"{group}.txt"
        if not src.exists():
            problems.append(f"{group}.in missing")
            continue
        if not lock.exists():
            problems.append(f"{group}.txt lock missing")
            continue
        locked = pins(lock)
        for name, version in pins(src).items():
            if not version:
                problems.append(f"{group}.in: {name!r} is not an exact == pin")
            elif locked.get(name) != version:
                problems.append(f"{group}.txt: {name} locked at {locked.get(name)}, want {version}")
        entries = re.split(r"\n(?=[A-Za-z0-9])", lock.read_text(encoding="utf-8"))
        for entry in entries:
            if PIN_RE.match(entry) and "--hash=sha256:" not in entry:
                problems.append(f"{group}.txt: {entry.split()[0]} has no hash")
        if group in NO_TORCH_GROUPS and "torch" in locked:
            problems.append(f"{group}.txt pulls in torch; only the dl group may")
    return problems


def _text_files(root: Path, dirs: tuple[str, ...]):
    for d in dirs:
        base = root / d
        if base.exists():
            for p in base.rglob("*"):
                if p.is_file() and p.suffix in {
                    ".py",
                    ".yaml",
                    ".yml",
                    ".json",
                    ".toml",
                    ".ts",
                    ".md",
                }:
                    yield p


def check_secrets(root: Path) -> list[str]:
    problems = []
    for p in _text_files(root, ("configs", ".github")):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith(("secret_env:", "#")):
                continue  # env var names are allowed; values never are
            if any(rx.search(line) for rx in SECRET_PATTERNS):
                problems.append(f"{p.relative_to(root)}:{n}: looks like a secret value")
    return problems


def check_paid(root: Path) -> list[str]:
    problems = []
    for p in _text_files(root, ("src", "configs", ".github", "worker", "web")):
        text = p.read_text(encoding="utf-8")
        for host in PAID_HOSTS:
            if host in text:
                problems.append(f"{p.relative_to(root)}: references paid service {host}")
    return problems


def check_state_configs(root: Path) -> list[str]:
    sys.path.insert(0, str(root / "src"))
    from atlas.config import load_state

    problems = []
    for p in sorted((root / "configs" / "states").glob("*.yaml")):
        try:
            load_state(p)
        except Exception as exc:  # validation errors are reported, not raised
            problems.append(f"{p.relative_to(root)}: {exc}".splitlines()[0])
    return problems


def check_workflows(root: Path) -> list[str]:
    problems = []
    for p in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(root)
        for n, line in enumerate(text.splitlines(), 1):
            m = re.search(r"uses:\s*([^\s#]+)", line)
            if (
                m
                and not m.group(1).startswith("./")
                and not re.search(r"@[0-9a-f]{40}$", m.group(1))
            ):
                problems.append(f"{rel}:{n}: action {m.group(1)} is not pinned to a commit SHA")
        if not re.search(r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$", text):
            problems.append(f"{rel}: top-level permissions must be exactly contents: read")
        if re.search(r"(?m)^\s+\w+:\s*write", text):
            problems.append(f"{rel}: write permission granted")
        if "pull_request_target" in text:
            problems.append(f"{rel}: pull_request_target exposes secrets to forks")
        if re.search(r"(?m)^\s*pull_request\s*:", text) and "secrets." in text:
            problems.append(f"{rel}: secrets referenced in a workflow that runs on pull requests")
    return problems


def policy(root: Path = ROOT) -> list[str]:
    return (
        check_locks(root / "requirements")
        + check_secrets(root)
        + check_paid(root)
        + check_state_configs(root)
        + check_workflows(root)
    )


# --- network report --------------------------------------------------------------------------


def _pypi(name: str, version: str) -> dict:
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "MonsoonAtlas-audit/0.0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _licence(info: dict) -> str:
    if info.get("license_expression"):
        return info["license_expression"]
    lic = (info.get("license") or "").strip()
    if lic and len(lic) < 60:
        return lic
    classifiers = [
        c.split(" :: ")[-1] for c in info.get("classifiers", []) if c.startswith("License ::")
    ]
    return ", ".join(classifiers) or "UNKNOWN"


def _windows_wheel(urls: list[dict]) -> str:
    names = [u["filename"] for u in urls if u["packagetype"] == "bdist_wheel"]
    if any("win_amd64" in n and re.search(r"-(cp312|cp3\d+-abi3|py3-none)-", n) for n in names):
        return "yes (win_amd64)"
    if any(n.endswith("-none-any.whl") for n in names):
        return "yes (pure Python)"
    return "NO (sdist or other platforms only)"


def report(root: Path = ROOT) -> Path:
    rows, seen = [], set()
    for group in GROUPS:
        direct = pins(root / "requirements" / f"{group}.in")
        for name, version in sorted(pins(root / "requirements" / f"{group}.txt").items()):
            if (name, version) in seen:
                continue
            seen.add((name, version))
            data = _pypi(name, version)
            lic = _licence(data["info"])
            flag = "review" if lic == "UNKNOWN" or re.search(r"\b(A?GPL|LGPL)", lic) else ""
            rows.append(
                f"| {group} | {name} | {version} | {'direct' if name in direct else 'transitive'} "
                f"| {lic} {flag} | {_windows_wheel(data['urls'])} "
                f"| https://pypi.org/project/{name}/{version}/ |"
            )
    out = root / "docs" / "dependency-audit.md"
    header = (
        "# Dependency audit\n\nGenerated by `python scripts/audit_dependencies.py --report` from "
        "the hash locks in `requirements/`. Licences are as declared on PyPI; `review` marks "
        "copyleft or undeclared licences to check before redistribution. Locks are resolved "
        "on Windows with Python 3.12, so Linux-only packages (for example CUDA wheels for "
        "torch) are not in them.\n\n"
        "| Group | Package | Version | Kind | Licence | Windows wheel | Release |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    out.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--policy", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if not (args.policy or args.report):
        parser.error("choose --policy and/or --report")
    status = 0
    if args.policy:
        problems = policy()
        for p in problems:
            print(f"POLICY: {p}")
        print(f"policy: {len(problems)} problem(s)")
        status = 1 if problems else 0
    if args.report:
        print(f"wrote {report().relative_to(ROOT)}")
    return status


if __name__ == "__main__":
    sys.exit(main())
