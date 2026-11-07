"""T228: OCR drafts preserve real evidence and cannot be used as approved observations."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.s34_ocr import create_packet, require_review

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/ocr/s34.json"
MODEL = ROOT / ".tools/ocr/tessdata/eng.traineddata"


def source_artifact(eid):
    entries = json.loads((ROOT / "tests/fixtures/s34/manifest.json").read_text("utf-8"))["evidence"]
    e = next(x for x in entries if x["id"] == eid)
    path = ROOT / "data/raw" / e["raw_path"]
    if not path.exists():
        pytest.skip("S34 restricted raw PDFs stay local")
    return RawArtifact(
        sha256=e["sha256"],
        path=path,
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="s34-ocr-review-v1",
    )


def test_an_ocr_draft_cannot_satisfy_owner_review():
    with pytest.raises(SourceUnavailable, match="owner"):
        require_review({"review_status": "pending", "pages": []})
    # A status string is not an owner review record tied to a specific packet.
    with pytest.raises(SourceUnavailable):
        require_review({"review_status": "approved", "pages": []})


def test_source_hash_is_checked_before_ocr(tmp_path):
    raw = source_artifact("e08").model_copy(update={"sha256": "0" * 64})
    with pytest.raises(IngestError, match="hash"):
        create_packet(raw, [1], tmp_path, CONFIG, MODEL)


def test_language_model_hash_is_checked_before_engine_use(tmp_path):
    raw = source_artifact("e08")
    broken = tmp_path / "eng.traineddata"
    broken.write_bytes(b"invalid copy of the language model")
    with pytest.raises(IngestError, match="model hash"):
        create_packet(raw, [1], tmp_path / "out", CONFIG, broken)


def test_real_pdf_packet_is_a_draft_with_page_and_model_provenance(tmp_path):
    if not all(importlib.util.find_spec(p) for p in ("pypdf", "tesserocr", "PIL")):
        pytest.skip("Optional OCR lock is not installed")
    if not MODEL.exists():
        pytest.skip("Official OCR language model is local only")
    raw = source_artifact("e08")
    packet = create_packet(raw, [1], tmp_path, CONFIG, MODEL)
    assert packet["review_status"] == "pending" and packet["approval"] is None
    assert packet["source_sha256"] == raw.sha256 and packet["source_url"] == raw.source_url
    assert packet["model_sha256"] == hashlib.sha256(MODEL.read_bytes()).hexdigest()
    assert packet["tesserocr"] == "2.12.0" and packet["engine"]
    assert len(packet["pages"]) == 1
    page = packet["pages"][0]
    assert page["page_number"] == 1 and page["words"]
    assert all(
        {"text", "confidence", "left", "top", "width", "height"} <= w.keys() for w in page["words"]
    )
    assert (tmp_path / page["image"]).exists()
    assert (tmp_path / "review.html").is_file()
    with pytest.raises(SourceUnavailable):
        require_review(packet)


def test_targeted_cell_ocr_preserves_the_real_idukki_decimal_and_feet(tmp_path):
    if (
        not all(importlib.util.find_spec(p) for p in ("pypdf", "tesserocr", "PIL"))
        or not MODEL.exists()
    ):
        pytest.skip("Optional local OCR toolchain/model required")
    raw = source_artifact("e08")
    packet = create_packet(
        raw,
        [3],
        tmp_path,
        CONFIG,
        MODEL,
        review_cells=[{"page_number": 3, "label": "Idukki level", "box": [475, 164, 589, 193]}],
    )
    cell = packet["pages"][0]["review_cells"][0]
    assert any("2331.14" in c["text"] and "ft" in c["text"] for c in cell["candidates"])
    assert not cell["agreement"] and cell["selection"] is None
    assert cell["scale"] == 3 and cell["box"] == [475, 164, 589, 193]
    assert packet["review_status"] == "pending"


def test_coloured_irrigation_cells_keep_their_original_digits(tmp_path):
    if (
        not all(importlib.util.find_spec(p) for p in ("pypdf", "tesserocr", "PIL"))
        or not MODEL.exists()
    ):
        pytest.skip("Optional local OCR toolchain/model required")
    packet = create_packet(
        source_artifact("e10"),
        [3],
        tmp_path,
        CONFIG,
        MODEL,
        review_cells=[
            {"page_number": 3, "label": "Karapuzha", "box": [510, 935, 668, 990]},
            {"page_number": 3, "label": "Mangalam", "box": [510, 746, 668, 810]},
        ],
    )
    cells = packet["pages"][0]["review_cells"]
    for cell, source_value in zip(cells, ["757.50", "76.66"], strict=True):
        assert source_value in {c["text"] for c in cell["candidates"]}
        assert not cell["agreement"] and cell["selection"] is None


@pytest.mark.parametrize("approval", ["approved", [], {"decision": "approved"}])
def test_malformed_owner_record_fails_closed(approval):
    with pytest.raises(SourceUnavailable):
        require_review({"review_status": "pending"}, approval)


def test_review_inventory_is_pending_and_contains_no_source_transcripts():
    inventory = json.loads((ROOT / "reports/ocr/s34-review.json").read_text("utf-8"))
    assert {p["evidence_id"] for p in inventory} == {"e08", "e10"}
    assert sum(len(p["pages"]) for p in inventory) == 3
    assert sum(p["sample_cells"] for p in inventory) == 8
    assert all(p["review_status"] == "pending" for p in inventory)
    assert all(len(p["packet_sha256"]) == 64 and "text" not in p for p in inventory)
    assert not load_state(ROOT / "configs/states/kl.yaml").source("S34").enabled
