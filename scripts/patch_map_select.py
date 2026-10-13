"""Main map: when a PPS school is clicked (its panel open), the bus route and corridor layers show only that school's
routes: its own runs and corridors, or, for a school the scenario closes, the simulated runs of the schools receiving
its students and the corridors from its Status Quo area to them (D.corr.F). Closing the panel shows every school again.
Runs after patch_map_layers. Code added once.
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

if 'pickClosed = !!(pick' not in html:
    rep("""  const base = scen === 'C' ? custom.base : scen, typ = k => (D.types[base] || {})[k] || D.types.SQ[k], B = D.busmap, notes = [];
  if (mlBus && B) {""", """  const base = scen === 'C' ? custom.base : scen, typ = k => (D.types[base] || {})[k] || D.types.SQ[k], B = D.busmap, notes = [];
  // a school picked on the map: only its routes (a closing school: the routes to the schools receiving its students)
  const pick = isoSel && byKey[isoSel] ? isoSel : null, pickClosed = !!(pick && D.detail[base]?.[pick]?.closed);
  const recv = pick ? new Set([pick, ...(pickClosed ? (D.flows[base]?.receivers || []).filter(r => r.from_key === pick).map(r => r.to_key) : [])]) : null;
  if (pick) notes.push(`Showing routes for <b>${esc(short(byKey[pick].name))}</b> only${pickClosed ? ` (it closes in ${esc(LABEL[base])}: routes to the schools receiving its students)` : ''}; close the school panel to see every school.`);
  if (mlBus && B) {""")
    rep("""      const sll = B.schools[k]; if (!sll || !gradeOK(mlBus === 'posted' ? D.types.SQ[k] : typ(k))) continue;""",
        """      const sll = B.schools[k]; if (!sll || (recv ? !recv.has(k) : !gradeOK(mlBus === 'posted' ? D.types.SQ[k] : typ(k)))) continue;""")
    rep("""    for (const k of Object.keys(S0.SQ)) {
      if (D.detail[base]?.[k]?.closed || !gradeOK(typ(k))) continue;""", """    for (const k of Object.keys(S0.SQ)) {
      if (D.detail[base]?.[k]?.closed || (pick ? k !== pick : !gradeOK(typ(k)))) continue;""")
    rep("""        .bindTooltip(`${nm}: ${['3-10%', '10-25%', '25-50%', '50%+'][lv]} of its attendance area's school-age residents ${m === 'bike' ? 'would ride' : 'would be driven'} along here`, { sticky: true }).addTo(mlLayer);
    }""", """        .bindTooltip(`${nm}: ${['3-10%', '10-25%', '25-50%', '50%+'][lv]} of its attendance area's school-age residents ${m === 'bike' ? 'would ride' : 'would be driven'} along here`, { sticky: true }).addTo(mlLayer);
    }
    if (pickClosed) for (const r of D.corr.F[m]?.[base]?.[pick] || []) {
      n++; const c2 = `hsl(${mlHue(r.to)} 60% 38%)`, to = esc(short(byKey[r.to]?.name || r.to));
      for (const [lv, p] of r.L) L.polyline(mlDec(p), { renderer: mlRenderer, color: c2, weight: [1.6, 2.6, 4, 6][lv], opacity: .7, lineCap: 'round' })
        .bindTooltip(`From ${esc(short(byKey[pick].name))}'s area to ${to}: ${['3-10%', '10-25%', '25-50%', '50%+'][lv]} of those residents ${m === 'bike' ? 'would ride' : 'would be driven'} along here`, { sticky: true }).addTo(mlLayer);
    }""")
    rep("  isoSel = key || null; renderIso(); markSel();", "  isoSel = key || null; renderIso(); markSel(); renderMapLayers();")
# the clicked school's attendance area: Status Quo outline (dashed) and its area under the scenario (filled); a closing
# school's Status Quo area is shaded in the closure color
if 'const selArea' not in html:
    rep("""function renderMapLayers() {""", """const selArea = L.layerGroup().addTo(map);
function renderSelArea() {
  selArea.clearLayers();
  const k = isoSel && byKey[isoSel] ? isoSel : null; if (!k) return;
  const base = scen === 'C' ? custom.base : scen, closed = !!D.detail[base]?.[k]?.closed;
  const BANDS = { ES: ['k5'], K8: ['k5', '68'], MS: ['68'], HS: ['912'] };
  const bands = [...new Set([...(BANDS[D.types.SQ[k]] || []), ...(BANDS[(D.types[base] || {})[k]] || [])])];
  const draw = (g, style) => L.geoJSON(g, { renderer: bRenderer, interactive: false, style }).addTo(selArea);
  for (const b of bands) {
    const S = D.bounds['sq_' + b], C = D.bounds[base.toLowerCase() + '_' + b];
    if (base !== 'SQ' && !closed && C?.akeys) C.areas.forEach(([, g], i) => { if (C.akeys[i] === k) draw(g, { color: css('--change'), weight: 2.5, opacity: .95, fillColor: css('--change'), fillOpacity: .16 }); });
    if (S?.akeys) S.areas.forEach(([, g], i) => { if (S.akeys[i] === k) draw(g, base === 'SQ' ? { color: css('--change'), weight: 2.5, opacity: .95, fillColor: css('--change'), fillOpacity: .16 }
      : closed ? { color: css('--close'), weight: 2.5, dashArray: '6 4', opacity: .95, fillColor: css('--close'), fillOpacity: .14 } : { color: '#33312c', weight: 2, dashArray: '6 4', opacity: .85, fill: false }); });
  }
}
function renderMapLayers() {
  renderSelArea();""")
    rep("""  if (pick) notes.push(`Showing routes for <b>${esc(short(byKey[pick].name))}</b> only${pickClosed ? ` (it closes in ${esc(LABEL[base])}: routes to the schools receiving its students)` : ''}; close the school panel to see every school.`);""",
        """  if (pick) notes.push(`<b>${esc(short(byKey[pick].name))}</b>: ${base === 'SQ' ? 'attendance area shaded' : pickClosed ? `Status Quo attendance area shaded (it closes in ${esc(LABEL[base])})` : `${esc(LABEL[base])} attendance area shaded, Status Quo area dashed`}; routes shown for this school only${pickClosed ? ' (to the schools receiving its students)' : ''}. Close the school panel to see every school.`);""")
# a click on the map outside the PPS district (all attendance areas) closes the school panel; clicks on school markers
# open that school instead
if 'function clickOutsideSel' not in html:
    rep("""function renderMapLayers() {
  renderSelArea();""", """// the PPS district: the high school attendance areas together (bounding boxes first, for speed)
let PPS_AREA = null;
function inPPS(x, y) {
  if (!PPS_AREA) PPS_AREA = (D.bounds.sq_912?.areas || []).map(([, g]) => { const bb = [Infinity, Infinity, -Infinity, -Infinity];
    for (const poly of g.type === 'Polygon' ? [g.coordinates] : g.coordinates) for (const [px, py] of poly[0]) { bb[0] = Math.min(bb[0], px); bb[1] = Math.min(bb[1], py); bb[2] = Math.max(bb[2], px); bb[3] = Math.max(bb[3], py); }
    return { g, bb }; });
  return PPS_AREA.some(a => x >= a.bb[0] && x <= a.bb[2] && y >= a.bb[1] && y <= a.bb[3] && ptInGeom(x, y, a.g));
}
function clickOutsideSel(e) {
  if (!dockFn) return;
  const { lng: x, lat: y } = e.latlng;
  if (!inPPS(x, y)) closeDock();
}
map.on('click', clickOutsideSel);
function renderMapLayers() {
  renderSelArea();""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
