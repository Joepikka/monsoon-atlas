# Kerala release gate (T144)

Prepared 9 Nov 2026 on branch `p1/gate-core`. `tests/test_kl_release.py` checks every
table below against the configs, the model registry, the T142 replay file and git, so this
page cannot drift from the evidence without a failing test.

**Result: Kerala config passes the shared checks; every Kerala item has measured or blocked
evidence; all four Kerala models (M07 to M10) are blocked, none is research-only. Nothing here
approves a public release:** that waits for the owner's H11 review (D129, [ka.md](ka.md),
[h11-ka.md](h11-ka.md)). The Karnataka product is reused as is and its gate
([ka-v1.md](ka-v1.md)) still passes.

Nothing on this page claims data or a model that does not exist. A blocked source stays
disabled and raises `SourceUnavailable`; it never returns synthetic rows.

## Sources

4 of 19 Kerala sources enabled in `configs/states/kl.yaml`; 7 have outcome `blocked`; 8 are
`available` in discovery but still disabled for Kerala because no Kerala adapter or config run
exists. Each row has a discovery record that passes `atlas.ingest.discovery.check`, a stored
evidence manifest and a source page.

| Source | Name | Outcome | Enabled | Licence | Evidence | Retry condition (short) |
|---|---|---|---|---|---|---|
| S01 | Open-Meteo weather forecast | available | no | open | [s01](../sources/s01.md) | Run a Kerala point config and adapter test; not needed for the descriptive Kerala views. |
| S02 | Open-Meteo historical weather / ERA5 | available | no | open | [s02](../sources/s02.md) | Run a Kerala point config and adapter test; S08 covers historical rain. |
| S06 | Open-Meteo climate projections | available | yes | open | [s06](../sources/s06.md) |  |
| S08 | IMD Pune gridded rainfall | available | yes | restricted | [s08](../sources/s08.md) |  |
| S09 | NDMA Sachet CAP alerts | available | no | open | [s09](../sources/s09.md) | Add a Kerala region filter and adapter test. |
| S15 | OpenFreeMap basemap | available | no | open | [s15](../sources/s15.md) | Kerala map view config and attribution check. |
| S16 | WorldPop India population | available | no | open | [s16](../sources/s16.md) | Kerala tile selection and adapter test (exposure used Karnataka cells, D128). |
| S17 | geoBoundaries administrative boundaries | available | no | open | [s17](../sources/s17.md) | Kerala district extract and crosswalk test. |
| S26 | aisstream ships | blocked | no | unverified | [s26](../sources/s26.md) | Owner creates an aisstream key (H12) and the sign-in terms allow reuse; then T111. |
| S32 | KSEB daily water level | available | yes | open | [s32](../sources/s32.md) |  |
| S33 | KSEB monthly dam statistics | blocked | no | unverified | [s33](../sources/s33.md) | KSEB restores its statistics pages or supplies a linked monthly file with dates, units, datum and licence (T115). |
| S34 | KSDMA dam level reports | available | no | restricted | [s34](../sources/s34.md) | Owner approves T118 bulk OCR, or KSDMA or KSEB supplies the daily tables as spreadsheets with a licence. |
| S35 | Kerala 2018 flood dataset | blocked | no | unverified | [s35](../sources/s35.md) | Owner signs in to Kaggle (H10) and the dataset has dated rows and a stated licence (T119). |
| S36 | KSDMA post-disaster assessment | available | yes | restricted | [s36](../sources/s36.md) |  |
| S37 | 2018 landslide inventory / ISRO Atlas | blocked | no | restricted | [s37](../sources/s37.md) | NRSC links a downloadable inventory with terms, or the owner obtains it (T123). |
| S40 | Kerala ward / taluk polygons and crosswalks | available | no | open | [s40](../sources/s40.md) | Separate Kerala boundary discovery; Karnataka results do not verify Kerala. |
| S41 | Permitted news RSS sources | blocked | no | restricted | [s41](../sources/s41.md) | Owner obtains written publisher permission for headline, link and timestamp storage (T125). |
| S42 | Sentinel-1 / NDVI quantitative imagery | blocked | no | open | [s42](../sources/s42.md) | Owner registers a Copernicus Data Space account (proposed H15); then T127. |
| S43 | Kerala official shelters and flood impact labels | blocked | no | unverified | [s43](../sources/s43.md) | Dated official shelter or flood-impact records for Kerala, then re-run T085. |

## Models

