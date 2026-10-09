"""Check page for the PPS bus routes: shows how scripts/fetch_pps_bus.py parsed each route PDF and how
scripts/estimate_bus_cost.py located and measured it, so both can be checked against the PDFs.

Runs the first part of estimate_bus_cost.py unchanged (route selection, stop geocoding, school matching, drive network,
runs), then finds the road path of every leg it measures and writes archive/bus-route-check.html (not published):
  - each run's measured road path, its stops joined in schedule order, and the school end
  - stops coloured by how they were located (address, intersection, street near neighbours, nearest pair), with the
    PDF's stop text, time and side; stops that could not be located are listed per run
  - flags: stops not located, a straight-line jump over JUMP_MI between consecutive stops, a road path more than
    DETOUR x the straight line, times out of order, a leg with no road path, routes skipped (no school match, too few
    stops located)
  - a link to each route's PDF on Google Drive
Open at http://127.0.0.1:8000/archive/bus-route-check.html with the local server running.
Usage: python scripts/build_bus_check.py
"""
import json, math, os, re, sys
import numpy as np
from scipy.sparse.csgraph import dijkstra
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JUMP_MI, DETOUR = 2.0, 3.0

# the estimate script's own processing, up to (not including) its leg measurement
src = open(os.path.join(ROOT, 'scripts', 'estimate_bus_cost.py'), encoding='utf-8').read()
cut = src.index('\nlegs = {')
g = {'__file__': os.path.join(ROOT, 'scripts', 'estimate_bus_cost.py'), '__name__': 'bus_check'}
exec(compile(src[:cut], 'estimate_bus_cost.py', 'exec'), g)
R, runs, geo, G, LON, LAT, MILE, school_of, mins = (g[k] for k in ('R', 'runs', 'geo', 'G', 'LON', 'LAT', 'MILE', 'school_of', 'mins'))
ALL = json.load(open(os.path.join(ROOT, 'source', 'pps-bus', 'pps-bus-routes.json'), encoding='utf-8'))['routes']
byroute = {r['route']: r for r in R}
SCH = {s['key']: s for s in g['school_at'].values()}   # the explorer's schools plus ACCESS

# road path of every leg: shortest paths with predecessors, in batches of sources
legs = {(a, b) for x in runs for a, b in zip(x['nodes'][:-1], x['nodes'][1:]) if a != b}
by_src = {}
for a, b in legs: by_src.setdefault(a, []).append(b)
srcs, path = sorted(by_src), {}
for i in range(0, len(srcs), 25):
    bt = srcs[i:i + 25]
    d, pred = dijkstra(G, directed=True, indices=bt, limit=40000, return_predecessors=True)
    for j, a in enumerate(bt):
        for b in by_src[a]:
            if not np.isfinite(d[j, b]): path[a, b] = None; continue
            seq, n = [b], b
            while n != a and n >= 0: n = pred[j, n]; seq.append(n)
            path[a, b] = (seq[::-1], float(d[j, b]))
    if i % 500 == 0: print(f'paths {i}/{len(srcs)}')
r5 = lambda v: round(float(v), 5)
def straight(p, q):
    k = math.cos(math.radians(45.53))
    return math.hypot((p[0] - q[0]) * k, p[1] - q[1]) * 69.05

