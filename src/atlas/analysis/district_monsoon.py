"""District monsoon tracker for Karnataka (D192).

S02 ERA5 reanalysis (Open-Meteo, CC BY 4.0) daily rain at each S17 district point. For the
southwest (1 Jun to 30 Sep) and northeast (1 Oct to 31 Dec) seasons, the current season's rain to
date is compared with the same window in each reference year (2001-2025): percent of the median and
rank. ERA5 is a model reanalysis published about 6 days late, not a rain-gauge count, and one grid
point stands for a whole district, so the page says "reanalysis" and never "observed".

History is fetched once, one year per request for all points, within the free API's daily limit
(about 460 weighted calls a year, so 26 years take two days); `backfill` resumes where it stopped.
Normals derived from it are committed (configs/static/ka/monsoon-normals.json), so the daily job
fetches only the current season.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from atlas.analysis.monsoon import percentile_rank

ROOT = Path(__file__).resolve().parents[3]
PLACES = ROOT / "configs/static/ka/places.json"
NORMALS = ROOT / "configs/static/ka/monsoon-normals.json"
CACHE = ROOT / "data/clean/S02/ka-districts"
REFERENCE = (2001, 2025)
SEASONS = {"southwest": ((6, 1), (9, 30)), "northeast": ((10, 1), (12, 31))}
STEP_DAYS = 7  # checkpoints: every 7th day of the season and its last day
CALLS_PER_YEAR = 480  # 30 points x ~16 two-week blocks (Open-Meteo weights by length)


def points() -> list[dict]:
    rows = json.loads(PLACES.read_text("utf-8"))["rows"]
    return [{"name": r["name"], "lat": r["latitude"], "lon": r["longitude"]} for r in rows]


def season_days(season: str, year: int) -> tuple[date, date]:
    (m1, d1), (m2, d2) = SEASONS[season]
    return date(year, m1, d1), date(year, m2, d2)


def checkpoints(season: str, year: int) -> list[int]:
    """Day offsets (0 = first day) of the weekly checkpoints, plus the season's last day."""
    start, end = season_days(season, year)
    last = (end - start).days
    return sorted({*range(STEP_DAYS - 1, last + 1, STEP_DAYS), last})


def cumulative(daily: dict[str, float | None], start: date, offset: int) -> float | None:
    total = 0.0
    for i in range(offset + 1):
        v = daily.get((start + timedelta(days=i)).isoformat())
        if v is None:
            return None  # a missing day is never filled
        total += v
    return round(total, 1)


def normals(history: dict[int, dict[str, dict[str, float | None]]]) -> dict:
    """{district: {season: {offset: sorted reference values}}} from cached reference years."""
    years = [y for y in range(REFERENCE[0], REFERENCE[1] + 1) if y in history]
    out: dict = {}
    for p in points():
        for season in SEASONS:
            for offset in checkpoints(season, 2001):
                values = []
                for y in years:
                    start, _ = season_days(season, y)
                    v = cumulative(history[y].get(p["name"], {}), start, offset)
                    if v is not None:
                        values.append(v)
                out.setdefault(p["name"], {}).setdefault(season, {})[str(offset)] = sorted(values)
    return {
        "schema_version": 1,
        "source_id": "S02",
        "product": "ERA5 reanalysis via Open-Meteo (CC BY 4.0)",
        "reference": f"{REFERENCE[0]}-{REFERENCE[1]}",
        "reference_years": years,
        "step_days": STEP_DAYS,
        "districts": out,
    }


def band(pct: float) -> str:
    """Plain bands on percent of median; not IMD's official categories."""
    if pct < 60:
        return "far below normal"
    if pct < 80:
        return "below normal"
    if pct <= 120:
        return "near normal"
    if pct <= 160:
        return "above normal"
    return "far above normal"