| Model | Name | Status | Blocked by | Evidence |
|---|---|---|---|---|
| M07 | Kerala seven-day dam forecast | blocked | S34 | [report](../../reports/models/m07.md), [data gate](../../reports/models/m07-data-gate.json), [registry](../../models/registry/m07.json) |
| M08 | Kerala district flood occurrence | blocked | S35 | [report](../../reports/models/m08.md), [data gate](../../reports/models/m08-data-gate.json), [registry](../../models/registry/m08.json) |
| M09 | Kerala landslide susceptibility | blocked | S37, S42 | [report](../../reports/models/m09.md), [data gate](../../reports/models/m09-data-gate.json), [registry](../../models/registry/m09.json) |
| M10 | Rain-to-price effect study | blocked | S22, S23 | [report](../../reports/models/m10.md), [data gate](../../reports/models/m10-data-gate.json), [registry](../../models/registry/m10.json) |

Why each is blocked (from the registry records): M07 has a known vertical datum for 4 of the 8
dams the gate needs and S32 history is sampled dates only; M08 has 2018 district totals but no
audited earlier positives or negatives; M09 has state-level counts only, with no landslide
point or date; M10 has zero price rows (S23 is a one-day snapshot). Each registry record has
no baseline, candidate, score, weights or predictions (all `null`, 0 rows). The UI shows the
words "blocked" and "research-only" beside these items (labels in [kl-ml.json](kl-ml.json)); it
shows no number for them.

No Kerala model is research-only. The only research-only item the Kerala product shares with
Karnataka is Ask (C3, D101). C1 (the Kerala dam model) is blocked (D104).

## Layers

Kerala sections of the product, reusing the Karnataka map, source badges and accuracy page.
"Built, not mounted pending H11" means the component and its tests exist, but no public
snapshot carries it (D127, D128).

| Section | Layer | Depends on | Status | Evidence |
|---|---|---|---|---|
| Dams | Current daily dam levels | S32 | measured | [s32](../sources/s32.md), [labels](../labels/kerala.md) |
| Dams | Dam level outlook | M07, S34 | blocked | [m07](../../reports/models/m07.md) |
| Flood | 2018 descriptive replay | S08, S36 | built, not mounted pending H11 | D127, `web/src/components/Replay.tsx` |
| Flood | District flood occurrence | M08, S35 | blocked | [m08](../../reports/models/m08.md) |
| Flood | Exposure and route comparison | S16, S18, S43 | blocked | D128, `web/src/components/RouteComparison.tsx` |
| Landslide | Landslide susceptibility | M09, S37, S42 | blocked | [m09](../../reports/models/m09.md) |
| Climate | Rainfall history and projections | S06, S08 | measured | `reports/eda/07_climate/summary.json` |
| Prices | Rain-to-price event study | M10, S22, S23 | blocked | [m10](../../reports/models/m10.md) |

Exposure and routing code is tested on hand-built graphs only: with no road network (S18
blocked) it returns "unavailable", and with no official shelter record (S43 blocked) shelter
routing is disabled. Every route result carries "not a safe route".

## 2018 chronology audit

Source: `reports/eda/05_kl_flood2018/replay2018.json` (T142; local only since 11 Nov 2026, so
the audit below is re-checked only where that file exists). 157 records, window 1 Jun to
30 Sep 2018, **0 forecast vintages**. A record is `as_known` only when the publisher's own dated
issue is on or before 30 Sep 2018 and it shows only from that date; everything else is
`reconstructed` and never shown as known at the time (D127).

| Source | Kind | Mode | Known from | Records | Basis |
|---|---|---|---|---|---|
| S36 | flooded_area_ha | as_known | 2018-08-07 | 7 | Memorandum 1, submitted 7 Aug 2018 |
| S36 | human_fatalities | as_known | 2018-08-07 | 14 | Memorandum 1, submitted 7 Aug 2018 |
| S36 | human_fatalities | as_known | 2018-09-13 | 14 | Memorandum 2, submitted 13 Sep 2018 |
| S08 | daily_rain | reconstructed | none | 122 | Gridded analysis, 2018 file fetched 5 Nov 2026 |

35 records are `as_known`, 122 are `reconstructed`. Caveats (D127): the as-known dates are the
memoranda submission dates, but the web copies sit under a 2019 upload path, so "as known"
means issued by the state then, not online then. A fetch date is not a publication date, so
every S08 value is reconstructed. S32 holds no 2018 dam row (its 15 Aug 2018 report is empty).
No 2018 forecast vintage is held or imitated, so there is no 2018 forecast claim of any kind,
and no model trained on later data is shown as a 2018 forecast (none exists).

## Licence audit

Sources whose licence forbids redistribution (status `restricted`) keep raw files local:
`data/raw` is not tracked, and git holds only each source's `manifest.json` under
`tests/fixtures/sNN/`. Only derived outputs are published.

