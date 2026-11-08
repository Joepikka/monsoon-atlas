# H11 release review: Karnataka MVP decision sheet

Prepared 8 Nov 2026 for the owner. Each item is one decision. Evidence is
linked; nothing here is approved until the owner answers. The release
checklist is [ka.md](ka.md); it stays "not releasable" while any item is open.

Reply with the item number and your answer, for example `1 approve`,
`3 option b`.

## 1. Publish the model accuracy table

- **Decision:** approve publishing the accuracy table (M07, M05, M06) on the
  `?page=accuracy` page.
- **Evidence:** [ka.md](ka.md) accuracy rows; M05 is a hindcast champion
  (D43); M07 and M06 show "Unavailable", never 0 (D94).
- **Recommended:** approve. The table states the hindcast label and shows
  no rainfall values.

## 2. Count a research-only Ask (C3) for the MVP gate

- **Decision:** does C3, recorded as research-only (D101), meet T046 extra
  check 2 ("C3 passes the T181 thresholds")?
- **Evidence:** [reports/rag.md](../../reports/rag.md) (evidence support
  0.86 against 0.95); [docs/ask.md](../ask.md); A3 says an honest negative
  result counts as a finished core model.
- **Options:** (a) yes, publish Ask labelled research-only; (b) no, keep the
  gate failing until a new evaluation passes.
- **Recommended:** (a). The page already shows the research-only note.

## 3. Use IMD rainfall (S08) only through derived outputs

- **Decision:** may the site and repository publish values derived from IMD
  gridded rainfall (district SPI, M05 forecasts and accuracy numbers)?
- **Evidence:** the IMD site says its data "should not be reproduced
  anywhere without prior permission" and states no licence
  ([configs/sources/s08.yaml](../../configs/sources/s08.yaml)); the M05 card
  allows only derived SPI and model outputs, never rainfall values.
- **Options:** (a) publish derived outputs only, citing Pai et al. (2014);
  (b) also ask IMD for written permission before publishing; (c) keep all
  M05 outputs off public pages.
- **Recommended:** (b) if you want certainty, otherwise (a). This is a legal
  judgement only you can make.

## 4. Attribution for the open sources shown on the map

- **Decision:** confirm the credits are enough for the open sources.
- **Evidence:** Open-Meteo data are CC BY 4.0 and the free API is for
  non-commercial use (S01, S02); OpenFreeMap and OpenStreetMap credits must
  show on the map (S15), which the map's compact attribution control does;
  geoBoundaries IND ADM2 is ODbL and ADM1 is CC BY 2.5 IN (S17); Sachet CAP
  is public domain (S09). The site credits each source by name
  ([web/src/report.ts](../../web/src/report.ts)). WorldPop (S16) is not shown
  on the map yet.
- **Recommended:** approve, provided the project stays non-commercial.

## 5. Keep official alerts, model outputs and inferred items separate

- **Decision:** confirm the "not an emergency service" presentation.
- **Evidence:** footer and Place Lens say "Not an emergency service"; the
  header links to official Sachet warnings; Ask points to official warnings.
- **Recommended:** approve.

## 6. Refit M05 now that IMD 2025 is published

- **Decision:** refit M05 as a new version (v2) with 2025 data, or keep v1.
- **Evidence:** [m05-2025.md](../../reports/models/m05-2025.md) (v1 holds on
  2025: MAE 0.625 against 0.744); the card's retraining rule says refit when a
  new IMD year is published; a refit leaves no unused year to test v2.
- **Options:** (a) keep v1 until the 2026 file is published, then refit and
  test on 2026; (b) refit now and label v2 untested.
- **Recommended:** (a).

## Still blocking the gate after H11

These do not depend on this review: C1 has no model until the S34 OCR
review and T130 pass; T045 needs the H05/H06 tokens; T041 needs S18.
