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
