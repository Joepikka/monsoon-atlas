"""T228: local OCR review packets for restricted S34 PDFs. Emits no observations."""

from __future__ import annotations

import csv
import hashlib
import html
import importlib.metadata
import io
import json
from pathlib import Path
from urllib.parse import urlsplit

from atlas.contracts import RawArtifact
from atlas.ingest.base import IngestError, SourceUnavailable


def packet_sha256(packet: dict) -> str:
    return hashlib.sha256(
        json.dumps(packet, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def require_review(packet: dict, approval: dict | None = None) -> None:
    """Only an explicit owner record tied to this exact packet can clear this gate.

    This is a workflow record, not authentication. The agent may record it only after
    the owner has actually reviewed the sample. A draft's status text is insufficient.
    """
    if not (
        isinstance(approval, dict)
        and approval.get("decision") == "approved"
        and approval.get("owner")
        and approval.get("reviewed_at")
        and approval.get("packet_sha256") == packet_sha256(packet)
    ):
        raise SourceUnavailable("S34 OCR needs an explicit owner review of this exact packet")


def _words(tsv: str) -> list[dict]:
    out = []
    # The C++ API returns rows without the header that the CLI TSV renderer adds.
    fields = (
        "level",
        "page_num",
        "block_num",
        "par_num",
        "line_num",
        "word_num",
        "left",
        "top",
        "width",
        "height",
        "conf",
        "text",
    )
    for row in csv.DictReader(
        io.StringIO(tsv), fieldnames=fields, delimiter="\t", quoting=csv.QUOTE_NONE
    ):
        if row.get("level") == "5" and row.get("text", "").strip():
            out.append(
                {
                    "text": row["text"],
                    "confidence": float(row["conf"]),
                    **{k: int(row[k]) for k in ("left", "top", "width", "height")},
                }
            )
    return out


def create_packet(
    raw: RawArtifact,
    pages: list[int],
    output: Path,
    config_path: Path,
    model: Path,
    *,
    review_cells: list[dict] | None = None,
):
    """Pages are 1-based. Keep PDF images, OCR text and word coordinates local for review."""
    body = raw.path.read_bytes()
    if hashlib.sha256(body).hexdigest() != raw.sha256:
        raise IngestError("S34: source PDF hash mismatch")
    url = urlsplit(raw.source_url)
    if url.scheme != "https" or url.hostname != "sdma.kerala.gov.in":
        raise IngestError("S34: source must be the verified KSDMA host")
    settings = json.loads(config_path.read_text("utf-8"))
    if hashlib.sha256(model.read_bytes()).hexdigest() != settings["model"]["sha256"]:
        raise IngestError("S34: language model hash mismatch")
    for package in ("pypdf", "tesserocr", "Pillow"):
        if importlib.metadata.version(package) != settings[package]:
            raise IngestError(f"S34: {package} differs from the pinned OCR toolchain")
    # Optional dependencies stay out of core imports and CI's core-only environment.
    import numpy as np
    from PIL import Image, ImageOps
    from pypdf import PdfReader
    from tesserocr import PyTessBaseAPI, tesseract_version

    if tesseract_version() != settings["engine"]:
        raise IngestError("S34: embedded OCR engine differs from the recorded build")

    try:
        reader = PdfReader(io.BytesIO(body), strict=True)
    except Exception as exc:
        raise IngestError("S34: unreadable PDF") from exc
    if not pages or len(pages) > 10 or len(set(pages)) != len(pages):
        raise IngestError("S34: select 1 to 10 distinct pages for the review sample")
    if any(p < 1 or p > len(reader.pages) for p in pages):
        raise IngestError("S34: page outside the PDF")
    output.mkdir(parents=True, exist_ok=True)
    packet = {
        "source_sha256": raw.sha256,
        "source_url": raw.source_url,
        "fetched_at": raw.fetched_at.isoformat(),
        "review_status": "pending",
        "approval": None,
        "model_sha256": settings["model"]["sha256"],
        "model_commit": settings["model"]["commit"],
        "language": settings["language"],
        "psm": settings["psm"],
        "tesserocr": settings["tesserocr"],
        "pypdf": settings["pypdf"],
        "Pillow": settings["Pillow"],
        "engine": tesseract_version(),
        "pages": [],
    }
    with PyTessBaseAPI(
        path=str(model.parent), lang=settings["language"], psm=settings["psm"]
    ) as api:
        for number in pages:
            images = list(reader.pages[number - 1].images)
            if len(images) != 1:
                raise IngestError(f"S34: page {number} is not the verified single-image layout")
            image = images[0].image.convert("RGB")
            name = f"page-{number:02d}.png"
            image.save(output / name)
            api.SetPageSegMode(settings["psm"])
            api.SetVariable("tessedit_char_whitelist", "")
            api.SetImage(image)
            api.Recognize()
            text, tsv = api.GetUTF8Text(), api.GetTSVText(number - 1)
            (output / f"page-{number:02d}.txt").write_text(text, encoding="utf-8")
            (output / f"page-{number:02d}.tsv").write_text(tsv, encoding="utf-8")
            cells = []
            for spec in review_cells or []:
                if spec["page_number"] != number:
                    continue
                left, top, right, bottom = spec["box"]
                if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                    raise IngestError("S34: review cell outside the source image")
                crop = image.crop((left, top, right, bottom))
                cell_name = f"page-{number:02d}-cell-{len(cells) + 1:02d}.png"
                crop.save(output / cell_name)
                # Coloured table backgrounds otherwise suppress valid dark digits.
                gray = ImageOps.autocontrast(crop.convert("L"))
                contrast = gray.resize((crop.width * 3, crop.height * 3), Image.Resampling.LANCZOS)
                contrast = ImageOps.expand(contrast, border=12, fill="white")
                pixels = np.asarray(gray).copy()
                # Long table rulings can be read as extra '1' digits. Keep the
                # original crop intact and record the rules removed from the OCR copy.
                grid_columns = np.where((pixels < 64).mean(axis=0) > 0.75)[0]
                grid_rows = np.where((pixels < 64).mean(axis=1) > 0.75)[0]
                pixels[:, grid_columns] = 255
                pixels[grid_rows, :] = 255
                binary = Image.fromarray(np.where(pixels < 80, 0, 255).astype("uint8"))
                ys, xs = np.where(np.asarray(binary) == 0)
                content_box, cell_text, cell_words = None, "", []
                if len(xs):
                    content_box = [
                        int(xs.min()),
                        int(ys.min()),
                        int(xs.max()) + 1,
                        int(ys.max()) + 1,
                    ]
                    tight = binary.crop(content_box)
                    enlarged = tight.resize(
                        (tight.width * 3, tight.height * 3), Image.Resampling.NEAREST
                    )
                    enlarged = ImageOps.expand(enlarged, border=20, fill="white")
                    api.SetPageSegMode(7)
                    api.SetVariable("tessedit_char_whitelist", "0123456789.ftm%/-: ")
                    api.SetImage(enlarged)
                    api.Recognize()
                    cell_text, cell_words = (
                        api.GetUTF8Text().strip(),
                        _words(api.GetTSVText(number - 1)),
                    )
                binary_candidate = {
                    "method": "binary80-tight-nearest",
                    "text": cell_text,
                    "scale": 3,
                    "border": 20,
                    "threshold": 80,
                    "content_box": content_box,
                    "preprocessing": (
                        "grayscale, autocontrast, grid rules removed, binary80, "
                        "tight crop, nearest 3x, white border"
                    ),
                    "removed_grid_columns": grid_columns.tolist(),
                    "removed_grid_rows": grid_rows.tolist(),
                    "psm": 7,
                    "whitelist": "0123456789.ftm%/-: ",
                    "words": cell_words,
                }
                api.SetPageSegMode(7)
                api.SetVariable("tessedit_char_whitelist", "0123456789.ftm%/-: ")
                api.SetImage(contrast)
                api.Recognize()
                contrast_candidate = {
                    "method": "contrast-lanczos",
                    "text": api.GetUTF8Text().strip(),
                    "scale": 3,
                    "border": 12,
                    "psm": 7,
                    "whitelist": "0123456789.ftm%/-: ",
                    "preprocessing": "grayscale, autocontrast, Lanczos 3x, white border",
                    "words": _words(api.GetTSVText(number - 1)),
                }
                cells.append(
                    spec
                    | {
                        "image": cell_name,
                        "image_sha256": hashlib.sha256(
                            (output / cell_name).read_bytes()
                        ).hexdigest(),
                        "scale": 3,
                        "selection": None,
                        "agreement": bool(cell_text) and contrast_candidate["text"] == cell_text,
                        "candidates": [contrast_candidate, binary_candidate],
                    }
                )
            packet["pages"].append(
                {
                    "page_number": number,
                    "image": name,
                    "image_sha256": hashlib.sha256((output / name).read_bytes()).hexdigest(),
                    "width": image.width,
                    "height": image.height,
                    "text": text,
                    "words": _words(tsv),
                    "review_cells": cells,
                }
            )
    (output / "packet.json").write_text(
        json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    sections = []
    for page in packet["pages"]:
        cell_rows = "".join(
            f"<tr><td>{html.escape(c['label'])}</td>"
            f'<td><img src="{c["image"]}" alt="Original sample cell"></td>'
            + "".join(
                f"<td><code>{html.escape(v['text'] or '(blank OCR; not zero)')}</code></td>"
                for v in c["candidates"]
            )
            + "<td>"
            + ("Same reading; unreviewed" if c["agreement"] else "DISAGREEMENT — manual review")
            + "</td></tr>"
            for c in page["review_cells"]
        )
        sections.append(
            f"<section><h2>PDF page {page['page_number']}</h2>"
            "<h3>Targeted sample cells (draft OCR)</h3><table>"
            "<tr><th>Sample</th><th>Original crop</th><th>Reading A</th>"
            "<th>Reading B</th><th>Status</th></tr>"
            + cell_rows
            + "</table><details><summary>Original full page and "
            "uncorrected whole-page OCR</summary>"
            f'<div class="columns"><img src="{page["image"]}" '
            f'alt="Original PDF page {page["page_number"]}">'
            f"<pre>{html.escape(page['text'])}</pre></div></details></section>"
        )
    document = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>S34 OCR review</title>'
        "<style>body{font:16px system-ui;margin:24px;max-width:1800px} "
        ".columns{display:grid;grid-template-columns:1fr 1fr;gap:24px} "
        "img{width:100%;height:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;"
        "font-size:14px}section{border-top:1px solid #ccc;margin-top:24px}"
        "td,th{border:1px solid #ccc;padding:10px}td img{min-width:150px;max-width:300px}</style>"
        "<h1>S34 OCR sample — owner review pending</h1>"
        "<p>Compare the report date, operator, reservoir names, water levels and units "
        "with the original image. English OCR does not certify Malayalam text, row colours "
        "or table-cell associations. Whole-page OCR has known digit errors. The targeted "
        "cell drafts show two preprocessing methods. Disagreements remain unresolved; "
        "no digits have been manually repaired and no candidate is selected automatically. "
        "No observation rows have been created.</p>"
        f'<p>Source: <a href="{html.escape(raw.source_url, quote=True)}">KSDMA report</a>'
        f"<br>PDF SHA256: {raw.sha256}</p>" + "".join(sections) + "</html>"
    )
    (output / "review.html").write_text(document, encoding="utf-8")
    return packet
