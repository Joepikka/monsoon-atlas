"""D192: the district monsoon tracker compares season-to-date ERA5 rain with the same window in
each reference year; a missing day is never filled; the latest completed weekly checkpoint is used;
bands are plain percent-of-median bands, not IMD categories."""

from datetime import date, timedelta

from atlas.analysis.district_monsoon import (
    REFERENCE,
    band,
    checkpoints,
    cumulative,
    normals,
    points,
    season_days,
    tracker,
)

NAMES = [p["name"] for p in points()]


def daily(year: int, mm: float, missing: set[str] = frozenset()) -> dict[str, float | None]:
    out, d = {}, date(year, 6, 1)
    while d <= date(year, 12, 31):
        out[d.isoformat()] = None if d.isoformat() in missing else mm
        d += timedelta(days=1)
    return out


def history() -> dict:
    # each reference year rains 1 + (year - 2001) * 0.1 mm a day everywhere
    return {y: {n: daily(y, 1 + (y - 2001) * 0.1) for n in NAMES} for y in range(2001, 2026)}


def test_checkpoints_are_weekly_and_end_on_the_last_day():
    sw = checkpoints("southwest", 2026)
    assert sw[:3] == [6, 13, 20] and sw[-1] == (date(2026, 9, 30) - date(2026, 6, 1)).days
    assert season_days("northeast", 2026) == (date(2026, 10, 1), date(2026, 12, 31))


def test_missing_day_is_never_filled():
    d = daily(2026, 2.0, missing={"2026-06-03"})
    assert cumulative(d, date(2026, 6, 1), 1) == 4.0
    assert cumulative(d, date(2026, 6, 1), 5) is None


def test_normals_hold_every_reference_year():
    norm = normals(history())
    assert norm["reference_years"] == list(range(REFERENCE[0], REFERENCE[1] + 1))
    values = norm["districts"][NAMES[0]]["southwest"]["6"]
    assert len(values) == 25 and values == sorted(values) and values[0] == 7.0


def test_tracker_uses_the_latest_completed_checkpoint_and_ranks_against_normals():
    norm = normals(history())
    current = {n: daily(2026, 3.6) for n in NAMES}  # heavier than every reference year
    for n in NAMES:  # ERA5 only reaches 10 Oct
        for k in list(current[n]):
            if k > "2026-10-10":
                del current[n][k]
    out = tracker(current, 2026, date(2026, 10, 16), norm)
    rows = {(r["district"], r["season"]): r for r in out["rows"]}
    sw, ne = rows[(NAMES[0], "southwest")], rows[(NAMES[0], "northeast")]
    assert sw["complete"] and sw["through"] == "2026-09-30" and sw["rank_percentile"] == 100.0
    assert ne["through"] == "2026-10-07" and not ne["complete"]  # day 6 is the latest checkpoint
    assert ne["pct_of_median"] > 160 and ne["band"] == "far above normal"
    assert "reanalysis" in out["label"] and "gauge" in out["label"]


def test_bands_are_plain_percent_of_median():
    assert [band(v) for v in (50, 70, 100, 150, 200)] == [
        "far below normal",
        "below normal",
        "near normal",
        "above normal",
        "far above normal",
    ]
