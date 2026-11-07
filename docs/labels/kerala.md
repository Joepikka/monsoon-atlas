# Kerala evidence audit: T226 bootstrap of T129

Checked against the repository's captured discovery evidence on 5 November 2026.
This is a record of evidence already collected, not a new source verification.
**Full T129 remains pending. M07 is not training-ready.** Decision D44 splits the
configuration prerequisite from the later adapter, geography and label audit.

**6 November update (T114):** S32 is now the only enabled Kerala source. Its
adapter normalizes today's report and quarantines missing/conflicting rows; all
other sources remain disabled. The historical bootstrap descriptions below refer
to T226's state at completion. No datum or M07 readiness gate has been cleared.

## State isolation

`configs/states/kl.yaml` loads through the existing `StateConfig`. Its raw, clean and
publish roots are separate from Karnataka. The shared content-addressed discovery
archive under `data/raw/SNN` is historical evidence, not a Kerala output directory.
Every Kerala source is disabled. Shared source IDs do not mean that Karnataka
filters, ward polygons or verified coverage can be used for Kerala.

S40/T030 and S43/T085 are the original catalogue verification task references;
their Karnataka results do not verify Kerala. There is no `verified_by` reference
for those Kerala entries. Full T129 must supply Kerala-specific evidence before
either can be enabled. No public Kerala records or predictions are created here.

## Available history and its limits

| Source | Existing evidence | Resolution / coverage | Readiness |
|---|---|---|---|
| S32 KSEB | [T113 report](../sources/s32.md); manifest `tests/fixtures/s32/manifest.json`, e02-e07 and the dated sample | Daily 07:00 IST observations; first populated report sampled is 26 Oct 2023; twice-monthly checks find a long Aug 2024-Jul 2026 gap | T114 parser missing; sample does not prove complete daily coverage; no stated datum |
| S34 KSDMA | [T117 report](../sources/s34.md); manifest `tests/fixtures/s34/manifest.json`, e04, e08-e12 | 2,296 distinct valid archive dates, 20 Jun 2020-4 Nov 2026; scanned daily bundles, mixed layouts and units | T118 OCR, owner sample review and overlap checks pending; archive dates are not verified per-dam observations; no stated datum |
| S33 monthly statistics | T115/T116 pending; no source discovery record yet | Unknown until discovery; monthly data can support EDA only | Never interpolate monthly values into daily training labels |
| S35 flood dataset | [T119 report](../sources/s35.md); `configs/sources/s35.yaml` | Blocked; no usable forecasting labels certified | Remains disabled; no invented positives or negatives |
| S36 disaster memoranda | [T121 report](../sources/s36.md); manifest `tests/fixtures/s36/manifest.json`, e06-e11 | District aggregates; one dated flood-area table on 16 Jul 2018 (e06 p9), August narratives (e07 p12), period totals | Descriptive 2018 replay only (D29); not a district-day forecasting dataset |
| S37 landslides | T123/T124 pending | Survey footprint, event dates and explicit negatives unverified | No landslide ground truth; absence from an inventory is not a negative |

Before 2018, S36 contains a year-only 2013 map (e10) and mixed-hazard June totals
(e11), not independent positive and negative district-day flood labels. Do not
spread a period total over its days, turn district counts into ward labels, or
infer an unaffected place from missing documentation. S36 district aliases must
be resolved in T122 with cited evidence. The uncertainty about 1,259 versus 1,260
affected villages in the PDNA remains unresolved, as recorded in T121.

## Dam identity, units, datum and precedence

The source names are documented; canonical dam IDs and a verified vertical datum
are **not registered yet**. T114/T118 must produce the registry from parsed real
evidence, retaining the original name, operator, units and cited mapping. In S34,
KSEB Kuttiyadi and irrigation Kuttiyadi are different dams: a name-only join is
invalid. Do not assume a latitude, elevation datum or alias match from the name.

The following is the adapter policy to implement, not a claim of completed joins:

1. Retain S32 and S34 observations separately with source, operator, table time,
   units, raw hash and report date. A 07:00 S32 value and an 11:00 S34 value are
   different observations; the same calendar date does not make them duplicates.
2. Prefer validated S32 structured observations for its own observation time. Use
   S34 reviewed OCR for historical coverage only after operator/dam identity,
   vertical datum and time compatibility are established. Conflicts are retained
   for review, never silently overwritten or averaged.
3. Read explicit feet/metres per cell and convert only explicit feet (0.3048).
   Quarantine unlabelled unit anomalies in early S32 reports. Inflow in MU is
   energy, not m3/s; never convert it to discharge without physical evidence.
4. Previous-year columns describe their actual historical observation date, but
   were available only in the later report. Do not backdate availability. Datum
   remains unknown; metre units and within-dam comparison do not establish it.

M07's plan gate still requires at least three years of daily observations across
at least eight dams **and a known vertical datum**. Neither the discovery span nor
the number of archive links establishes that gate. T130 must measure coverage
after parsing and OCR review, verify datum, and write splits appropriate to the
actual history before fitting. If the gate fails, record the blocked/research
result and export no operational prediction. Do not reuse the unrelated
route/station prospective schedule accidentally repeated in the T130 task text;
resolve it against the M07 model card and log the decision in T130.

## Geography, shelters and publication

No Kerala ward/taluk geometry or institutional shelter dataset is verified here.
Karnataka's GBA wards must never appear in Kerala. S17 India district evidence may
support a future Kerala extension, after its state filter and boundary version
are tested; it is disabled in this bootstrap. Shelter coordinates, operators and
current status require their own official evidence in full T129. No synthetic
locations, raster-to-ward labels or claims of safe routing are permitted.

Keep S34/S36 restricted raw PDFs local under the existing project policy. Source
reports document restrictions; this audit does not grant permission to redistribute
the raw documents or certify every possible derived publication. Public outputs
still require the existing H11 review. S32's recorded attribution/share-alike
terms must follow any permitted derived publication.

## Completion boundary and next task

T226 acceptance: `python -m pytest tests/test_kl_data.py -q`, plus this evidence
audit. It proved isolated config and disabled source registration. T114 updates
the isolation checks to permit only its tested S32 adapter. The full T129
audit (dam registry/datum, parsed labels, survey footprint, Kerala boundaries and
shelters) stays pending on its original dependencies. T114/T227 are complete;
the gap census found 700 validated empty reports (see `docs/sources/s32-history.md`).
Next is T118 with the required owner OCR review.
S33/T115-T116 is resolved as a blocked source and tested disabled adapter (D51),
not as verified monthly observations. T130 still needs its actual daily coverage,
datum, split and full-T129 dependency checks; no data gate has been waived.