out, issues = [], {}
for x in runs:
    r = byroute[x['route']]
    s = SCH[x['school']]
    geom, miles, flags, nopath = [], 0.0, [], 0
    for a, b in zip(x['nodes'][:-1], x['nodes'][1:]):
        if a == b: continue
        p = path.get((a, b))
        if not p: nopath += 1; continue
        miles += p[1] / MILE
        geom.append([[r5(LAT[n]), r5(LON[n])] for n in p[0]])
    st = [t for t in r['stops'] if not t['loading_zone']]
    stops = [dict(t=t['time'], loc=t['location'], side=t['side'], ll=[r5(geo[t['location']][1]), r5(geo[t['location']][0])] if t['location'] in geo else None,
                  m=geo[t['location']][2] if t['location'] in geo else 'not located') for t in st]
    pts = [q['ll'] for q in stops if q['ll']]
    seq = (pts + [[s['lat'], s['lng']]]) if x['period'] == 'morning' else ([[s['lat'], s['lng']]] + pts)
    line = sum(straight((p[1], p[0]), (q[1], q[0])) for p, q in zip(seq[:-1], seq[1:]))
    if x['n_missing']: flags.append(f"{x['n_missing']} stop{'s' if x['n_missing'] > 1 else ''} not located")
    jumps = [round(straight((p[1], p[0]), (q[1], q[0])), 1) for p, q in zip(pts[:-1], pts[1:]) if straight((p[1], p[0]), (q[1], q[0])) > JUMP_MI]
    if jumps: flags.append(f"jump of {max(jumps)} mi between stops")
    if line and miles / line > DETOUR: flags.append(f'road path {miles / line:.1f}x the straight line')
    if nopath: flags.append(f'{nopath} leg{"s" if nopath > 1 else ""} with no road path')
    tt = [mins(t['time']) for t in r['stops']]
    if any(b < a for a, b in zip(tt[:-1], tt[1:])): flags.append('times out of order')
    for f in flags: issues[re.sub(r'[\d.]+', 'N', f)] = issues.get(re.sub(r'[\d.]+', 'N', f), 0) + 1
    out.append(dict(route=x['route'], period=x['period'], school=x['school'], sll=[s['lat'], s['lng']], file=r['file'], drive=r['drive_id'],
                    anchor=r['anchor'], eff=r['effective'], miles=round(miles, 2), line=round(line, 2), stops=stops,
                    lz=[dict(t=t['time'], loc=t['location']) for t in r['stops'] if t['loading_zone']], geom=geom, flags=flags))
measured = {x['route'] for x in runs}
skipped = []
for r in R:
    if r['route'] in measured: continue
    st = [t for t in r['stops'] if not t['loading_zone']]
    why = 'no school match' if not school_of(r) else f"{sum(t['location'] not in geo for t in st)} of {len(st)} stops not located"
    skipped.append(dict(route=r['route'], file=r['file'], drive=r['drive'] if 'drive' in r else r['drive_id'], pages=r['pages'], anchor=r['anchor'], why=why,
                        stops=[dict(t=t['time'], loc=t['location'], m=geo[t['location']][2] if t['location'] in geo else 'not located') for t in st]))
meth = {}
for x in out:
    for q in x['stops']: meth[q['m']] = meth.get(q['m'], 0) + 1
summary = dict(parsed=len(ALL), current=len(R), snow=sum(1 for r in ALL if r['snow']), outdated=sum(1 for r in ALL if not r['current']),
               measured=len(out), skipped=len(skipped), flagged=sum(1 for x in out if x['flags']), methods=meth, issues=issues,
               miles=round(sum(x['miles'] for x in out)))
