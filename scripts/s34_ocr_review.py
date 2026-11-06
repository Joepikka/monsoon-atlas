"""T228: generate a restricted, local-only OCR sample for required owner review."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

from atlas.contracts import RawArtifact
from atlas.ingest.s34_ocr import create_packet, packet_sha256

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")
    evidence = json.loads((ROOT / "tests/fixtures/s34/manifest.json").read_text("utf-8"))[
        "evidence"
    ]
    output = ROOT / "data/raw/S34/ocr-review"
    packets = []
    cells = {
        "e08": [
            {"page_number": 3, "label": "2020 KSEB Idukki level", "box": [475, 164, 589, 193]},
            {"page_number": 3, "label": "2020 KSEB Sholayar level", "box": [475, 646, 589, 674]},
        ],
        "e10": [
            {"page_number": 2, "label": "2023 KSEB Idukki level", "box": [415, 478, 582, 537]},
            {"page_number": 2, "label": "2023 KSEB Kuttiyadi level", "box": [416, 1244, 581, 1301]},
            {
                "page_number": 2,
                "label": "2023 KSEB Kallarkutti storage",
                "box": [586, 796, 773, 855],
            },
            {
                "page_number": 3,
                "label": "2023 irrigation Kuttiyadi level",
                "box": [510, 877, 668, 931],
            },
            {
                "page_number": 3,
                "label": "2023 irrigation Karapuzha level",
                "box": [510, 935, 668, 990],
            },
            {
                "page_number": 3,
                "label": "2023 irrigation Mangalam level",
                "box": [510, 746, 668, 810],
            },
        ],
    }
    # These are the KSEB 2020 and KSEB/irrigation 2023 table pages verified in T117.
    for eid, pages in (("e08", [3]), ("e10", [2, 3])):
        e = next(item for item in evidence if item["id"] == eid)
        raw = RawArtifact(
            sha256=e["sha256"],
            path=ROOT / "data/raw" / e["raw_path"],
            fetched_at=e["fetched_at"],
            media_type=e["media_type"],
            response_status=e["status"],
            source_url=e["url"],
            schema_mapping_version="s34-ocr-review-v1",
        )
        packet = create_packet(
            raw,
            pages,
            output / eid,
            ROOT / "configs/ocr/s34.json",
            ROOT / ".tools/ocr/tessdata/eng.traineddata",
            review_cells=cells[eid],
        )
        packets.append(
            {
                "evidence_id": eid,
                "packet_sha256": packet_sha256(packet),
                "review_status": "pending",
                "pages": pages,
                "word_count": sum(len(p["words"]) for p in packet["pages"]),
                "sample_cells": sum(len(p["review_cells"]) for p in packet["pages"]),
                "disagreements": sum(
                    not c["agreement"] for p in packet["pages"] for c in p["review_cells"]
                ),
                "source_sha256": raw.sha256,
                "source_url": raw.source_url,
            }
        )
    (output / "manifest.json").write_text(json.dumps(packets, indent=2) + "\n", encoding="utf-8")
    inventory = ROOT / "reports/ocr/s34-review.json"
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text(json.dumps(packets, indent=2) + "\n", encoding="utf-8")
    links = "".join(
        f'<li><a href="{p["evidence_id"]}/review.html">{html.escape(p["evidence_id"])}: '
        f"original table and OCR text (pages {p['pages']})</a></li>"
        for p in packets
    )
    index = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>S34 owner review</title>'
        "<style>body{font:18px system-ui;max-width:1000px;margin:32px auto;padding:20px}"
        "li{margin:12px 0}table{border-collapse:collapse}"
        "td,th{padding:10px;border:1px solid #ccc}</style>"
        "<h1>S34 OCR sample: review required</h1>"
        "<p>These are draft OCR transcripts of three real table pages. No data rows, "
        "labels or forecasts have been approved. Source S34 remains disabled.</p>"
        "<ol><li>Open the 2020 sample. Compare the two targeted cell crops with their OCR text. "
        "Expand the original table to check its date/time and dam names.</li>"
        "<li>Open the 2023 samples. Compare the six targeted crops with both OCR readings. "
        "Confirm that ft and m remain distinct and the two "
        "operators are separate.</li><li>For a disagreement, read the original crop and reply "
        "with its actual value and unit. For matching readings, confirm they match the crop. "
        "No value is selected automatically.</li></ol>"
        f"<ul>{links}</ul>"
        "<p>English OCR cannot verify Malayalam text or alert colours. Low-confidence words "
        "and coordinates are retained in packet.json; no colour meaning is inferred.</p></html>"
    )
    (output / "index.html").write_text(index, encoding="utf-8")
    print("Review packet:", output / "index.html")
    for packet in packets:
        print(packet["evidence_id"], "pages", packet["pages"], "OCR words", packet["word_count"])


if __name__ == "__main__":
    main()
