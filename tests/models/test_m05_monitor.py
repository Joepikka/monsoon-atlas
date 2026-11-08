"""T263 (child of T103): M05 2025 monitoring check fixed by D98 before scoring."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = json.loads((ROOT / "models/registry/M05/v1.monitor-2025.json").read_text("utf-8"))
REPORT = (ROOT / "reports/models/m05-2025.md").read_text("utf-8")


def numbers(value):
    if isinstance(value, dict):
        return [n for v in value.values() for n in numbers(v)]
    if isinstance(value, list):
        return [n for v in value for n in numbers(v)]
    return [value] if isinstance(value, int | float) and not isinstance(value, bool) else []


def test_record_scores_the_unused_2025_year_with_the_v1_inputs():
    release = json.loads((ROOT / "models/registry/M05/v1.json").read_text("utf-8"))
    manifest = json.loads((ROOT / "tests/fixtures/s08/manifest.json").read_text("utf-8"))
    e06 = next(e for e in manifest["evidence"] if e["id"] == "e06")
    assert e06["url"].endswith("rain=2025") and RECORD["s08_2025_sha256"] == e06["sha256"]
    assert RECORD["dataset_sha256_1981_2024"] == release["dataset_sha256"]
    assert release["cutoffs"]["test"].endswith("2024-12-31")  # 2025 was never scored
    assert (RECORD["period"], RECORD["rows"], RECORD["months"]) == (
        "2025-01-01/2025-12-31",
        360,
        12,
    )


def test_flag_and_hidden_intervals_follow_d98():
    mae = RECORD["mae"]
    assert RECORD["flag"] == ("holds" if mae["ridge"] <= mae["persistence"] else "degraded")
    assert abs(RECORD["mae_ratio"] - mae["ridge"] / mae["persistence"]) < 1e-12
    imp = RECORD["improvement"]
    assert imp["lower95"] <= imp["mean"] <= imp["upper95"]
    assert RECORD["interval80"]["shown"] is False  # one year is below the 24-month minimum


def test_report_states_limits_and_uses_only_recorded_numbers():
    assert f"**Flag: {RECORD['flag']}.**" in REPORT
    assert "provisional" in REPORT and "hindcast (D39)" in REPORT and "not a new release" in REPORT
    recorded = numbers(RECORD)
    for number in re.findall(r"-?\d+\.\d{3}", REPORT):
        assert any(f"{v:.3f}" == number for v in recorded), number
