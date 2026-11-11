# Delhi release gate (T166)

Prepared 10 Nov 2026 on branch `p1/gate-core`. `tests/test_dl_release.py` checks every table
below against the configs, the model registry, git and the Karnataka and Kerala gates, so this
page cannot drift from the evidence without a failing test.

**Result: Delhi config passes the shared checks; every Delhi item has measured or blocked
evidence; all four Delhi models (M12 to M15) are blocked, none is research-only. Nothing is
released:** the data is not there yet, and any public release waits for the owner's H11 review
(D143, [ka.md](ka.md), [h11-ka.md](h11-ka.md)). The Karnataka and Kerala products are reused as
is and their gates ([ka-v1.md](ka-v1.md), [kl.md](kl.md)) still pass.

Nothing on this page claims data or a model that does not exist. A blocked source stays
disabled and raises `SourceUnavailable`; it never returns synthetic rows.

## Sources

0 of 8 Delhi sources enabled in `configs/states/dl.yaml`; 2 have outcome `blocked`; 6 are
`available` in discovery but still disabled for Delhi because no Delhi adapter or config run
exists. Each row has a discovery record that passes `atlas.ingest.discovery.check`, a stored
evidence manifest and a source page.

| Source | Name | Outcome | Enabled | Licence | Evidence | Retry condition (short) |
|---|---|---|---|---|---|---|
| S01 | Open-Meteo weather forecast | available | no | open | [s01](../sources/s01.md) | Run a Delhi point config and adapter test, then collect issue-time vintages (M15 needs them). |
| S02 | Open-Meteo historical weather / ERA5 | available | no | open | [s02](../sources/s02.md) | Run a Delhi point config and adapter test. |
| S09 | NDMA Sachet CAP alerts | available | no | open | [s09](../sources/s09.md) | Add a Delhi region filter and adapter test. |
| S15 | OpenFreeMap basemap | available | no | open | [s15](../sources/s15.md) | Delhi map view config and attribution check. |
| S16 | WorldPop India population | available | no | open | [s16](../sources/s16.md) | Delhi tile selection and adapter test. |
| S17 | geoBoundaries administrative boundaries | available | no | open | [s17](../sources/s17.md) | Delhi boundary extract and crosswalk test. |
| S24 | CPCB station pollution via data.gov.in | blocked | no | unverified | [s24](../sources/s24.md) | Read the data.gov.in resource page in a browser that can read page content (resource ID, licence, fields, units, averaging interval), then re-run T146; no new key is needed. |
| S38 | Delhi Open Transit Data | blocked | no | restricted | [s38](../sources/s38.md) | Owner completes H04 (key, Terms, static GTFS); then re-run T148. |

S04 (CAMS air-quality estimates) is not a Delhi source: it is `available` and enabled for
Karnataka only, and `dl.yaml` lists no S04 entry (D141, D142).

## Models

| Model | Name | Status | Blocked by | Evidence |
|---|---|---|---|---|
| M12 | Delhi bus arrival and delay | blocked | S38 | [report](../../reports/models/m12.md), [data gate](../../reports/models/m12-data-gate.json), [registry](../../models/registry/m12.json) |
| M13 | Delhi bus bunching anomaly | blocked | S38 | [report](../../reports/models/m13.md), [data gate](../../reports/models/m13-data-gate.json), [registry](../../models/registry/m13.json) |
| M14 | Delhi station pollution / AQI forecast | blocked | S24 | [report](../../reports/models/m14.md), [data gate](../../reports/models/m14-data-gate.json), [registry](../../models/registry/m14.json) |
| M15 | Heat exposure and heatwave outlook | blocked | S01, S02, S18 | [report](../../reports/models/m15.md), [data gate](../../reports/models/m15-data-gate.json), [registry](../../models/registry/m15.json) |

Why each is blocked (from the registry records): M12 and M13 take their labels from S38, which
is blocked on owner step H04, so there are 0 vehicle positions, 0 service days and no scheduled
arrival or headway; M14 takes its labels from S24, which is blocked, so there are 0 station rows
and no PM2.5 label; M15 has no Delhi source enabled, S01 keeps no issue-time vintages, S02 is
reanalysis and S18 is blocked by robots.txt. Each registry record has no baseline, candidate,
score, weights or predictions (all `null`, 0 rows). The UI shows the words "blocked" and
"planned, not started" beside these items; it shows no number for them.

No Delhi model is research-only. The only research-only item the Delhi product shares with the
other states is Ask (C3, D101).

## Label windows

The preregistered windows are planned only. They assume source approval and the readiness gate
on schedule. Approval is a calendar delay, not a development failure: if it is late, the whole
manifest shifts together and no observation earlier than collection is invented. No window has
started, no split manifest is written and no label exists (D137, D139).

| Model | Collect from | Train | Tune | Calibrate | Locked test | State |
|---|---|---|---|---|---|---|
| M12 | 2028-01-17 | 2028-01-17 to 2028-03-28 | 2028-03-29 to 2028-04-12 | 2028-04-13 to 2028-04-26 | 2028-04-27 to 2028-05-26 | planned, not started |
| M13 | 2028-01-17 | 2028-01-17 to 2028-03-28 | 2028-03-29 to 2028-04-12 | 2028-04-13 to 2028-04-26 | 2028-04-27 to 2028-05-26 | planned, not started |
| M14 | 2028-01-17 | 2028-01-17 to 2028-03-28 | 2028-03-29 to 2028-04-12 | 2028-04-13 to 2028-04-26 | 2028-04-27 to 2028-05-26 | planned, not started |
| M15 | 2028-01-17 | 2028-01-17 to 2028-03-28 | 2028-03-29 to 2028-04-12 | 2028-04-13 to 2028-04-26 | 2028-04-27 to 2028-05-26 | planned, not started |

