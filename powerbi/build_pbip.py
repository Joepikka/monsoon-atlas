# ruff: noqa: E501  (report copy and generated TMDL lines are long by nature)
"""Generate the Power BI project (powerbi/MonsoonAtlas.pbip) from code (T223, D132).

Same approach as build_pbip.py in kerala-veg-prices: a TMDL semantic model that imports small CSVs
through Power Query, and a PBIR report with ten Karnataka pages (D197, D198). The CSVs in reports/powerbi/data/ are
derived from files already committed (S29 district gauge totals, M05 registry records, and the S32
tables in reports/sql_insights.md). Raw restricted data is never embedded: the S08 grid columns of
the S29 file are dropped, and no blocked source (S22, S23, S28, S43) feeds a table. Blocked pages
carry their reason in a text box instead.

Run:  .venv/Scripts/python powerbi/build_pbip.py   then open powerbi/MonsoonAtlas.pbip in Power BI
Desktop (free). Rerun after moving the repo: the DataFolder parameter holds this checkout's path.
No Power BI Service publishing. PNG and PDF exports need the Desktop GUI and are an owner step (D132).
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import uuid
from pathlib import Path, PureWindowsPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "reports" / "powerbi" / "data"
NAME = "MonsoonAtlas"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
ACCENT, GREY, INK, MUTED = "#1F6F8B", "#8A94A0", "#1B1F24", "#5B6470"
SQL_REPORT = ROOT / "reports" / "sql_insights.md"
S29_CSV = ROOT / "reports" / "eda" / "02_ka_rain" / "district_year_comparison.csv"
M05_DIR = ROOT / "models" / "registry" / "M05"
CLIMATE = ROOT / "reports" / "eda" / "08_climate_product" / "climate.json"
ACCESS = ROOT / "reports" / "eda" / "11_ka_hospital_access"
BUS = ROOT / "reports" / "eda" / "04_bmtc_coverage"
# sql_insights.md question -> (window label, sign of the *_points column relative to end - start)
RESERVOIR_WINDOWS = {
    "Q08": ("1 Aug to 1 Nov 2026", 1),
    "Q09": (
        "1 Dec 2023 to 1 Jun 2024",
        -1,
    ),  # the table gives a loss, so the change is its negative
}

# table -> (csv, source id, [(column, dataType)], [(measure, DAX, format)])
TABLES = {
    "District Rain": (
        "district_rain.csv",
        "S29",
        [("district", "string"), ("year", "int64"), ("gauge_mm", "double")],
        [
            ("Mean Annual Rain", "AVERAGE('District Rain'[gauge_mm])", "#,0"),
            (
                "Rain Variability",
                "DIVIDE(STDEV.P('District Rain'[gauge_mm]), AVERAGE('District Rain'[gauge_mm]))",
                "0.0%",
            ),
            ("Wettest Year", "MAX('District Rain'[gauge_mm])", "#,0"),
            ("Driest Year", "MIN('District Rain'[gauge_mm])", "#,0"),
        ],
    ),
    "Model Error": (
        "model_error.csv",
        "M05",
        [("period", "string"), ("model", "string"), ("mae", "double")],
        [("Mean Absolute Error", "AVERAGE('Model Error'[mae])", "0.000")],
    ),
    "Model Gain": (
        "model_gain.csv",
        "M05",
        [
            ("period", "string"),
            ("district_months", "int64"),
            ("mae_baseline", "double"),
            ("mae_ridge", "double"),
            ("improvement", "double"),
            ("lower95", "double"),
            ("upper95", "double"),
            ("promoted", "string"),
        ],
        [
            ("Mean Gain", "AVERAGE('Model Gain'[improvement])", "0.000"),
            ("Gain Lower 95", "AVERAGE('Model Gain'[lower95])", "0.000"),
            ("Gain Upper 95", "AVERAGE('Model Gain'[upper95])", "0.000"),
            (
                "Gain 2020-2024",
                "CALCULATE(MAX('Model Gain'[improvement]), 'Model Gain'[period] = \"2020-2024 locked test\")",
                "+0.000",
            ),
        ],
    ),
}
TABLES |= {
    "Rain Trend": (
        "rain_trend.csv",
        "S08",
        [
            ("district", "string"),
            ("first_year", "int64"),
            ("last_year", "int64"),
            ("sen_pct_per_decade", "double"),
            ("ols_pct_per_decade", "double"),
            ("mk_p", "double"),
            ("fdr_q", "double"),
            ("lag1_autocorrelation", "double"),
            ("significance", "string"),
        ],
        [
            ("Sen Slope", "AVERAGE('Rain Trend'[sen_pct_per_decade])", "+0.0;-0.0;0.0"),
            (
                "Significant Districts",
                "CALCULATE(COUNTROWS('Rain Trend'), 'Rain Trend'[fdr_q] < 0.05)",
                "0",
            ),
            ("BH q Value", "AVERAGE('Rain Trend'[fdr_q])", "0.000"),
        ],
    ),
    "Hospital Access": (
        "hospital_access.csv",
        "S18",
        [
            ("district", "string"),
            ("people", "int64"),
            ("mean_km", "double"),
            ("median_km", "double"),
            ("p90_km", "double"),
            ("share_beyond_5km", "double"),
            ("share_beyond_10km", "double"),
        ],
        [
            ("Mean km", "AVERAGE('Hospital Access'[mean_km])", "0.0"),
            (
                "People Beyond 10 km",
                "SUMX('Hospital Access', 'Hospital Access'[people] * 'Hospital Access'[share_beyond_10km])",
                "#,0",
            ),
            ("Median Distance", "AVERAGE('Hospital Access'[median_km])", "0.0"),
            ("Share Beyond 5 km", "AVERAGE('Hospital Access'[share_beyond_5km])", "0.0%"),
            ("Share Beyond 10 km", "AVERAGE('Hospital Access'[share_beyond_10km])", "0.0%"),
            ("District People", "SUM('Hospital Access'[people])", "#,0"),
        ],
    ),
    "Bus Access": (
        "bus_access.csv",
        "S30",
        [("band", "string"), ("band_order", "int64"), ("cells", "int64"), ("people", "int64")],
        [("Total People", "SUM('Bus Access'[people])", "#,0")],
    ),
    "Headline": (
        "headline.csv",
        "derived",
        [("order", "int64"), ("metric", "string"), ("value", "string"), ("source", "string")],
        [],
    ),
}
# D198: more views of the same committed results (no new source, no new number)
TABLES |= {
    "Statewide Access": (
        "statewide_access.csv",
        "S18",
        [
            ("hospitals", "int64"),
            ("state_people", "int64"),
            ("state_mean_km", "double"),
            ("state_median_km", "double"),
            ("state_p90_km", "double"),
            ("state_share_5km", "double"),
            ("state_share_10km", "double"),
            ("gini", "double"),
        ],
        [
            ("Hospitals Mapped", "MAX('Statewide Access'[hospitals])", "#,0"),
            ("Statewide Median km", "MAX('Statewide Access'[state_median_km])", "0.0"),
            ("Statewide 90th Percentile km", "MAX('Statewide Access'[state_p90_km])", "0.0"),
            ("Statewide Beyond 10 km", "MAX('Statewide Access'[state_share_10km])", "0.0%"),
            ("Access Gini", "MAX('Statewide Access'[gini])", "0.000"),
        ],
    ),
    "Lorenz": (
        "lorenz.csv",
        "S18",
        [("people_share", "double"), ("distance_share", "double")],
        [
            ("Share of Total Distance", "AVERAGE('Lorenz'[distance_share])", "0%"),
            ("Equal Access Line", "AVERAGE('Lorenz'[people_share])", "0%"),
        ],
    ),
    "Bus Cells": (
        "bus_cells.csv",
        "S30",
        [
            ("cell_id", "string"),
            ("lon", "double"),
            ("lat", "double"),
            ("population", "double"),
            ("covered_population", "double"),
            ("band", "string"),
            ("band_order", "int64"),
        ],
        [
            ("Cell Longitude", "AVERAGE('Bus Cells'[lon])", "0.000"),
            ("Cell Latitude", "AVERAGE('Bus Cells'[lat])", "0.000"),
            ("Cell People", "SUM('Bus Cells'[population])", "#,0"),
            ("People Within Walk", "SUM('Bus Cells'[covered_population])", "#,0"),
            (
                "Bengaluru Covered Share",
                "DIVIDE(SUM('Bus Cells'[covered_population]), SUM('Bus Cells'[population]))",
                "0.0%",
            ),
        ],
    ),
    "Model Scores": (
        "model_scores.csv",
        "M05",
        [("score", "string"), ("model", "string"), ("value", "double")],
        [("Score Value", "AVERAGE('Model Scores'[value])", "0.000")],
    ),
    "Model Gates": (
        "model_gates.csv",
        "M05",
        [
            ("order", "int64"),
            ("check", "string"),
            ("value", "double"),
            ("reference", "double"),
            ("passed", "string"),
        ],
        [],
    ),
    "Calibration": (
        "calibration.csv",
        "M05",
        [
            ("season", "string"),
            ("district_months", "int64"),
            ("observed_drought", "double"),
            ("mean_probability", "double"),
        ],
        [
            ("Observed Drought Rate", "AVERAGE('Calibration'[observed_drought])", "0.0%"),
            ("Forecast Drought Probability", "AVERAGE('Calibration'[mean_probability])", "0.0%"),
        ],
    ),
    "Interval Check": (
        "interval_check.csv",
        "M05",
        [("order", "int64"), ("stage", "string"), ("coverage", "double"), ("result", "string")],
        [
            ("Interval Coverage", "AVERAGE('Interval Check'[coverage])", "0.0%"),
            ("Target Low", "0.75", "0%"),
            ("Target High", "0.85", "0%"),
        ],
    ),
    "Interval Selection": (
        "interval_selection.csv",
        "M05",
        [
            ("window_years", "int64"),
            ("by_season", "string"),
            ("coverage_2010_2019", "double"),
            ("mean_width", "double"),
            ("chosen", "string"),
        ],
        [],
    ),
    "Moran": (
        "moran.csv",
        "M05",
        [
            ("month", "string"),
            ("moran_i", "double"),
            ("p", "double"),
            ("q_bh", "double"),
            ("significant", "string"),
        ],
        [
            ("Moran I", "AVERAGE('Moran'[moran_i])", "0.00"),
            (
                "Significant Months",
                "CALCULATE(COUNTROWS('Moran'), 'Moran'[significant] = \"yes\")",
                "0",
            ),
        ],
    ),
    "Variogram": (
        "variogram.csv",
        "M05",
        [
            ("lo_km", "double"),
            ("hi_km", "double"),
            ("lag_km", "double"),
            ("site_pairs", "int64"),
            ("gamma", "double"),
        ],
        [("Semivariance", "AVERAGE('Variogram'[gamma])", "0.000")],
    ),
    "Gauge Stations": (
        "gauge_stations.csv",
        "S29",
        [("district", "string"), ("stations", "int64"), ("with_value", "int64")],
        [("Gauge Count", "SUM('Gauge Stations'[stations])", "#,0")],
    ),
    "Grid Coverage": (
        "grid_coverage.csv",
        "S08",
        [("year", "int64"), ("month", "int64"), ("share", "double")],
        [("Grid Completeness", "AVERAGE('Grid Coverage'[share])", "0.0%")],
    ),
}
SORT_BY = {
    ("Bus Access", "band"): "band_order",
    ("Bus Cells", "band"): "band_order",
    ("Headline", "metric"): "order",
    ("Model Gates", "check"): "order",
    ("Interval Check", "stage"): "order",
}
M_TYPES = {"string": "type text", "int64": "Int64.Type", "double": "type number"}
FORMATS = {"double": "0.000", "int64": "0"}


# ---------------- data (derived from committed files only) ----------------
def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def sql_table(question: str) -> list[dict[str, str]]:
    """Rows of the markdown table under '## Qnn.' in reports/sql_insights.md."""
    text = SQL_REPORT.read_text("utf-8")
    section = re.search(rf"^## {question}\..*?(?=^## )", text, re.S | re.M).group(0)
    lines = [ln for ln in section.splitlines() if ln.startswith("|")]
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    return [
        dict(zip(head, (c.strip() for c in ln.strip("|").split("|")), strict=True))
        for ln in lines[2:]
    ]


def reservoir_rows() -> list[list]:
    out = []
    for q_id, (window, sign) in RESERVOIR_WINDOWS.items():
        for r in sql_table(q_id):
            pct = [k for k in r if k.startswith("pct_")]
            start, end = float(r[pct[0]]), float(r[pct[1]])
            reported = sign * float(r[next(k for k in r if k.endswith("_points"))])
            assert abs((end - start) - reported) < 0.15, (
                q_id,
                r,
            )  # rounding of the printed percentages
            out.append([window, r["reservoir_name"], start, end, round(end - start, 1)])
    return out


def district_rows() -> list[list]:
    with S29_CSV.open(encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["status"] == "compared"]
    # the grid_mm, bias_mm and ratio columns come from S08 (restricted) and are never copied
    return sorted([r["district"], int(r["year"]), round(float(r["gauge_mm"]), 1)] for r in rows)


MODELS = {
    "persistence": "persistence (baseline)",
    "climatology": "climatology",
    "ridge": "M05 ridge",
    "lightgbm": "LightGBM challenger",  # not promoted: its gain over ridge on tune had a lower bound below 0 (D41)
}


def model_rows() -> tuple[list[list], list[list]]:
    err, gain = [], []
    for period, fname in (
        ("2020-2024 locked test", "v1.evaluation.json"),
        ("2025 hindcast", "v1.monitor-2025.json"),
    ):
        d = json.loads((M05_DIR / fname).read_text("utf-8"))
        base, model, imp = d["mae"]["persistence"], d["mae"]["ridge"], d["improvement"]
        err += [
            [period, label, round(d["mae"][k], 3)] for k, label in MODELS.items() if k in d["mae"]
        ]
        gain.append(
            [
                period,
                d["rows"],
                round(base, 3),
                round(model, 3),
                round(imp["mean"], 3),
                round(imp["lower95"], 3),
                round(imp["upper95"], 3),
                "yes" if imp["lower95"] > 0 else "no",
            ]
        )
    return err, gain


def trend_rows() -> list[list]:
    """30 Karnataka district trends from the climate product (indices and tests, no S08 mm)."""
    rows = json.loads(CLIMATE.read_text("utf-8"))["trend"]
    out = []
    for r in rows:
        if "(Karnataka district)" not in r["area"]:
            continue
        out.append(
            [
                r["area"].replace(" (Karnataka district)", ""),
                r["first_year"],
                r["last_year"],
                r["sen_slope_pct_per_decade"],
                r["slope_pct_per_decade"],
                r["mann_kendall_p"],
                r["fdr_q"],
                r["lag1_autocorrelation"],
                r["significance"],
            ]
        )
    return sorted(out)


def access_rows() -> list[list]:
    with (ACCESS / "district_access.csv").open(encoding="utf-8", newline="") as f:
        return [
            [
                r["district"],
                int(r["people"]),
                float(r["mean_km"]),
                float(r["median_km"]),
                float(r["p90_km"]),
                float(r["share_beyond_5km"]),
                float(r["share_beyond_10km"]),
            ]
            for r in csv.DictReader(f)
        ]


BUS_BANDS = [(0.25, "under 25%"), (0.5, "25 to 50%"), (0.75, "50 to 75%"), (1.01, "75% or more")]


def bus_cell_rows() -> list[list]:
    """Populated 1 km cells: lon, lat, people and people within the walk, the D191 web fields."""
    out = []
    with (BUS / "cell_coverage.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            pop, covered = float(r["population"]), float(r["covered_population"])
            if pop <= 0:
                continue
            i = next(i for i, (top, _) in enumerate(BUS_BANDS) if covered / pop < top)
            out.append(
                [r["cell_id"], float(r["lon"]), float(r["lat"]), pop, covered, BUS_BANDS[i][1], i]
            )
    return out


def bus_rows() -> list[list]:
    """People and cells per bus-access band (derived shares only, no S30 timetable, D191)."""
    counts = [[0, 0.0] for _ in BUS_BANDS]
    for *_, pop, _, _, i in bus_cell_rows():
        counts[i][0] += 1
        counts[i][1] += pop
    return [[label, i, counts[i][0], round(counts[i][1])] for i, (_, label) in enumerate(BUS_BANDS)]


def statewide_rows() -> list[list]:
    s = json.loads((ACCESS / "summary.json").read_text("utf-8"))
    w = s["statewide"]
    keys = ("people", "mean_km", "median_km", "p90_km", "share_beyond_5km", "share_beyond_10km")
    return [[s["hospitals"], *(w[k] for k in keys), w["gini"]]]


def lorenz_rows() -> list[list]:
    return [list(p) for p in json.loads((ACCESS / "summary.json").read_text("utf-8"))["lorenz"]]


def registry(fname: str) -> dict:
    return json.loads((M05_DIR / fname).read_text("utf-8"))


def score_rows() -> list[list]:
    d = registry("v1.evaluation.json")
    return [
        [score, MODELS[k], round(d[key][k], 4)]
        for score, key in (("Brier score", "brier"), ("CRPS", "crps"))
        for k in ("persistence", "ridge")
    ]


def gate_rows() -> list[list]:
    d = registry("v1.evaluation.json")
    g, imp = d["gates"], d["improvement"]
    rows = [
        ("MAE ratio to persistence (below 1)", d["mae_ratio"], 1.0, g["mae"]),
        (
            "PR-AUC above drought prevalence",
            d["pr_auc"],
            d["drought_prevalence"],
            g["pr_auc_above_prevalence"],
        ),
        ("Brier skill above 0", d["brier_skill"], 0.0, g["brier_skill_above_0"]),
        (
            "CRPS below persistence",
            d["crps"]["ridge"],
            d["crps"]["persistence"],
            g["crps_below_baseline"],
        ),
        ("Lower 95% bound of the MAE gain above 0", imp["lower95"], 0.0, imp["lower95"] > 0),
    ]
    return [
        [i, name, round(v, 4), round(ref, 4), "yes" if ok else "no"]
        for i, (name, v, ref, ok) in enumerate(rows, 1)
    ]


def calibration_rows() -> list[list]:
    cal = registry("v1.evaluation.json")["calibration_by_season"]
    return [
        [season, c["rows"], round(c["observed_drought"], 4), round(c["mean_probability"], 4)]
        for season, c in cal.items()
    ]


def interval_rows() -> tuple[list[list], list[list]]:
    """80% interval coverage at each look (gate 75-85%), and the D97 rule search on 2010-2019."""
    ev, iv, mon = (
        registry(f) for f in ("v1.evaluation.json", "v1.intervals.json", "v1.monitor-2025.json")
    )
    lo, hi = iv["gate"]
    looks = [
        ("v1 intervals, 2020-2024 (first look)", ev["interval80_coverage"]),
        ("D97 rule, 2020-2024 (second look)", iv["test"]["coverage"]),
        ("Persistence, same rule, 2020-2024", iv["test"]["persistence_same_rule"]["coverage"]),
        ("D97 rule, 2025 hindcast", mon["interval80"]["coverage"]),
    ]
    check = [
        [i, stage, round(c, 4), "inside 75-85%" if lo <= c <= hi else "outside 75-85%"]
        for i, (stage, c) in enumerate(looks, 1)
    ]
    rule = iv["rule"]
    selection = [
        [
            s["window_years"],
            "yes" if s["seasonal"] else "no",
            round(s["coverage"], 4),
            round(s["width"], 3),
            "yes"
            if (s["window_years"], s["seasonal"]) == (rule["window_years"], rule["seasonal"])
            else "",
        ]
        for s in iv["selection"]
    ]
    return check, selection


SPATIAL = ROOT / "reports" / "eda" / "10_spatial_statistics"


def moran_rows() -> list[list]:
    with (SPATIAL / "moran_by_month.csv").open(encoding="utf-8", newline="") as f:
        return [
            [
                r["month"],
                round(float(r["moran_i"]), 4),
                float(r["p"]),
                round(float(r["q_bh"]), 4),
                "yes" if r["significant_q05"] == "True" else "no",
            ]
            for r in csv.DictReader(f)
        ]


def variogram_rows() -> list[list]:
    with (SPATIAL / "variogram_training.csv").open(encoding="utf-8", newline="") as f:
        return [
            [
                float(r["lo_km"]),
                float(r["hi_km"]),
                round(float(r["mean_km"]), 1),
                int(r["site_pairs"]),
                round(float(r["gamma"]), 4),
            ]
            for r in csv.DictReader(f)
        ]


def station_rows() -> list[list]:
    with (ROOT / "reports/eda/02_ka_rain/station_coverage_2023.csv").open(
        encoding="utf-8", newline=""
    ) as f:
        return [
            [r["district"], int(r["stations"]), int(r["with_value"])] for r in csv.DictReader(f)
        ]


def grid_coverage_rows() -> list[list]:
    """S08 completeness (cell-days present / expected); counts only, no rain value."""
    with (ROOT / "reports/eda/01_ka_quality/s08_coverage.csv").open(
        encoding="utf-8", newline=""
    ) as f:
        return [
            [int(r["year"]), int(r["month"]), round(float(r["share"]), 4)]
            for r in csv.DictReader(f)
        ]


def headline_rows() -> list[list]:
    access = json.loads((ACCESS / "summary.json").read_text("utf-8"))["statewide"]
    bus = json.loads((BUS / "summary.json").read_text("utf-8"))["population"]
    trends = trend_rows()
    sig = sum(1 for t in trends if t[6] < 0.05)
    return [
        [
            1,
            "Median distance to a hospital (Karnataka)",
            f"{access['median_km']:.1f} km",
            "S16, S18",
        ],
        [
            2,
            "People more than 10 km from a hospital",
            f"{access['share_beyond_10km'] * 100:.1f}%",
            "S16, S18",
        ],
        [
            3,
            "Bengaluru people within a 500 m walk of a served bus stop",
            f"{bus['covered_share'] * 100:.1f}%",
            "S16, S18, S30",
        ],
        [
            4,
            "Districts with a significant rain rise since 1981",
            f"{sig} of {len(trends)}",
            "S08 (indices only)",
        ],
    ]


def write_data(data_dir: Path = DATA) -> None:
    err, gain = model_rows()
    check, selection = interval_rows()
    rows = {
        "Statewide Access": statewide_rows(),
        "Lorenz": lorenz_rows(),
        "Bus Cells": bus_cell_rows(),
        "Model Scores": score_rows(),
        "Model Gates": gate_rows(),
        "Calibration": calibration_rows(),
        "Interval Check": check,
        "Interval Selection": selection,
        "Moran": moran_rows(),
        "Variogram": variogram_rows(),
        "Gauge Stations": station_rows(),
        "Grid Coverage": grid_coverage_rows(),
        "Rain Trend": trend_rows(),
        "Hospital Access": access_rows(),
        "Bus Access": bus_rows(),
        "Headline": headline_rows(),
        "District Rain": district_rows(),
        "Model Error": err,
        "Model Gain": gain,
    }
    for table, data in rows.items():
        csv_name, _, cols, _ = TABLES[table]
        write_csv(data_dir / csv_name, [c for c, _ in cols], data)


# ---------------- semantic model ----------------
def tag(*parts: str) -> str:
    """Stable lineage tags, so regenerating produces no spurious diffs."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "monsoon-atlas/" + "/".join(parts)))


