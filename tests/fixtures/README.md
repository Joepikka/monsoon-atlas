# Test fixtures

**These files are for tests only. Never publish them as observations.** Publishing code must not read from `tests/`.

Each real-record fixture states where it came from. Malformed copies are built inside the tests from these records; they are not stored here.

| File | Source | Retrieved (UTC) | Request |
|---|---|---|---|
| `s02_openmeteo_archive_bengaluru_2024-07-01_04.json` | S02 Open-Meteo historical weather (ERA5), unmodified response | 2026-11-05T06:09:33Z | `https://archive-api.open-meteo.com/v1/archive?latitude=12.97&longitude=77.59&start_date=2024-07-01&end_date=2024-07-04&daily=precipitation_sum&timezone=Asia%2FKolkata` |

Open-Meteo data is CC BY 4.0 (attribution: Open-Meteo.com). Dates in this response are local Asia/Kolkata calendar days (`utc_offset_seconds: 19800`).
