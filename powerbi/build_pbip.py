# ruff: noqa: E501  (report copy and generated TMDL lines are long by nature)
"""Generate the Power BI project (powerbi/MonsoonAtlas.pbip) from code (T223, D132).

Same approach as build_pbip.py in kerala-veg-prices: a TMDL semantic model that imports small CSVs
through Power Query, and a PBIR report with seven Karnataka pages (D197). The CSVs in reports/powerbi/data/ are
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
        [("Mean Annual Rain", "AVERAGE('District Rain'[gauge_mm])", "0")],
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
        [],
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


def model_rows() -> tuple[list[list], list[list]]:
    err, gain = [], []
    for period, fname in (
        ("2020-2024 locked test", "v1.evaluation.json"),
        ("2025 hindcast", "v1.monitor-2025.json"),
    ):
        d = json.loads((M05_DIR / fname).read_text("utf-8"))
        base, model, imp = d["mae"]["persistence"], d["mae"]["ridge"], d["improvement"]
        err += [
            [period, "persistence (baseline)", round(base, 3)],
            [period, "M05 ridge", round(model, 3)],
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


def bus_rows() -> list[list]:
    """People and cells per bus-access band (derived shares only, no S30 timetable, D191)."""
    counts = {label: [0, 0.0] for _, label in BUS_BANDS}
    with (BUS / "cell_coverage.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            pop = float(r["population"])
            if pop <= 0:
                continue
            frac = float(r["covered_population"]) / pop
            label = next(lab for top, lab in BUS_BANDS if frac < top)
            counts[label][0] += 1
            counts[label][1] += pop
    return [
        [label, i, counts[label][0], round(counts[label][1])]
        for i, (_, label) in enumerate(BUS_BANDS)
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
    rows = {
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


def visual(name, vtype, x, y, w, h, roles=None, title=None, objects=None):
    v = {"visualType": vtype, "drillFilterOtherVisuals": True}
    if roles:
        v["query"] = {"queryState": {role: {"projections": items} for role, items in roles.items()}}
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


PAGES = [
    (
        "overview",
        "Overview",
        [
            *heading(
                "Karnataka in four numbers",
                "Monsoon Atlas, a Rs 0 open-data project. Every figure is derived from committed, licensed data "
                "with its limits stated; blocked sources are shown as blocked, never as zero.",
            ),
            visual(
                "headline",
                "tableEx",
                24,
                110,
                1232,
                260,
                {
                    "Values": [
                        C("Headline", "metric", "Measure"),
                        C("Headline", "value", "Value"),
                        C("Headline", "source", "Sources"),
                    ]
                },
                "Headline results",
            ),
            textbox(
                "method",
                24,
                390,
                1232,
                160,
                "Methods: exact great-circle nearest-site search (hospitals), network walking catchments "
                "(buses), Mann-Kendall with Benjamini-Hochberg correction (rain trends), ridge regression "
                "against persistence with a paired block bootstrap (drought model). Notebooks 02, 04, 08, 11.",
                "11pt",
                False,
                MUTED,
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
            slicer("sig", 24, 110, 220, 200, "Rain Trend", "significance", "Significance"),
            visual(
                "slope",
                "clusteredBarChart",
                260,
                110,
                996,
                380,
                {"Category": [C("Rain Trend", "district")], "Y": [M("Rain Trend", "Sen Slope")]},
                "Sen slope, % of the 1981-2010 mean per decade",
            ),
            visual(
                "tests",
                "tableEx",
                24,
                500,
                1232,
                210,
                {
                    "Values": [
                        C("Rain Trend", "district", "District"),
                        C("Rain Trend", "sen_pct_per_decade", "Sen, %/decade"),
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
        "hospitals",
        "Hospital access",
        [
            *heading(
                "How far people live from the nearest hospital",
                "WorldPop 2025 1 km cells (S16) to OpenStreetMap hospitals (S18), straight-line km, people-weighted. "
                "OSM is thinner in rural areas, so remote distances are upper bounds.",
            ),
            visual(
                "beyond",
                "clusteredBarChart",
                24,
                110,
                700,
                600,
                {
                    "Category": [C("Hospital Access", "district")],
                    "Y": [M("Hospital Access", "Mean km")],
                },
                "People-weighted mean km to the nearest hospital",
            ),
            visual(
                "access",
                "tableEx",
                740,
                110,
                516,
                600,
                {
                    "Values": [
                        C("Hospital Access", "district", "District"),
                        C("Hospital Access", "median_km", "Median km"),
                        C("Hospital Access", "p90_km", "90th pct km"),
                        C("Hospital Access", "share_beyond_10km", "Share > 10 km"),
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
            visual(
                "bands",
                "clusteredColumnChart",
                24,
                110,
                800,
                420,
                {"Category": [C("Bus Access", "band")], "Y": [M("Bus Access", "Total People")]},
                "People by share of their 1 km cell within the walk",
            ),
            visual(
                "bandtable",
                "tableEx",
                840,
                110,
                416,
                420,
                {
                    "Values": [
                        C("Bus Access", "band", "Band"),
                        C("Bus Access", "cells", "1 km cells"),
                        C("Bus Access", "people", "People"),
                    ]
                },
                "Bands",
            ),
        ],
    ),
    (
        "accuracy",
        "Model accuracy",
        [
            *heading(
                "M05 drought outlook beats persistence, and the gain is clearly above zero",
                "District SPI-3 forecast, mean absolute error (lower is better), against the strongest simple baseline. "
                "Hindcast, because IMD publishes the grid yearly (D39). Promoted only if the lower 95% bound of the improvement is above 0.",
            ),
            visual(
                "mae",
                "clusteredColumnChart",
                24,
                110,
                620,
                330,
                {
                    "Category": [C("Model Error", "period")],
                    "Series": [C("Model Error", "model")],
                    "Y": [M("Model Error", "Mean Absolute Error")],
                },
                "Mean absolute error, SPI units",
            ),
            visual(
                "gain",
                "tableEx",
                660,
                110,
                596,
                330,
                {
                    "Values": [
                        C("Model Gain", "period", "Period"),
                        C("Model Gain", "district_months", "District-months"),
                        C("Model Gain", "improvement", "Improvement"),
                        C("Model Gain", "lower95", "Lower 95%"),
                        C("Model Gain", "upper95", "Upper 95%"),
                        C("Model Gain", "promoted", "Lower bound above 0"),
                    ]
                },
                "Improvement over persistence (paired block bootstrap)",
            ),
        ],
    ),
    (
        "rain",
        "Gauge rain",
        [
            *heading(
                "Karnataka gauge rain by district",
                "KSNDMC rain-gauge annual district totals (S29, public domain), 29 districts with like-for-like years. Gauge totals only.",
            ),
            slicer("year", 24, 110, 200, 200, "District Rain", "year", "Year"),
            visual(
                "rain",
                "clusteredBarChart",
                240,
                110,
                1016,
                480,
                {
                    "Category": [C("District Rain", "district")],
                    "Y": [M("District Rain", "Mean Annual Rain")],
                },
                "Mean annual rain at the gauges, mm",
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
            blocked_card("prices", 24, 120, 1232, 90, "Market prices (S22, S23)"),
            blocked_card("flood", 24, 220, 1232, 90, "Flood labels (S43) and ward-level rain"),
            blocked_card("models", 24, 320, 1232, 90, "Models M07 and M06"),
        ],
    ),
]
THEME = {
    "name": "Monsoon Atlas",
    "dataColors": [ACCENT, GREY, "#2C3A4A", "#4FA3C0", "#B8BFC7", MUTED],
    "background": "#FFFFFF",
    "foreground": INK,
    "tableAccent": ACCENT,
    "textClasses": {"title": {"fontFace": "Segoe UI Semibold", "color": INK}},
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
