# T038: static map shell

The local product reference is plan D15 and T038: a practical map workspace in
muted teal and sand, with the map and the matching readable list as the primary
surface. Users choose Karnataka, a radius and the available snapshot, inspect
dated records and follow official sources. No marketing landing page precedes it.

At 1280px the record panel sits beside the map; at 360px the map sits above a
scrolling bottom panel. Labels wrap, controls stay reachable and the list remains
usable without map tiles. Tablet checks run at 768px. System fonts avoid an extra
font service. Simple borders and a coordinate-grid loading surface keep the
application recognisable without copying any reference product's branding.

Loading has explicit progress; an absent release explains what is missing;
unapproved, malformed or hash-mismatched data is rejected; stale data retains its
as-of time; failed refreshes keep only the same state's in-memory last-good view.
No records or approval are seeded into production. A publisher must produce the
approved immutable snapshot after its review gate. T038 supplies the browser
contract, not an operational data pipeline or a public deployment.

Use portable Node 22.16.0/npm 10.9.2 under `.tools/node/`:

```powershell
powershell -NoProfile -File scripts/web.ps1 ci --ignore-scripts
powershell -NoProfile -File scripts/web.ps1 run build
powershell -NoProfile -File scripts/web.ps1 run test
powershell -NoProfile -File scripts/web.ps1 run test:e2e -- shell.spec.ts
```

The wrapper keeps npm, browser downloads and temp files on D. Browser checks
require Playwright's Chromium installed using that same environment. They cover
three viewports, loading/empty/error/last-good states, keyboard focus, overflow
and automated axe checks. This is not a complete screen-reader/WCAG audit.

The same records drive the list and map markers. The committed public-domain
Sachet test sample is bound to the original CAP/polygon hashes and checked
against the Python adapter. Its point is explicitly an alert-area representative
point, not an incident location. Its canonical `official` provenance is preserved
alongside the other common-envelope values (`model`, `inferred`, `reconstructed`).
Test release metadata stays inside test routes; none is served by the application.

Visual checks caught and fixed a MapLibre CSS cascade that clipped its container;
the browser suite now compares the container/canvas dimensions to the map panel.
A real-server test also protects JSON requests from Vite's HTML fallback. Local
captures at 360/768/1280px have no horizontal overflow. These first captures are
an inspected reference, not a comparison against an earlier visual baseline.

## Accuracy page (T259)

`?page=accuracy` shows the model accuracy table (F036). It loads only
`/data/ka/accuracy/latest.json` pointing, with `approved`, to
`/data/ka/accuracy/<sha256>.json` whose bytes match that digest. Without a
release it says none exists; an unapproved or tampered release is refused.
Unavailable values show as "Unavailable", never 0. The browser fixture is
written by `python -m atlas.models.accuracy` from committed records. No
accuracy release is served until H11 approves publication.
