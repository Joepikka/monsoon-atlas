# Karnataka v1 handoff gate (T110)

Prepared 9 Nov 2026 on branch `p1/gate-core`. `tests/test_ka_v1.py` checks every
table below against the configs, the model registry and the frozen files, so
this page cannot drift from the evidence without a failing test.

**Result: shared platform ready; every KA v1 item has measured or blocked
evidence; Kerala work can begin.** This opens Kerala work only. It does not
approve a public release: T046 (the Karnataka MVP release) still waits for the
owner's H11 review (D105, [ka.md](ka.md), [h11-ka.md](h11-ka.md)).

Nothing in this page claims data or a model that does not exist. A blocked
source stays disabled and raises `SourceUnavailable`; it never returns
synthetic rows.

## Sources

23 of 33 sources enabled; 10 blocked and disabled (outcome `blocked`, retry
condition recorded in each `configs/sources/sNN.yaml`). Every row has a
discovery record that passes the discovery contract
(`atlas.ingest.discovery.check`), a manifest of stored evidence, and a source
page. Enabled rows also have an adapter, a schema and a test file. S28 has no
adapter by design: T008 ended at discovery.

| Source | Name | Outcome | Enabled | Licence | Evidence | Retry condition (short) |
|---|---|---|---|---|---|---|
| S01 | Open-Meteo weather forecast | available | yes | open | [s01](../sources/s01.md) |  |
| S02 | Open-Meteo historical weather / ERA5 | available | yes | open | [s02](../sources/s02.md) |  |
| S03 | Open-Meteo GloFAS river discharge | available | yes | open | [s03](../sources/s03.md) |  |
| S04 | Open-Meteo CAMS air-quality estimates | available | yes | open | [s04](../sources/s04.md) |  |
| S05 | Open-Meteo ensemble | available | yes | open | [s05](../sources/s05.md) |  |
| S06 | Open-Meteo climate projections | available | yes | open | [s06](../sources/s06.md) |  |
| S07 | NASA POWER daily point | available | yes | open | [s07](../sources/s07.md) |  |
| S08 | IMD Pune gridded rainfall 1901-2024 | available | yes | restricted | [s08](../sources/s08.md) |  |
| S09 | NDMA Sachet CAP alerts | available | yes | open | [s09](../sources/s09.md) |  |
| S10 | adsb.lol live aircraft | available | yes | open | [s10](../sources/s10.md) |  |
| S11 | OpenSky flight fallback | blocked | no | unverified | [s11](../sources/s11.md) | Owner reads OpenSky terms of use and records a decision (optional; S10 covers live aircraft). |
| S12 | CelesTrak orbit elements | available | yes | restricted | [s12](../sources/s12.md) |  |
| S13 | NASA GIBS satellite imagery | available | yes | open | [s13](../sources/s13.md) |  |
| S14 | AWS Terrarium terrain | available | yes | open | [s14](../sources/s14.md) |  |
| S15 | OpenFreeMap basemap | available | yes | open | [s15](../sources/s15.md) |  |
| S16 | WorldPop India population | available | yes | open | [s16](../sources/s16.md) |  |
| S17 | geoBoundaries administrative boundaries | available | yes | open | [s17](../sources/s17.md) |  |
| S18 | Geofabrik OSM extracts | blocked | no | open | [s18](../sources/s18.md) | Owner downloads the Geofabrik southern-zone .pbf in a browser, or Geofabrik allows scripted downloads, or an Overpass source task passes. |
| S19 | Google Open Buildings | available | yes | open | [s19](../sources/s19.md) |  |
| S20 | USGS earthquakes | available | yes | restricted | [s20](../sources/s20.md) |  |
| S21 | Datameet railway schedules | available | yes | open | [s21](../sources/s21.md) |  |
| S22 | India Data Portal Agmarknet / existing price data | blocked | no | unverified | [s22](../sources/s22.md) | Working browser render of the Agmarknet page, or owner notes the download button, format and licence. |
| S23 | data.gov.in mandi prices | blocked | no | open | [s23](../sources/s23.md) | Publisher statement of the min/modal/max price denominator for the resource; GODL is already verified. |
| S25 | NASA FIRMS active fires | blocked | no | open | [s25](../sources/s25.md) | Owner gets a FIRMS MAP_KEY (H09), or a key-free FIRMS download link is recorded with its terms. |
| S27 | KSNDMC gauges | blocked | no | unverified | [s27](../sources/s27.md) | KSNDMC serves gauge data over HTTPS with station list, units and terms, or an equivalent open dataset appears. |
| S28 | KWRIS reservoirs and rainfall | blocked | no | restricted | [s28](../sources/s28.md) | KWRIS account (owner step) with API terms allowing research, or ACIWRM sends daily history with units and licence, or the site publishes an export. |
| S29 | OpenCity KSNDMC hobli rainfall 2017-2023 | available | yes | open | [s29](../sources/s29.md) |  |
| S30 | BMTC and Namma Metro static GTFS | available | yes | restricted | [s30](../sources/s30.md) |  |
| S31 | Karnataka RERA projects | blocked | no | restricted | [s31](../sources/s31.md) | Owner asks K-RERA for permission to reproduce the project list and records the reply. |
| S39 | Telegram Bot API | blocked | no | restricted | [s39](../sources/s39.md) | Owner creates the bot and public channel (H08), accepts Telegram terms, stores the token in .env. |
| S40 | Ward / taluk polygons and crosswalks | available | yes | open | [s40](../sources/s40.md) |  |
| S43 | Official shelters and flood impact labels | blocked | no | unverified | [s43](../sources/s43.md) | Dated official ward-level flood records, or BBMP/GBA sites pass TLS, or owner accepts citizen complaints as labels at T222. |
| S44 | District crime statistics | available | yes | open | [s44](../sources/s44.md) |  |

