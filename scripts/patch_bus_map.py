"""Before-and-after bus route map at the bottom of the getting-to-school section, collapsed by default: Status Quo
(PPS's posted morning runs, or the generated candidate runs) against the scenario selected at the top (generated
candidate runs; Status Quo selected shows Scenario A; a custom scenario shows its starting scenario), over that
view's K-5 or 6-8 attendance areas. Schools the scenario closes are marked on both views. Lines follow each run's road
path (stops in pickup order, then the school). Data: source/pps-bus/bus-map.json
(scripts/build_bus_map.py). Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['busmap'] = json.load(open(os.path.join(ROOT, 'source', 'pps-bus', 'bus-map.json'), encoding='utf-8'))
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderBusMap' not in html:
    rep("""    <div id="buscost" class="buscost"></div>""", """    <div id="buscost" class="buscost"></div>
    <details id="bmwrap" class="bmwrap"><summary>Bus routes map: before and after</summary>
      <p class="bmnote"><b>Not a plan.</b> These bus routes are not representative of any final PPS plan. The generated routes are candidates this page builds to estimate the bus cost of each scenario (see Estimated yellow-bus cost above); PPS's posted routes show today's service for comparison.</p>
      <div class="controls bmctl"><span class="seg bmseg" id="bm-view"></span>
        <label>Routes <select id="bm-src"><option value="gen">Generated candidate routes</option><option value="posted">PPS posted routes (Status Quo)</option></select></label>
        <label>Attendance areas <select id="bm-band"><option value="k5">K-5</option><option value="68">6-8</option><option value="">Off</option></select></label></div>
      <div id="busmap" class="busmap"></div>
      <p class="sub" id="bm-note"></p>
    </details>""")
    rep(".seg button[aria-pressed=\"true\"] { background: #1c3557; color: #fff; }",
        ".seg button[aria-pressed=\"true\"] { background: #1c3557; color: #fff; }\n"
        ".bmwrap { margin-top: 14px; } .bmnote { margin: 6px 0 4px; padding: 8px 12px; border-left: 4px solid var(--over); border-radius: 4px; background: color-mix(in srgb, var(--over) 14%, transparent); font-size: 13px; line-height: 1.45; } .bmwrap > summary { cursor: pointer; font-weight: 600; font-size: 15px; padding: 6px 0; }\n"
        ".bmctl { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin: 8px 0; } .bmseg button { font-size: 13px; padding: 5px 12px; }\n"
        ".busmap { height: 560px; border-radius: 8px; border: 1px solid var(--line); } @media (max-width: 700px) { .busmap { height: 420px; } }")
    rep("function renderAll() {", r"""// ---------- before-and-after bus route map (D.busmap, scripts/build_bus_map.py) ----------
let bmMap = null, bmLayer = null, bmView = 'before';
const bmAfter = () => { const s = scen === 'C' ? custom.base : scen; return s === 'SQ' ? 'A' : s; };
// road path: [lat0, lng0, dlat, dlng, ...] in steps of 1e-5 degrees (scripts/build_bus_map.py)
function bmDecode(p) { const out = []; let a = p[0], b = p[1]; out.push([a / 1e5, b / 1e5]);
  for (let i = 2; i < p.length; i += 2) { a += p[i]; b += p[i + 1]; out.push([a / 1e5, b / 1e5]); } return out; }
