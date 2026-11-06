# Test fixtures

**These files are for tests only. Never publish them as observations.** Publishing code must not read from `tests/`.

Each real-record fixture states where it came from. Malformed copies are built inside the tests from these records; they are not stored here.

| File | Source | Retrieved (UTC) | Request |
|---|---|---|---|
| `s02_openmeteo_archive_bengaluru_2024-07-01_04.json` | S02 Open-Meteo historical weather (ERA5), unmodified response | 2026-11-05T06:09:33Z | `https://archive-api.open-meteo.com/v1/archive?latitude=12.97&longitude=77.59&start_date=2024-07-01&end_date=2024-07-04&daily=precipitation_sum&timezone=Asia%2FKolkata` |
| `s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json` | S01 Open-Meteo forecast (T009 evidence e08), unmodified response | 2026-11-05T12:55:01Z | `https://api.open-meteo.com/v1/forecast?latitude=12.97&longitude=77.59&hourly=temperature_2m,precipitation,relative_humidity_2m,wind_speed_10m&temperature_unit=celsius&wind_speed_unit=ms&precipitation_unit=mm&timezone=GMT&forecast_days=16&models=ecmwf_ifs025` |
| `s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json` | S01 Open-Meteo forecast (T009 evidence e09), unmodified response | 2026-11-05T12:55:05Z | `https://api.open-meteo.com/data/ecmwf_ifs025/static/meta.json` |
| `s02_openmeteo_era5_bengaluru_2026-10-20_11-04.json` | S02 Open-Meteo ERA5 (T011 evidence e05), unmodified response | 2026-11-05T13:01:07Z | `https://archive-api.open-meteo.com/v1/archive?latitude=12.97&longitude=77.59&daily=precipitation_sum,temperature_2m_max,temperature_2m_min&temperature_unit=celsius&precipitation_unit=mm&timezone=Asia%2FKolkata&models=era5&start_date=2026-10-20&end_date=2026-11-04` |
| `s02_openmeteo_era5_bengaluru_1940-01-01_07.json` | S02 Open-Meteo ERA5 (T011 evidence e06), unmodified response | 2026-11-05T13:01:11Z | `https://archive-api.open-meteo.com/v1/archive?latitude=12.97&longitude=77.59&daily=precipitation_sum,temperature_2m_max,temperature_2m_min&temperature_unit=celsius&precipitation_unit=mm&timezone=Asia%2FKolkata&models=era5&start_date=1940-01-01&end_date=1940-01-07` |
| `s09_sachet_cap_1793881986295019.xml` | S09 NDMA Sachet CAP (T013 evidence e03), unmodified response | 2026-11-05T13:05:40Z | `https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1793881986295019` |
| `s09_sachet_polygon_1793881986295019.xml` | S09 NDMA Sachet CAP (T013 evidence e04), unmodified response | 2026-11-05T13:05:43Z | `https://sachet.ndma.gov.in/cap_public_website/FetchPolygonXMLFile?identifier=1793881986295019` |
| `s09_sachet_cap_1793880856139008.xml` | S09 NDMA Sachet CAP (T013 evidence e06), unmodified response | 2026-11-05T13:05:49Z | `https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1793880856139008` |
| `s09_sachet_cap_1793871793334006.xml` | S09 NDMA Sachet CAP (T013 evidence e08), unmodified response | 2026-11-05T13:05:56Z | `https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=1793871793334006` |
| `s09_sachet_rss_india_2026-11-05.xml` | S09 NDMA Sachet RSS feed (T013 evidence e02), unmodified response | 2026-11-05T13:05:37Z | `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml` |

Open-Meteo data is CC BY 4.0 (attribution: Open-Meteo.com). Dates in this response are local Asia/Kolkata calendar days (`utc_offset_seconds: 19800`).

Sachet CAP files are public domain (feed `<copyright>`, T013 e02).

## KSEB S32 title/table excerpts (T114)

`s32_kseb_e02.html`, `s32_kseb_e03.html`, `s32_kseb_e04.html`,
`s32_kseb_e09.html` and `s32_kseb_e10.html` contain unchanged report headings and
tables extracted from the T113 captures. Surrounding page content was omitted;
no measurement was edited. `s32_samples.json` records the exact source URLs,
original retrieval times, original raw hashes and excerpt hashes.

Attribution: **Kerala State Electricity Board Limited (KSEB), Daily report: water
levels of main reservoirs**, retrieved 5 November 2026 from
<https://kseb.in/dashboard/view/waterlevel> (dated requests in the manifest).
These excerpts retain **CC BY-SA 2.5 India or later**, as recorded in the captured
[KSEB terms](https://kseb.in/articledetail/terms_and_conditions) (T113 e06), rather
than the repository's MIT code licence. Licence text:
<https://creativecommons.org/licenses/by-sa/2.5/in/>.

Tests create corrupted copies only in temporary directories. The full discovery
pages remain local; `tests/fixtures/s32/` still contains only the evidence manifest.