Licence `restricted` on an enabled source (S08, S12, S20, S30) means derived
outputs only, with the owner's H11 review before public display (see the H11
sheet and D109, D110, D115).

## Models

| Model | Name | Status | Blocked by | Evidence |
|---|---|---|---|---|
| M01 | Bengaluru ward flood occurrence | blocked | S43 | [report](../../reports/models/m01.md), [data gate](../../reports/models/m01-data-gate.json), [registry](../../models/registry/m01.json) |
| M02 | Karnataka reservoir level and storage | blocked | S28 | [report](../../reports/models/m02.md), [data gate](../../reports/models/m02-data-gate.json), [registry](../../models/registry/m02.json) |
| M03 | Karnataka reservoir inflow | blocked | S28 | [report](../../reports/models/m03.md), [data gate](../../reports/models/m03-data-gate.json), [registry](../../models/registry/m03.json) |
| M04 | Rain-gauge gap filling | blocked | S27, S29 | [report](../../reports/models/m04.md), [data gate](../../reports/models/m04-data-gate.json), [registry](../../models/registry/m04.json) |
| M05 | Karnataka drought outlook (district SPI-3, hindcast) | approved | none | [report](../../reports/models/m05.md), [card](../../reports/models/m05-card.md), [release v1](../../models/registry/M05/v1.json), [approval](../../models/registry/M05/v1.approval.json) |
| M06 | Kolar tomato price-spike warning | blocked | S22, S23 | [report](../../reports/models/m06.md), [data gate](../../reports/models/m06-data-gate.json), [registry](../../models/registry/m06.json) |

Blocked rows are not failed experiments: each has no baseline, candidate,
score, weights or predictions (all `null`, 0 rows). S29 is available but
annual only (D113), so M04 still has no gauge-day to withhold. M05 is a
hindcast champion (D39, D43): ridge beats persistence with the lower 95%
bootstrap bound above 0 (0.0026). Do not publish its intervals (D42).

Core slots (the accuracy page, [ka.md](ka.md)):

| Slot | Model | Status | Evidence |
|---|---|---|---|
| C1 | Kerala seven-day dam forecast | blocked | data gate T130, owner decides at the end (D103, D104) |
| C2 | Karnataka drought outlook | approved | [m05 report](../../reports/models/m05.md) |
| C3 | Ask (cited question answering) | research-only | [rag report](../../reports/rag.md), D101 |

## Layers

The KA v1 rows of the plan's feature catalogue whose task is in phase P2
(T085 to T110). "Measured" means the enabled sources and the approved model
are present with tests. "Built, not mounted pending H11" means the layer code
and its tests exist, but no public snapshot carries the layer (D116, D117).

| Feature | Layer | Depends on | Status | Evidence |
|---|---|---|---|---|
| F011 | Transit stations and scheduled positions | S30 | built, not mounted pending H11 | D116, [web-layers.md](../web-layers.md), `tests/test_schedule.py` |
| F015 | Fire hotspots | S25 | blocked | [s25](../sources/s25.md), D117 |
| F019 | Public RERA projects | S31 | blocked | [s31](../sources/s31.md), D117 |
| F020 | Building outlines | S19 | built, not mounted pending H11 | D117, `tests/test_context_layers.py` |
| F022 | District crime totals (stretch) | S44 | built, not mounted pending H11 | D114, D117, `tests/test_context_layers.py` |
| F027 | Reservoir levels and inflow forecasts (Karnataka) | M02, M03 | blocked | [m02](../../reports/models/m02.md), [m03](../../reports/models/m03.md) |
| F028 | Ward flood risk | M01 | blocked | [m01](../../reports/models/m01.md) |
| F030 | Taluk drought outlook (district level) | S08, S17, M05 | measured | [m05](../../reports/models/m05.md), [release v1](../../models/registry/M05/v1.json) |
| F060 | Gauge interpolation and gaps study | M04 | blocked | [m04](../../reports/models/m04.md) |

