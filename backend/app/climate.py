"""Heatwave detection + trend statistics.
Definition: >=3 consecutive days with Tmax above the calendar-day 95th percentile
(+-7-day window, 1991-2020 baseline) of the region."""
import math
import numpy as np, pandas as pd

BASE0, BASE1 = 1991, 2020
PCT, WINDOW, MIN_RUN, MIN_COV = 95, 7, 3, 0.85
VERSION = 2

def _nn(v):
    if v is None: return None
    if isinstance(v, (float, np.floating)) and not math.isfinite(v): return None
    return round(float(v), 3) if isinstance(v, (float, np.floating)) else v

def clean(dates, vals):
    """Daily series with gaps -> NaN, physically impossible values and spikes -> NaN."""
    s = pd.Series(pd.to_numeric(pd.Series(vals, dtype="object"), errors="coerce").values,
                  index=pd.to_datetime(dates))
    s = s[~s.index.duplicated()].sort_index().asfreq("D")
    n_gap = int(s.isna().sum())
    bad = (s < -70) | (s > 60)
    spike = (s - s.rolling(15, center=True, min_periods=7).median()).abs() > 20
    n_out = int((bad | spike).sum())
    s[bad | spike] = np.nan
    return s, n_gap, n_out

def _doy(idx):
    doy = idx.dayofyear.values.copy()
    leap = idx.is_leap_year
    doy = np.where(leap & (idx.month > 2), doy - 1, doy)
    return np.where(leap & (idx.month == 2) & (idx.day == 29), 59, doy)

def thresholds(s):
    doy = _doy(s.index)
    m = (s.index.year >= BASE0) & (s.index.year <= BASE1) & s.notna().values
    if len(set(s.index.year[m])) < 20:
        raise ValueError("Insufficient baseline data (need >=20 years of 1991-2020)")
    bv, bd = s.values[m], doy[m]
    thr = np.full(366, np.nan)
    for d in range(1, 366):
        dist = np.abs(bd - d); dist = np.minimum(dist, 365 - dist)
        sel = bv[dist <= WINDOW]
        if sel.size >= 30: thr[d] = np.percentile(sel, PCT)
    return thr, doy

def process(dates, vals):
    s, n_gap, n_out = clean(dates, vals)
    thr, doy = thresholds(s)
    t = thr[doy]; v = s.values
    exc = (v > t) & ~np.isnan(v) & ~np.isnan(t)
    d = np.diff(np.concatenate([[0], exc.astype(int), [0]]))
    events = []
    for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
        if b - a >= MIN_RUN:
            events.append(dict(start=s.index[a].strftime("%Y-%m-%d"), end=s.index[b - 1].strftime("%Y-%m-%d"),
                               days=int(b - a), mean_excess=round(float((v[a:b] - t[a:b]).mean()), 2),
                               peak_tmax=round(float(v[a:b].max()), 1)))
    cov = s.notna().groupby(s.index.year).mean()
    years = []
    for y, c in cov.items():
        ev = [e for e in events if e["start"].startswith(str(y))]
        years.append(dict(year=int(y), coverage=round(float(c), 3), events=len(ev),
                          hw_days=sum(e["days"] for e in ev), max_duration=max([e["days"] for e in ev], default=0),
                          mean_intensity=round(float(np.mean([e["mean_excess"] for e in ev])), 2) if ev else None))
    return dict(version=VERSION, years=years, events=events, n_days=len(s), n_gap_days=n_gap, n_outliers=n_out,
                threshold_summer_peak=_nn(np.nanmax(thr)), threshold_annual_mean=_nn(np.nanmean(thr)),
                data_end_year=int(s.index.year.max()))

def mann_kendall(x, y):
    x, y, n = np.asarray(x, float), np.asarray(y, float), len(y)
    s = sum(np.sign(y[i + 1:] - y[i]).sum() for i in range(n - 1))
    _, c = np.unique(y, return_counts=True)
    var = (n * (n - 1) * (2 * n + 5) - (c * (c - 1) * (2 * c + 5)).sum()) / 18
    z = 0.0 if s == 0 or var <= 0 else (s - np.sign(s)) / math.sqrt(var)
    slopes = [(y[j] - y[i]) / (x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n)]
    return math.erfc(abs(z) / math.sqrt(2)), float(np.median(slopes))