def write_json(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def q(name: str) -> str:
    return f"'{name}'" if " " in name else name


def import_table(name, csv_name, cols, measures) -> str:
    out = [f"table {q(name)}", f"\tlineageTag: {tag(name)}", ""]
    for m, dax, fmt in measures:
        out += [
            f"\tmeasure {q(m)} = {dax}",
            f"\t\tformatString: {fmt}",
            f"\t\tlineageTag: {tag(name, m)}",
            "",
        ]
    for c, t in cols:
        out += [f"\tcolumn {c}", f"\t\tdataType: {t}"]
        if (name, c) in SORT_BY:
            out.append(f"\t\tsortByColumn: {SORT_BY[name, c]}")
        if t in FORMATS:
            out.append(f"\t\tformatString: {FORMATS[t]}")
        out += [
            f"\t\tlineageTag: {tag(name, c)}",
            "\t\tsummarizeBy: none",
            f"\t\tsourceColumn: {c}",
            "",
        ]
    types = ", ".join(f'{{"{c}", {M_TYPES[t]}}}' for c, t in cols)
    out += [
        f"\tpartition {q(name)} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        f'\t\t\t\t    Source = Csv.Document(File.Contents(DataFolder & "{csv_name}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "\t\t\t\t    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f'\t\t\t\t    Typed = Table.TransformColumnTypes(Promoted, {{{types}}}, "en-US")',
        "\t\t\t\tin",
        "\t\t\t\t    Typed",
        "",
    ]
    return "\n".join(out)


def platform(kind: str) -> dict:
    return {
        "$schema": f"{SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": kind, "displayName": NAME},
        "config": {"version": "2.0", "logicalId": tag(kind.lower())},
    }