def tracker(
    current: dict[str, dict[str, float | None]], year: int, today: date, norm: dict
) -> dict:
    """Latest checkpoint of each season this year, per district, against the normals."""
    rows = []
    for p in points():
        daily = current.get(p["name"], {})
        for season in SEASONS:
            start, end = season_days(season, year)
            latest = max(
                (date.fromisoformat(d) for d, v in daily.items() if v is not None), default=None
            )
            if latest is None or latest < start:
                continue
            reached = (min(latest, end) - start).days
            done = [o for o in checkpoints(season, year) if o <= reached]
            if not done:
                continue
            offset = done[-1]
            value = cumulative(daily, start, offset)
            ref = norm["districts"].get(p["name"], {}).get(season, {}).get(str(offset), [])
            row = {
                "district": p["name"],
                "season": season,
                "through": (start + timedelta(days=offset)).isoformat(),
                "complete": offset == (end - start).days,
                "rain_mm": value,
                "reference_years": len(ref),
            }
            if value is not None and ref:
                med = statistics.median(ref)
                pct = round(100 * value / med, 1) if med else None
                row |= {
                    "median_mm": round(med, 1),
                    "pct_of_median": pct,
                    "rank_percentile": round(percentile_rank(value, ref), 1),
                    "band": band(pct) if pct is not None else None,
                }
            rows.append(row)
    return {
        "schema_version": 1,
        "state": "ka",
        "year": year,
        "built_on": today.isoformat(),
        "source_id": "S02",
        "reference": norm["reference"],
        "label": (
            "ERA5 reanalysis (model), about 6 days behind; one grid point per district, "
            "not a gauge total"
        ),
        "rows": rows,
    }


def fetch_years(start: date, end: date):  # pragma: no cover - network
    """S02 daily values for all district points between two dates: {name: {iso_date: rain}}."""
    from atlas.config import load_state
    from atlas.contracts import Budget, FetchContext
    from atlas.ingest.http import Fetcher
    from atlas.ingest.raw_store import RawStore
    from atlas.ingest.s02 import HOSTS, S02

    pts = points()
    raw_root = ROOT / "data/raw"
    now = datetime.now(UTC)
    ctx = FetchContext(
        source_id="S02",
        state="ka",
        run_id=f"monsoon-{now:%Y%m%dT%H%M%S}",
        requested_at=now,
        budget=Budget(max_requests=4, max_bytes=40 * 1024**2),
        raw_root=raw_root,
    )
    adapter = S02(
        "ka",
        [(p["lat"], p["lon"]) for p in pts],
        start,
        end,
        fetcher=Fetcher(RawStore(raw_root), HOSTS),
    )
    [raw] = adapter.fetch(ctx)
    adapter.parse(raw, load_state(ROOT / "configs/states/ka.yaml").source("S02"))  # validates
    body = json.loads(raw.path.read_bytes())
    locations = body if isinstance(body, list) else [body]
    if len(locations) != len(pts):
        raise ValueError(f"expected {len(pts)} locations, got {len(locations)}")
    # Locations come back in request order; two districts may share one ERA5 cell, so map by
    # position, never by cell ID.
    out = {}
    for p, loc in zip(pts, locations, strict=True):
        days = loc["daily"]
        out[p["name"]] = dict(zip(days["time"], days["precipitation_sum"], strict=True))
    return out


def backfill(max_calls: int, pause_s: float = 20.0) -> list[int]:  # pragma: no cover - network
    """Fetch reference years not yet cached, within `max_calls` weighted calls; resumable."""
    CACHE.mkdir(parents=True, exist_ok=True)
    done = []
    for year in range(REFERENCE[0], REFERENCE[1] + 1):
        path = CACHE / f"{year}.json"
        if path.exists():
            continue
        if max_calls < CALLS_PER_YEAR:
            break
        data = fetch_years(date(year, 6, 1), date(year, 12, 31))
        path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        max_calls -= CALLS_PER_YEAR
        done.append(year)
        time.sleep(pause_s)
    return done


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - network
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backfill")
    b.add_argument("--max-calls", type=int, default=4500)
    sub.add_parser("normals")
    c = sub.add_parser("current")
    c.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "backfill":
        years = backfill(args.max_calls)
        have = sorted(int(p.stem) for p in CACHE.glob("*.json"))
        print(json.dumps({"fetched": years, "cached": len(have)}))
    elif args.command == "normals":
        history = {int(p.stem): json.loads(p.read_text("utf-8")) for p in CACHE.glob("*.json")}
        body = normals(history)
        NORMALS.write_text(
            json.dumps(body, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n"
        )
        print(json.dumps({"written": str(NORMALS), "years": len(body["reference_years"])}))
    else:
        today = datetime.now(UTC).date()
        year = today.year
        current = fetch_years(date(year, 6, 1), min(today - timedelta(days=6), date(year, 12, 31)))
        body = tracker(current, year, today, json.loads(NORMALS.read_text("utf-8")))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(body, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n"
        )
        print(json.dumps({"written": str(args.out), "rows": len(body["rows"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
