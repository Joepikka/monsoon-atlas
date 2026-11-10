"""T188: wall mode contract, checked from the source files (D154).

Behaviour (current, stale and disconnected states, source timestamps kept, ticker pause under
reduced motion, Escape, four columns at 1920 px) is tested in web/src/map/WallMode.test.ts by
rendering the component to markup. The Playwright viewport is not used: that layout rule is a
pure function and the rendered markup carries the grid, so no timing-sensitive browser step is
needed. Here: no sound, no flashing, one ticker, strings through the lookup, and the 24 hour
limit equal to the app's.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web/src"
WALL = (WEB / "map/WallMode.tsx").read_text(encoding="utf-8")
CSS = (WEB / "styles.css").read_text(encoding="utf-8")
WALL_CSS = CSS[CSS.index("T188: wall mode") :]


def test_no_sound_no_flashing_and_no_motion():
    assert not re.search(r"<audio|<video|new Audio|AudioContext|\.play\(|autoPlay|autoplay", WALL)
    assert not re.search(r"@keyframes|animation|transition|blink|flash|opacity", WALL_CSS)
    assert not re.search(
        r"setInterval|setTimeout|requestAnimationFrame", WALL
    )  # motion is the ticker's


def test_it_reuses_the_existing_ticker_and_source_pause_and_does_not_write_a_second():
    assert "import EventTicker from '../components/EventTicker'" in WALL
    ticker = (WEB / "components/EventTicker.tsx").read_text(encoding="utf-8")
    assert "Pause alerts" in ticker and "prefers-reduced-motion: reduce" in ticker
    assert "setInterval" in ticker and "aria-pressed={paused}" in ticker
    assert "wall-ticker" in WALL and not (WEB / "map/WallTicker.tsx").exists()


def test_escape_exits_and_the_exit_button_is_focused():
    assert "'Escape'" in WALL and "addEventListener('keydown'" in WALL
    assert "removeEventListener('keydown'" in WALL and "exit.current?.focus()" in WALL


def test_the_stale_limit_is_the_apps_and_a_stale_wall_never_says_live_or_current():
    data = (WEB / "data.ts").read_text(encoding="utf-8")
    assert "export const STALE_MS = 24 * 60 * 60 * 1000;" in data
    assert "STALE_MS" in WALL and not re.search(r"\blive\b", WALL, re.IGNORECASE)
    en = json.loads((WEB / "i18n/en.json").read_text(encoding="utf-8"))
    assert "24 hours" in en["wall.state_stale"] and "disconnected" in en["wall.state_disconnected"]
    assert "stale" in en["wall.alerts_hidden"] and "disconnected" in en["wall.alerts_hidden"]


def test_wall_strings_come_from_the_lookup_in_all_four_locales():
    jsx = WALL[WALL.index("return <section") :]
    assert not re.findall(r">([^<>{}]*[A-Za-z][^<>{}]*)<", jsx), "literal text in JSX"
    assert not re.findall(r"(?:aria-label|title|placeholder|alt)=\"", jsx)
    wall_keys = set()
    for locale in ("en", "kn", "ml", "hi"):
        keys = {
            k for k in json.loads((WEB / f"i18n/{locale}.json").read_text("utf-8")) if "wall" in k
        }
        wall_keys = wall_keys or keys
        assert keys == wall_keys, locale
    assert wall_keys == set(re.findall(r"\bt\(\s*'(wall\.\w+)'", WALL))  # none unused, none missing
    assert (
        "not an emergency service"
        in json.loads((WEB / "i18n/en.json").read_text("utf-8"))["wall.not_emergency"].lower()
    )
