"""T217 (D161): the four dashboards are bound to committed records and cannot drift from them.

web/src/dashboards.json is built by atlas.models.accuracy from the model registry, the source
records and the M16 and M05 monitor files. The pages themselves are checked in vitest
(web/src/dashboards.test.ts), which this file runs when the pinned web toolchain is installed.
"""

import json
import re
from pathlib import Path

from atlas.models.accuracy import DASHBOARD_DATA, accuracy_rows, dashboard_data, dashboard_json

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads(DASHBOARD_DATA.read_text("utf-8"))


def test_dashboard_data_matches_committed_records():
    assert DASHBOARD_DATA.read_text("utf-8") == dashboard_json()


def test_only_m05_has_a_score_and_it_matches_the_registry_with_a_denominator_and_ci():
    scored = [m for m in DATA["models"] if m["score"] is not None]
    assert [m["id"] for m in scored] == ["M05"]
    score = scored[0]["score"]
    m05 = next(r for r in accuracy_rows() if r["model"] == "M05")
    assert score["model_value"] == m05["candidate"] and score["ci95"] == m05["ci95"]
    assert score["label"] == "hindcast" and score["rows"] == 1800 and score["months"] == 60
    assert score["ci95"][0] > 0  # the promotion rule: lower 95% bound above 0
    blocked = [m for m in DATA["models"] if m["id"] != "M05"]
    assert len(blocked) == 19 and all(m["status"] in {"blocked", "research_only"} for m in blocked)
    assert all(m["score"] is None and m["reason"] for m in blocked)


def test_hidden_m05_intervals_and_s08_values_are_not_in_the_data():
    text = DASHBOARD_DATA.read_text("utf-8").lower()
    m05 = next(m for m in DATA["models"] if m["id"] == "M05")
    assert not [k for k in m05["score"] if "interval" in k or "width" in k]
    assert "coverage_by_season" not in text and "interval80" not in text
    assert "cell_box" not in text and "rain_mm" not in text


def test_every_card_links_an_existing_source_record_or_report():
    links = [link for m in DATA["models"] for link in m["links"]]
    links += [s["link"] for s in DATA["sources"]] + [a["link"] for a in DATA["analyses"]]
    links += DATA["anomaly_queue"]["links"] + [DATA["drift"]["link"]]
    links += [s["link"] for s in DATA["series"]]
    links += [v[k] for v in DATA["states"].values() for k in ("link", "page")]
    assert all(m["links"] for m in DATA["models"])
    assert all(a["link"] for a in DATA["analyses"]) and all(s["link"] for s in DATA["sources"])
    for link in links:
        assert (ROOT / link).is_file(), link
    assert {src for a in DATA["analyses"] for src in a["sources"]} <= {
        s["id"] for s in DATA["sources"]
    }


def test_state_counts_match_the_gate_pages():
    ka = (ROOT / "docs/releases/ka-v1.md").read_text("utf-8")
    kl = (ROOT / "docs/releases/kl.md").read_text("utf-8")
    dl = (ROOT / "docs/releases/dl.md").read_text("utf-8")
    pairs = {
        "ka": re.search(r"(\d+) of (\d+) sources enabled", ka),
        "kl": re.search(r"(\d+) of (\d+) Kerala sources enabled", kl),
        "dl": re.search(r"(\d+) of (\d+) Delhi sources enabled", dl),
    }
    for state, found in pairs.items():
        assert found, state
        counts = DATA["states"][state]
        assert (counts["enabled"], counts["sources"]) == tuple(map(int, found.groups())), state
    assert [DATA["states"][s]["blocked"] for s in ("kl", "dl")] == [7, 2]


def test_review_queue_is_unadjudicated_counts_from_the_m16_file_and_no_values():
    queue = DATA["anomaly_queue"]
    counts = json.loads((ROOT / "reports/models/m16-flag-counts.json").read_text("utf-8"))["totals"]
    assert queue["label"] == "unadjudicated rule output, not incidents"
    assert (queue["adjudicated"], queue["required"]) == (0, 100)
    assert {k: v["flags"] for k, v in queue["states"].items()} == {
        k: v["flags_z"] for k, v in counts.items()
    }
    assert set(queue["states"]["ka"]) == {"evaluated", "flags"}


def test_drift_is_the_m05_2025_monitor_record():
    monitor = json.loads((ROOT / "models/registry/M05/v1.monitor-2025.json").read_text("utf-8"))
    drift = DATA["drift"]
    assert (drift["flag"], drift["rows"], drift["mae_ratio"]) == (
        monitor["flag"],
        monitor["rows"],
        monitor["mae_ratio"],
    )
    assert "hindcast" in drift["label"]


def test_the_only_series_is_ka_so_no_state_pair_is_comparable():
    assert [s["state"] for s in dashboard_data()["series"]] == ["ka"]


def test_new_pages_are_wired_and_use_only_the_string_lookup():
    main = (ROOT / "web/src/main.tsx").read_text("utf-8")
    for page in ("quality", "analysis", "compare"):
        assert re.search(rf"\b{page}: \(\) =>", main), page
    for name in ("Quality", "Analysis", "Compare"):
        jsx = (ROOT / f"web/src/pages/{name}.tsx").read_text("utf-8")
        jsx = jsx[jsx.index("return <main") :]
        assert not re.findall(r">([^<>{}]*[A-Za-z][^<>{}]*)<", jsx), f"literal text in {name}"


def test_dashboard_unit_and_build_checks(web_check):
    for args in (["run", "build"], ["run", "test"]):
        web_check(*args)
