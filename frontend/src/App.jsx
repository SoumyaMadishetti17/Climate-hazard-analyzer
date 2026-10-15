import {useState, useEffect} from 'react'
import {Chart as C, CategoryScale, LinearScale, BarElement, PointElement, LineElement, BarController, LineController, Tooltip, Legend} from 'chart.js'
import {Chart} from 'react-chartjs-2'
import {MapContainer, TileLayer, CircleMarker, useMapEvents} from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
C.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, BarController, LineController, Tooltip, Legend)

const API = import.meta.env.VITE_API_URL || ''
const LAST = new Date().getFullYear() - 1
const sgn = v => (v > 0 ? '+' : '') + v

function Picker({onPick}) { useMapEvents({click: e => onPick(+e.latlng.lat.toFixed(3), +e.latlng.lng.toFixed(3))}); return null }

export default function App() {
  const [lat, setLat] = useState(17.385), [lon, setLon] = useState(78.487)
  const [start, setStart] = useState(1990), [end, setEnd] = useState(LAST)
  const [q, setQ] = useState(''), [hits, setHits] = useState([])
  const [data, setData] = useState(null), [err, setErr] = useState(''), [busy, setBusy] = useState(false)

  async function call(path) {
    const r = await fetch(API + path)
    const j = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(typeof j.detail === 'string' ? j.detail : 'Invalid request (check inputs)')
    return j
  }
  async function search() { try { setErr(''); setHits(await call('/api/geocode?q=' + encodeURIComponent(q))) } catch (e) { setErr(e.message) } }
  async function run() {
    setBusy(true); setErr('')
    try { setData(await call(`/api/analysis?lat=${lat}&lon=${lon}&start=${start}&end=${end}&hazard=heatwave`)) }
    catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  useEffect(() => { run() }, [])

  function csv() {
    const s = data.series, rows = ['year,events,heatwave_days,max_duration_days,mean_intensity_C']
    s.years.forEach((y, i) => rows.push([y, s.events[i], s.hw_days[i], s.max_duration[i], s.mean_intensity[i]].map(v => v ?? '').join(',')))
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([rows.join('\n')], {type: 'text/csv'}))
    a.download = `heatwaves_${data.region.key}_${data.range.join('-')}.csv`; a.click()
  }

  const s = data?.series, t = data?.trends
  const opts = (y1) => ({responsive: true, maintainAspectRatio: false, interaction: {mode: 'index', intersect: false},
    scales: {y: {beginAtZero: true, title: {display: true, text: y1[0]}}, ...(y1[1] && {y1: {position: 'right', beginAtZero: true, grid: {drawOnChartArea: false}, title: {display: true, text: y1[1]}}})}})
  const daysChart = s && {labels: s.years, datasets: [
    {type: 'bar', label: 'Heatwave days', data: s.hw_days, backgroundColor: '#d9480f99'},
    {type: 'line', label: '5-yr rolling mean', data: data.rolling5, borderColor: '#1c7ed6', pointRadius: 0, tension: .3},
    {type: 'line', label: 'Linear trend', data: data.trend_line, borderColor: '#2b8a3e', borderDash: [6, 4], pointRadius: 0}]}
  const evChart = s && {labels: s.years, datasets: [
    {type: 'bar', label: 'Events', data: s.events, backgroundColor: '#f08c0099'},
    {type: 'line', label: 'Longest event (days)', data: s.max_duration, borderColor: '#862e9c', pointRadius: 2},
    {type: 'line', label: 'Mean intensity (°C above P95)', data: s.mean_intensity, borderColor: '#c92a2a', pointRadius: 2, yAxisID: 'y1'}]}

  return <>
    <header><h1>🔥 Climate Hazard Trend Analyzer</h1></header>
    <main>
      <aside>
        <div className="card">
          <label>Hazard</label>
          <select value="heatwave" onChange={() => {}}><option value="heatwave">Heatwave</option><option disabled>Drought (coming soon)</option><option disabled>Heavy rainfall (coming soon)</option></select>
          <label>Search city / state</label>
          <div className="row"><input value={q} maxLength={80} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && search()} placeholder="e.g. Karimnagar"/><button style={{flex:'0 0 70px',marginTop:0}} onClick={search}>Find</button></div>
          {hits.map((h, i) => <div key={i} className="hit" onClick={() => {setLat(+h.lat.toFixed(3)); setLon(+h.lon.toFixed(3)); setHits([])}}>{h.name}{h.admin && ', ' + h.admin}, {h.country}</div>)}
          <div className="row"><div><label>Latitude</label><input type="number" step="0.01" min="-90" max="90" value={lat} onChange={e => setLat(+e.target.value)}/></div>
          <div><label>Longitude</label><input type="number" step="0.01" min="-180" max="180" value={lon} onChange={e => setLon(+e.target.value)}/></div></div>
          <MapContainer center={[lat, lon]} zoom={5} key={hits.length + '' + (data?.region.key || '')}>
            <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap"/>
            <Picker onPick={(a, b) => {setLat(a); setLon(b)}}/><CircleMarker center={[lat, lon]} radius={8}/>
          </MapContainer>
          <div className="mut">Click the map to pick a point (analysed on a 0.25° grid cell).</div>
          <div className="row"><div><label>From</label><input type="number" min="1990" max={LAST - 9} value={start} onChange={e => setStart(+e.target.value)}/></div>
          <div><label>To</label><input type="number" min="1999" max={LAST} value={end} onChange={e => setEnd(+e.target.value)}/></div></div>
          <button disabled={busy} onClick={run}>{busy ? 'Analysing… (first load of a region can take ~20s)' : 'Analyse'}</button>
          {err && <p className="err">{err}</p>}
        </div>
        {data && <div className="card mut">
          <b>Definition:</b> {data.definition.rule}, baseline {data.definition.baseline.join('–')}.<br/>
          <b>Source:</b> {data.definition.source}.<br/>
          <b>Quality:</b> {data.quality.gap_days} gap days, {data.quality.outliers_removed} outliers removed. {data.cached ? 'Served from DB cache.' : 'Freshly ingested.'}
          <button className="sec" onClick={csv}>Download CSV</button><button className="sec" onClick={() => window.print()}>Print / Save PDF</button>
        </div>}
      </aside>
      <section>
        {!data && <div className="card">{busy ? 'Loading…' : 'Pick a region and click Analyse.'}</div>}
        {data && <>
          <div className="card"><div className="head">{data.insight.headline}</div><p>{data.insight.detail}</p>
            {t && <div className="stats">
              {[['events', 'Events / decade'], ['hw_days', 'Heatwave days / decade'], ['max_duration', 'Longest event (days) / decade']].map(([k, n]) =>
                <div className="stat" key={k}><span className="mut">{n}</span><b>{sgn(t[k].sen_per_decade)}</b><span className="mut">Sen slope · p={t[k].mk_p} {t[k].significant ? '✔ significant' : '✘ n.s.'}</span></div>)}</div>}
            <details><summary className="mut">Read before quoting (caveats)</summary><ul>{data.insight.caveats.map((c, i) => <li key={i} className="mut">{c}</li>)}</ul></details>
          </div>
          <div className="card"><b>Heatwave days per year</b><div className="chart"><Chart type="bar" data={daysChart} options={opts(['days'])}/></div></div>
          <div className="card"><b>Frequency, duration & intensity</b><div className="chart"><Chart type="bar" data={evChart} options={opts(['events / days', '°C'])}/></div></div>
          <div className="card"><b>Most severe events</b><table><thead><tr><th>Start</th><th>End</th><th>Days</th><th>Mean excess °C</th><th>Peak Tmax °C</th></tr></thead>
            <tbody>{data.top_events.map((e, i) => <tr key={i}><td>{e.start}</td><td>{e.end}</td><td>{e.days}</td><td>{e.mean_excess}</td><td>{e.peak_tmax}</td></tr>)}</tbody></table></div>
        </>}
      </section>
    </main></>
}
