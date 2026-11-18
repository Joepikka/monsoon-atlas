"""T219 (D163): monitoring alerts, delivery, quota thresholds and the rollback drill.

Inputs marked "test input" are hand-built numbers, not observations. The M05 frozen baseline and
the source cadences are read from the committed release and source records.
"""

import hashlib
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from test_asof import fixture_rows, table
from test_storage import PUBLISHED, published

from atlas import jsonl, monitoring
from atlas.config import load_budgets, load_state
from atlas.data.budget import GB, QuotaLedger, StorageQuota
from atlas.data.store import write_partitioned
from atlas.monitoring import (
    Alert,
    append_correction,
    cadence_hours,
    current_label,
    deliver,
    feed_age_alert,
    frozen_baseline_mae,
    mae_alert,
    missingness_alert,
    model_sources,
    psi_alert,
    residual_alert,
    rollback_if_corrupt,
    schema_alert,
    stopped_models,
    storage_alerts,
    write_report_revision,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 11, 6, 0, tzinfo=UTC)


# --- feeds ------------------------------------------------------------------------------------


def test_cadence_comes_from_the_stated_schedule_and_is_never_invented():
    assert cadence_hours("every 6 hours") == 6
    assert cadence_hours("every 15 minutes") == 0.25
    assert cadence_hours("hourly (past-day feed); history by dated query") == 1
    assert cadence_hours("daily; store every run (no archive of runs)") == 24
    for stated in ("yearly check", "static, on demand", "once per release", None):
        assert cadence_hours(stated) is None
    schedules = {
        s.source_id: s.schedule for s in load_state(ROOT / "configs/states/ka.yaml").sources
    }
    assert cadence_hours(schedules["S01"]) == 6  # the S01 record states "every 6 hours"


def test_stale_feed_alerts_with_age_and_stops_the_models_that_read_it():
    schedule = "every 6 hours"
    assert feed_age_alert("S01", schedule, NOW - timedelta(hours=11), NOW) is None
    alert = feed_age_alert("S01", schedule, NOW - timedelta(hours=13), NOW)
    assert (alert.kind, alert.subject, alert.evidence["age_hours"]) == ("feed_stale", "S01", 13.0)
    assert feed_age_alert("S01", schedule, None, NOW).evidence["age_hours"] is None
    assert feed_age_alert("S29", "yearly check", None, NOW) is None  # no recurring cadence stated
    stopped = stopped_models(["S01"], model_sources(ROOT))
    assert {a.subject for a in stopped} == {"M01", "M15"}  # the configs that read S01
    assert all(
        a.kind == "model_stopped" and a.evidence["stale_sources"] == ["S01"] for a in stopped
    )


def test_model_dependencies_come_from_the_configs():
    deps = model_sources(ROOT)
    assert deps["M05"] == ["S08"] and deps["M07"] == ["S32", "S34", "S33"]
    assert deps["M16"] == ["S08"]  # only the source M16 reads, not the ones it records as unused
    assert deps["M21"] == ["S08"] and len(deps) == 21


def test_missingness_and_schema_alerts():  # test input: counts and field maps
    assert missingness_alert("S01", 5, 100) is None
    assert missingness_alert("S01", 25, 100).evidence["missing_fraction"] == 0.25
    empty = missingness_alert("S01", 0, 0)
    assert empty.evidence["missing_fraction"] is None  # undefined denominator, not 0
    base = {"date": "string", "rain_mm": "double"}
    assert schema_alert("S02", base, dict(base)) is None
    alert = schema_alert("S02", base, {"date": "string", "rain_mm": "int64", "extra": "string"})
    assert alert.evidence == {"added": ["extra"], "removed": [], "retyped": ["rain_mm"]}


# --- model drift ------------------------------------------------------------------------------


def test_psi_needs_two_consecutive_windows_above_the_limit():  # test input: synthetic samples
    train = [i % 10 for i in range(1000)]
    same = [i % 10 for i in range(300)]
    shifted = [5 + i % 5 for i in range(300)]
    assert psi_alert("M05", "rain", train, [same, same]) is None
    assert psi_alert("M05", "rain", train, [shifted, same]) is None  # only the older window
    assert psi_alert("M05", "rain", train, [same, shifted]) is None  # only the latest window
    alert = psi_alert("M05", "rain", train, [same, shifted, shifted])
    assert alert.kind == "model_psi" and all(v > 0.2 for v in alert.evidence["psi"])
    assert psi_alert("M05", "rain", train, [shifted]) is None


