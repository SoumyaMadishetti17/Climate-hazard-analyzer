<<<<<<< HEAD
# Climate Hazard Trend Analyzer (Heatwaves)

React + FastAPI + MongoDB app that detects heatwaves in historical weather data for any point on Earth and shows frequency / duration / intensity trends with honest statistics.

**Live demo:** _<add URL>_ · **Demo video:** _<optional>_

## Setup
```bash
# backend (file-based store by default; set MONGO_URI to use MongoDB/Atlas)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload            # :8000
pytest                                    # synthetic-data tests, no network needed

# frontend
cd frontend && npm install && npm run dev # :5173, /api proxied to :8000
```
Env: `MONGO_URI`, `MONGO_DB`, `ALLOWED_ORIGINS` (comma list), `RATE_LIMIT` (req/min/IP, 60), `INGEST_LIMIT` (new-region fetches/min/IP, 6), `DATA_DIR`. Frontend: `VITE_API_URL`.

**Deploy:** backend → Render/Cloud Run via `backend/Dockerfile` (+ free MongoDB Atlas M0, set `MONGO_URI`, `ALLOWED_ORIGINS=<frontend url>`); frontend → Vercel/Netlify (`npm run build`, env `VITE_API_URL=<backend url>`).

## Architecture
```
React (Chart.js, Leaflet) → FastAPI ──► MongoDB  raw (daily Tmax) | analysis (yearly stats + events)
                                  └──► Open-Meteo Archive/Geocoding (only on cache miss)
```
`GET /api/analysis?lat&lon&start&end&hazard=heatwave` → checks the `analysis` collection; on a miss it ingests 1990–last full year in one upstream call, caches raw data, runs detection, stores results, then **reads from the DB** to build the JSON (series, 5-yr rolling mean, trend line, Mann-Kendall/Sen/OLS, top events, insight text). `GET /api/geocode?q=` for city/state search.

## Data source & handling
Open-Meteo Historical Weather API (ERA5-based reanalysis, ~10 km, daily max 2 m temperature, °C requested explicitly).
- Gaps → NaN (never interpolated); a gap breaks a heatwave run. Years with <85 % coverage are excluded from trends and flagged.
- Outliers: values outside −70…60 °C or >20 °C from a 15-day rolling median → NaN, count reported.
- Malformed/failed upstream responses are validated; 3 retries with backoff; 502 returned to client.

## Hazard logic
Heatwave = **≥3 consecutive days with Tmax > the calendar-day 95th percentile** (±7-day window around each day-of-year, **1991–2020 baseline**, Feb 29 folded into Feb 28). A fixed baseline is used regardless of the selected range so results are comparable and trends aren't an artifact of the chosen window. Per year: event count (by start date), heatwave days, longest event, mean intensity (°C above threshold).
Trends over valid years in the selected range: **Mann-Kendall** p-value + **Sen's slope** (robust to outliers) and OLS slope/R². "Significant" = p<0.05. The headline % compares the first and last 10 years (or halves for short ranges) and always states significance; caveats are shown in the UI.

## Security / performance
Pydantic-validated bounds on lat/lon/years, regex-limited geocode query, fixed upstream hosts (no SSRF), 0.25° grid snapping (bounded cache keys), per-region lock (no duplicate ingestion), per-IP sliding-window rate limits (general + stricter for ingestion), CORS allow-list, GET-only API, DB cache with freshness check (new year / algorithm version).

## Assumptions & limitations
- Custom "box" regions are not implemented: a point is analysed (nearest 0.25° cell). Box = area-average would be the next step.
- One grid cell ≠ a station; Tmax only (no humidity / heat index / Tmin).
- Rate limiter is in-memory (single instance). Open-Meteo free tier is for non-commercial use.
- Only heatwaves implemented (selector shows drought/rainfall as coming soon).

## With more time
Region-box averaging, multi-source cross-check (NOAA/ERA5-Land), heat-index definition (EHF), Redis rate-limit/cache, serverless-friendly background ingestion with progress, server-side PDF export, frontend tests, CI.

## AI tools used
Claude (Anthropic) generated the initial scaffold of backend, tests, frontend and README from the case brief; I reviewed, ran and adapted the code. _<edit to reflect your own usage>_
=======
# Climate-hazard-analyzer
>>>>>>> 08c6413c19b4557cf1d39e8da243f4c9442cbbc4
