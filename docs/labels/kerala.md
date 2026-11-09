# Kerala evidence audit: T226 bootstrap and T129 history report

Checked against the repository's captured discovery evidence on 5 November 2026.
This is a record of evidence already collected, not a new source verification.
**T129 audit run 9 Nov 2026 (D124): see the history availability report below.
M07 is not training-ready.** Decision D44 split the configuration prerequisite
from this audit.

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
for those Kerala entries. T129 found no Kerala-specific evidence, so
neither can be enabled. No public Kerala records or predictions are created here.

## History availability report (T129, 9 November 2026)

Dam IDs, per-dam datum status and source precedence are registered in
[`configs/states/kl/dams.yaml`](../../configs/states/kl/dams.yaml): 16 KSEB dams
exactly as S32 publishes them, **4 with a known datum (MSL), 12 unknown**; the
T130 gate needs 8, so it is **not met**. Precedence for dam levels: S32 daily,
then S34 only after T118 reviewed OCR and a known datum, S33 monthly never as a
daily label. T118 (bulk OCR) is not done: D102 approved eight crops only, so S34
counts as **unavailable**. No cleaned Kerala data (`data/clean/kl`) exists yet.

### Label families held

| Label family | Source | Resolution | Date range actually held | Count | Verifiable |
|---|---|---|---|---|---|
| Dam level (S32) | KSEB daily report | daily 07:00 IST, per dam | Sampled dates only: 26 Oct 2023; 15 Nov 2023-1 Aug 2024; 1 Aug-1 Nov 2026 (73-date twice-monthly sample, e08-e80). Census of 15 Aug 2024-15 Jul 2026: 700 dates, all empty (T227) | 16 dams per populated report; per-day parsed series not stored | Yes for the dated reports; the 700 empty days are absence of rows, not zero level. Datum known for 4 dams only |
| 2018 district flood area | S36 (enabled, D123) | one dated table, 16 Jul 2018, NRSC flooded area | 16 Jul 2018 | 7 districts, 55,007 ha | Yes, page-cited. It is an area snapshot, not a daily flood label for every district |

### EXCLUDED labels (not used for any training label)

| Excluded item | Reason |
|---|---|
| S36 district period totals (fatalities: 138 in Memorandum 1, 339 in Memorandum 2) | Cover whole periods (29 May-31 Jul 2018; 1-30 Aug 2018), `event_date` is null. Not spread over days; no monthly-to-daily or period-to-daily interpolation |
| 2018 August narrative dates (for example 8-9 Aug flooding in Wayanad, Kannur, Malappuram) | Prose in the memorandum, not a table with district-day rows; no negatives for other districts |
| Pre-2018 negatives (no flood) | None audited. S36 holds a year-only 2013 map (e10) and mixed-hazard June 2013 totals (e11). A district missing from a document is not a verified negative |
| S35 Kerala 2018 flood dataset | Blocked (T119): origin unverified, monthly or annual flood yes/no flags, no certified labels |
| S34 KSDMA dam reports (2,296 archive dates, 20 Jun 2020-4 Nov 2026) | Scanned images; T118 bulk OCR not approved (D102); no datum; mixed units. Archive dates are not verified observations |
| S33 monthly dam statistics | Blocked (T115); pages return error content. Monthly values are EDA-only and never become daily labels |
| S32 dates 15 Aug 2024-15 Jul 2026 | 700 empty reports: no observations to label |
| S32 early rows (26 Oct 2023 feet-for-metres, 15 Nov 2023 percentage x100) | Quarantined by the adapter, not rescaled |
| Landslide labels (S37) | Blocked (T123/T124): no inventory points were obtained, so the survey footprint (which areas were mapped) is unknown and no negatives exist. The atlas gives year counts only (for example 5,191 for 2018), with no per-event date. Absence from an inventory is not a negative |
| Kerala ward or taluk geometry (S40) | None verified. T030 is Karnataka-only (GBA wards); Karnataka ward geometry is never reused for Kerala. No S40 Kerala `verified_by` |
| Kerala institutional shelters and flood impact labels (S43) | None verified. T085 found no official shelter dataset even for Karnataka; no Kerala source exists in `configs/sources`. No shelter coordinates are invented |

The one Kerala flood geometry source in use is S36 district names (published
names, no crosswalk); S17 geoBoundaries remains disabled until a Kerala filter
and boundary version are tested.

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

The 16 S32 dam IDs are now registered (T129, `configs/states/kl/dams.yaml`).
A vertical datum is verified for four KSEB reservoirs only (T267, below). T118 must extend the registry from parsed real
evidence, retaining the original name, operator, units and cited mapping. In S34,
KSEB Kuttiyadi and irrigation Kuttiyadi are different dams: a name-only join is
invalid. Do not assume a latitude, elevation datum or alias match from the name.

### Vertical datum (T267, D103)

The daily reports name no datum. KSEB's operation and maintenance manuals
(S32 evidence e81-e98, fetched 8 Nov 2026) were read for each dam's own
statement. A dam counts as datum-known only when its manual names the
reference; a bare elevation such as "+707.75 m" or "(El.) +811.68 m" does not.

| Reservoir (manual) | Evidence | Statement | Datum |
|---|---|---|---|
| Idukki, Cheruthoni, Kulamavu (O&M-09, O&M-24) | e81 p223; e82 p35 | levelling from Survey of India benchmarks above mean sea level | known: MSL |
| Sengulam (O&M-20) | e83 p30 | FRL +847.65 m above MSL | known: MSL |
| Kakki and Anathode (O&M-02) | e96 p33 | FRL + 981.46 m above MSL | known: MSL |
| Pamba (O&M-03) | e97 p29 | FRL +981.46 m above MSL | known: MSL |
| Ponmudi, Lower Periyar, Kundala, Madupetty, Poringalkuthu, Kallarkutty, Kuttiyadi, Anayirankal, Erattayar, Kallar, Moozhiyar, Sholayar, Idamalayar | e84-e95, e98 | elevations with no named datum | unknown |

Four reservoirs with a known datum are below the T130 gate of eight dams, so
the datum part of the gate is **not met**. A datum for the other dams needs an
official statement (for example a KSEB or CWC document, or a reply from KSEB's
Dam Safety Organisation); it is never assumed from the elevation numbers.

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
current status require their own official evidence; T129 found none. No synthetic
locations, raster-to-ward labels or claims of safe routing are permitted.

Keep S34/S36 restricted raw PDFs local under the existing project policy. Source
reports document restrictions; this audit does not grant permission to redistribute
the raw documents or certify every possible derived publication. Public outputs
still require the existing H11 review. S32's recorded attribution/share-alike
terms must follow any permitted derived publication.

## Completion boundary and next task

T226 acceptance: `python -m pytest tests/test_kl_data.py -q`, plus this evidence
audit. It proved isolated config and disabled source registration. T114 updates
the isolation checks to permit only its tested S32 adapter. The T129
audit (report above) ran on 9 Nov 2026 with T046 and T118 pending (D124). T114/T227 are complete;
the gap census found 700 validated empty reports (see `docs/sources/s32-history.md`).
Next is T118 with the required owner OCR review.
S33/T115-T116 is resolved as a blocked source and tested disabled adapter (D51),
not as verified monthly observations. T130 still needs its actual daily coverage,
datum, split and full-T129 dependency checks; no data gate has been waived.
