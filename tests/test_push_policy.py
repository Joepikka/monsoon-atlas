"""T184: background Web Push stays disabled under privacy_mode=no_personal_data (D150).

The Worker refusal and the browser capability report run under the pinned Node (as in
tests/test_dl_poll.py). The rest is read from the source: no code creates a push subscription,
asks for notification permission or registers a service worker, and the decision document holds
the conflict, the conditional design and the feature status.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/decisions/web-push.md"
NODE = ROOT / ".tools/node/node-v22.16.0-win-x64/node.exe"


def shipped() -> dict[Path, str]:
    return {
        p: p.read_text(encoding="utf-8")
        for folder in ("web/src", "worker/src")
        for p in (ROOT / folder).rglob("*.ts*")
        if ".test." not in p.name
    }


def test_no_subscription_is_created_and_no_permission_is_requested():
    code = shipped()
    assert (ROOT / "web/src/push.ts") in code and (ROOT / "worker/src/push.ts") in code
    for path, text in code.items():
        assert not re.search(
            r"pushManager|\.subscribe\(|requestPermission|serviceWorker\.register|showNotification",
            text,
        ), path
    assert not (ROOT / "web/public/sw.js").exists()


def test_worker_refuses_registration_and_browser_reports_the_reason():
    if not NODE.exists():
        pytest.skip("Optional pinned Worker toolchain is not installed in core-only CI")
    env = {**os.environ, "TEMP": str(ROOT / ".cache/tmp"), "TMP": str(ROOT / ".cache/tmp")}
    result = subprocess.run(
        [str(NODE), "--experimental-strip-types", "--test", "tests/push.test.mjs"],
        cwd=ROOT / "worker",
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    # web/src/push.test.ts (vitest) checks the browser side: enabled false, the same reason.


def test_the_worker_route_is_wired_before_the_capability_gate():
    index = (ROOT / "worker/src/index.ts").read_text(encoding="utf-8")
    assert index.index("pushRegistration(request)") < index.index("env.CAPABILITY_GATE !==")
    assert "push.test.mjs" in (ROOT / "worker/package.json").read_text(encoding="utf-8")


def test_decision_document_holds_the_conflict_and_the_conditional_design():
    text = DOC.read_text(encoding="utf-8")
    low = " ".join(text.lower().split())
    for needle in (
        "privacy_mode=no_personal_data",
        "pseudonymous personal data",
        "endpoint",
        "keys",
        "f051",
        "conditional stretch",
        "consent",
        "encrypted",
        "30-day expiry",
        "delete endpoint",
        "batch send",
        "no public repository storage",
        "do not enable any of this without a written policy revision",
    ):
        assert needle in low, needle
    assert "disabled" in low and "in-app watch notifications" in low


def test_the_privacy_rule_that_causes_the_conflict_is_still_in_force():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "No personal data. No accounts or subscriber databases." in agents