def build_model(model: Path, data_folder: str) -> None:
    d = model / "definition"
    write_json(model / ".platform", platform("SemanticModel"))
    write_json(
        model / "definition.pbism",
        {
            "$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {},
        },
    )
    write(d / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    write(
        d / "model.tmdl",
        "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tsourceQueryCulture: en-US\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        + "".join(f"ref table {q(n)}\n" for n in TABLES),
    )
    write(
        d / "expressions.tmdl",
        f'expression DataFolder = "{data_folder}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
        f"\tlineageTag: {tag('DataFolder')}\n",
    )
    for name, (csv_name, _, cols, measures) in TABLES.items():
        write(d / "tables" / f"{name}.tmdl", import_table(name, csv_name, cols, measures))


# ---------------- report ----------------
def lit(v: str) -> dict:
    return {"expr": {"Literal": {"Value": v}}}


def proj(entity, prop, measure=False, label=None) -> dict:
    kind = "Measure" if measure else "Column"
    p = {
        "field": {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }
    if label:
        p["displayName"] = label
    return p


def M(entity, prop, label=None):
    return proj(entity, prop, True, label)


def C(entity, prop, label=None):
    return proj(entity, prop, False, label)


def visual(name, vtype, x, y, w, h, roles=None, title=None, objects=None, sort=None, labels=False):
    """sort: (projection, "Ascending" | "Descending"); labels: show data labels."""
    v = {"visualType": vtype, "drillFilterOtherVisuals": True}
    if roles:
        v["query"] = {"queryState": {role: {"projections": items} for role, items in roles.items()}}
        if sort:
            v["query"]["sortDefinition"] = {
                "sort": [{"field": sort[0]["field"], "direction": sort[1]}],
                "isDefaultSort": True,
            }
    if labels:
        objects = (objects or {}) | {"labels": [{"properties": {"show": lit("true")}}]}
    if objects:
        v["objects"] = objects
    if title:
        v["visualContainerObjects"] = {
            "title": [
                {
                    "properties": {
                        "show": lit("true"),
                        "text": lit(f"'{title}'"),
                        "fontSize": lit("12D"),
                    }
                }
            ]
        }
    return name, {
        "$schema": f"{SCHEMA}/item/report/definition/visualContainer/2.1.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0},
        "visual": v,
    }


def textbox(name, x, y, w, h, text, size="11pt", bold=False, color=INK):
    style = {"fontSize": size, "fontWeight": "bold" if bold else "normal", "color": color}
    paragraphs = [{"textRuns": [{"value": text, "textStyle": style}]}]
    return visual(
        name,
        "textbox",
        x,
        y,
        w,
        h,
        objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
    )


def heading(title, sub):
    return [
        textbox("title", 24, 12, 1230, 52, title, "20pt", True),
        textbox("subtitle", 24, 58, 1230, 40, sub, "11pt", False, MUTED),
    ]


def card(name, x, y, w, h, entity, measure, label):
    """One KPI tile; the label is the tile's caption."""
    return visual(name, "card", x, y, w, h, {"Values": [M(entity, measure, label)]})


def cards(prefix, y, items, x=24, w=1232, h=104, gap=16):
    """A row of equal KPI tiles: items are (entity, measure, label)."""
    size = (w - gap * (len(items) - 1)) / len(items)
    return [
        card(f"{prefix}{i}", round(x + i * (size + gap)), y, round(size), h, *item)
        for i, item in enumerate(items)
    ]


def note(name, x, y, w, h, text):
    return textbox(name, x, y, w, h, text, "10pt", False, MUTED)


def slicer(name, x, y, w, h, entity, column, title):
    return visual(
        name,
        "slicer",
        x,
        y,
        w,
        h,
        {"Values": [C(entity, column)]},
        title,
        objects={"header": [{"properties": {"show": lit("false")}}]},
    )


# Blocked notes: key -> (blocking source ids, reason). Tests check each id is blocked in configs/sources.
BLOCKED = {
    "KWRIS daily reservoir levels (S28)": (
        "S28",
        "blocked (D105): no daily reservoir history, so no trend after rain. The S32 dam reports above are sampled about every 15 days.",
    ),
    "Flood labels (S43) and ward-level rain": (
        "S43",
        "blocked (D105, D131): no licensed flood incident labels are held, so no ward flood exposure is shown. No ward-level rain is committed.",
    ),
    "Market prices (S22, S23)": (
        "S22 S23",
        "blocked (D120, D126): S22 and S23 hold zero price rows, so there is nothing to chart. Not zero, not estimated.",
    ),
    "Models M07 and M06": (
        "S28 S22 S23",
        "M07 (dam level) and M06 (price spike) have no model, so no accuracy is shown (docs/releases/ka.md).",
    ),
}


def blocked_card(name, x, y, w, h, key):
    return textbox(name, x, y, w, h, f"Blocked: {key}. {BLOCKED[key][1]}", "12pt", False, "#8A2B2B")


LIMITS = {
    "hospital": json.loads((ACCESS / "summary.json").read_text("utf-8"))["limits"],
    "bus": json.loads((BUS / "summary.json").read_text("utf-8"))["limits"],
}
PAGES = [
    (
        "overview",
        "Overview",
        [
            *heading(
                "Karnataka, measured: open data, tested methods, stated limits",
                "Monsoon Atlas, a Rs 0 open-data project. Every figure comes from committed, licensed data; "
                "blocked sources are shown as blocked, never as zero. Use the tabs below for each analysis.",
            ),
            *cards(
                "kpi",
                108,
                [
                    ("Statewide Access", "Statewide Median km", "Median km to a hospital"),
                    ("Statewide Access", "Statewide Beyond 10 km", "People over 10 km away"),
                    ("Bus Cells", "Bengaluru Covered Share", "Bengaluru within 500 m of a bus"),
                    ("Rain Trend", "Significant Districts", "Districts with a rain rise"),
                    ("Model Gain", "Gain 2020-2024", "Drought model gain, SPI"),
                    ("Statewide Access", "Hospitals Mapped", "Hospitals mapped (OSM)"),
                ],
            ),
            visual(
                "headline",
                "tableEx",
                24,
                224,
                600,
                196,
                {
                    "Values": [
                        C("Headline", "metric", "Measure"),
                        C("Headline", "value", "Value"),
                        C("Headline", "source", "Sources"),
                    ]
                },
                "Headline results",
                sort=(C("Headline", "order"), "Ascending"),
            ),
            visual(
                "mae",
                "clusteredColumnChart",
                640,
                224,
                616,
                196,
                {
                    "Category": [C("Model Error", "period")],
                    "Series": [C("Model Error", "model")],
                    "Y": [M("Model Error", "Mean Absolute Error")],
                },
                "Drought outlook error against baselines (lower is better)",
                labels=True,
            ),
            visual(
                "lorenz",
                "lineChart",
                24,
                436,
                600,
                176,
                {
                    "Category": [C("Lorenz", "people_share", "Share of people, closest first")],
                    "Y": [M("Lorenz", "Share of Total Distance"), M("Lorenz", "Equal Access Line")],
                },
                "Hospital distance inequality (Lorenz curve)",
                sort=(C("Lorenz", "people_share"), "Ascending"),
            ),
            visual(
                "bands",
                "clusteredColumnChart",
                640,
                436,
                616,
                176,
                {"Category": [C("Bus Access", "band")], "Y": [M("Bus Access", "Total People")]},
                "Bengaluru people by share of their cell within a 500 m walk",
                sort=(C("Bus Access", "band"), "Ascending"),
                labels=True,
            ),
            note(
                "method",
                24,
                624,
                1232,
                84,
                "Methods: exact great-circle nearest-site search and a people-weighted Gini (hospitals); network "
                "walking catchments (buses); Mann-Kendall, Sen slope and Benjamini-Hochberg (rain trends); ridge "
                "regression against persistence, climatology and a LightGBM challenger, with a paired block "
                "bootstrap (drought model); Moran's I and a variogram (spatial errors). Notebooks 02, 04, 08, 10, 11.",
            ),
        ],
    ),
    (
        "trends",
        "Rain trends",
        [
            *heading(
                "Annual rain rose in 9 of 30 districts since 1981, after correcting for 30 tests",
                "IMD gridded rain (S08) as % of the 1981-2010 mean, never mm. Sen slope per decade; Mann-Kendall p; "
                "Benjamini-Hochberg q across the 30 districts. Autocorrelated series are flagged as weaker.",
            ),
            slicer("sig", 24, 108, 200, 140, "Rain Trend", "significance", "Significance"),
            card(
                "sigcount",
                24,
                260,
                200,
                100,
                "Rain Trend",
                "Significant Districts",
                "Significant districts",
            ),
            card(
                "meanslope",
                24,
                372,
                200,
                100,
                "Rain Trend",
                "Sen Slope",
                "Mean Sen slope, %/decade",
            ),
            visual(
                "slope",
                "clusteredBarChart",
                240,
                108,
                620,
                380,
                {"Category": [C("Rain Trend", "district")], "Y": [M("Rain Trend", "Sen Slope")]},
                "Sen slope, % of the 1981-2010 mean per decade",
                labels=True,
            ),
            visual(
                "evidence",
                "scatterChart",
                876,
                108,
                380,
                380,
                {
                    "Category": [C("Rain Trend", "district")],
                    "Series": [C("Rain Trend", "significance")],
                    "X": [M("Rain Trend", "Sen Slope")],
                    "Y": [M("Rain Trend", "BH q Value")],
                },
                "Effect size against evidence (q below 0.05 is significant)",
            ),
            visual(
                "tests",
                "tableEx",
                24,
                500,
                1232,
                208,
                {
                    "Values": [
                        C("Rain Trend", "district", "District"),
                        C("Rain Trend", "first_year", "From"),
                        C("Rain Trend", "last_year", "To"),
                        C("Rain Trend", "sen_pct_per_decade", "Sen, %/decade"),
                        C("Rain Trend", "ols_pct_per_decade", "OLS, %/decade"),
                        C("Rain Trend", "mk_p", "Mann-Kendall p"),
                        C("Rain Trend", "fdr_q", "BH q"),
                        C("Rain Trend", "lag1_autocorrelation", "Lag-1 r"),
                        C("Rain Trend", "significance", "Result"),
                    ]
                },
                "Tests per district",
            ),
        ],
    ),
    (
        "rain",
        "Gauge rain",
        [
            *heading(
                "Karnataka gauge rain by district",
                "KSNDMC rain-gauge annual district totals (S29, public domain), 29 districts, the four years with "
                "like-for-like coverage (2020, 2021, 2022, 2024). Gauge totals only.",
            ),
            slicer("year", 24, 108, 180, 150, "District Rain", "year", "Year"),
            card(
                "meanrain",
                24,
                270,
                180,
                100,
                "District Rain",
                "Mean Annual Rain",
                "Mean annual rain, mm",
            ),
            card(
                "cv",
                24,
                382,
                180,
                100,
                "District Rain",
                "Rain Variability",
                "Year-to-year variation",
            ),
            visual(
                "rain",
                "clusteredBarChart",
                220,
                108,
                520,
                380,
                {
                    "Category": [C("District Rain", "district")],
                    "Y": [M("District Rain", "Mean Annual Rain")],
                },
                "Mean annual rain at the gauges, mm",
                labels=True,
            ),
            visual(
                "variability",
                "clusteredBarChart",
                756,
                108,
                500,
                380,
                {
                    "Category": [C("District Rain", "district")],
                    "Y": [M("District Rain", "Rain Variability")],
                },
                "Year-to-year variation (coefficient of variation)",
                labels=True,
            ),
            visual(
                "matrix",
                "pivotTable",
                24,
                500,
                1232,
                208,
                {
                    "Rows": [C("District Rain", "district", "District")],
                    "Columns": [C("District Rain", "year", "Year")],
                    "Values": [M("District Rain", "Mean Annual Rain", "Gauge rain, mm")],
                },
                "Gauge rain, mm, by district and year",
            ),
        ],
    ),
    (
        "hospitals",
        "Hospital access",
        [
            *heading(
                "How far people live from the nearest hospital",
                "WorldPop 2025 1 km cells (S16) to OpenStreetMap hospitals (S18), straight-line km, people-weighted. "
                "OSM is thinner in rural areas, so remote distances are upper bounds.",
            ),
            *cards(
                "kpi",
                108,
                [
                    ("Statewide Access", "Hospitals Mapped", "Hospitals mapped"),
                    ("Statewide Access", "Statewide Median km", "Median km"),
                    ("Statewide Access", "Statewide 90th Percentile km", "90th percentile km"),
                    ("Statewide Access", "Statewide Beyond 10 km", "People over 10 km away"),
                    ("Statewide Access", "Access Gini", "Gini of distance"),
                ],
                h=96,
            ),
            visual(
                "beyond",
                "clusteredBarChart",
                24,
                220,
                400,
                488,
                {
                    "Category": [C("Hospital Access", "district")],
                    "Y": [M("Hospital Access", "Mean km")],
                },
                "People-weighted mean km to the nearest hospital",
                labels=True,
            ),
            visual(
                "spread",
                "scatterChart",
                440,
                220,
                420,
                236,
                {
                    "Category": [C("Hospital Access", "district")],
                    "X": [M("Hospital Access", "Mean km")],
                    "Y": [M("Hospital Access", "Share Beyond 10 km")],
                    "Size": [M("Hospital Access", "District People")],
                },
                "Mean km against share over 10 km (size: people)",
            ),
            visual(
                "lorenz",
                "lineChart",
                440,
                472,
                420,
                236,
                {
                    "Category": [C("Lorenz", "people_share", "Share of people, closest first")],
                    "Y": [M("Lorenz", "Share of Total Distance"), M("Lorenz", "Equal Access Line")],
                },
                "Lorenz curve of distance",
                sort=(C("Lorenz", "people_share"), "Ascending"),
            ),
            visual(
                "access",
                "tableEx",
                876,
                220,
                380,
                488,
                {
                    "Values": [
                        C("Hospital Access", "district", "District"),
                        C("Hospital Access", "median_km", "Median km"),
                        C("Hospital Access", "p90_km", "90th pct km"),
                        C("Hospital Access", "share_beyond_5km", "Over 5 km"),
                        C("Hospital Access", "share_beyond_10km", "Over 10 km"),
                    ]
                },
                "Distances per district",
            ),
        ],
    ),
    (
        "bus",
        "Bus access",
        [
            *heading(
                "Bengaluru: 65.3% of people live within a 500 m walk of a served bus stop",
                "Bangalore district, BMTC weekday service of 9 Sep 2026 (unofficial GTFS, S30), walking along OSM "
                "paths, WorldPop people. Derived shares only: no stops, routes or times (D191).",
            ),
            *cards(
                "kpi",
                108,
                [
                    ("Bus Cells", "Bengaluru Covered Share", "Within a 500 m walk"),
                    ("Bus Cells", "People Within Walk", "People within the walk"),
                    ("Bus Cells", "Cell People", "People in the district"),
                ],
                h=96,
            ),
            visual(
                "cellmap",
                "scatterChart",
                24,
                220,
                700,
                488,
                {
                    "Category": [C("Bus Cells", "cell_id")],
                    "Series": [C("Bus Cells", "band", "Share within the walk")],
                    "X": [M("Bus Cells", "Cell Longitude")],
                    "Y": [M("Bus Cells", "Cell Latitude")],
                    "Size": [M("Bus Cells", "Cell People")],
                },
                "Each dot is a 1 km cell (west to east, south to north), sized by people",
            ),
            visual(
                "bands",
                "clusteredColumnChart",
                740,
                220,
                516,
                264,
                {"Category": [C("Bus Access", "band")], "Y": [M("Bus Access", "Total People")]},
                "People by share of their 1 km cell within the walk",
                sort=(C("Bus Access", "band"), "Ascending"),
                labels=True,
            ),
            visual(
                "bandtable",
                "tableEx",
                740,
                496,
                516,
                212,
                {
                    "Values": [
                        C("Bus Access", "band", "Band"),
                        C("Bus Access", "cells", "1 km cells"),
                        C("Bus Access", "people", "People"),
                    ]
                },
                "Bands",
                sort=(C("Bus Access", "band"), "Ascending"),
            ),
        ],
    ),
    (
        "accuracy",
        "Model accuracy",
        [
            *heading(
                "M05 drought outlook beats persistence, and the gain is clearly above zero",
                "District SPI-3 forecast against the strongest simple baseline, climatology and a LightGBM challenger. "
                "Hindcast, because IMD publishes the grid yearly (D39). Promoted only if every gate passes.",
            ),
            visual(
                "mae",
                "clusteredColumnChart",
                24,
                108,
                620,
                300,
                {
                    "Category": [C("Model Error", "period")],
                    "Series": [C("Model Error", "model")],
                    "Y": [M("Model Error", "Mean Absolute Error")],
                },
                "Mean absolute error, SPI units (lower is better)",
                labels=True,
            ),
            visual(
                "gain",
                "clusteredColumnChart",
                660,
                108,
                596,
                300,
                {
                    "Category": [C("Model Gain", "period")],
                    "Y": [
                        M("Model Gain", "Gain Lower 95", "Lower 95%"),
                        M("Model Gain", "Mean Gain", "Mean gain"),
                        M("Model Gain", "Gain Upper 95", "Upper 95%"),
                    ],
                },
                "MAE gain over persistence with its 95% paired block bootstrap interval",
                labels=True,
            ),
            visual(
                "gates",
                "tableEx",
                24,
                420,
                620,
                288,
                {
                    "Values": [
                        C("Model Gates", "check", "Gate"),
                        C("Model Gates", "value", "M05"),
                        C("Model Gates", "reference", "Reference"),
                        C("Model Gates", "passed", "Passed"),
                    ]
                },
                "Promotion gates, 2020-2024 locked test (all must pass)",
                sort=(C("Model Gates", "check"), "Ascending"),
            ),
            visual(
                "scores",
                "clusteredColumnChart",
                660,
                420,
                596,
                288,
                {
                    "Category": [C("Model Scores", "score")],
                    "Series": [C("Model Scores", "model")],
                    "Y": [M("Model Scores", "Score Value")],
                },
                "Probability scores, 2020-2024 (lower is better)",
                labels=True,
            ),
        ],
    ),
    (
        "reliability",
        "Forecast reliability",
        [
            *heading(
                "Are the drought probabilities and ranges trustworthy?",
                "Calibration by season and 80% interval coverage. A range is shown only if its coverage falls "
                "inside 75-85%. It has not at any look, so the site shows no range (D97, D98).",
            ),
            visual(
                "calibration",
                "clusteredColumnChart",
                24,
                108,
                600,
                290,
                {
                    "Category": [C("Calibration", "season")],
                    "Y": [
                        M("Calibration", "Observed Drought Rate", "Observed"),
                        M("Calibration", "Forecast Drought Probability", "Forecast"),
                    ],
                },
                "Drought rate: observed against mean forecast probability, 2020-2024",
                labels=True,
            ),
            visual(
                "coverage",
                "clusteredBarChart",
                640,
                108,
                616,
                290,
                {
                    "Category": [C("Interval Check", "stage")],
                    "Y": [M("Interval Check", "Interval Coverage")],
                },
                "80% interval coverage at each look (target 75% to 85%)",
                sort=(C("Interval Check", "stage"), "Ascending"),
                labels=True,
            ),
            visual(
                "selection",
                "tableEx",
                24,
                410,
                600,
                298,
                {
                    "Values": [
                        C("Interval Selection", "window_years", "Window, years"),
                        C("Interval Selection", "by_season", "By season"),
                        C("Interval Selection", "coverage_2010_2019", "Coverage 2010-2019"),
                        C("Interval Selection", "mean_width", "Mean width, SPI"),
                        C("Interval Selection", "chosen", "Chosen"),
                    ]
                },
                "Interval rule chosen on 2010-2019 only, before any test year",
            ),
            visual(
                "looks",
                "tableEx",
                640,
                410,
                616,
                298,
                {
                    "Values": [
                        C("Interval Check", "stage", "Look"),
                        C("Interval Check", "coverage", "Coverage"),
                        C("Interval Check", "result", "Result"),
                    ]
                },
                "Every look at the test years, in order",
                sort=(C("Interval Check", "stage"), "Ascending"),
            ),
        ],
    ),
    (
        "spatial",
        "Spatial errors",
        [
            *heading(
                "Forecast errors cluster in space: neighbouring districts miss together",
                "Moran's I of M05 residuals per issue month, queen weights over 30 districts, 999 permutations, "
                "Benjamini-Hochberg across 60 months. Variogram of training residuals by distance between sites.",
            ),
            *cards(
                "kpi",
                108,
                [
                    ("Moran", "Significant Months", "Months with significant clustering, of 60"),
                    ("Moran", "Moran I", "Mean Moran's I (0 = none)"),
                ],
                h=96,
            ),
            visual(
                "moran",
                "lineChart",
                24,
                220,
                820,
                488,
                {"Category": [C("Moran", "month", "Issue month")], "Y": [M("Moran", "Moran I")]},
                "Moran's I of residuals by issue month, 2020-2024",
                sort=(C("Moran", "month"), "Ascending"),
            ),
            visual(
                "variogram",
                "lineChart",
                860,
                220,
                396,
                488,
                {
                    "Category": [C("Variogram", "lag_km", "Distance between sites, km")],
                    "Y": [M("Variogram", "Semivariance")],
                },
                "Semivariance of training residuals by distance",
                sort=(C("Variogram", "lag_km"), "Ascending"),
            ),
        ],
    ),
    (
        "quality",
        "Data quality",
        [
            *heading(
                "How complete the inputs are",
                "Counts of what is present against what is expected. No rain value is shown here.",
            ),
            *cards(
                "kpi",
                108,
                [
                    ("Grid Coverage", "Grid Completeness", "IMD grid cell-days present, 1981-2025"),
                    ("Gauge Stations", "Gauge Count", "KSNDMC rain gauges, 2023"),
                ],
                h=96,
            ),
            visual(
                "stations",
                "clusteredColumnChart",
                24,
                220,
                1232,
                400,
                {
                    "Category": [C("Gauge Stations", "district")],
                    "Y": [M("Gauge Stations", "Gauge Count")],
                },
                "Rain gauges per district, 2023 (S29)",
                labels=True,
            ),
            note(
                "qualitynote",
                24,
                632,
                1232,
                76,
                "The IMD 0.25 degree grid (S08) has every expected cell-day for Karnataka from 1981 to 2025. Gauge "
                "totals come from the KSNDMC network; a district total is compared only in years when its gauges "
                "report like for like. Notebook 01 holds the full checks.",
            ),
        ],
    ),
    (
        "limits",
        "Data limits",
        [
            *heading(
                "What this report cannot show, and why",
                "Blocked sources are listed with their reason; none feeds a table here.",
            ),
            blocked_card("prices", 24, 108, 1232, 80, "Market prices (S22, S23)"),
            blocked_card("flood", 24, 196, 1232, 80, "Flood labels (S43) and ward-level rain"),
            blocked_card("models", 24, 284, 1232, 80, "Models M07 and M06"),
            note(
                "hospitallimits",
                24,
                384,
                600,
                324,
                "Hospital access limits: " + " ".join(LIMITS["hospital"]),
            ),
            note("buslimits", 640, 384, 616, 324, "Bus access limits: " + " ".join(LIMITS["bus"])),
        ],
    ),
]
BORDER, PAGE = "#DDE3E8", "#F3F5F7"
THEME = {
    "name": "Monsoon Atlas",
    "dataColors": [ACCENT, "#E07A3F", "#4FA3C0", GREY, "#2C3A4A", "#9BC53D", "#B23A3A", "#6C5B7B"],
    "background": "#FFFFFF",
    "foreground": INK,
    "tableAccent": ACCENT,
    "good": "#2E7D4F",
    "neutral": GREY,
    "bad": "#B23A3A",
    "textClasses": {
        "title": {"fontFace": "Segoe UI Semibold", "color": INK},
        "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 26, "color": ACCENT},
        "label": {"fontFace": "Segoe UI", "color": MUTED},
    },
    "visualStyles": {
        "*": {
            "*": {
                "background": [
                    {"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}
                ],
                "border": [{"show": True, "color": {"solid": {"color": BORDER}}, "radius": 8}],
            }
        },
        "page": {
            "*": {
                "background": [{"color": {"solid": {"color": PAGE}}, "transparency": 0}],
                "outspace": [{"color": {"solid": {"color": PAGE}}}],
            }
        },
        "textbox": {"*": {"background": [{"show": False}], "border": [{"show": False}]}},
    },
}


def build_report(report: Path) -> None:
    write_json(report / ".platform", platform("Report"))
    write_json(
        report / "definition.pbir",
        {
            "$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
        },
    )
    write_json(report / "StaticResources" / "RegisteredResources" / "monsoon.json", THEME)
    d = report / "definition"
    write_json(
        d / "version.json",
        {
            "$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
    )
    at_import = {"visual": "1.8.97", "report": "2.0.97", "page": "1.3.97"}
    write_json(
        d / "report.json",
        {
            "$schema": f"{SCHEMA}/item/report/definition/report/3.0.0/schema.json",
            "themeCollection": {
                "customTheme": {
                    "name": "monsoon.json",
                    "reportVersionAtImport": at_import,
                    "type": "RegisteredResources",
                }
            },
            "resourcePackages": [
                {
                    "name": "RegisteredResources",
                    "type": "RegisteredResources",
                    "items": [
                        {"name": "monsoon.json", "path": "monsoon.json", "type": "CustomTheme"}
                    ],
                }
            ],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "defaultDrillFilterOtherVisuals": True,
                "useEnhancedTooltips": True,
            },
        },
    )
    write_json(
        d / "pages" / "pages.json",
        {
            "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": [p for p, _, _ in PAGES],
            "activePageName": PAGES[0][0],
        },
    )
    for page, display, visuals in PAGES:
        write_json(
            d / "pages" / page / "page.json",
            {
                "$schema": f"{SCHEMA}/item/report/definition/page/1.4.0/schema.json",
                "name": page,
                "displayName": display,
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
            },
        )
        for z, (name, v) in enumerate(visuals):
            v["position"]["z"] = v["position"]["tabOrder"] = z * 1000
            write_json(d / "pages" / page / "visuals" / name / "visual.json", v)


def data_folder_default() -> str:
    return str(PureWindowsPath(DATA)) + "\\"


def build(out: Path = HERE, data_folder: str | None = None) -> None:
    model, report = out / f"{NAME}.SemanticModel", out / f"{NAME}.Report"
    for p in (model, report):
        shutil.rmtree(p, ignore_errors=True)
    build_model(model, data_folder or data_folder_default())
    build_report(report)
    write_json(
        out / f"{NAME}.pbip",
        {
            "$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    write(out / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")


if __name__ == "__main__":
    write_data()
    build()
    print(
        f"wrote powerbi/{NAME}.pbip and reports/powerbi/data/*.csv (data folder: {data_folder_default()})"
    )
