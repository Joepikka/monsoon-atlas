# S34 OCR review tooling (T228, child of T118)

**Machine preparation complete; owner review pending. Full T118 remains pending
and S34 remains disabled.** No observation, label or prediction rows are created.

## Reproducible local tools

`requirements/ocr.in` and its pip-tools hash lock pin pypdf 6.21.4 (BSD-3-Clause),
tesserocr 2.12.0 (MIT) and Pillow 13.0.0 (MIT-CMU). The Windows Python 3.12 wheel supplies
Tesseract 5.5.3 and Leptonica 1.87.0 without a system installer. The exact embedded
build string is recorded in `configs/ocr/s34.json` and checked at runtime.
The optional OCR group is included in the dependency policy and forbids torch.

Sources: [tesserocr package/installation documentation](https://pypi.org/project/tesserocr/2.12.0/),
[pypdf package](https://pypi.org/project/pypdf/6.21.4/),
[Pillow package](https://pypi.org/project/Pillow/13.0.0/).
The package hashes are in `requirements/ocr.txt`; `pip check` passes locally.

English language data comes from the official
[tessdata_fast repository](https://github.com/tesseract-ocr/tessdata_fast), under
Apache-2.0, commit `87416418657359cb625c412a48b6e1d6d41c29bd`.
The 4,113,088-byte `eng.traineddata` SHA256 is
`7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.
It lives in ignored `.tools/ocr/tessdata/`, on drive D. No accounts, installer
terms, paid service, GPU training or source PDF downloads were needed.

## Actual sample and known limits

The packet uses existing, hash-checked T117 evidence:

| Evidence | PDF pages (1-based) | Content |
|---|---|---|
| e08 | 3 | KSEB table, 20 June 2020, 11 am |
| e10 | 2, 3 | KSEB and irrigation tables, 1 August 2023, 11 am |

`scripts/s34_ocr_review.py` writes original decoded page images, uncorrected
whole-page OCR text, per-word confidence/coordinates, and eight targeted numeric
cell crops. Every packet records PDF/model/image hashes and engine settings.
The original image/crop is retained unchanged for comparison.

Whole-page English OCR misreads digits, decimals, Malayalam names and row
associations. Coloured backgrounds and grid rules cause additional errors.
After three unsuccessful attempts at a universal recipe, D50 rejects the
assumption that one preprocessing recipe is reliable across these layouts.

Two draft readings are retained for each sample cell: contrast/Lanczos and
binary-80/tight-crop/nearest, both at 3x scale with single-line numeric OCR.
The second records removed grid rows/columns and its content bounding box.
**Six of eight sample cells disagree. No candidate is selected automatically,
including the two that agree.** These development samples do not establish an
OCR accuracy rate or validate a bulk extraction method. Alert colours are not
interpreted. No feet/metres conversion or dam alias mapping is performed here.

The local review index is:
`D:\monsoon-atlas\data\raw\S34\ocr-review\index.html`.
Open its two links, compare both readings to the original crops, and confirm or
correct the eight values/units. Expand the full-page images to verify operator,
date and row associations. Owner review is required by T117's source check and
the T118 process before extracted values may be used. It is a review of this
sample only, not approval of every future OCR result or of M07.

## Files and validation

Restricted PDF images, crops, OCR text and full packet JSON stay in ignored
`data/raw/S34/ocr-review`. The committed `reports/ocr/s34-review.json` contains
only packet/source hashes, source URLs, page IDs, counts and pending status.
Production ingestion does not read test fixtures. S34 stays disabled until its
complete adapter and review requirements pass.

```powershell
.\.venv\Scripts\python -m pip install --require-hashes --only-binary=:all: -r requirements/ocr.txt
.\.venv\Scripts\python scripts/s34_ocr_review.py
.\.venv\Scripts\python -m pytest tests/sources/test_s34_ocr.py -q
```

Set TEMP/TMP to the repository's `.cache/tmp` before downloads (D26). The review
gate rejects a status string or malformed approval; a real owner record must be
tied to the exact packet digest. This is a workflow record, not authentication.
No approval file is produced by the generator. PDF object-header whitespace
warnings are retained; they do not fabricate or correct table contents.

Machine acceptance: **10 passed in 3.88s**. Final suite: **419 passed, 1 skipped,
1 warning in 106.21s**. Lint, formatting, dependency policy, installed-package
compatibility, amendment parity and all 13 local artifact links passed. Independent
read-only review found no actionable defect. The skip and warning are unchanged
S36 PDF-tool availability and MLflow deprecation, described in HANDOFF.
