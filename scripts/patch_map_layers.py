"""Main map: a Grades filter (all, K-5, 6-8, 9-12) and three more layers: bus routes (PPS's current posted runs or this
page's simulated runs for the scenario, D.busmap), bike corridors and drive corridors (D.corr: the streets each
school's attendance-area residents would use). The grade filter applies to the PPS school markers (K-8s count for K-5
and 6-8), the closure and move lines, private schools and private alternatives, the new layers, and switches the
attendance-boundary layer to the same grades when it is on. Lines are drawn on a canvas (hundreds of routes) with hover
text only. Settings are remembered in the browser. Runs after patch_corridors / patch_bus_map. Code added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderMapLayers' not in html:
    rep("""    <div class="controls isoctl"><span>Travel time to school</span>""",
        """    <div class="controls isoctl"><span>Grades</span><span class="seg2" id="gseg"></span><span class="muted" id="gnote"></span></div>
    <div class="controls isoctl maplyr"><span>Layers</span><label>Bus routes <select id="ml-bus"><option value="">Off</option><option value="posted">Current (PPS posted)</option><option value="gen">Simulated, selected scenario</option></select></label>
      <label><input type="checkbox" id="ml-bike"> <span class="ln" style="border-top:3px solid #15803d;width:16px"></span>Bike corridors</label>
      <label><input type="checkbox" id="ml-drive"> <span class="ln" style="border-top:3px solid #b45309;width:16px"></span>Drive corridors</label></div>
    <p class="muted mlnote" id="mlnote"></p>
    <div class="controls isoctl"><span>Travel time to school</span>""")
    rep("""function renderIso() {""", r"""// ---------- grade filter and route / corridor layers (scripts/patch_map_layers.py) ----------
const G_LABEL = [['', 'All'], ['k5', 'K-5'], ['68', '6-8'], ['912', '9-12']];
const BAND_T = { k5: ['ES', 'K8'], '68': ['MS', 'K8'], '912': ['HS'] }, BAND_RANGE = { k5: [0, 5], '68': [6, 8], '912': [9, 12] };
let gBand = '';
try { gBand = localStorage.getItem('rsGrade') || ''; } catch (e) {}
const gradeOK = t => !gBand || BAND_T[gBand].includes(t || 'ES');
const privGradeOK = x => { if (!gBand) return true; const [a, b] = BAND_RANGE[gBand]; return [...(x.g || [])].some(k => k >= a && k <= b); };
map.createPane('routes').style.zIndex = 360;   // above boundaries (340) and travel-time areas (350), under flows (390)
const mlRenderer = L.canvas({ pane: 'routes', tolerance: 5 }), mlLayer = L.layerGroup().addTo(map);
let mlBus = '', mlBike = false, mlDrive = false;
try { const v = JSON.parse(localStorage.getItem('rsMapLayers') || 'null'); if (v) { mlBus = v.bus || ''; mlBike = !!v.bike; mlDrive = !!v.drive; } } catch (e) {}
const mlDec = p => { const out = []; let a = p[0], b = p[1]; out.push([a / 1e5, b / 1e5]); for (let i = 2; i < p.length; i += 2) { a += p[i]; b += p[i + 1]; out.push([a / 1e5, b / 1e5]); } return out; };
const mlHue = k => { let h = 0; for (const c of k) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
function mlSave() { try { localStorage.setItem('rsMapLayers', JSON.stringify({ bus: mlBus, bike: mlBike, drive: mlDrive })); } catch (e) {} }
function renderGradeSeg() {
  const seg = document.getElementById('gseg'); if (!seg) return;
  seg.innerHTML = G_LABEL.map(([k, l]) => `<button data-g="${k}" aria-pressed="${k === gBand}">${l}</button>`).join('');
  seg.onclick = e => { const b = e.target.closest('button'); if (!b) return; gBand = b.dataset.g; try { localStorage.setItem('rsGrade', gBand); } catch (e) {}
    if (gBand && bBand) { bBand = gBand; try { localStorage.setItem('rsBand', bBand); } catch (e) {} }
    renderMap(); };
  document.getElementById('gnote').textContent = gBand ? `Showing schools, lines and layers for grades ${G_LABEL.find(x => x[0] === gBand)[1]}${gBand !== '912' ? ' (K-8 schools count for K-5 and 6-8)' : ''}.` : '';
}
function renderMapLayers() {
  mlLayer.clearLayers();
  const bs = document.getElementById('ml-bus'), bk = document.getElementById('ml-bike'), dr = document.getElementById('ml-drive'); if (!bs) return;
  bs.value = mlBus; bk.checked = mlBike; dr.checked = mlDrive;
  bs.onchange = () => { mlBus = bs.value; mlSave(); renderMapLayers(); };
  bk.onchange = () => { mlBike = bk.checked; mlSave(); renderMapLayers(); };
  dr.onchange = () => { mlDrive = dr.checked; mlSave(); renderMapLayers(); };
  const base = scen === 'C' ? custom.base : scen, typ = k => (D.types[base] || {})[k] || D.types.SQ[k], B = D.busmap, notes = [];
  if (mlBus && B) {
    const R = mlBus === 'posted' ? B.posted : (B.generated[base] || {});
    let runs = 0, riders = 0;
    for (const [k, rs] of Object.entries(R)) {
      const sll = B.schools[k]; if (!sll || !gradeOK(mlBus === 'posted' ? D.types.SQ[k] : typ(k))) continue;
      const col = `hsl(${mlHue(k)} 55% 40%)`, nm = esc(short(byKey[k]?.name || k));
      for (const r of rs) {
        runs++; const rd = r.s.reduce((a, p) => a + (p[2] || 0), 0); riders += rd;
        L.polyline(r.p ? mlDec(r.p) : [...r.s.map(p => [p[0], p[1]]), sll], { renderer: mlRenderer, color: col, weight: 2, opacity: .75, dashArray: mlBus === 'posted' ? '5 4' : null })
          .bindTooltip(`${nm}: ${mlBus === 'posted' ? 'current PPS route' : `simulated ${esc(LABEL[base])} route`}, ${r.s.length} stop${r.s.length === 1 ? '' : 's'}${mlBus === 'gen' ? `, about ${Math.round(rd)} riders` : ''}`, { sticky: true }).addTo(mlLayer);
      }
    }
    notes.push(`<b>Bus routes:</b> ${runs} ${mlBus === 'posted' ? 'current PPS morning runs (posted routes, located stops only)' : `simulated ${esc(LABEL[base])} morning runs, about ${Math.round(riders).toLocaleString()} riders`}${gBand === '912' ? ' (high school students ride TriMet; almost no yellow-bus runs)' : ''}. ` +
      (mlBus === 'gen' ? 'Simulated for illustration only: not PPS plans; built from projected 2027-28 enrollment to estimate bus costs. ' : '') + 'Lines follow the shortest drive path between stops, not the exact bus path.');
  }
  for (const [m, on, col] of [['bike', mlBike, '#15803d'], ['drive', mlDrive, '#b45309']]) {
    if (!on || !D.corr) continue;
    const S0 = D.corr.S[m]; let n = 0;
    for (const k of Object.keys(S0.SQ)) {
      if (D.detail[base]?.[k]?.closed || !gradeOK(typ(k))) continue;
      const r = S0[base]?.[k] || S0.SQ[k]; if (!r) continue; n++;
      const nm = esc(short(byKey[k]?.name || k));
      for (const [lv, p] of r.L) L.polyline(mlDec(p), { renderer: mlRenderer, color: col, weight: [1.4, 2.4, 3.8, 5.5][lv], opacity: .55, lineCap: 'round' })
        .bindTooltip(`${nm}: ${['3-10%', '10-25%', '25-50%', '50%+'][lv]} of its attendance area's school-age residents ${m === 'bike' ? 'would ride' : 'would be driven'} along here`, { sticky: true }).addTo(mlLayer);
    }
    notes.push(`<b>${m === 'bike' ? 'Bike' : 'Drive'} corridors</b> for ${n} schools: the streets each school's attendance-area residents would use ${m === 'bike' ? 'by bike on the lowest-stress route' : 'by car on the fastest route'}; width = share of the school's residents (3-10%, 10-25%, 25-50%, 50%+). Modelled from 2020 Census residents, not counts of trips; the school report lists each school's streets.`);
  }
  document.getElementById('mlnote').innerHTML = notes.join('<br>');
}
function renderIso() {""")
    # the grade filter on the existing layers
    rep("""  for (const s of [...D.schools].sort((x, y) => order[role(x, scen)] - order[role(y, scen)])) {
    const rl = role(s, scen), r = radiusOf(s);""", """  for (const s of [...D.schools].sort((x, y) => order[role(x, scen)] - order[role(y, scen)])) {
    if (!gradeOK(s.type[scen] || s.type.SQ)) continue;
    const rl = role(s, scen), r = radiusOf(s);""")
    rep("""    const a = byKey[mv.from_key], b = byKey[mv.to_key]; if (!a || !b || a === b) continue;""",
        """    const a = byKey[mv.from_key], b = byKey[mv.to_key]; if (!a || !b || a === b) continue;
    if (!gradeOK(a.type[scen] || a.type.SQ) && !gradeOK(b.type[scen] || b.type.SQ)) continue;""")
    rep("""    const a = byKey[r.from_key], b = byKey[r.to_key]; if (!a || !b) continue;
    const g = flowGeometry(a, b), c = css('--close');""", """    const a = byKey[r.from_key], b = byKey[r.to_key]; if (!a || !b) continue;
    if (!gradeOK(b.type[scen] || b.type.SQ)) continue;
    const g = flowGeometry(a, b), c = css('--close');""")
    rep("""    const a = alternatives(s, scen); if (!a) continue;
    nSchools++; if (!a.within.length) nNone++;""", """    const a = alternatives(s, scen); if (!a) continue;
    if (!gradeOK(a.r.kind === 'grades' ? 'MS' : s.type.SQ)) continue;
    nSchools++; if (!a.within.length) nNone++;""")
    rep("""    if (hidePreK && x.preKOnly) continue;
    const sz = Math.round""", """    if (hidePreK && x.preKOnly) continue;
    if (!privGradeOK(x)) continue;
    const sz = Math.round""")
    rep("""  wirePrivate(); renderPrivate(); renderIso(); renderBounds();
  if (dockFn) document.getElementById('dockbody').innerHTML = dockFn();""", """  wirePrivate(); renderPrivate(); renderIso(); renderBounds(); renderGradeSeg(); renderMapLayers();
  if (dockFn) document.getElementById('dockbody').innerHTML = dockFn();""")
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
.maplyr label { display: inline-flex; align-items: center; gap: 4px; } .maplyr .ln { display: inline-block; height: 0; vertical-align: middle; }
.mlnote { font-size: 12px; margin: 0 0 6px; } .mlnote:empty { display: none; }
#map canvas.leaflet-interactive { cursor: grab; }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