def test_residual_mae_over_14_labelled_days_against_the_frozen_m05_baseline():
    baseline = frozen_baseline_mae("M05", ROOT)  # real: the M05 v1 release, persistence MAE
    assert baseline == pytest.approx(0.8082546)
    day = date(2026, 6, 1)
    ok = {day + timedelta(days=i): 1.2 * baseline for i in range(14)}  # test input
    bad = {day + timedelta(days=i): 1.2 * baseline + 0.01 for i in range(14)}  # test input
    assert residual_alert("M05", ok, baseline) is None
    assert residual_alert("M05", bad, baseline).kind == "model_residual"
    assert residual_alert("M05", dict(list(bad.items())[:13]), baseline) is None  # under 14 days
    older_bad = {day - timedelta(days=30): 9.0} | ok  # only the latest 14 labelled days count
    assert residual_alert("M05", older_bad, baseline) is None


def test_the_real_m05_2025_monitor_is_inside_the_limit():
    rows = monitoring.committed_report(ROOT, NOW)
    m05 = rows[0]
    assert m05["status"] == "ok" and "0.625" in m05["detail"]
    assert mae_alert("M05", 0.969, 0.8082546) is None and mae_alert("M05", 0.971, 0.8082546)
    assert {r["status"] for r in rows[1:3]} == {"unavailable"}


# --- budgets and delivery ---------------------------------------------------------------------


def test_storage_warns_at_80_percent_and_is_archive_only_at_95_percent(tmp_path):
    budgets = load_budgets(ROOT / "configs/budgets.yaml")
    data = tmp_path / "clean"
    data.mkdir()
    quota = StorageQuota((data,), budget_bytes=1000, warn_at=0.8, stop_at=0.95)
    ledger = QuotaLedger(tmp_path / "ledger.jsonl")
    day = NOW.date()
    (data / "a").write_bytes(b"x" * 799)
    assert storage_alerts(budgets, ledger, quota, day) == []
    (data / "b").write_bytes(b"x" * 1)
    assert [a.kind for a in storage_alerts(budgets, ledger, quota, day)] == ["storage_warn"]
    (data / "c").write_bytes(b"x" * 150)
    alert = storage_alerts(budgets, ledger, quota, day)[0]
    assert alert.kind == "storage_archive_only" and "nothing is deleted" in alert.action
    assert quota.budget_bytes < GB and (data / "a").exists()  # nothing was deleted


def test_a_service_over_its_daily_cap_alerts(tmp_path):
    budgets = load_budgets(ROOT / "configs/budgets.yaml")
    quota = StorageQuota((tmp_path,), budget_bytes=GB, warn_at=0.8, stop_at=0.95)
    ledger = QuotaLedger(tmp_path / "ledger.jsonl")
    ledger.record("open_meteo", "calls", 2001, at=NOW)  # test input; the cap is 2000 per day
    alerts = storage_alerts(budgets, ledger, quota, NOW.date())
    assert [(a.kind, a.subject) for a in alerts] == [("quota_over", "open_meteo.calls")]


def test_alerts_are_delivered_only_to_the_owner_run_log(tmp_path):
    log = tmp_path / "monitor.jsonl"
    alerts = [Alert("feed_stale", "S01", {"age_hours": 13.0}, "check the feed log")]
    assert deliver(alerts, log, NOW) == 1
    assert deliver(alerts, log, NOW) == 1  # append-only: a second delivery adds a line
    lines = jsonl.read(log)
    assert [e["kind"] for e in lines] == ["feed_stale", "feed_stale"]
    assert lines[0]["at"] == NOW.isoformat() and lines[0]["subject"] == "S01"
    source = (ROOT / "src/atlas/monitoring.py").read_text("utf-8")
    assert not re.search(
        r"^\s*(import|from)\s+(httpx|requests|urllib|smtplib|socket|telegram)", source, re.M
    )
    assert "https://" not in source


