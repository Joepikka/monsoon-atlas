# Case study: M07 Kerala seven-day dam forecast (core C1 fallback)

Status: blocked at the data gate. No model was trained or evaluated, so this
case study reports the data work and why it stops. Numbers come from
[the Kerala label audit](../../docs/labels/kerala.md), the S32 and S34 source
reports, the S32 gap census and decisions D17 and D44-D51. The owner reviews
it under H14.

## Problem and intended use

Forecast daily water level for Kerala dams seven days ahead, as the C1
fallback chosen at GATE-CORE (D17) after Karnataka's KWRIS history proved
unavailable (S28 blocked). It would support reservoir context on the map,
never dam-operation or flood-release decisions.

## Data and label provenance

- S32 KSEB daily reports: 16 dams at 07:00 IST; the first populated report
  sampled is 26 Oct 2023. The T227 census of 15 Aug 2024-15 Jul 2026 found
  700 of 700 dates returned validated empty reports. No vertical datum is
  stated.
- S34 KSDMA archive: 2,296 valid dates from 20 Jun 2020 to 4 Nov 2026, but
  the tables are scanned images. The T228 OCR sample shows six of eight cells
  disagreeing between two readings; owner review is pending and no value is
  used.
- S33 KSEB monthly statistics: blocked; monthly values could never be daily
  labels (D51).

## Target definition

Planned: dam water level in metres seven days after issue, from validated
daily observations with a known datum. Missing days stay missing.

## Time split

Not written. The plan's gate requires at least three years of daily
observations across at least eight dams and a known vertical datum before
dated splits are drawn (T130). Neither the archive span nor the census
passes it.

## Baselines

Planned persistence and seasonal baselines; none computed without labels.

## Hypothesis and candidate

None fitted. Fitting on 2023-2024 S32 rows alone would leave too little
history for an honest seasonal test.

## Leakage audit

The audit found the label gap before any feature was built. Archive dates
were not treated as observations, and monthly statistics were not converted
into daily values.

## Metrics with paired confidence interval

None. No baseline or candidate has scores, and none is published.

## Failure slices

The whole period from 15 Aug 2024 to 15 Jul 2026 has empty official daily
reports, and earlier history depends on unreviewed OCR.

## Computational cost

The S32 census fetched 700 report pages (91.63 MiB) at Rs 0. No training ran.

## Deployment decision

Not deployable. M07 stays unavailable on the map until T118 OCR review,
datum verification and the T130 gate pass.

## Monitoring and retraining

Retry when the owner reviews the S34 OCR sample, a full T118 extraction
passes its checks, or KSEB publishes the missing daily history with a datum.

## Reproducibility

Per-date hashes and counts of the S32 census are committed; raw pages stay in
the ignored `data/raw` store. The OCR packet pins its toolchain (D49/D50).

## What changed after review

D44 split the Kerala bootstrap from the full label audit, D46 made the gap
census its own task and D51 moved monthly-source discovery forward. Each
kept the gate intact instead of waiving it.

## One positive result, one negative lesson

- Positive: a date-by-date census proved the 700-day gap before any training,
  so no forecast was built on a broken history.
- Negative: an archive with 2,296 dates looked sufficient but holds scanned
  tables; date counts are not labels until values are extracted and reviewed.
