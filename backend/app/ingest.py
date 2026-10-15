"""Open-Meteo access. Only fixed hosts are called; user input never forms a URL."""
import time, httpx

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"

def _get(url, params, tries=3):
    err = None
    for i in range(tries):
        try:
            r = httpx.get(url, params=params, timeout=45)
            if r.status_code == 429 or r.status_code >= 500:
                raise httpx.HTTPError(f"upstream {r.status_code}")
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            err = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"Upstream unavailable: {err}")

def fetch_tmax(lat, lon, start, end):
    j = _get(ARCHIVE, dict(latitude=lat, longitude=lon, start_date=start, end_date=end,
                           daily="temperature_2m_max", temperature_unit="celsius", timezone="UTC"))
    d = j.get("daily") or {}
    t, v = d.get("time"), d.get("temperature_2m_max")
    if not t or not v or len(t) != len(v):
        raise RuntimeError("Malformed upstream response")
    return {"dates": t, "tmax": v}

def geocode(q):
    j = _get(GEOCODE, dict(name=q, count=6, language="en", format="json"), tries=2)
    return [dict(name=r["name"], admin=r.get("admin1"), country=r.get("country"),
                 lat=r["latitude"], lon=r["longitude"]) for r in j.get("results", [])]