# --- rollback drill ---------------------------------------------------------------------------


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_corrupted_release_rolls_back_and_the_ledger_keeps_prediction_and_correction(tmp_path):
    ms, first, clean = published(tmp_path, "r1")  # real Open-Meteo fixture rows in Parquet
    files = write_partitioned(table(fixture_rows()[:2]), clean)
    second = ms.build("r2", files, published_at=PUBLISHED + timedelta(days=1))
    ms.publish(second)
    assert ms.current().release_id == "r2" and rollback_if_corrupt(ms) is None  # healthy: no move

    # Prediction history: one append-only ledger (test inputs) and a first report.
    ledger = tmp_path / "ledger.jsonl"
    jsonl.append(
        ledger,
        {
            "kind": "prediction",
            "prediction_id": "p1",
            "model": "M05",
            "value": 0.4,
            "issued_at": "2026-11-01T00:00:00+00:00",
            "release": "r2",
        },
    )
    jsonl.append(ledger, {"kind": "label", "prediction_id": "p1", "label": 0.9})
    report1 = write_report_revision(tmp_path / "reports", "m05-eval", {"mae": 0.5, "label": 0.9})
    before = {p: sha(p) for p in (ledger, report1)}
    ledger_before = ledger.read_bytes()
    manifests_before = {p.name: sha(p) for p in (tmp_path / "manifests").glob("r*.json")}

    corrupt = next(f for f in second.files if f not in first.files)
    with open(clean / corrupt.path, "ab") as f:
        f.write(b"corruption")
    result = rollback_if_corrupt(ms)

    assert result["from"] == "r2" and result["to"] == "r1"
    assert ms.current().release_id == "r1" and ms.current() == first
    assert result["data_revision"] == first.data_revision  # the pointer names the prior hash
    assert {p: sha(p) for p in (ledger, report1)} == before  # history was not rewritten
    assert {p.name: sha(p) for p in (tmp_path / "manifests").glob("r*.json")} == manifests_before

    # A corrupted label is re-scored as a new revision; the old line and old report stay.
    assert append_correction(ledger, "p1", 0.7, "label source corrected", NOW) == 1
    assert append_correction(ledger, "p1", 0.75, "second correction", NOW) == 2
    report2 = write_report_revision(tmp_path / "reports", "m05-eval", {"mae": 0.3, "label": 0.7})
    assert (
        report2.name == "m05-eval.r2.json" and report1.exists() and sha(report1) == before[report1]
    )
    entries = jsonl.read(ledger)
    assert [e["kind"] for e in entries] == [
        "prediction",
        "label",
        "label_correction",
        "label_correction",
    ]
    assert ledger.read_bytes().startswith(ledger_before)  # old lines are an untouched prefix
    assert current_label(ledger, "p1") == 0.75 and entries[1]["label"] == 0.9


def test_rollback_refuses_when_there_is_no_prior_release_or_the_prior_one_is_bad(tmp_path):
    ms, first, clean = published(tmp_path, "r1")
    with open(clean / first.files[0].path, "ab") as f:
        f.write(b"x")
    with pytest.raises(ValueError, match="no prior release"):
        rollback_if_corrupt(ms)
    assert ms.current().release_id == "r1"  # nothing moved


def test_a_stale_feed_report_pairs_with_stopped_models():
    deps = model_sources(ROOT)
    stale = feed_age_alert("S01", "every 6 hours", NOW - timedelta(days=2), NOW)
    stopped = stopped_models([stale.subject], deps)
    assert stale.kind == "feed_stale" and {a.subject for a in stopped} == {"M01", "M15"}


# --- the workflow -----------------------------------------------------------------------------


def test_monitor_workflow_is_manual_read_only_and_messages_no_one():
    text = (ROOT / ".github/workflows/monitor.yml").read_text("utf-8")
    assert re.search(r"(?m)^on:\s*\n\s+workflow_dispatch:", text)
    assert not re.search(
        r"(?m)^\s*(schedule|push|pull_request|pull_request_target|workflow_run)\s*:", text
    )
    assert re.search(r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$", text)
    assert "secrets." not in text and "GITHUB_STEP_SUMMARY" in text
    assert not re.search(r"(?i)slack|telegram|mail|webhook|curl|notify", text)
    assert all(
        re.search(r"@[0-9a-f]{40}$", u.split("#")[0].strip())
        for u in re.findall(r"uses:\s*(\S+)", text)
    )
    assert "python -m atlas.monitoring" in text


def test_runbook_lists_the_commands_the_drill_exercises():
    text = (ROOT / "docs/runbooks/rollback.md").read_text("utf-8")
    for command in (
        "rollback_if_corrupt",
        "append_correction",
        "write_report_revision",
        "python -m atlas.monitoring",
        "atlas quota --check",
    ):
        assert command in text, command
