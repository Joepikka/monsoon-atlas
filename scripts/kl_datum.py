"""Fetch KSEB dam O&M manuals as S32 evidence and list datum statements (T267, D103).

Run from the repository root: .venv/Scripts/python scripts/kl_datum.py [fetch|scan]
`fetch` downloads e81-e98 through the project fetcher (robots.txt allows all) and adds
them to tests/fixtures/s32/manifest.json. `scan` prints each manual's lines that name a
levelling reference, with page numbers, for the reviewer to quote. Nothing is inferred.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas.ingest.discovery import capture, load_manifest, write_manifest  # noqa: E402

RAW = ROOT / "data/raw"
MANIFEST = ROOT / "tests/fixtures/s32/manifest.json"
BASE = "https://kseb.in/uploads/Downloadtemsuppy/"
# KSEB Dam Safety > Operation Manuals listing, read 8 Nov 2026 (D103).
MANUALS = {
    "e81": (
        "o_m_manual_idukki_cheruthoni_kulamavu-17166131361466455665.pdf",
        "Idukki, Cheruthoni and Kulamavu dams (O&M-09)",
    ),
    "e82": (
        "O_M_Kulamavu_Saddle_Dams_KSEB-171696373158946266.pdf",
        "Kulamavu saddle dams (O&M-24)",
    ),
    "e83": ("O_M_Sengulam_Dam_KSEB-17169631791336096338.pdf", "Sengulam dam (O&M-20)"),
    "e84": ("O_M_Ponmudi_Dam-17169594641734735654.pdf", "Ponmudi dam (O&M-21)"),
    "e85": ("O_M_Lower_Periyar_KSEB-17166190931929587582.pdf", "Lower Periyar dam (O&M-16)"),
    "e86": ("O_M_Kundala_Dam_KSEB-1716617408514848068.pdf", "Kundala dam (O&M-10)"),
    "e87": ("O_M_Madupetty_KSEB-17166183861461299945.pdf", "Madupetty dam (O&M-15)"),
    "e88": ("O_M_Poringalkuthu_Dam_KSEB-1716960153514908244.pdf", "Poringalkuthu dam (O&M-06)"),
    "e89": ("O_M_Kallarkutty_KSEB-17166144811970114423.pdf", "Kallarkutty dam (O&M-08)"),
    "e90": ("O_M_Kuttiyadi_KSEB-17166179952115261197.pdf", "Kuttiyadi dam, Kakkayam (O&M-07)"),
    "e91": ("O_M_Anayirankal_KSEB-1716613456585367477.pdf", "Anayirankal dam (O&M-18)"),
    "e92": ("O_M_Erattayar_KSEB-17166137001481325810.pdf", "Erattayar dam (O&M-14)"),
    "e93": ("O_M_Kallar_KSEB-17166143321439416105.pdf", "Kallar dam (O&M-13)"),
    "e94": ("O_M_Moozhiyar_KSEB-1716618782589753332.pdf", "Moozhiyar dam (O&M-11)"),
    "e95": ("O_M_Sholayar_Dams_KSEB-1716963388589982523.pdf", "Sholayar dams (O&M-04)"),
    "e96": ("O_M_Kakki_Anathode_KSEB-1716614201391646806.pdf", "Kakki and Anathode dams (O&M-02)"),
    "e97": ("O_M_Pamba_KSEB-1716619202387866381.pdf", "Pamba dam (O&M-03)"),
    "e98": ("O_M_Idamalayar_KSEB-17166138702118609236.pdf", "Idamalayar dam (O&M-01)"),
}
DATUM = re.compile(r"M\.?S\.?L|mean sea|sea level|datum|G\.?T\.?S|Survey of India", re.I)


def fetch() -> None:
    manifest = load_manifest(MANIFEST)
    known = {e.id for e in manifest.evidence}
    for eid, (name, title) in MANUALS.items():
        if eid in known:
            continue
        shows = f"KSEB operation and maintenance manual (PDF): {title}"
        got = capture("S32", "kl", {eid: (BASE + name, shows)}, RAW, {"kseb.in"})
        manifest.evidence.extend(got.evidence)
        write_manifest(manifest, MANIFEST)  # after each file, so a failure keeps earlier ones
        print(eid, got.evidence[0].bytes, got.evidence[0].sha256[:12], flush=True)
        time.sleep(2)


def scan() -> None:
    from pypdf import PdfReader

    evidence = {e.id: e for e in load_manifest(MANIFEST).evidence}
    report = {}
    for eid in MANUALS:
        reader = PdfReader(RAW / evidence[eid].raw_path)
        hits = []
        for number, page in enumerate(reader.pages, start=1):
            for line in (page.extract_text() or "").splitlines():
                if DATUM.search(line):
                    hits.append((number, " ".join(line.split())[:200]))
        report[eid] = {"pages": len(reader.pages), "hits": hits[:12]}
        print(eid, MANUALS[eid][1], "pages", len(reader.pages), "hits", len(hits), flush=True)
        for number, text in hits[:12]:
            print(f"   p{number}: {text}")
    out = ROOT / ".cache/tmp/kl_datum_scan.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), "utf-8")


if __name__ == "__main__":
    {"fetch": fetch, "scan": scan}[sys.argv[1] if len(sys.argv) > 1 else "fetch"]()