const bmHue = k => { let h = 0; for (const c of k) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
function renderBusMap() {
  const wrap = document.getElementById('bmwrap'); if (!wrap || !wrap.open || typeof L === 'undefined') return;
  if (!bmMap) {
    bmMap = L.map('busmap', { preferCanvas: true, scrollWheelZoom: false }).setView([45.53, -122.64], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(bmMap);
    bmLayer = L.layerGroup().addTo(bmMap);
    ['bm-src', 'bm-band'].forEach(id => document.getElementById(id).onchange = renderBusMap);
  }
  setTimeout(() => bmMap.invalidateSize(), 0);
  const B = D.busmap, after = bmAfter(), sc = bmView === 'before' ? 'SQ' : after;
  const srcSel = document.getElementById('bm-src'), band = document.getElementById('bm-band').value;
  srcSel.options[1].disabled = bmView !== 'before';
  if (bmView !== 'before' && srcSel.value === 'posted') srcSel.value = 'gen';
  const src = srcSel.value;
  const seg2 = document.getElementById('bm-view');
  seg2.innerHTML = [['before', 'Before: Status Quo'], ['after', `After: ${LABEL[after]}`]].map(([v, l]) => `<button data-v="${v}" aria-pressed="${v === bmView}">${l}</button>`).join('');
  seg2.onclick = e => { const b = e.target.closest('button'); if (!b) return; bmView = b.dataset.v; renderBusMap(); };
  bmLayer.clearLayers();
  // attendance areas of the view shown
  const bd = band && D.bounds[`${sc.toLowerCase()}_${band}`];
  if (bd) for (const [label, g] of bd.areas)
    L.geoJSON(g, { interactive: false, style: { color: '#33312c', weight: 1.2, opacity: .6, fillOpacity: 0 } }).bindTooltip(esc(label)).addTo(bmLayer);
  // routes: stops in pickup order, then the school
  const closing = new Set(Object.keys(D.detail[after] || {}).filter(k => D.detail[after][k]?.closed));
  const R = src === 'posted' ? B.posted : (B.generated[sc] || {});
  let nRuns = 0, nStops = 0, riders = 0;
  for (const [k, runs] of Object.entries(R)) {
    const sll = B.schools[k]; if (!sll) continue;
    const cl = closing.has(k), col = cl ? '#c2410c' : `hsl(${bmHue(k)} 55% 42%)`;
    for (const run of runs) {
      const r = run.s, pts = r.map(p => [p[0], p[1]]); nRuns++; nStops += r.length; riders += r.reduce((a, p) => a + (p[2] || 0), 0);
      // road path (stops in order, then the school), else straight lines
      L.polyline(run.p ? bmDecode(run.p) : [...pts, sll], { color: col, weight: cl ? 2.4 : 1.8, opacity: .75, dashArray: cl ? '5 4' : null })
        .bindTooltip(`${esc(short(byKey[k]?.name || k))}: ${r.length} stop${r.length === 1 ? '' : 's'}${src === 'gen' ? `, about ${Math.round(r.reduce((a, p) => a + (p[2] || 0), 0))} riders` : ''}${cl ? ` (closes in ${LABEL[after]})` : ''}`, { sticky: true }).addTo(bmLayer);
      for (const p of pts) L.circleMarker(p, { radius: 2.2, stroke: false, fillColor: col, fillOpacity: .9, interactive: false }).addTo(bmLayer);
    }
  }
  // schools with routes in this view, plus the schools the scenario closes
  for (const [k, ll] of Object.entries(B.schools)) {
    const cl = closing.has(k), here = !!R[k];
    if (!here && !cl) continue;
    const gone = cl && bmView === 'after';
    L.circleMarker(ll, { radius: gone ? 6 : 5, color: '#fff', weight: 1.5, fillColor: gone ? '#9ca3af' : cl ? '#c2410c' : `hsl(${bmHue(k)} 55% 35%)`, fillOpacity: 1 })
      .bindTooltip(`${esc(short(byKey[k]?.name || k))}${cl ? (gone ? ' (closed)' : ` (closes in ${LABEL[after]})`) : ''}`).addTo(bmLayer);
  }
  const G = D.buscost?.gen, t = src === 'gen' ? G?.totals?.[sc] : null;
  document.getElementById('bm-note').innerHTML = `${bmView === 'before' ? 'Status Quo' : esc(LABEL[after])}: <b>${nRuns}</b> morning runs, ${nStops.toLocaleString()} stops` +
    (src === 'gen' ? `, about ${Math.round(riders).toLocaleString()} riders${t ? `, ${Math.round(t.miles).toLocaleString()} road miles, about ${t.buses_morning} buses at the busiest time` : ''} (generated candidate routes, ${esc(B.year)})` : ' (PPS\'s posted routes; located stops only)') +
    `. Lines follow the shortest drive path between each run's stops in pickup order and on to the school (OpenStreetMap streets), not PPS's exact bus path. Dashed orange: routes to schools that close in ${esc(LABEL[after])}${bmView === 'after' ? ' (grey dots: closed schools)' : ''}. ` +
    (scen === 'SQ' ? 'Pick Scenario A or B at the top to compare it. ' : scen === 'C' ? `Custom scenarios show their starting scenario's routes (${esc(LABEL[after])}). ` : '') +
    `${band ? `Lines: ${bmView === 'before' ? 'Status Quo' : esc(LABEL[after])} ${band === 'k5' ? 'K-5' : '6-8'} attendance areas.` : ''} Generated routes: see Estimated yellow-bus cost above for how they are built.`;
}
document.getElementById('bmwrap')?.addEventListener('toggle', renderBusMap);
function renderAll() {""")
    rep("renderHsDistricts(); renderVirtual(); }", "renderHsDistricts(); renderVirtual(); renderBusMap(); }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
