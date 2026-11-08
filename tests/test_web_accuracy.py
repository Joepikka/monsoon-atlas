"""T259 (child of T046): web accuracy page bound to committed records (D94)."""

from pathlib import Path

from atlas.models.accuracy import WEB_FIXTURE, release_json

ROOT = Path(__file__).resolve().parents[1]


def test_browser_fixture_matches_committed_records():
    assert WEB_FIXTURE.read_text("utf-8") == release_json()


def test_no_production_accuracy_release_is_seeded():
    assert not (ROOT / "web/public/data/ka/accuracy").exists()


def test_accuracy_page_unit_and_browser_checks(web_check):
    for args in (["run", "build"], ["run", "test"], ["run", "test:e2e", "--", "accuracy.spec.ts"]):
        web_check(*args)
