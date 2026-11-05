# KW Live research and Kerala project plan

Research date: 2026-11-04. Status labels: ✅ confirmed from KW Live's own site, screenshots or the CTV story · ❔ inferred (best guess).

## 1. What KW Live is

- Site: https://kw-live.com/ (private beta, founder-only testing, no public demo). Beta form: https://tally.so/r/rjeDXR
- One dark map of Waterloo Region, Ontario (Kitchener, Waterloo, Cambridge and 4 townships) that combines public data: transit, roads, public safety, cameras, aviation, weather, permits, municipal GIS, buildings.
- Founder: Mike Nickason (news misspells "Nickerson"), 52, ex-forklift operator, first software project, started April 2026, built solo with AI coding tools.
- Sister sites (vision pages only): ontario-live.com, northamerica-live.com, existencefoundry.com (founder's brand).
- Programs: CCIN Vertex inaugural cohort (Oct 2026), Communitech, Accelerator Centre AC:Incubate, Google for Startups Cloud, AWS Activate, Cloudflare for Startups, Neo4j for Startups. About US$70k in cloud credits.
- Terms forbid copying the KW Live name, visual identity or site text. Our version needs its own name and design.
- Sources: [StartupHub article](https://www.startuphub.ai/ai-news/artificial-intelligence/2026/a-forklift-driver-vibe-coded-his-way-to-a-startup), [CTV News video](https://www.youtube.com/watch?v=qvOxAbC3d0U), [LinkedIn](https://www.linkedin.com/in/mike-nickason/).

## 2. Features (about 30)

### Map and layers
| Feature | What it does | |
|---|---|---|
| Live regional map | Dark map with clustered live items and amber road-closure lines | ✅ |
| Radius filter | Show data within a radius of a point (for example 1.5 km) | ✅ |
| Roads and construction | Closures from Ontario 511, ROADS tab | ✅ |
| GRT live vehicles | Click a bus for headsign, route, direction, trip ID and stop list | ✅ |
| GO Transit | Bus and rail routes, stations and alerts | ✅ |
| Public safety | Live fire, EMS and police calls, counted by type: Fire, Medical, Possible OD, MVC, Gas, Public Assist, Rescue, Police | ✅ |
| Scanner reports | Pins from radio scanner audio (mostly fire, because police radio is encrypted), marked "not official" | ✅ |
| WRPS History | Police occurrence locations, 2024 | ✅ |
| Cameras | Traffic cameras and North Dumfries CCTV/ALPR locations | ✅ |
| Aviation | Flight tracking, YKF airport | ✅ |
| Weather alerts | Weather alert badge and layer | ✅ |
| Permits, planning, housing | Development markers | ✅ |
| Building outlines | Official building outlines, used to match an address to its building | ✅ |
| Garbage day lookup | "Check address, see waste dates" | ✅ |
| Starlink view | Probably a Starlink satellite overlay | ❔ |

### Views and controls
- View modes: Operating Picture, Wall Mode, Atlas (3D globe), Starlink, WRPS History, CCTV/ALPR ✅
- "Live Day" time window (since 3 a.m.) plus a time menu for older data ✅
- Map alerts: Focus, Quiet, Standard, Wall and Mobile modes, sound, read-aloud, 5/10/15 s dwell time ✅
- Feed status badges, for example "Roads unavailable – Ontario 511" and "Weather alerts 1 – issued 4d ago" ✅
- Left panels: Events, Log, GO, Roads, GRT, EMS, Home, Memory, Campus. Right panels: Activity, Scanner, Newsroom, Signal Tape, Police ✅
- Bottom panels: Categories, Memory Status, Place Lens, Civic Sources (graph), Daily Brief (24h), Market Watch, Stock Ticker, Housing, Civic, Campus, Radio, News Video ✅ (what most of them do is unknown)

### Place features (the most distinctive part)
- **Place Lens:** pick an address and it shows tabs for now, property, around, history, watch, sources and Ask. Actions: Focus, Watch, Copy link ✅
- **Sources:** each item shows its source, whether it is official, reference or inferred, how current it is, and a link to the source of record ✅
- **Ask KW Live:** ask questions by text or voice, answered from map data with sources (V2 preview) ✅
- **Watches:** follow a place for changes ✅
- **City Memory:** history of how places changed (in development) ✅
- Newsroom tools, and planned links to traffic, fleet and digital-twin systems (not connected yet) ✅

## 3. Data sources

| Layer | Source | Feed URL | |
|---|---|---|---|
| Base map | CARTO dark + OpenStreetMap | `https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png` | ✅ |
| Satellite / globe | Esri World Imagery | https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer | ✅ |
| Police history | WRPS 2024 occurrence data | https://wrps.ca/resource/2024-occurrence-data | ✅ |
| GO routes and stations | Metrolinx GO GTFS | https://assets.metrolinx.com/raw/upload/Documents/Metrolinx/Open%20Data/GO-GTFS.zip | ✅ |
| Roads | Ontario 511 API (free key, 10 calls per minute) | https://511on.ca/developers/doc | ✅ |
| Municipal GIS, permits, bylaws | Region of Waterloo, Kitchener, Waterloo, Cambridge open data | https://rowopendata-rmw.opendata.arcgis.com/ · https://open-kitchenergis.opendata.arcgis.com/ · https://data.waterloo.ca/ · https://geohub.cambridge.ca/ | ✅ |
| Scanner | Fire radio audio; the pipeline that turns it into pins is unknown | Possibly Broadcastify, Waterloo Region | ✅ / source ❔ |
| GRT live buses | Region of Waterloo GTFS-realtime | https://webapps.regionofwaterloo.ca/api/grt-routes/api/vehiclepositions/1 | ❔ |
| GO alerts | Metrolinx Open Data API (free key) | http://api.openmetrolinx.com/OpenDataAPI/Help | ❔ |
| Cameras | Ontario 511 cameras | https://511on.ca/api/v2/get/cameras?key=... | ❔ |
| Flights | adsb.lol / OpenSky | https://api.adsb.lol/v2/point/43.46/-80.38/25 | ❔ |
| Weather | Environment and Climate Change Canada (ECCC) | https://api.weather.gc.ca/collections/weather-alerts/items | ❔ |
| Starlink | CelesTrak | https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=json | ❔ |
| Police live calls | WRPS incidents page (no API) | https://wrps.ca/news/incidents | ❔ |

## 4. Tech stack
- ✅ Built with ChatGPT, Claude Code and Codex. Started on $20/month plans, later about $200/month.
- ✅ Marketing sites are static HTML on Cloudflare, with Cloudflare Web Analytics. PostHog analytics on the sister sites. Tally beta form.
- ❔ A 3D WebGL map library (MapLibre GL or Cesium).
- ❔ Neo4j graph database for place identity ("Civic Sources GRAPH" panel).
- ❔ AWS or Google Cloud backend. An LLM and a speech provider for Ask.
- Unknown: the exact endpoints the private app calls, the scanner pipeline, and what Market Watch, Stock Ticker, Starlink and Compute Pulse do.

## 5. Our project: state choice for an Indian version

National data covers every state:
- IMD 0.25° daily gridded rainfall, 1901–2024 (`imdlib` Python library): https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html
- India-WRIS reservoir and river levels: https://indiawris.gov.in/wris/
- Agmarknet mandi prices: https://agmarknet.gov.in/
- CPCB hourly AQI: https://www.data.gov.in/catalog/real-time-air-quality-index
- ISRO Landslide Atlas (about 80,000 landslides)

States ranked by extra data:
1. **Karnataka:** KSNDMC rain gauges in every gram panchayat, KWRIS dam data, Bengaluru rainfall 2017–23 (data.opencity.in), BMTC bus timetable
2. **Tamil Nadu:** Chennai lake levels monthly since 1945 plus daily (https://cmwssb.tn.gov.in/lake-level)
3. **Kerala:** KSEB dam levels daily (https://kseb.in/dashboard/view/waterlevel) with monthly archive (https://dams.kseb.in/?p=329), KSDMA dam page, 2018 flood data (Kaggle, KSDMA report), Kochi Metro GTFS (https://kochimetro.org/open-data/)
4. **Telangana / Andhra Pradesh:** 1,000+ (Telangana) and 2,218 (AP) live weather stations
5. **Delhi:** live bus positions (https://otd.delhi.gov.in/, needs registration), densest air quality network, no dams

**Current pick: Kerala.** Reasons: 2018 flood labels, dam + rain + price data, and a link to the existing `kerala-veg-prices` project.

Missing in Kerala: live KSRTC bus positions, road closures, police data, traffic cameras.

## 6. Project framing: data + ML

"Kerala flood and price intelligence: live data pipeline + dam level forecasting + rain-to-price impact analysis + RAG Q&A."

Minimum for it to count as data + ML:
1. Daily pipeline collecting rain, dam and price data
2. Analysis notebook: does rain affect prices?
3. One forecast model with an accuracy score (for example dam level 7 days ahead)
4. Map showing live data and the model's predictions

ML options: dam level or price forecast (Prophet, XGBoost, LSTM), flood risk classification, NLP on Malayalam and English news for road closures, satellite flood detection (Sentinel-1), RAG "Ask" feature.

Differentiation: a basic Kerala dam dashboard already exists (Reddit, 2024). The ML forecasts and the price link must make ours different.

## Open checks
- Download-test each Kerala source, especially the KSEB monthly PDF archive and how many years it covers.
- Check whether the Kochi Metro GTFS is still published.
- Pick a project name (not "Live").

## 7. Free data check, tested live 2026-11-04

Test scripts: `probe.py`, `probe2.py`, `probe_states.py` (in the session scratchpad, not kept).

### Free with no key, works in every state and UT (36/36 tested)
| Data | API | Result |
|---|---|---|
| Weather forecast | Open-Meteo `api.open-meteo.com/v1/forecast` | 14/14 Kerala districts, 36/36 states |
| Historical rain, 1940 onwards (ERA5) | Open-Meteo `archive-api.open-meteo.com/v1/archive` | 36/36. 2018 flood visible (Idukki 1,072 mm, 1–20 Aug 2018) |
| River discharge, past + forecast (GloFAS) | Open-Meteo `flood-api.open-meteo.com/v1/flood` | 35/36 (no river cell for Lakshadweep, Puducherry or Andaman) |
| Air quality (model estimate, not stations) | Open-Meteo `air-quality-api.open-meteo.com` | 36/36 |
| Rain and solar (NASA POWER) | `power.larc.nasa.gov/api/temporal/daily/point` | OK |
| Live planes | adsb.lol `api.adsb.lol/v2/point/{lat}/{lon}/{nm}`, OpenSky | Free, but rate-limited after about 15 fast calls. Needs caching. |
| Satellites | CelesTrak | OK (11,181 Starlink satellites) |
| Disaster alerts | NDMA Sachet RSS `sachet.ndma.gov.in/cap_public_website/rss/rss_<state>.xml` | 28/36 have their own feed. Andhra Pradesh, Arunachal, Himachal, Madhya Pradesh, Tamil Nadu, Uttar Pradesh, West Bengal and Dadra NH & Daman Diu appear only in `rss_india.xml` |
| District boundaries | geoBoundaries IND ADM2 | 736 districts |
| OSM roads, hospitals, shelters | Geofabrik extracts (southern-zone etc.) | OK. Overpass API refused (HTTP 406), so use the extract |
| Earthquakes | USGS | OK (0 M2.5+ events near Kerala since 2000) |
| IMD gridded rain, 1901–2024 | IMD Pune NetCDF / `imdlib` | Page OK |
| Mandi prices | India Data Portal (ISB), already used in kerala-veg-prices | OK |

### Free, but needs a free key or login
- data.gov.in API (mandi prices, CPCB AQI stations): HTTP 400 "Authorization field missing"
- Delhi Open Transit Data (live buses): needs registration
- aisstream.io (ships): needs a free key
- Ontario-style traffic APIs: none exist in India

### State portals (pages load; mostly HTML or PDF, so they need scraping)
| State | Source | Status |
|---|---|---|
| Kerala | KSEB daily dam levels (16 dams parsed), KSDMA dam PDFs, Sachet `rss_kerala.xml` | OK |
| Kerala | KSEB monthly archive (dams.kseb.in) | Page loads, but no file links in the HTML (probably loaded by JS). Needs a browser scrape |
| Kerala | Kochi Metro open data | Connection timed out (blocked or down) |
| Karnataka | KSNDMC, KWRIS rainfall/reservoirs, OpenCity Bengaluru, BMTC GTFS | All OK |
| Tamil Nadu | Chennai lake levels daily + since 1945 | OK |
| Telangana / Andhra Pradesh | TGDPS weather stations, open data portal, APSDPS realtime rain | OK |
| Gujarat | Reservoir system, Sardar Sarovar | OK |
| Maharashtra | WRD dam storage | OK |
| Delhi | Open Transit Data | OK (registration) |
| Odisha, Himachal, Uttarakhand | OSDMA, landslide inventory (Mendeley), GSI | OK |
| Assam | ASDMA flood report page | 404 (URL moved) |
| Bihar | FMISC flood portal | DNS failure (site gone) |
| All | India-WRIS | SSL certificate error from Python, so retest in a browser |

### What to add to the Kerala project
- Core (free, no key, all 14 districts): Open-Meteo rain history + forecast, GloFAS river discharge, KSEB dam levels (scrape daily), Sachet Kerala alerts.
- ML labels: 2018 flood (Kaggle + KSDMA report), ISRO and Kerala landslide inventories.
- Price link: reuse kerala-veg-prices data (Agmarknet via India Data Portal).
- Map context: geoBoundaries districts, Geofabrik OSM hospitals and shelters, adsb.lol planes (cached).
- Optional: Open-Meteo air quality, CelesTrak, aisstream ships (free key).

## 8. Plan decided 2026-11-04: Karnataka first, then Kerala, then Delhi

### Shared platform (built once with Karnataka, reused for Kerala and Delhi)
- Daily pipeline: fetch, clean, Parquet storage. Every reading keeps a timestamp and its source.
- Data quality checks: missing days, sensor outliers, unit checks.
- Map with live layers plus model predictions.
- Ask (RAG): answers questions using the project's data and cites its sources.
- Model evaluation rules: chronological split, always beat a baseline (persistence or climatology), report the error honestly.
- Daily backtest: compare yesterday's forecasts with what actually happened.

### Karnataka (state 1)
Data: KSNDMC rain gauges (every gram panchayat), Bengaluru hobli rain 2017–23 (OpenCity), KWRIS reservoirs (KRS, Kabini, Almatti, Tungabhadra), IMD rain since 1901 + ERA5 since 1940, GloFAS discharge (Cauvery, Krishna, Tungabhadra), Agmarknet (Kolar tomato), BMTC GTFS, Bengaluru wards, lakes and flood spots, Sachet alerts, OSM + Google Open Buildings, BLR flights.

ML:
1. Bengaluru ward flood-risk model: rain + elevation + lakes/drains + past flood spots. Metric: PR-AUC.
2. Reservoir level / inflow forecast, 7 and 30 days. Metric: MAE against persistence.
3. Rain gauge gap-filling and spatial interpolation (kriging vs ML). Metric: RMSE.
4. Taluk drought forecast (SPI index).
5. Kolar tomato price spike warning with rain features (method reused from kerala-veg-prices).
6. Analysis: BMTC stop coverage gaps per ward; how rain hits each ward.

### Kerala (state 2)
Data: KSEB 16 dams daily, IMD + ERA5 rain, GloFAS rivers, Sachet Kerala, 2018 flood data, landslide inventories, kerala-veg-prices data (26.5M records), Sentinel-1 radar.

ML:
1. Dam level forecast, 7 days.
2. District/taluk flood-risk classifier, tested on the 2018 flood.
3. Landslide susceptibility map (random forest: slope, rain, soil). Metric: AUC.
4. Rain-to-veg-price effect (event study / Granger causality).
5. Stretch: flood mapping from Sentinel-1 satellite radar (U-Net), 2018.
6. Stretch: Malayalam + English news NLP to pull landslide and road-block events.
7. Transfer test: does the Karnataka flood model work in Kerala?

### Delhi (state 3)
Data: Open Transit Data live bus GPS (registration), GTFS static, CPCB stations (data.gov.in key), Open-Meteo, flights, Sachet.

ML:
1. Bus delay / arrival-time prediction. Metric: MAE in minutes.
2. Bus bunching detection (anomaly detection).
3. Station AQI forecast, 24–72 h (LightGBM). Must beat the CAMS model forecast.
4. Heatwave risk map (temperature + population).
5. Analysis: air pollution exposure along bus routes.

### Rough time (my estimate)
Karnataka MVP 1 week, full 3–4 weeks. Kerala 2–3 weeks (reuses the platform). Delhi 2–3 weeks (needs the bus data sign-up first).

## 9. Product features and use cases (decided 2026-11-04)

### Features
**Map**
1. Live state map: rain, rivers, dams, alerts, air quality, flights, buses (Delhi), hospitals/shelters, mandi prices.
2. Time slider: replay the past, for example the 2018 Kerala flood or a Bengaluru cloudburst.
3. Radius filter: show only what is near a point.
4. Feed health badges: each source shows whether it is live, stale or down.

**Place Lens (our version)**
5. Click a ward, taluk or address to see now, risk scores, forecast, history and sources.
6. Every item labelled official, model prediction or inferred, with a source link and update time.

**ML layers**
7. Forecast layers: dam/reservoir level (7 and 30 days), ward flood risk, landslide risk, drought, AQI (72 h), bus delay, price spike warning.
8. Model accuracy page: error against a baseline, plus a chart of each day's forecast against what happened.

**Alerts and Ask**
9. Watch a place: alert when flood risk is high, a dam crosses a level, or a price spikes.
10. Ask: questions by text (voice later), answered from the data with citations. English first, then Kannada and Malayalam.
11. Daily brief: an automatic morning summary for each state.

**Analysis**
12. Dashboards: rain trends, dam history, price trends, bus coverage gaps.
13. State comparison: Karnataka against Kerala against Delhi.
14. Open data download of the cleaned datasets.

### Use cases
- Residents: is my area at flood or landslide risk this week?
- Farmers and traders: will tomato or onion prices jump after this rain?
- Disaster teams and NGOs: which wards or taluks need help first?
- Journalists: what happened where, with the official source one click away?
- Researchers and students: clean history data plus tested models.
- Delhi commuters: is my bus late, and how bad is the air on my route?
- Portfolio: shows data engineering + analysis + ML + LLM in one project.

## 10. Full feature list v2 (KW Live check + extras), 2026-11-04

Section 10 replaces the feature list in section 9; the use cases in section 9 still apply. Legend: **KW** = KW Live has it · **SUB** = our substitute for a KW Live layer India lacks · **NEW** = beyond KW Live. Data status from live tests on 2026-11-04.

### KW Live features against ours
| KW Live feature | Ours | Data (tested) |
|---|---|---|
| Live regional map | KW | OpenFreeMap tiles (free, no key) ✅ |
| Radius filter | KW | – |
| Roads and construction | SUB: flood-exposed roads (OSM roads × flood risk) + road blocks pulled from news | Geofabrik OSM ✅, news via GDELT (rate-limited) |
| Live buses (GRT) | KW in Delhi; SUB elsewhere: scheduled positions from GTFS timetables | Delhi OTD ✅ (sign-up), BMTC GTFS ✅, Namma Metro GTFS ✅ |
| GO Transit routes/stations | KW: bus, metro and railway stations | datameet railways stations/trains/schedules ✅ (old data) |
| Fire/EMS/police calls | SUB: Sachet alerts + NASA FIRMS fire hotspots | Sachet ✅, FIRMS ✅ (free key) |
| Scanner reports | SUB: news-derived event pins (NLP), labelled preliminary | GDELT / news RSS |
| WRPS police history | SUB: district crime totals | NCRB site failed to load; data.gov.in (key) ❔ |
| Cameras | SUB: daily satellite imagery (NASA GIBS MODIS) | GIBS ✅ (no key) |
| Aviation | KW | adsb.lol / OpenSky ✅ (cache it) |
| Weather alerts | KW + lightning and thunderstorm alerts | Sachet ✅, Open-Meteo ✅ |
| Permits/planning/housing | SUB: RERA real-estate projects | Karnataka RERA ✅ (scrape), Kerala RERA 503 ❌ |
| Building outlines | KW | Google Open Buildings ✅ |
| Garbage day lookup | SUB: nearest hospital/shelter/police/fire station | OSM ✅ |
| Starlink view | KW: satellites passing overhead now | CelesTrak ✅ |
| View modes (Wall, Atlas globe) | KW + 3D terrain | AWS terrain tiles ✅ (no key) |
| Live Day + time menu | KW (time slider) | – |
| Map alerts (sound, read-aloud) | KW | browser Speech API (free) |
| Feed status badges | KW | – |
| Event log / Signal Tape ticker | KW | – |
| Newsroom panel | KW: news panel + shareable place report | – |
| Daily Brief | KW | – |
| Market Watch / stock ticker | KW: mandi price ticker | India Data Portal ✅ |
| Campus / Radio / News Video | skipped (low value; AIR stream list 404) | – |
| Place Lens | KW | – |
| Sources / provenance | KW | – |
| Ask (text + voice) | KW, plus Kannada / Malayalam / Hindi | – |
| Watches | KW, alerts via Telegram bot + web push | Telegram Bot API ✅ (free) |
| City Memory (as-known-then) | KW: every snapshot stored, so "what did the forecast say on date X" | our own pipeline |

### NEW: beyond KW Live
**ML and prediction**
1. All forecast layers (dams, ward flood risk, landslide, drought, AQI, bus delay, price spikes)
2. "What if" simulator: enter 200 mm of rain and the model redraws the flood-risk map
3. Explain each prediction: why this ward is high risk (SHAP)
4. Uncertainty bands on forecasts (Open-Meteo 40-member ensemble ✅)
5. Model accuracy page + daily backtest
6. Anomaly feed: unusual rain, dam jumps, price jumps, found automatically

**Risk and people**
7. People at risk: population inside flood/landslide zones (WorldPop 100 m ✅)
8. Safe-route helper: route to the nearest shelter that avoids flood-risk roads (OSM routing)
9. Heatwave / heat-index layer
10. Crop health (vegetation index from satellite) for drought and farmers

**Climate and history**
11. Rainfall trend since 1901 for each district (IMD)
12. Climate outlook to 2050 (Open-Meteo CMIP6 ✅)
13. Monsoon onset and progress tracker
14. Past-disaster replay (2018 Kerala, Bengaluru 2022)

**Data and access**
15. Data quality dashboard (missing data, sensor faults)
16. Open data download + public API
17. Telegram alert bot
18. Installable mobile app (PWA), works offline
19. Multilingual interface (English, Kannada, Malayalam, Hindi)
20. Embeddable widgets for news sites
21. State comparison view

Not available free anywhere in India: live road closures, live police calls, public traffic cameras, live KSRTC buses, groundwater levels (CGWB site failed to load).

## 11. Free-of-cost stack (rule: ₹0)
| Need | Free option | Limit to watch |
|---|---|---|
| Daily pipeline | GitHub Actions cron (public repo) | free for public repos |
| Storage | Parquet files in Cloudflare R2 (10 GB free) or Hugging Face Datasets | R2 free tier 10 GB |
| Queries | DuckDB (local) / DuckDB-WASM in the browser | – |
| Website | Cloudflare Pages or Vercel Hobby | Vercel Hobby is non-commercial |
| Map | MapLibre GL + OpenFreeMap (no key) + AWS terrain + NASA GIBS | attribution required |
| ML training | Own laptop, Kaggle (free GPU 30 h/week), Colab | – |
| Model serving | Precompute predictions daily in Actions and publish JSON (no server) | – |
| Ask (LLM) | Free tiers: Gemini API free tier, Groq free tier, or Cloudflare Workers AI (10k neurons/day). Local embeddings (sentence-transformers) | rate limits; Claude API is paid |
| Voice | Browser Web Speech API | browser support varies |
| Alerts | Telegram Bot API, web push | – |
| Free keys needed | data.gov.in, NASA FIRMS, aisstream, Delhi OTD | sign-up only |
