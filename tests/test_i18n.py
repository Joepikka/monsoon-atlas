"""T182: four-language UI strings and opt-in voice, checked from the source files (D148).

English is the only selectable locale: Kannada, Malayalam and Hindi are machine drafts nobody
has reviewed (D147, A7). The vitest file web/src/voice.test.ts runs the lookup and voice logic.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web/src"
LOCALES = ("en", "kn", "ml", "hi")
STATUS = "_review_status"
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def load(locale: str) -> dict[str, str]:
    raw = (WEB / f"i18n/{locale}.json").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "UTF-8 without BOM"
    return json.loads(raw.decode("utf-8"))


def sources() -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in WEB.rglob("*.ts*") if ".test." not in p.name}


def test_all_four_locales_have_the_same_keys_and_placeholders():
    en = load("en")
    for locale in LOCALES[1:]:
        other = load(locale)
        assert set(other) == set(en), locale
        for key, text in other.items():
            assert isinstance(text, str) and text.strip(), (locale, key)
            if key != STATUS:
                assert PLACEHOLDER.findall(text) == PLACEHOLDER.findall(en[key]), (locale, key)
                assert text != en[key], f"{locale}:{key} is an untranslated copy"


def test_review_status_is_recorded_and_only_english_is_selectable():
    assert load("en")[STATUS] == "reviewed"
    for locale in LOCALES[1:]:
        assert load(locale)[STATUS] == "machine_draft_unreviewed"
    index = (WEB / "i18n/index.ts").read_text(encoding="utf-8")
    assert re.search(r"SELECTABLE[^=]*=\s*\['en'\]", index)
    ask = (WEB / "pages/Ask.tsx").read_text(encoding="utf-8")
    assert "<select" not in ask and "locale" not in ask  # no language switch is offered


def test_every_lookup_key_exists_and_no_key_is_dead():
    en = load("en")
    used = set()
    for path, text in sources().items():
        if path.parent.name == "i18n":
            continue
        used |= set(re.findall(r"\bt\(\s*'([\w.]+)'", text))
        used |= set(re.findall(r"'((?:ask|corpus|result|voice|read)\.\w+)'", text))
    assert used - set(en) == set()
    assert set(en) - {STATUS} - used == set()


def test_ask_controls_do_not_bypass_the_lookup():
    ask = (WEB / "pages/Ask.tsx").read_text(encoding="utf-8")
    jsx = ask[ask.index("return <main") :]
    assert not re.findall(r">([^<>{}]*[A-Za-z][^<>{}]*)<", jsx), "literal text in JSX"
    assert not re.findall(r"(?:aria-label|title|placeholder|alt)=\"", jsx)
    assert not re.findall(r"message: '", (WEB / "ask.ts").read_text(encoding="utf-8"))


def test_microphone_and_speech_start_only_from_a_button_press():
    code = sources()
    for path, text in code.items():
        assert "getUserMedia" not in text, path
        if path.name != "voice.ts":
            started = re.search(r"SpeechRecognition|\.start\(\)|speechSynthesis\.speak", text)
            assert not started, path
    ask = (WEB / "pages/Ask.tsx").read_text(encoding="utf-8")
    assert ask.count("listen(") == 1 and ask.count("speak(") == 1
    for handler, call in (("toggleVoice", "listen("), ("readAloud", "speak(")):
        assert f"onClick={{{handler}}}" in ask
        body = ask[ask.index(f"function {handler}") :].split("\n  }\n")[0].split("\n\n")[0]
        assert call in body, handler
    assert re.findall(r"useEffect\(.*", ask) == [re.findall(r"useEffect\(.*loadCorpus.*", ask)[0]]
    voice = (WEB / "voice.ts").read_text(encoding="utf-8")
    assert voice.count(".start()") == 1 and voice.count(".speak(") == 1  # one start, one speak


@pytest.mark.parametrize("locale", LOCALES)
def test_json_is_valid_utf8_with_lf_endings(locale):
    raw = (WEB / f"i18n/{locale}.json").read_bytes()
    assert b"\r" not in raw and raw.endswith(b"}\n")


def test_map_carries_the_boundary_disclaimer_in_all_locales():
    # H11 item 8 (D166): every public map shows it; the app footer area is App.tsx's map panel.
    assert load("en")["map.disclaimer"] == (
        "District boundaries are approximate and not authoritative. "
        "For official boundaries see the Survey of India."
    )
    for locale in LOCALES:
        assert load(locale)["map.disclaimer"].strip()
    assert "t('map.disclaimer')" in (WEB / "App.tsx").read_text(encoding="utf-8")
