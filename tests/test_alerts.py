"""T183: place watches, daily brief and the Telegram message, tested on the committed S09 files.

The brief is built from real public-domain Sachet CAP fixtures (tests/fixtures/s09_*), with copies
edited the way tests/sources/test_s09.py does for update, cancel and expiry cases. Current records
for the model and inferred sections are hand-built TEST INPUTS. Telegram sending is blocked (H08).
The web watch rules are tested in web/src/components/Watches.test.ts; here we scan its source.
"""

import hashlib
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pytest

from atlas.alerts import brief as brief_mod
from atlas.alerts import telegram
from atlas.alerts.brief import CurrentRecord, build_brief
from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s09 import S09

ROOT = Path(__file__).resolve().parents[1]
KA_CAP = ROOT / "tests/fixtures/s09_sachet_cap_1793881986295019.xml"
CONFIG = load_state(ROOT / "configs/states/ka.yaml").source("S09")
RUN = date(2026, 11, 5)
START = datetime(2026, 11, 5, 1, 0, tzinfo=UTC)  # the 01:00 UTC job = 06:30 IST
DURING = datetime(2026, 11, 5, 13, 0, tzinfo=UTC)  # after the fixture alert was sent
SENT = "2026-11-05T18:05:10+05:30"  # fixture sent and onset time, 12:35:10 UTC
REF = "IMD-Bengaluru,IN-1793881986295019_51,2026-11-05T18:01:57+05:30"
ORIGINAL = (
    ("IN-1793881986295019_19", "IN-1793881986295019_51"),
    ("<cap:msgType>Update", "<cap:msgType>Alert"),
    ("<cap:sender>Karnataka-SNDMC", "<cap:sender>IMD-Bengaluru"),
    (SENT, "2026-11-05T18:01:57+05:30"),
    (f"<cap:references>{REF}</cap:references>", "<cap:references/>"),
)


def parse(tmp_path: Path, name: str, *swaps: tuple[str, str]) -> pa.Table:
    text = KA_CAP.read_text("utf-8")
    for old, new in swaps:
        assert old in text, old
        text = text.replace(old, new)
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    raw = RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=datetime(2026, 11, 5, 13, 5, 40, tzinfo=UTC),
        media_type="text/xml",
        response_status=200,
        source_url=f"https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?id={name}",
        schema_mapping_version="s09-v1",
    )
    return S09("ka").parse(raw, CONFIG)


def ids(brief) -> list[str]:
    return [x.text.split(" Issued by")[0] for x in brief.lines if x.provenance == "official"]


def test_active_alert_keeps_its_source_link_and_timestamps(tmp_path):
    table = parse(tmp_path, "update.xml")
    got = build_brief("ka", RUN, DURING, table)
    (line,) = got.lines
    assert line.provenance == "official" and line.source_url == table["source_url"][0].as_py()
    assert line.as_of == datetime(2026, 11, 5, 12, 35, 10, tzinfo=UTC)
    assert "Thunderstorm with Lightning (Moderate)" in line.text
    assert "5 districts of Karnataka" in line.text and "Karnataka-SNDMC" in line.text
    assert "2026-11-05 18:05 IST" in line.text and "until 2026-11-05 21:00 IST" in line.text


def test_cancelled_and_superseded_alerts_are_not_repeated(tmp_path):
    update = parse(tmp_path, "update.xml")
    original = parse(tmp_path, "original.xml", *ORIGINAL)
    assert len(build_brief("ka", RUN, DURING, original).lines) == 1  # alone it is active
    both = build_brief("ka", RUN, DURING, pa.concat_tables([original, update]))
    assert (
        len(both.lines) == 1 and "Karnataka-SNDMC" in both.lines[0].text
    )  # the update replaces it
    cancel = parse(
        tmp_path,
        "cancel.xml",
        ("<cap:identifier>IN-1793881986295019_19", "<cap:identifier>IN-1793881986295019_77"),
        ("<cap:msgType>Update", "<cap:msgType>Cancel"),
        (REF, "Karnataka-SNDMC,IN-1793881986295019_19,2026-11-05T18:05:10+05:30"),
    )
    gone = build_brief("ka", RUN, DURING, pa.concat_tables([original, update, cancel]))
    assert gone.lines == ()
    assert "No active official alerts" in telegram.format_message(gone)


def test_duplicates_collapse_and_a_later_revision_wins(tmp_path):
    update = parse(tmp_path, "update.xml")
    assert len(build_brief("ka", RUN, DURING, pa.concat_tables([update, update])).lines) == 1
    later = parse(tmp_path, "later.xml", (SENT, "2026-11-05T18:30:00+05:30"))
    got = build_brief("ka", RUN, DURING, pa.concat_tables([update, later]))
    assert len(got.lines) == 1 and got.lines[0].as_of == datetime(2026, 11, 5, 13, 0, tzinfo=UTC)


def test_expired_and_not_yet_sent_alerts_are_dropped_and_open_ended_ones_say_so(tmp_path):
    update = parse(tmp_path, "update.xml")  # expires 15:30 UTC
    expiry = datetime(2026, 11, 5, 15, 30, tzinfo=UTC)
    assert build_brief("ka", RUN, expiry - timedelta(seconds=1), update).lines != ()
    assert build_brief("ka", RUN, expiry, update).lines == ()  # expired exactly at its end time
    assert build_brief("ka", RUN, START, update).lines == ()  # sent after this run finished
    open_ended = parse(
        tmp_path, "open.xml", ("<cap:expires>2026-11-05T21:00:00+05:30</cap:expires>", "")
    )
    (line,) = build_brief("ka", RUN, expiry + timedelta(days=1), open_ended).lines
    assert "no end time given" in line.text and line.expires_at is None


