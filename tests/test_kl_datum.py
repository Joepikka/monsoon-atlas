"""T267 (child of T130): KSEB dam vertical datum evidence (D103)."""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "tests/fixtures/s32/manifest.json").read_text("utf-8"))
EVIDENCE = {item["id"]: item for item in MANIFEST["evidence"]}
DOC = (ROOT / "docs/labels/kerala.md").read_text("utf-8")
MANUALS = [f"e{n}" for n in range(81, 99)]


def test_all_manuals_are_recorded_kseb_evidence():
    for eid in MANUALS:
        item = EVIDENCE[eid]
        assert item["url"].startswith("https://kseb.in/uploads/Downloadtemsuppy/")
        assert item["status"] == 200 and item["media_type"] == "application/pdf"
        assert re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) and item["bytes"] > 1_000_000
        assert item["raw_path"].startswith("S32/2026-11-08/")
        assert item["shows"].startswith("KSEB O&M-")


def test_datum_table_counts_only_named_references():
    rows = re.findall(r"^\| (.+?) \| (.+?) \| (.+?) \| (known: MSL|unknown) \|$", DOC, re.M)
    known = [row for row in rows if row[3] == "known: MSL"]
    assert len(known) == 4
    for _, cites, statement, _ in known:
        assert re.search(r"(?i)mean sea level|MSL", statement)
        for eid in re.findall(r"e\d{2}", cites):
            assert re.search(r"(?i)mean sea level|msl", EVIDENCE[eid]["shows"])
    unknown_shows = [
        EVIDENCE[e]["shows"] for e in MANUALS if e not in {"e81", "e82", "e83", "e96", "e97"}
    ]
    assert all(
        "no named datum" in s or "no levelling reference" in s or "only for river" in s
        for s in unknown_shows
    )
    assert "the datum part of the gate is **not met**" in DOC  # 4 < 8 dams (T130)


def test_s32_units_claim_cites_the_manuals():
    claim = yaml.safe_load((ROOT / "configs/sources/s32.yaml").read_text("utf-8"))["units"]
    assert set(MANUALS) <= set(claim["evidence"])
    assert "datum-unknown (D103)" in " ".join(claim["detail"].split())
