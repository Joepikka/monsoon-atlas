# ruff: noqa: E501  (report copy and generated TMDL lines are long by nature)
"""Generate the Power BI project (powerbi/MonsoonAtlas.pbip) from code (T223, D132).

Same approach as build_pbip.py in kerala-veg-prices: a TMDL semantic model that imports small CSVs
through Power Query, and a PBIR report with four pages. The CSVs in reports/powerbi/data/ are
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
    "Reservoir Change": (
        "reservoir_change.csv",
        "S32",
        [
            ("window", "string"),
            ("reservoir", "string"),
            ("start_pct", "double"),
            ("end_pct", "double"),
            ("change_points", "double"),
        ],
        [("Storage Change", "AVERAGE('Reservoir Change'[change_points])", "+0.0;-0.0;0.0")],
    ),
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
        [("MAE", "AVERAGE('Model Error'[mae])", "0.000")],
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


def write_data(data_dir: Path = DATA) -> None:
    err, gain = model_rows()
    rows = {
        "Reservoir Change": reservoir_rows(),
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
        "reservoirs",
        "Reservoir trends",
        [
            *heading(
                "Kerala dam storage changed between sampled report dates",
                "KSEB daily water level reports (S32, CC BY-SA 2.5 India, credit KSEB; share alike), sampled about every 15 days. "
                "8 of 16 dams have complete readings. Net of rain, releases and generation.",
            ),
            slicer("window", 24, 110, 200, 160, "Reservoir Change", "window", "Window"),
            visual(
                "change",
                "clusteredBarChart",
                240,
                110,
                1016,
                330,
                {
                    "Category": [C("Reservoir Change", "reservoir")],
                    "Y": [M("Reservoir Change", "Storage Change")],
                },
                "Change in live storage, percentage points of full capacity",
            ),
            visual(
                "table",
                "tableEx",
                240,
                452,
                1016,
                200,
                {
                    "Values": [
                        C("Reservoir Change", "reservoir", "Reservoir"),
                        C("Reservoir Change", "window", "Window"),
                        C("Reservoir Change", "start_pct", "Start, %"),
                        C("Reservoir Change", "end_pct", "End, %"),
                        C("Reservoir Change", "change_points", "Change, points"),
                    ]
                },
                "Readings",
            ),
            blocked_card("blocked", 24, 660, 1232, 50, "KWRIS daily reservoir levels (S28)"),
        ],
    ),
    (
        "rain",
        "Ward rain and flood exposure",
        [
            *heading(
                "Karnataka rain by district; ward flood exposure is blocked",
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
            blocked_card("blocked", 24, 600, 1232, 100, "Flood labels (S43) and ward-level rain"),
        ],
    ),
    (
        "prices",
        "Prices",
        [
            *heading("Market prices are blocked", "No price series is shown because none is held."),
            blocked_card("blocked", 24, 120, 1232, 120, "Market prices (S22, S23)"),
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
                    "Y": [M("Model Error", "MAE")],
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
            blocked_card("blocked", 24, 460, 1232, 60, "Models M07 and M06"),
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
