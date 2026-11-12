# T040: frozen Place Lens reports

Place Lens reads versioned places from the approved browser snapshot. The Now,
Risk, Forecast, History, Nearby and Sources tabs share one report object with the
print view. No production place list, facility, score or approval is seeded.

Choose a source-backed place, then use **Open frozen report** or **Print / Save
PDF**. The URL binds the state, place ID, boundary version, exact as-of string
and verified snapshot SHA256. Reopening it reads the same-origin immutable
`/data/{state}/releases/{sha256}.approval.json` pointer, checks approval and hash,
then checks the downloaded bytes and report identity. Missing old releases,
incorrect versions and malformed links produce an error. They cannot silently
substitute the current release. T045 must publish these approval pointers after
the actual review gate; this feature does not grant publication approval.

The cutoff and original source times stay visible. Now means known at that
cutoff, not current conditions. Forecast includes only forecast records whose
validity is at or after the cutoff. History contains past validity times found
in this snapshot, not a complete historical archive. Original CAP warning text
and instructions are rendered as text, with severity and expiry. Expired
warnings remain visibly expired.

Point records and facilities use approximate great-circle distance within 25 km
of the place's representative point. This is neither a street address nor a
walking-network distance. Area warnings remain statewide context; their presence
does not prove an incident at this place. A model score needs an explicit match
to the place ID and boundary version, plus a model ID and release status. No
score is inferred from proximity or converted from missing to zero.

S18 is available from the owner's extract (D174). `python -m atlas.ingest.s18_prepare`
exports hospitals, police and fire stations, the nearest 10 of each within 25 km of
every S17 district point, each linked to its OpenStreetMap object (D175). Nearby
shows the kind, approximate distance, source-check status and fetch time, without
an open-now or safe-routing claim. OSM shelters stay out. Facilities appear only
once T045 adds them to an approved release; until then Nearby says facility data is
unavailable.

The local test place is Bangalore district, derived from the captured S17
geoBoundaries ADM2 release `9469f09`; its original name and boundary version are
preserved. Provenance cites both original boundary files and their hashes. The
test projection is checked against the adapter and original geometry locally.
The genuine CAP and Open-Meteo projections are checked against source evidence.
Test release metadata exists only inside browser test routes.

Acceptance: `python -m pytest tests/test_lens.py -q`. It checks source fidelity,
builds the application, runs report unit checks and runs Chromium at 360, 768 and
1280 px, including frozen-link reopening, malformed identities, keyboard/axe
checks and actual browser PDF generation. Local PDFs remain under `.cache/`.
