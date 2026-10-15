import numpy as np, pandas as pd
from fastapi.testclient import TestClient
from app import climate, main

def ar(rng, n):  # autocorrelated weather noise (persistence makes multi-day spells realistic)
    e, x = rng.normal(0, 1.5, n), np.zeros(n)
    for i in range(1, n): x[i] = 0.75*x[i-1] + e[i]
    return x

def synth(warming=0.05):
    idx = pd.date_range("1990-01-01", "2025-12-31")
    rng = np.random.default_rng(1)
    yrs = (idx.year - 1990).values
    v = 30 + 8*np.sin((idx.dayofyear.values-100)/365*2*np.pi) + warming*yrs + ar(rng, len(idx))
    v = v.astype(object); v[100:120] = None; v[500] = 999   # gaps + outlier
    return [d.strftime("%Y-%m-%d") for d in idx], list(v)

def test_trend_and_quality():
    d, v = synth(); doc = climate.process(d, v)
    assert doc["n_outliers"] >= 1 and doc["n_gap_days"] >= 20
    r = climate.summarize(doc, 1990, 2025)
    assert r["trends"]["hw_days"]["significant"] and r["trends"]["hw_days"]["sen_per_decade"] > 0
    assert "%" in r["insight"]["headline"]

def test_api(monkeypatch, tmp_path):
    d, v = synth(); calls = []
    monkeypatch.setattr(main.ingest, "fetch_tmax", lambda *a: calls.append(a) or {"dates": d, "tmax": v})
    monkeypatch.setattr(main, "last_full_year", lambda: 2025)
    main.store = main.FileStore(tmp_path) if hasattr(main, "FileStore") else main.store
    c = TestClient(main.app)
    r1 = c.get("/api/analysis?lat=17.38&lon=78.48&start=1990&end=2020").json()
    r2 = c.get("/api/analysis?lat=17.4&lon=78.5&start=2000&end=2025").json()
    assert not r1["cached"] and r2["cached"] and len(calls) == 1
    assert c.get("/api/analysis?lat=999&lon=0").status_code == 422
    assert c.get("/api/analysis?lat=1&lon=1&start=2020&end=2022").status_code == 422
    assert c.get("/api/geocode?q=<script>").status_code == 422
