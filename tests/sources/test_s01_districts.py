"""D206: genuine 30-district S01 capture (Open-Meteo, 13 Nov 2026) through collect and prepare."""

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

import atlas.ingest.s01_collect as collect
from atlas.ingest.s01_prepare import prepare_weather

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests/fixtures"
NOW = datetime(2026, 11, 13, 5, tzinfo=UTC)
FORECAST = "s01_openmeteo_forecast_ecmwf_ifs025_ka_districts_2026-11-13.json"
META = "s01_openmeteo_meta_ecmwf_ifs025_2026-11-13.json"


def capture(root, change=lambda body: body):
    def respond(request):
        meta = request.url.path.endswith("meta.json")
        body = (FIX / (META if meta else FORECAST)).read_bytes()
        return httpx.Response(200, content=body if meta else change(body))

    return collect.collect_weather(
        root, clock=lambda: NOW, sleep=lambda _: None, transport=httpx.MockTransport(respond)
    )


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = (
        math.sin((la2 - la1) / 2) ** 2
        + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


def test_every_district_gets_its_own_cell_within_the_lens_radius(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "PROFILE", "ka-districts-ecmwf_ifs025-v1")
    assert capture(tmp_path)["status"] == "captured"
    result = prepare_weather(tmp_path, as_of=NOW + timedelta(seconds=1))
    records = json.loads(Path(result["payload_path"]).read_bytes())["snapshot"]["records"]
    places = {
        r["name"]: (r["latitude"], r["longitude"])
        for r in json.loads((ROOT / "configs/static/ka/places.json").read_text("utf-8"))["rows"]
    }
    assert len(records) == 30 == len({r["id"] for r in records})
    for record in records:
        name = record["title"].removeprefix("ECMWF IFS temperature — ").removesuffix(" grid cell")
        assert km(places[name], (record["latitude"], record["longitude"])) < 25, name
        assert record["valid_at"] >= "2026-11-13T05:00:00Z" and math.isfinite(record["value"])


def test_a_moved_grid_cell_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "PROFILE", "ka-districts-ecmwf_ifs025-v1")

    def move(body):
        locations = json.loads(body)
        locations[5]["latitude"] += 0.25
        return json.dumps(locations).encode()

    assert capture(tmp_path, move)["status"] == "unavailable"