def test_official_model_and_inferred_lines_stay_separate(tmp_path):
    update = parse(tmp_path, "update.xml")
    t = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    url = "https://example.test/"
    current = [
        CurrentRecord("model", "MODEL TEST: rain estimate", url + "m", t, t + timedelta(hours=6)),
        CurrentRecord("inferred", "INFERRED TEST: road wet", url + "i", t),
        CurrentRecord(
            "official", "OFFICIAL TEST: current forecast", url + "o", t, t + timedelta(hours=6)
        ),
        CurrentRecord(
            "official", "OFFICIAL TEST: expired forecast", url + "e", t, t + timedelta(hours=1)
        ),
    ]
    got = build_brief("ka", RUN, DURING, update, current)
    assert [x.provenance for x in got.lines] == ["official", "official", "model", "inferred"]
    assert "expired forecast" not in " ".join(x.text for x in got.lines)
    assert got == build_brief("ka", RUN, DURING, update, list(reversed(current)))  # deterministic
    text = telegram.format_message(got)
    official, model = text.index("OFFICIAL ("), text.index("MODEL ESTIMATES")
    assert official < text.index("OFFICIAL TEST: current") < model < text.index("MODEL TEST")
    assert text.index("INFERRED (not") > text.index("MODEL TEST") and "not official" in text
    for line in got.lines:
        assert f"Source: {line.source_url}" in text  # source links retained


def test_bad_current_records_are_refused():
    t = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    bad = [
        CurrentRecord("rumour", "x", "https://example.test/", t),
        CurrentRecord("model", "x", "http://example.test/", t),
        CurrentRecord("model", "x", "", t),
        CurrentRecord("model", "x", "https://example.test/", datetime(2026, 11, 5, 12, 0)),
    ]
    for record in bad:
        with pytest.raises(ValueError):
            build_brief("ka", RUN, DURING, None, [record])
    with pytest.raises(ValueError):
        build_brief("ka", RUN, datetime(2026, 11, 5, 3, 0), None)  # no timezone


def test_publication_label_is_06_30_only_when_the_job_finished_on_time():
    on_time = build_brief("ka", RUN, START + timedelta(minutes=20), None)
    assert on_time.published_label == "06:30 IST"
    late = build_brief("ka", RUN, datetime(2026, 11, 5, 3, 0, tzinfo=UTC), None)
    assert "2026-11-05 08:30 IST" in late.published_label and "06:30 IST" in late.published_label
    assert "Published 2026-11-05 08:30 IST" in telegram.format_message(late)
    with pytest.raises(ValueError, match="has not completed"):
        build_brief("ka", RUN, START - timedelta(seconds=1), None)  # yesterday's run


def test_message_fits_the_telegram_limit_and_says_how_many_were_cut():
    t = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    many = [
        CurrentRecord("model", f"MODEL TEST {n:03d} " + "x" * 200, "https://example.test/", t)
        for n in range(60)
    ]
    text = telegram.format_message(build_brief("ka", RUN, DURING, None, many))
    assert len(text) <= telegram.MAX_CHARS and re.search(r"\d+ more entries not shown\.", text)
    assert "MODEL TEST 000" in text and "MODEL TEST 059" not in text


def test_sending_is_blocked_before_any_io(monkeypatch):
    import socket

    def no_socket(*args, **kwargs):
        raise AssertionError("a network socket was opened")

    monkeypatch.setattr(socket, "socket", no_socket)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "must-not-be-read")
    with pytest.raises(SourceUnavailable, match="H08"):
        telegram.send_message("brief")


def test_nothing_about_readers_is_stored():
    sources = {
        p.name: p.read_text(encoding="utf-8") for p in (ROOT / "src/atlas/alerts").glob("*.py")
    }
    assert set(sources) == {"__init__.py", "brief.py", "telegram.py"}
    for name, text in sources.items():
        assert not re.search(r"chat_id|subscriber|user_id|username|environ|getenv", text, re.I), (
            name
        )
        assert not re.search(
            r"\bopen\(|write_text|write_bytes|sqlite|duckdb|httpx|urllib|socket", text
        ), name
    assert set(brief_mod.Brief.__dataclass_fields__) == {
        "state",
        "run_date",
        "completed_at",
        "published_label",
        "lines",
    }


def test_watches_stay_in_the_browser():
    web = ROOT / "web/src"
    watches = (web / "components/Watches.tsx").read_text(encoding="utf-8")
    assert "indexedDB.open(" in watches
    banned = r"fetch\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|cookie"
    banned += "|geolocation|new Notification|serviceWorker|pushManager"
    assert not re.search(banned, watches)
    others = [p for p in web.rglob("*.ts*") if p.name not in {"Watches.tsx", "Watches.test.ts"}]
    imports = [p.name for p in others if re.search(r"import .*Watches", p.read_text("utf-8"))]
    assert not imports  # built, not mounted
