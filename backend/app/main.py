import os, threading, time
from collections import defaultdict, deque
from datetime import date
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from . import climate, ingest
from .store import get_store, FileStore

START_YEAR = 1990
store = get_store()
app = FastAPI(title="Climate Hazard Trend Analyzer")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
                   allow_methods=["GET"], allow_headers=["*"])

# ---- in-memory sliding-window rate limiter (swap for Redis if running >1 instance)
_hits = defaultdict(deque)
def _allow(ip, bucket, limit, window=60):
    q, now = _hits[(ip, bucket)], time.time()
    while q and q[0] < now - window: q.popleft()
    if len(q) >= limit: return False
    q.append(now); return True
def _ip(r):
    fwd = r.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (r.client.host if r.client else "?")

@app.middleware("http")
async def limiter(request: Request, call_next):
    if request.url.path.startswith("/api") and not _allow(_ip(request), "all", int(os.getenv("RATE_LIMIT", 60))):
        return JSONResponse({"detail": "Rate limit exceeded"}, 429, headers={"Retry-After": "60"})
    return await call_next(request)

_locks, _glock = {}, threading.Lock()
def _lock(k):
    with _glock: return _locks.setdefault(k, threading.Lock())

def last_full_year(): return date.today().year - 1

def get_analysis(lat, lon, ip):
    # snap to 0.25° grid: bounded key space -> better cache hits, limits cache-flooding
    glat, glon = round(lat * 4) / 4, round(lon * 4) / 4
    key = f"{glat:.2f}_{glon:.2f}"
    fresh = lambda d: d and d.get("version") == climate.VERSION and d.get("data_end_year") == last_full_year()
    doc = store.get("analysis", key)
    if fresh(doc): return doc, key, True
    if not _allow(ip, "ingest", int(os.getenv("INGEST_LIMIT", 6))):
        raise HTTPException(429, "Too many new-region requests; retry in a minute")
    with _lock(key):
        doc = store.get("analysis", key)
        if fresh(doc): return doc, key, True
        raw = store.get("raw", key)
        if not raw or raw.get("end_year") != last_full_year():
            try: d = ingest.fetch_tmax(glat, glon, f"{START_YEAR}-01-01", f"{last_full_year()}-12-31")
            except RuntimeError as e: raise HTTPException(502, str(e))
            raw = dict(lat=glat, lon=glon, end_year=last_full_year(), fetched_at=time.time(), **d)
            store.put("raw", key, raw)
        try: doc = climate.process(raw["dates"], raw["tmax"])
        except ValueError as e: raise HTTPException(422, str(e))
        doc.update(lat=glat, lon=glon, computed_at=time.time())
        store.put("analysis", key, doc)
        return doc, key, False

@app.get("/api/health")
def health(): return {"ok": True}

@app.get("/api/geocode")
def geocode(q: str = Query(..., min_length=2, max_length=80, pattern=r"^[\w\s,.\-'’]+$")):
    try: return ingest.geocode(q)
    except RuntimeError as e: raise HTTPException(502, str(e))

@app.get("/api/analysis")
def analysis(request: Request,
             lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180),
             start: int = Query(1990, ge=START_YEAR, le=2100), end: int = Query(None, ge=START_YEAR, le=2100),
             hazard: str = Query("heatwave", pattern="^heatwave$")):
    end = end or last_full_year()
    if end > last_full_year(): raise HTTPException(422, f"end must be <= {last_full_year()}")
    if end - start < 9: raise HTTPException(422, "Time range must span at least 10 years")
    doc, key, cached = get_analysis(lat, lon, _ip(request))
    res = climate.summarize(doc, start, end)
    events = sorted([e for e in doc["events"] if start <= int(e["start"][:4]) <= end], key=lambda e: (-e["days"], -e["mean_excess"]))
    return dict(region=dict(lat=doc["lat"], lon=doc["lon"], key=key, requested=dict(lat=lat, lon=lon)),
                hazard=hazard, range=[start, end], cached=cached,
                definition=dict(rule=f">={climate.MIN_RUN} consecutive days Tmax > calendar-day P{climate.PCT} (±{climate.WINDOW}d window)",
                                baseline=[climate.BASE0, climate.BASE1], unit="°C", source="Open-Meteo Historical Weather API (ERA5)"),
                quality=dict(gap_days=doc["n_gap_days"], outliers_removed=doc["n_outliers"], total_days=doc["n_days"],
                             annual_mean_threshold=doc["threshold_annual_mean"], peak_threshold=doc["threshold_summer_peak"]),
                top_events=events[:10], **res)
