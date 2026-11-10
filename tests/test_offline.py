"""T218 (D162): offline plan, widget and export controls. Fast and offline.

No service worker is registered: there is no public host and no approved public snapshot (H05,
H06, H11). The pure cache plan, the banner, the widget rules and the export check are tested here
and in web/src/offline.test.ts, which this file runs when the pinned web toolchain is installed.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

from atlas.export import MAX_BYTES, MAX_ROWS, export_manifest
from atlas.ingest.base import SourceUnavailable
from atlas.models.accuracy import dashboard_data
from atlas.spatial.tiles import require_open_source

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
FIXTURE = ROOT / "tests/fixtures/s02_openmeteo_archive_bengaluru_2024-07-01_04.json"


def web_sources() -> dict[Path, str]:
    paths = [*(WEB / "src").rglob("*.ts*"), WEB / "index.html", *(WEB / "public").rglob("*")]
    return {p: p.read_text("utf-8") for p in paths if p.is_file()}


def fixture_rows() -> list[dict]:
    daily = json.loads(FIXTURE.read_text("utf-8"))["daily"]
    return [
        {"date": d, "precipitation_sum_mm": v}
        for d, v in zip(daily["time"], daily["precipitation_sum"], strict=True)
    ]


def test_manifest_is_ours_and_relative_and_linked():
    manifest = json.loads((WEB / "public/manifest.webmanifest").read_text("utf-8"))
    assert manifest["name"] == "Monsoon Atlas" and manifest["start_url"] == "./"
    assert "icons" not in manifest  # no asset exists yet; none is borrowed from another project
    text = json.dumps(manifest).lower()
    assert "kw live" not in text and "kwlive" not in text and "http" not in text
    assert 'rel="manifest" href="manifest.webmanifest"' in (WEB / "index.html").read_text("utf-8")


def test_no_service_worker_is_registered_anywhere():
    for path, text in web_sources().items():
        assert not re.search(r"serviceWorker\s*\.|\.register\(", text), path
    sw = (WEB / "src/sw.ts").read_text("utf-8")
    assert "addEventListener" not in sw and "self." not in sw and "caches." not in sw  # pure plan
    assert "20 * 1024 * 1024" in sw and "not_allowlisted" in sw and "x-atlas-cached-at" in sw


def test_widget_cannot_reach_the_embedding_page_and_has_no_controls():
    code = (WEB / "src/pages/Widget.tsx").read_text("utf-8")
    assert not re.search(r"window\.(parent|top|opener)|document\.referrer|postMessage", code)
    assert not re.search(
        r"<(button|input|form|select|textarea|iframe|script)\b|onClick|fetch\(", code
    )
    assert 'rel="noopener noreferrer"' in code and "WIDGET_ORIGINS: readonly string[] = []" in code
    assert "APP_FRAME_ANCESTORS = \"frame-ancestors 'self'\"" in code
    main = (WEB / "src/main.tsx").read_text("utf-8")
    assert "widget: () => <Widget />" in main


def test_prohibited_data_export_is_blocked_and_an_open_source_passes():
    for source_id in ("S08", "S30", "S34"):
        with pytest.raises(SourceUnavailable):
            export_manifest(source_id, fixture_rows())
    manifest, shards = export_manifest("S02", fixture_rows())
    assert (
        manifest["source_id"] == "S02" and manifest["licence"] == "open" and manifest["rows"] == 4
    )
    assert manifest["content_sha256"] == hashlib.sha256(b"".join(shards)).hexdigest()
    assert manifest["shards"][0]["sha256"] == hashlib.sha256(shards[0]).hexdigest()
    assert shards[0].count(b"\n") == 4 and b"2024-07-03" in shards[0]


def test_export_limits_split_into_shards():
    assert (MAX_ROWS, MAX_BYTES) == (10_000, 10 * 1024 * 1024)
    rows = [{"i": i} for i in range(25_000)]
    manifest, shards = export_manifest("S02", rows)
    assert [s["rows"] for s in manifest["shards"]] == [10_000, 10_000, 5_000]
    manifest, shards = export_manifest("S02", rows[:10], max_bytes=40)
    assert len(shards) > 1 and all(len(s) <= 40 for s in shards)
    with pytest.raises(ValueError):
        export_manifest("S02", rows[:1], max_bytes=3)


def test_the_browser_gate_and_the_python_gate_read_the_same_records():
    for source in dashboard_data()["sources"]:
        try:
            require_open_source(source["id"], "an export")
            allowed = True
        except SourceUnavailable:
            allowed = False
        assert allowed == (source["outcome"] == "available" and source["licence"] == "open")
    ids = {s["id"]: s for s in dashboard_data()["sources"]}
    assert all(ids[i]["licence"] != "open" for i in ("S08", "S30", "S34"))


def test_offline_unit_and_build_checks(web_check):
    for args in (["run", "build"], ["run", "test"]):
        web_check(*args)