F030 is district level because no taluk polygons exist (D43). F027 also needs
the Kerala dam model (C1), which is blocked separately.

Other KA v1 rows of the catalogue belong to later tasks and are not gated here:
F003 (T142); F018, F038, F039 (T143; F018 and F039 need blocked S18 and S43);
F035 (T034); F037 (T216); F040 (T164); F042, F043, F044 (T145); F046 (T180);
F048 (T182); F049, F050, F052 (T183); F053 (T045); F054, F055, F059 (T217);
F056, F057 (T218); F064 (T219).

## Frozen shared interfaces

These files are the contract Kerala adapters build on. Hashes are SHA-256 of
the file with line endings normalised to LF, at the commit that adds this page.

| File | SHA-256 |
|---|---|
| `src/atlas/contracts.py` | `f6d0dd16ed3a89ac4557ad36fdb2c60aee739e3a51dd98f766d166342c009a8a` |
| `src/atlas/config.py` | `8f6087ad8a6050ea0a1e723556fc4e4e5135674475f3185bdb399cff7ac26171` |
| `src/atlas/ingest/base.py` | `0526cc38e15e7ca0066d839922d1e5235bfbfcc28b9349c56900aa29e5041a0d` |
| `src/atlas/ingest/discovery.py` | `7f090c6a0158c4d263e0ec76b580a4f2e0167933fe80c7eb4902cbf07bfaabaf` |
| `src/atlas/ingest/http.py` | `16b3ffd4c428080f4d44b5dd6c72ddc37dbe2310998679b54e5d1ceed0682992` |
| `src/atlas/ingest/raw_store.py` | `8935b5d4e8e4d56d9c1f471e18cf4cfeb4d89181e580e1a08f5c3203267da401` |
| `src/atlas/data/validate.py` | `3da74ac18234fc1f996dd152dfe61962903112f871eb0e4ae2ff93203656bfd5` |
| `schemas/common.json` | `d9ada01615bd45848e19ce325ce028b1e565f5a242873d6c9900fe85286cd1ec` |

Rule: while Kerala work is in progress, a change to any file above needs a
decision entry in `docs/decisions.md` first, and the hash here must be updated
in the same commit. `tests/test_ka_v1.py` fails when they differ. Adding new
files or new source adapters does not touch the freeze.

## Unresolved history-dependent models

Each waits for history that does not exist. None is faked or inferred.

| Model | Missing history | Retry condition |
|---|---|---|
| M01 | Dated ward-level inundation labels and audited negatives (S43) | Official dated ward records, or BBMP/GBA TLS passes, or the owner accepts citizen complaints as labels at T222; then re-run T085 |
| M02 | Daily reservoir level and storage with units and datum (S28) | KWRIS account or ACIWRM data with units and licence, or a published export; then re-run T008 |
| M03 | Daily reported reservoir inflow with units (S28); never inferred from levels | Same as M02 |
| M04 | Daily gauge rainfall with coordinates (S27; S29 is annual only) | KSNDMC publishes gauge data over HTTPS with station list, units and terms; then re-run T077 |
| M06 | Karnataka price history, price units and publication timing (S22, S23) | S23 price denominator statement, or a working S22 render; then re-run T025 or T023 |

Feeds that only have history from the day they are first stored (S01, S05,
S09, S10, S12) cannot support a trained model until the archive has grown; M05
uses S08 and S17, which have full history.

## Still owner-gated

From `docs/HANDOFF.md` section 8, "Pending human-only steps" (not edited here):

- H11 review before any public deployment: licences (S08 and S34 forbid
  reproduction, so only derived outputs), S12 and S20 display terms, boundary
  map guidance, OpenFreeMap 18+ confirmation, WorldPop undercount label.
- H05 and H06 tokens (deferred by the owner on 6 Nov); T045 needs them.
- H09 FIRMS key (S25), H08 Telegram bot (S39), K-RERA permission (S31), OpenSky
  terms (S11), Geofabrik download (S18), KWRIS request (S28), S23 denominator
  statement.
- H04 Delhi Open Transit Data registration (needed in P4).

T046 (the Karnataka MVP release) remains open and waits for H11. C1 (Kerala
dam model) is deferred to the owner at the end (D104).