print(json.dumps(summary, indent=1))

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bus Route Check</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
:root { --bg: #f6f5f1; --panel: #fff; --text: #1d1d1b; --muted: #6b6a64; --line: #e2e0d8; --flag: #b4511f; --sel: #1c3557; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #16171a; --panel: #1f2024; --text: #ecebe6; --muted: #a3a29b; --line: #34353a; --flag: #f0955e; --sel: #8fb3ff; } }
:root[data-theme="dark"] { --bg: #16171a; --panel: #1f2024; --text: #ecebe6; --muted: #a3a29b; --line: #34353a; --flag: #f0955e; --sel: #8fb3ff; }
* { box-sizing: border-box; } body { margin: 0; font: 14px/1.4 system-ui, sans-serif; background: var(--bg); color: var(--text); }
.wrap { display: grid; grid-template-columns: 400px 1fr; height: 100vh; }
@media (max-width: 800px) { .wrap { grid-template-columns: 1fr; grid-template-rows: 55vh auto; height: auto; } #map { order: -1; height: 55vh; } }
aside { overflow: auto; padding: 12px 16px; background: var(--panel); border-right: 1px solid var(--line); }
#map { height: 100%; } h1 { font-size: 18px; margin: 0 0 6px; } h2 { font-size: 14px; margin: 14px 0 6px; }
.sum { font-size: 12.5px; color: var(--muted); } .sum b { color: var(--text); }
.ctl { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; } select, input, button { font: inherit; font-size: 13px; padding: 4px 6px; background: var(--panel); color: var(--text); border: 1px solid var(--line); border-radius: 6px; }
.run { padding: 6px 8px; border-bottom: 1px solid var(--line); cursor: pointer; } .run:hover { background: color-mix(in srgb, var(--sel) 8%, transparent); }
.run.on { outline: 2px solid var(--sel); outline-offset: -2px; } .run .f { color: var(--flag); font-size: 12px; } .run .m { color: var(--muted); font-size: 12px; }
table { border-collapse: collapse; width: 100%; font-size: 12px; } td, th { padding: 3px 4px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; vertical-align: -1px; }
.legend span { margin-right: 10px; font-size: 12px; white-space: nowrap; } a { color: var(--sel); }
</style></head><body>
<div class="wrap"><aside>
<h1>Bus route check</h1>
<div class="sum" id="sum"></div>
<div class="legend" id="legend"></div>
<div class="ctl"><select id="school"><option value="">All schools</option></select>
<select id="show"><option value="all">Posted runs</option><option value="flag">Flagged posted runs</option><option value="skip">Skipped routes</option></select>
<input id="q" placeholder="Route or stop" size="12"></div>
<div id="detail"></div><h2 id="listh"></h2><div id="list"></div>
</aside><div id="map"></div></div>
<script>
const B = __DATA__;
const COL = { 'census-address': '#2f6fd1', 'osm-intersection': '#2e9e5b', 'osm-street-near-neighbours': '#e08a1e', 'osm-nearest-pair': '#9b4dca', 'not located': '#c8312b' };
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const pdf = id => `https://drive.google.com/file/d/${id}/view`;
const S = B.summary;
document.getElementById('sum').innerHTML = `<b>${S.parsed}</b> route PDFs parsed: <b>${S.current}</b> current non-snow (${S.outdated} outdated, ${S.snow} snow routes left out). ` +
  `<b>${S.measured}</b> runs measured (${S.miles.toLocaleString()} road miles), <b>${S.skipped}</b> skipped, <b>${S.flagged}</b> flagged. ` +
  `Stops: ${Object.entries(S.methods).map(([k, v]) => `${esc(k)} ${v.toLocaleString()}`).join(', ')}. ` +
  `Flags: ${Object.entries(S.issues).map(([k, v]) => `${esc(k.replace(/N/g, 'n'))} (${v})`).join('; ') || 'none'}.`;
document.getElementById('legend').innerHTML = Object.entries(COL).map(([k, c]) => `<span><span class="sw" style="background:${c}"></span>${k}</span>`).join('') +
  '<span>solid: road path &middot; dashed: stops in order &middot; square: school</span>';
const map = L.map('map', { preferCanvas: true }).setView([45.53, -122.65], 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
const all = L.layerGroup().addTo(map), sel = L.layerGroup().addTo(map);
const schools = [...new Set([...B.runs.map(r => r.school), ...Object.keys(B.gen?.schools || {})])].sort();
document.getElementById('school').innerHTML += schools.map(s => `<option>${esc(s)}</option>`).join('');
let cur = null;
// generated candidate routes: one option per scenario, each run shaped like a posted run (straight lines between stops)
const GL = { SQ: 'Status Quo', A: 'Scenario A', B: 'Scenario B' }, GEN = {};
if (B.gen) {
  const sel_ = document.getElementById('show');
  sel_.innerHTML += Object.keys(B.gen.runs).map(sc => `<option value="gen-${sc}">Generated: ${GL[sc]} ${B.gen.year}</option>`).join('');
  for (const [sc, bySchool] of Object.entries(B.gen.runs)) GEN[sc] = Object.entries(bySchool).flatMap(([k, rs]) => rs.map((r, i) => ({
    route: `${k} #${i + 1}`, school: k, period: 'morning', gen: sc, sll: B.gen.schools[k].ll, miles: r.miles, minutes: r.minutes, riders: r.riders, flags: [],
    stops: r.stops.map(s => ({ t: '', loc: `${s[2]} riders`, ll: [s[0], s[1]], m: 'generated' })) })));
  const G = B.gen, T = G.totals, C = G.calibration, P = G.params, mx = String(P.max_ride_min);
  document.getElementById('sum').innerHTML += `<br><br><b>Generated routes</b> (${G.year}, morning): ` + Object.entries(T).map(([sc, t]) =>
    `${GL[sc]} ${t.runs} runs, ${t.stops.toLocaleString()} stops, ${t.riders.toLocaleString()} riders, ${Math.round(t.miles).toLocaleString()} mi, ${t.buses_morning} buses` +
    (G.change[sc] ? ` (${G.change[sc].runs >= 0 ? '+' : ''}${G.change[sc].runs} runs, ${G.change[sc].miles >= 0 ? '+' : ''}${Math.round(G.change[sc].miles)} mi)` : '')).join('; ') +
    `. Calibrated on ${C.posted.schools} schools' posted ${C.year} routes: posted ${C.posted.runs} runs, ${C.posted.stops_per_run} stops a run, ${C.posted.mean_minutes} min, ${Math.round(C.posted.miles)} mi; ` +
    `generated ${C.generated[mx].runs} runs, ${C.generated[mx].stops_per_run} stops a run, ${C.generated[mx].mean_minutes} min, ${Math.round(C.generated[mx].miles)} mi ` +
    `(max ride ${P.max_ride_min} min, max ${P.max_stops} stops, ${P.capacity} riders, ${P.min_per_road_mile} min per road mile + ${P.min_per_stop} min per stop, ${Math.round(100 * P.ride_share)}% of eligible students ride).`;
  COL.generated = '#d0367a';
  document.getElementById('legend').innerHTML += '<span><span class="sw" style="background:#d0367a"></span>generated stop / run</span>';
}
function filtered() {
  const sc = document.getElementById('school').value, sh = document.getElementById('show').value, q = document.getElementById('q').value.trim().toUpperCase();
  const src = sh.startsWith('gen-') ? GEN[sh.slice(4)] : sh === 'skip' ? B.skipped : B.runs.filter(r => sh !== 'flag' || r.flags.length);
  return src.filter(r => (!sc || r.school === sc) && (!q || r.route.includes(q) || r.stops.some(s => s.loc.includes(q))));
}
function drawAll(list) {
  all.clearLayers();
  for (const r of list) {
    if (r.geom) for (const g of r.geom) L.polyline(g, { color: r.flags.length ? '#c8312b' : '#5a6b85', weight: 1.5, opacity: .45 }).on('click', () => pick(r)).addTo(all);
    else if (r.gen) L.polyline([...r.stops.map(s => s.ll), r.sll], { color: '#d0367a', weight: 1.5, opacity: .5 }).on('click', () => pick(r)).addTo(all);
  }
}
function pick(r) {
  cur = r; sel.clearLayers();
  document.querySelectorAll('.run').forEach(e => e.classList.toggle('on', e.dataset.r === r.route));
  const b = [];
  if (r.geom) for (const g of r.geom) { L.polyline(g, { color: '#1c3557', weight: 5, opacity: .85 }).addTo(sel); b.push(...g); }
  const pts = r.stops.filter(s => s.ll).map(s => s.ll);
  if (r.sll) { const seq = r.period === 'morning' ? [...pts, r.sll] : [r.sll, ...pts]; L.polyline(seq, { color: '#e0a400', weight: 2, dashArray: '5 6' }).addTo(sel);
    L.marker(r.sll, { icon: L.divIcon({ className: '', html: '<div style="width:14px;height:14px;background:#1c3557;border:2px solid #fff"></div>', iconSize: [14, 14] }) })
      .bindTooltip(esc(r.school)).addTo(sel); b.push(r.sll); }
  r.stops.forEach((s, i) => { if (!s.ll) return; b.push(s.ll);
    L.circleMarker(s.ll, { radius: 7, color: '#fff', weight: 1.5, fillColor: COL[s.m] || '#888', fillOpacity: 1 })
      .bindTooltip(`<b>${i + 1}. ${esc(s.t)}</b> ${esc(s.loc)}${s.side ? ' (' + esc(s.side) + ' side)' : ''}<br>${esc(s.m)}: ${s.ll.join(', ')}`).addTo(sel); });
  if (b.length) map.fitBounds(b, { padding: [30, 30], maxZoom: 16 });
  document.getElementById('detail').innerHTML = `<h2>${esc(r.route)} &middot; ${esc(r.school || r.pages?.join(', '))} ${r.period ? '&middot; ' + r.period : ''}</h2>` +
    (r.gen ? `<div class="m">Generated candidate run, ${GL[r.gen]} ${B.gen.year}: ${r.stops.length} stops, ${r.riders} riders (estimated), ${r.miles} road miles, about ${r.minutes} min first stop to school. Lines are straight between stops.</div>`
      : `<div class="m">${esc(r.anchor)} &middot; effective ${esc(r.eff || '')} &middot; <a href="${pdf(r.drive)}" target="_blank" rel="noopener">${esc(r.file)}</a></div>` +
    (r.why ? `<div class="f" style="color:var(--flag)">Skipped: ${esc(r.why)}</div>` : `<div class="m">${r.miles} road miles (straight-line ${r.line} mi)</div>`)) +
    (r.flags?.length ? `<div style="color:var(--flag)">${r.flags.map(esc).join('<br>')}</div>` : '') +
    `<table><tr><th>#</th><th>Time</th><th>Stop (PDF text)</th><th>Located by</th></tr>` +
    (r.lz || []).filter((_, i) => r.period === 'afternoon' && i === 0).map(z => `<tr><td></td><td>${esc(z.t)}</td><td><i>${esc(z.loc)}</i></td><td>school</td></tr>`).join('') +
    r.stops.map((s, i) => `<tr><td>${i + 1}</td><td>${esc(s.t)}</td><td>${esc(s.loc)}${s.side ? ` <span class="m">(${esc(s.side)})</span>` : ''}</td><td><span class="sw" style="background:${COL[s.m] || '#888'}"></span>${esc(s.m)}</td></tr>`).join('') +
    (r.lz || []).filter((_, i, a) => r.period === 'morning' && i === a.length - 1).map(z => `<tr><td></td><td>${esc(z.t)}</td><td><i>${esc(z.loc)}</i></td><td>school</td></tr>`).join('') + '</table>';
}
function render() {
  const list = filtered(), sh = document.getElementById('show').value;
  drawAll(sh === 'skip' ? [] : list);
  document.getElementById('listh').textContent = `${list.length} ${sh === 'skip' ? 'skipped routes' : 'runs'}`;
  document.getElementById('list').innerHTML = list.map(r => `<div class="run" data-r="${esc(r.route)}"><b>${esc(r.route)}</b> <span class="m">${esc(r.school || r.pages?.join(', '))}${r.period ? ' &middot; ' + r.period : ''} &middot; ${r.stops.length} stops${r.miles != null ? ' &middot; ' + r.miles + ' mi' : ''}</span>` +
    (r.why ? `<div class="f">${esc(r.why)}</div>` : r.flags.length ? `<div class="f">${r.flags.map(esc).join('; ')}</div>` : '') + '</div>').join('');
  document.querySelectorAll('.run').forEach(e => e.onclick = () => pick(list.find(r => r.route === e.dataset.r)));
}
['school', 'show'].forEach(id => document.getElementById(id).onchange = render);
document.getElementById('q').oninput = render;
render();
</script></body></html>
"""
os.makedirs(os.path.join(ROOT, 'archive'), exist_ok=True)
# generated candidate routes (scripts/build_bus_routes.py), shown as extra layers when present
GEN = os.path.join(ROOT, 'source', 'pps-bus', 'generated-routes.json')
gen = None
if os.path.exists(GEN):
    J = json.load(open(GEN, encoding='utf-8'))
    gen = {k: J[k] for k in ('year', 'params', 'calibration', 'totals', 'change', 'runs', 'schools')}
    gen['calibration'] = {k: v for k, v in J['calibration'].items() if k != 'posted_by_school'}
data = json.dumps(dict(summary=summary, runs=out, skipped=skipped, gen=gen), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
open(os.path.join(ROOT, 'archive', 'bus-route-check.html'), 'w', encoding='utf-8', newline='\n').write(PAGE.replace('__DATA__', data))
print('wrote archive/bus-route-check.html', f'{os.path.getsize(os.path.join(ROOT, "archive", "bus-route-check.html")) / 1e6:.1f} MB')
