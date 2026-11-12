"""T145: write the derived-statistics climate product (indices only; no mm of area-mean rain).

Run from the repository root: .venv/Scripts/python scripts/climate_product.py
Needs the S08 1981-2025 and S17 raw files (local only). S42 NDVI is blocked (H15): status only.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from m05_release import RAW, s17  # noqa: E402

from atlas.analysis import monsoon, vegetation  # noqa: E402
from atlas.analysis.rain import annual_grid_totals  # noqa: E402
from atlas.analysis.replay import daily_box_mean  # noqa: E402
from atlas.config import load_state  # noqa: E402
from atlas.features.m05 import district_monthly_rain, year_artifacts  # noqa: E402
from atlas.ingest.s08 import S08  # noqa: E402
from atlas.ingest.s17 import S17  # noqa: E402

OUT = ROOT / "reports/eda/08_climate_product/climate.json"
YEARS, TRACKED = range(1981, 2026), 2025
CHECKPOINTS = [
    date(TRACKED, 6, 30),
    date(TRACKED, 7, 31),
    date(TRACKED, 8, 31),
    date(TRACKED, 9, 30),
]


def build() -> dict:
    kl, ka = (load_state(ROOT / f"configs/states/{s}.yaml") for s in ("kl", "ka"))
    raws = year_artifacts(RAW, YEARS)
    daily, annual = {}, {}
    for raw in raws:
        year = int(raw.source_url.rsplit("=", 1)[1])
        means = daily_box_mean(S08("kl", [year]).parse(raw, kl.source("S08")))
        daily[year] = {d: m for d, (m, _) in means.items()}
        full = 366 if year % 4 == 0 else 365
        annual[year] = sum(daily[year].values()) if len(means) == full else None
    districts = S17("ka").parse(s17("e06"), ka.source("S17"), adm1=s17("e05"))
    by_district = defaultdict(dict)
    for (name, year), v in annual_grid_totals(
        district_monthly_rain(raws, districts).to_pylist()
    ).items():
        by_district[name][year] = v
    trends = [monsoon.trend("Kerala cell box (IMD 0.25 deg; not the state boundary)", annual)]
    trends += [
        monsoon.trend(f"{n} (Karnataka district)", by_district[n]) for n in sorted(by_district)
    ]
    with open(ROOT / "reports/eda/07_climate/s06_model_change.csv", encoding="utf-8") as f:
        projection = monsoon.projections(csv.DictReader(f))
    return monsoon.product(
        ndvi=vegetation.layer_status(ROOT / "configs/sources/s42.yaml"),
        tracker=monsoon.tracker(daily, TRACKED, CHECKPOINTS),
        onset=monsoon.official_onset()
        | {"inferred": monsoon.inferred_onset(daily[TRACKED], TRACKED)},
        trend=trends,
        projection=projection,
        source="S08 IMD 0.25 deg gridded rainfall (Kerala box, S17 Karnataka districts); S06 CMIP6",
    )


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), indent=2) + "\n", "utf-8", newline="\n")
    print("wrote", OUT)