| Source | Licence status | Committed raw files | Published form |
|---|---|---|---|
| S08 | restricted | manifest only | Derived indices and model results with the Pai et al. (2014) citation; no raw or area-averaged rainfall values without permission |
| S34 | restricted | manifest only | Derived model results only, credited to KSDMA, KSEB and the Irrigation Department |
| S36 | restricted | manifest only | District-level facts with document and page citations, credited to KSDMA |
| S37 | restricted | manifest only | None; the state-level counts stay in the evidence notes |
| S41 | restricted | manifest only | None; no publisher permission is on record |

Licence finding, settled at H11: the T142 files `replay2018.json`, `monthly_2018.csv` and
`s08_kerala_annual.csv` under `reports/eda/` hold S08 box-mean rain values. The S08 licence does
not allow publishing area-averaged rainfall without permission, so on 11 Nov 2026 the owner
decided (H11 item 9, D166) to remove them from the repository: they were removed from tracking
that day, are listed in `.gitignore` and stay on local disk only. Old copies remain in git
history, which is not rewritten. The replay keeps derived departures only. This page therefore
quotes only a derived departure, not rainfall values. The notebooks `05_kl_flood2018` and
`07_climate` regenerate the files locally from `data/raw`; the tests that read them skip when
they are absent.

Second step, the same day (D167): the tracked outputs of notebooks `02_ka_rain`, `05_kl_flood2018`
and `07_climate` hold no S08 rain in mm either. Their summaries carry the percent departure
(2018), the driest and wettest years as a percent of the 1981 to 2010 mean, and the ratio of the
grid to the gauge total. `district_year_comparison.csv` no longer has `grid_mm` and `bias_mm`. The
four charts that plot S08 mm (`gauge_vs_grid.png`, `bias_by_district.png`,
`rain_2018_vs_climatology.png`, `s08_annual_rain.png`) are untracked and stay local. The S29
gauge totals and the S06 model values are other sources and stay.

## Case study draft: Kerala 2018 and dams

Measured results from committed reports only. No future outcome is claimed or implied.

- **Rainfall in 2018 (descriptive).** June to September 2018 box-mean rain was 30.7% above the
  1981 to 2010 mean for the same months; the 95% bootstrap interval of that mean lies below
  the 2018 value. Source: S08 IMD 0.25 degree grid, Kerala cell box (it includes some Tamil Nadu
  and Karnataka border cells, so it is not Kerala's boundary); 144 cells, 0 missing cell-days
  ([summary](../../reports/eda/05_kl_flood2018/summary.json)). It describes what happened. It
  is not a flood model.
- **Climate projections.** Across 7 high-resolution models at two points (Thiruvananthapuram
  and Kozhikode), the projected change in annual rain runs from -11.7% to +25.3% (median
  -1.05%). These are projections; the spread is model spread, not confidence
  ([summary](../../reports/eda/07_climate/summary.json)).
- **Dams.** A known vertical datum exists for 4 of 16 registered dams; the gate needs 8. A census
  of 15 Aug 2024 to 15 Jul 2026 found 700 of 700 report dates empty. M07 is blocked: no model,
  no baseline, no score ([report](../../reports/models/m07.md), [case study](../../reports/models/m07-case-study.md)).
- **Floods and landslides.** M08 and M09 are blocked for lack of labelled history. Exposure and
  route code exist but have no road, shelter or hazard-polygon input (D128).
- **Prices.** The rain-to-price study is not computable: 0 price rows, 0 markets, 0 rain
  events. It is labelled "association only" and draws no chart (D127).

## Malayalam labels

`docs/releases/kl-ml.json` holds the Malayalam text for the Kerala layer titles and the safety
phrases "Scheduled, not live", "not a safe route", "research-only" and "blocked". The web app
has no translation mechanism yet, so the file is a data contract, not mounted. **The strings
are machine-drafted and need native review before release (owner H11).** Until then the
English labels are authoritative.

## Frozen shared interfaces

Unchanged from [ka-v1.md](ka-v1.md): the SHA-256 hashes in that page's frozen-interface table
still match the files (D122). `tests/test_kl_release.py` re-checks them, so a change to a
frozen file needs a decision entry and a hash update in ka-v1.md first.

## Owner-gated items

| Item | What the owner does | Blocks |
|---|---|---|
| H11 | Reviews and approves any public release and the Malayalam strings. The S08 licence finding was answered on 11 Nov 2026 (D166): derived outputs only, files untracked | Every public Kerala layer |
| H12 | Creates an aisstream key | S26, T111 |
| H15 | Registers a Copernicus Data Space account (proposed in T127) | S42, M09 |
| T118 | Approves bulk OCR of the S34 dam-level reports | S34, M07 |
| S18 | Downloads the Geofabrik southern-zone extract, or an Overpass source task passes | Roads, route comparison |
| S41 | Obtains written publisher permission | News layer |
