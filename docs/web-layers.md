# T039 — dated layers and provenance

The same filtered records drive the map markers and readable list. Weather,
official CAP warnings, market prices and research models have independent
toggles. Source-health metadata is explicit; missing telemetry is not a healthy
empty feed. Unavailable prices never become zero or an implied known unit.

Each record retains canonical provenance plus provider issue, validity, fetch and
availability timestamps. The browser rejects data unavailable at the snapshot
cutoff, unknown numeric units, prices without a market/unit and numeric missing
values without a reason. CAP severity/expiry is retained. An inferred or model
item cannot enter the official S09 warning layer. Model evidence labels keep
forecasts, reanalysis and hindcasts distinct when supplied.

Radius selection works by clicking the map or panning with its keyboard controls
and pressing Enter. Point records use great-circle distance. The centre can be
cleared. Area warnings remain in state context because their representative
point does not measure distance to the entire polygon (D58); no incident or safe
route is inferred from that point. T230 also preserves S09 warnings with original
area text but no supplemental polygon. Both coordinates remain explicitly null;
the list, ticker and report retain the warning while the map creates no marker
or fly-to point. Unlocated weather, facilities and administrative places remain
invalid. A radius cannot establish which part of an unmapped warning area it
intersects, so that warning stays in state context.

The ticker is labelled as snapshot context, preserves severity and absolute
expiry, marks expired alerts, uses a polite live region and can be paused. Reduced
motion starts it paused. Minute clock updates change expiry presentation, never
the stored source timestamps. Official source links remain reachable when an
optional source or the basemap is unavailable.

Real, licensed test inputs:

- The existing public-domain Sachet CAP sample, including its original polygon,
  mapped only to a labelled representative point.
- One non-missing temperature from the existing CC BY 4.0 Open-Meteo/ECMWF sample,
  preserving its actual grid centre, value, unit, model run and retrieval times.

Each projection has source-file hashes and a derivation record. Python tests
check it against the existing adapter. No production snapshot is seeded.

Validation includes distance/antimeridian cases, source-health failures, cutoff
and unit checks; desktop/mobile/tablet toggles, original timestamps, severity,
keyboard radius selection and ticker controls; populated-view axe and overflow
checks. Screenshots stay in `.cache/playwright-results/`. This is an inspected
first reference, not a completed screen-reader or visual-regression audit.

## Scheduled transit and historical railway (T104)

`src/atlas/transit/schedule.py` builds the layer's JSON from S30 timetables
(`snapshot()`); `web/src/map/ScheduledTransit.tsx` validates and renders it.

- A trip runs on a local service date; times count from noon minus 12 h and
  may pass 24:00, so an instant checks that day's and the previous day's
  service (00:20 on 12 Nov shows BMRCL trips of 11 Nov; 25:10 is 01:10 next day).
- A vehicle is placed only between two consecutive scheduled stops, along the
  trip's shape (stops within 150 m of it, in order). No shape, a stop off the
  shape, a missing time or inconsistent times pause the trip: it is counted,
  never drawn.
- Every marker says "Scheduled position (timetable estimate), not live", with
  the feed's pinned commit, the service date and the compiler's own timing
  caveat. Metro stations (83 BMRCL parent stations) and S21 railway stations
  are overlays.
- S21 stays "2016 timetable (historical reference)": clock text only, no
  instant, position or ETA; passing S21 to the position engine is refused.

The component is not mounted in the app yet: S30's licence is restricted
(D115), so no public transit snapshot exists until the owner's H11 review
(D116).

## Context layers (T105)

`atlas.spatial.context.layer_status()` derives each context layer's control
from its source contract (enabled, discovery outcome, licence); the web copy is
`web/tests/fixtures/context-layers.json`, kept equal by a Python test.
`web/src/map/ContextLayers.tsx` renders disabled controls with the recorded
reason, the provider page and the evidence path.

- Fire (S25): disabled until the FIRMS MAP_KEY (H09). A hotspot can only be a
  `thermal_anomaly`; "fire", "confirmed_fire" and "structure_fire" are refused.
- RERA (S31): disabled until K-RERA permission; only the discovery's public
  fields pass `rera_public`, so promoter names and contacts never do.
- Buildings (S19): footprints of confidence 0.75 or more, clipped to one place
  boundary whose version must match; rows joined to another version fail.
- Crime (S44): district units' published "Total" per year (2023), listed with
  the under-reporting note; 2024 offence heads are never summed and nothing is
  mapped until a police-unit crosswalk exists (D114).

Like the transit layer, the controls are not mounted in the app until a
public snapshot carries them (D117).

## Terrain and globe (T186)

`web/src/map/Terrain.tsx` and `Globe.tsx` add MapLibre terrain (S14 Terrarium DEM,
exaggeration 1 unless set) and the globe projection, with S13 imagery under the date S13
reported (no imagery and a message when it reported none). No WebGL, a lost context or a
device with 2 GB or less memory falls back to the flat map or to a status message that points
to the record list; reduced motion removes camera animation; nothing is stored for later use.
Not mounted (D152); the Python contract test is `tests/test_tiles.py`.

## Movement overlays (T187)

`atlas.spatial.orbits.movement_status()` gates four layers from their source contracts (web copy:
`web/tests/fixtures/movement-layers.json`, kept equal by a Python test); `web/src/map/Movement.tsx`
renders them. Aircraft (S10) older than 300 s are hidden and carry no callsign, registration or
owner; satellites (S12) show only positions predicted from dated orbit elements, so none show
while propagation is unavailable; earthquakes (S20) show the USGS revision time and source
link; ships (S26) stay hidden. All but aircraft are held for H11 or H12. One region key and
poll gate serves flights and ships, so a fallback source cannot add a second poll. Not mounted
(D153).

## Wall mode (T188)

`web/src/map/WallMode.tsx` is a full-screen display: a large snapshot timestamp, per-source
health with each last-success time, and the existing pausable `EventTicker`. The snapshot is
"current" only when the feed is connected and at most 24 hours old (the app limit); otherwise
it is "stale" or "disconnected", styled and worded that way, with the last timestamps kept and
no alerts shown. No sound, animation or flashing; Escape or the exit button leaves; the ticker
starts paused under reduced motion. Strings come from `web/src/i18n`. Not mounted (D154).