def _trend(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    b, a = np.polyfit(x, y, 1)
    r2 = 1 - ((y - (a + b * x)) ** 2).sum() / max(((y - y.mean()) ** 2).sum(), 1e-12)
    p, sen = mann_kendall(x, y)
    return dict(ols_per_decade=round(float(b) * 10, 3), sen_per_decade=round(sen * 10, 3), r2=round(float(r2), 3),
                mk_p=round(p, 4), significant=bool(p < 0.05)), (a, b)

def summarize(doc, start, end):
    rows = [r for r in doc["years"] if start <= r["year"] <= end]
    ok = [r["coverage"] >= MIN_COV for r in rows]
    g = lambda k: [r[k] if o else None for r, o in zip(rows, ok)]
    yrs = [r["year"] for r in rows]
    out = dict(years=yrs, events=g("events"), hw_days=g("hw_days"), max_duration=g("max_duration"),
               mean_intensity=g("mean_intensity"), low_coverage_years=[r["year"] for r, o in zip(rows, ok) if not o])
    vy = [r["year"] for r, o in zip(rows, ok) if o]
    if len(vy) < 8:
        return dict(series=out, trends=None, rolling5=None, trend_line=None,
                    insight=dict(headline="Not enough valid years (need at least 8) to estimate a trend.", detail="", caveats=[]))
    roll = pd.Series([_nn(v) if v is not None else np.nan for v in out["hw_days"]], dtype=float).rolling(5, min_periods=3).mean()
    trends, line = {}, None
    for k in ("events", "hw_days", "max_duration"):
        yv = [r[k] for r, o in zip(rows, ok) if o]
        trends[k], (a, b) = _trend(vy, yv)
        if k == "hw_days": line = [round(a + b * y, 3) for y in yrs]
    k = min(10, len(vy) // 2)
    hv = [r["hw_days"] for r, o in zip(rows, ok) if o]
    f, l = float(np.mean(hv[:k])), float(np.mean(hv[-k:]))
    t = trends["hw_days"]
    sig = (f"The trend is statistically significant (Mann-Kendall p={t['mk_p']})." if t["significant"]
           else f"The trend is NOT statistically significant (Mann-Kendall p={t['mk_p']}); treat the change as inconclusive.")
    if f > 0:
        pct = (l - f) / f * 100
        head = f"Heatwave days per year changed by {pct:+.0f}% between {vy[0]}-{vy[k-1]} (avg {f:.1f}) and {vy[-k]}-{vy[-1]} (avg {l:.1f})."
    else:
        head = f"Heatwave days per year rose from 0 ({vy[0]}-{vy[k-1]}) to avg {l:.1f} ({vy[-k]}-{vy[-1]}); a % change is undefined."
    detail = f"{sig} Sen's slope: {t['sen_per_decade']:+.2f} heatwave days/decade (OLS {t['ols_per_decade']:+.2f}, R²={t['r2']})."
    caveats = ["Heatwave counts are small integers and inter-annual variability is large; start/end-year choice can change the % figure.",
               "Threshold is a fixed 1991-2020 percentile, so the trend is relative to that climate, not an absolute-temperature trend.",
               "Data is a ~10 km reanalysis grid cell (ERA5-based via Open-Meteo), not a station; it can miss urban/local effects.",
               "Tmax only: humidity/night-time heat (heat index, Tmin) is not considered."]
    if out["low_coverage_years"]: caveats.append(f"Years excluded for <{int(MIN_COV*100)}% data coverage: {out['low_coverage_years']}")
    return dict(series=out, trends=trends,
                rolling5=[_nn(x) for x in roll], trend_line=line,
                insight=dict(headline=head, detail=detail, caveats=caveats))
