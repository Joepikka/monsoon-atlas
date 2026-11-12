"""D199: the site's Data findings bundle is generated from committed results and stays in sync."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("findings", ROOT / "scripts/findings_product.py")
fp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp)


def test_bundle_matches_generator():
    assert (ROOT / "web/src/findings.json").read_text("utf-8") == fp.text()


def test_bundle_holds_indices_and_shares_only():
    d = json.loads(fp.text())
    text = json.dumps(d)
    for banned in ("gauge_mm", "grid_mm", "rain_mm", "stop_id", "route_id", "trip", "departure"):
        assert banned not in text, banned
    assert d["trends"]["significant"] == 9 and d["spatial"]["significant"] == 57
    assert abs(d["bus"]["covered_share"] - 0.6534) < 1e-9
    for path in (d["hospital"]["report"], d["bus"]["report"], d["model"]["report"]):
        assert (ROOT / path).exists(), path