The window covers January to May only. A short window like this does not show year-round skill.

## Layers

Delhi sections of the product, reusing the shared map, source badges and accuracy page. "Built,
not mounted pending H11" means the component and its tests exist, but no public snapshot carries
it (D142). "Not configured" means the source is available but `dl.yaml` does not list it.

| Section | Layer | Depends on | Status | Evidence |
|---|---|---|---|---|
| Buses | Scheduled and live bus positions | S38 | blocked | [s38](../sources/s38.md), [studies](../studies/delhi.md) |
| Buses | ETA p10/p50/p90 | M12, S38 | blocked | [m12](../../reports/models/m12.md) |
| Buses | Bunching flag | M13, S38 | blocked | [m13](../../reports/models/m13.md) |
| Buses | Transit component | none | built, not mounted pending H11 | D142, `web/src/components/Transit.tsx` |
| Air | Station air quality (observed) | S24 | blocked | [s24](../sources/s24.md) |
| Air | CAMS gridded model estimate | S04 | not configured | D141, D142 |
| Air | Station and model comparison, route exposure | S24, S04 | blocked | D142, `src/atlas/analysis/route_exposure.py` |
| Air | Station PM2.5 outlook | M14, S24 | blocked | [m14](../../reports/models/m14.md) |
| Air | Air quality component | none | built, not mounted pending H11 | D142, `web/src/components/AirQuality.tsx` |
| Heat | Heat exposure and heatwave outlook | M15, S01, S02, S18 | blocked | [m15](../../reports/models/m15.md) |

The 120 s rule (a bus position aged 120 s or more is never live and never animates as current)
and the route exposure rules (a time-weighted ambient concentration, never an inhaled dose;
mixed units, averaging, provenance or incompatible timestamps are refused) are tested on
hand-built inputs only. Station observations and the gridded model stay separate layers.

## Published and not published

The plan's fallback for insufficient labels is to publish scheduled transit, observed air quality
and blocked cards. Only the blocked cards can be published: no static GTFS and no station data
were read, so the first two do not exist either.

| Item | Status | Why |
|---|---|---|
| Scheduled bus transit | not published | No static GTFS was read (S38 blocked on H04) |
| Live bus positions | not published | Live mode is unavailable (`TRANSIT_LIVE`, D138) |
| Observed air quality | not published | No station row was read (S24 blocked) |
| CAMS estimate for Delhi | not published | S04 is not configured for Delhi |
| Blocked model cards (M12 to M15) | published | The four reports and status records above |
| ETA accuracy | none | No test labels exist and the locked test window has not started |
| AQI accuracy | none | No test labels exist and the locked test window has not started |
| Portfolio export of the frozen study and metrics | nothing exported | No study manifest and no metric exist |

## Licence audit

Sources whose licence forbids redistribution (status `restricted`) or is unverified keep raw
files local: `data/raw` is not tracked, and git holds only each source's `manifest.json` under
`tests/fixtures/sNN/`. Only derived outputs are published.

| Source | Licence status | Committed raw files | Published form |
|---|---|---|---|
| S24 | unverified | manifest only | None; the licence text was unreadable, so redistribution stays off |
| S38 | restricted | manifest only | None; no feed was read, and the Terms forbid tracking or profiling individuals |

## Cross-state regression

| Check | Result | Test |
|---|---|---|
| Karnataka gate | 23 of 33 sources enabled; M05 approved; frozen interfaces unchanged | `tests/test_ka_v1.py`, `tests/test_ka_release.py` |
| Kerala gate | 4 of 19 Kerala sources enabled; M07 to M10 blocked | `tests/test_kl_release.py` |
| Delhi isolation | `dl.yaml` keeps its own raw, clean and publish roots; S28 and S32 are not Delhi sources | `tests/test_dl_study.py` |
| Delhi poll and collection | Live mode unavailable; readiness gate failed (not run) | `tests/test_dl_poll.py`, `tests/test_dl_collection.py` |

All three state pages ([ka-v1.md](ka-v1.md), [kl.md](kl.md), this page) are tested against their
configs. Delhi added no change to a frozen file.

## No-card audit

Every Delhi discovery record has `no_card: true`: S01, S02, S09, S15, S16, S17, S24 and S38 ask
for no card on any captured page (S24 and S38 need a free key or registration, owner steps).
`python scripts/audit_dependencies.py --policy` reports 0 problems: free sources only, no secret
value in configs, no paid service referenced.

## Frozen shared interfaces

Unchanged from [ka-v1.md](ka-v1.md): the SHA-256 hashes in that page's frozen-interface table
still match the files (D122). `tests/test_dl_release.py` re-checks them, so a change to a frozen
file needs a decision entry and a hash update in ka-v1.md first.

## Owner-gated items

| Item | What the owner does | Blocks |
|---|---|---|
| H04 | Completes the Delhi Open Transit Data registration (key, Terms, static GTFS) | S38, M12, M13, Delhi buses |
| S24 browser read | Opens the data.gov.in resource page in a browser that can read page content and records the resource ID and licence (no new key needed) | S24, M14, observed air quality |
| H05, H06 | Cloudflare token and Hugging Face token | Any hosted Worker, snapshot or archive |
| H11 | Reviews and approves any public release (the Karnataka sheet was answered on 11 Nov 2026, D166; Delhi layers are not yet reviewed) | Every public Delhi layer |

M15's retry is not an owner step: enable S01 and S02 for Delhi and collect S01 forecast vintages
over the prospective window. Nothing here approves a public release.
