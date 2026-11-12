# T038 web dependency check — 6 Nov 2026

Direct official npm metadata returned HTTP 200 for every exact plan candidate.
Their declared engines support Node 22.16.0/npm 10.9.2. The installed Windows
runtime, TypeScript build, unit tests and real Chromium tests are verified
separately; registry existence alone is not a compatibility claim.

| Package | Exact pin | Declared licence |
|---|---|---|
| react / react-dom | 19.3.1 | MIT |
| typescript | 7.0.2 | Apache-2.0 |
| vite | 8.3.5 | MIT |
| maplibre-gl | 6.16.0 | BSD-3-Clause |
| vitest | 5.1.0 | MIT |
| @playwright/test | 1.64.1 | Apache-2.0 |
| @axe-core/playwright | 4.14.0 | MPL-2.0; development-only audit tool |
| @types/react / @types/react-dom | 19.3.0 | MIT |
| @types/node | 22.16.0 | MIT |

Evidence: official registry endpoints `https://registry.npmjs.org/<name>/<version>`
(scoped names URL-encoded); response URLs/hashes and raw metadata are retained
locally under `.cache/t038-research/`. `web/package-lock.json` commits exact
transitive versions and npm integrity values. D57 pins the test transport to
playwright-core 1.64.1 rather than mixing two Page-type versions.

The [official Node release](https://nodejs.org/dist/v22.16.0/) publishes the
Windows x64 ZIP and SHASUMS256.txt. The downloaded ZIP's SHA256 is
`21c2d9735c80b8f86dab19305aa6a9f6f59bbc808f68de3eef09d5832e3bfbbd`, matching that
published checksum. The version-tagged npm package file confirms npm 10.9.2.
The runtime and all npm/Playwright caches live on D and are not committed.

Vite handles TSX directly; no extra React plugin is needed for this static shell.
MapLibre 6 uses named ESM imports and its explicitly bundled worker URL, following
the [official migration guide](https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/).
The map module, CSS and worker load separately from the initial UI. The map chunk
is about 1.08 MB minified / 293 KB gzip; Vite reports its size warning. There is no
additional chart, PMTiles or transformer package until a later task needs it.
