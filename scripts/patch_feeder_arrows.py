"""Main map: a "Feeder arrows" layer. Arrows from each school to the school its students go on to (elementary to middle,
middle to high, K-8 or elementary to high when there is no middle school), from the feeder patterns of the scenario
being viewed (D.feeders; a custom scenario uses its base scenario's). Program feeders (immersion etc.) are dashed.
Schools the scenario closes are left out. Follows the grade filter (an arrow shows when either end is in it); with a
school picked, only its feeder chain. Hover an arrow for the program. Off by default; remembered with the other
layers. Redrawn on zoom (the curves avoid school markers). Code added once.
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

if 'renderFeeders' not in html:
    rep("""<label><input type="checkbox" id="ml-flows"> Closure arrows</label>""",
        """<label><input type="checkbox" id="ml-flows"> Closure arrows</label><label title="Arrows from each school to the school its students go on to, in the scenario being viewed"><input type="checkbox" id="ml-feed"> <span class="ln" style="border-top:3px solid #7c3aed;width:16px"></span>Feeder arrows</label>""")
    rep("""let mlBus = '', mlBike = true, mlDrive = false, mlWalk = false, mlHz = true;
try { const v = JSON.parse(localStorage.getItem('rsMapLayers2') || 'null'); if (v) { mlBus = v.bus || ''; mlBike = !!v.bike; mlDrive = !!v.drive; mlWalk = !!v.walk; mlHz = v.hz !== false; } } catch (e) {}""",
        """const feedLayer = L.layerGroup().addTo(map);   // feeder arrows (scripts/patch_feeder_arrows.py)
let mlBus = '', mlBike = true, mlDrive = false, mlWalk = false, mlHz = true, mlFeed = false;
try { const v = JSON.parse(localStorage.getItem('rsMapLayers2') || 'null'); if (v) { mlBus = v.bus || ''; mlBike = !!v.bike; mlDrive = !!v.drive; mlWalk = !!v.walk; mlHz = v.hz !== false; mlFeed = !!v.feed; } } catch (e) {}""")
    rep("""JSON.stringify({ bus: mlBus, bike: mlBike, drive: mlDrive, walk: mlWalk, hz: mlHz })""",
        """JSON.stringify({ bus: mlBus, bike: mlBike, drive: mlDrive, walk: mlWalk, hz: mlHz, feed: mlFeed })""")
    rep("""  if (hzb) { hzb.checked = mlHz; hzb.onchange = () => { mlHz = hzb.checked; mlSave(); renderMapLayers(); }; }
""", """  if (hzb) { hzb.checked = mlHz; hzb.onchange = () => { mlHz = hzb.checked; mlSave(); renderMapLayers(); }; }
  const fdb = document.getElementById('ml-feed');
  if (fdb) { fdb.checked = mlFeed; fdb.onchange = () => { mlFeed = fdb.checked; mlSave(); renderMapLayers(); }; }
""")
    rep("""  document.getElementById('mlnote').innerHTML = notes.join('<br>');
}""", """  const fn = renderFeeders(); if (fn) notes.push(fn);
  document.getElementById('mlnote').innerHTML = notes.join('<br>');
}
// feeder arrows (scripts/patch_feeder_arrows.py): D.feeders[base] rows [elementary, middle, high, program, note, ...]
function renderFeeders() {
  feedLayer.clearLayers(); lHits = lHits.filter(h => h.set !== 'fd'); if (bHover && bHover.set === 'fd') setBHover(null);
  if (!mlFeed) return '';
  const base = scen === 'C' ? custom.base : scen, F = (D.feeders || {})[base] || D.feeders?.SQ || [];
  const typ = k => (D.types[base] || {})[k] || D.types.SQ[k], shut = k => (D.detail[scen] || {})[k]?.closed;
  const pick = isoSel && byKey[isoSel] ? isoSel : null;
  const E = new Map();
  for (const [es, ms, hs, pg] of F) {
    if (pick && ![es, ms, hs].includes(pick)) continue;
    const prog = pg && !/^neighborhood$/i.test(pg) ? pg : '';
    for (const [a, b] of [[es, ms || hs], [ms, hs]]) {
      if (!a || !b || a === b || !byKey[a] || !byKey[b] || shut(a) || shut(b)) continue;
      if (!pick && !gradeOK(typ(a)) && !gradeOK(typ(b))) continue;
      const id = a + '|' + b, e = E.get(id) || { a, b, progs: new Set(), nb: false };
      if (prog) e.progs.add(prog); else e.nb = true;
      E.set(id, e);
    }
  }
  const col = '#7c3aed';
  for (const e of E.values()) {
    const g = flowGeometry(byKey[e.a], byKey[e.b]), progOnly = !e.nb;
    const what = [e.nb ? 'neighborhood students' : '', ...[...e.progs].map(p => p + ' students')].filter(Boolean).join('; ');
    regLine('fd', L.polyline(g.pts, { pane: 'flows', interactive: false, color: col, weight: 2.5, opacity: .85, dashArray: progOnly ? '6 5' : null }),
      `Feeder: ${esc(short(byKey[e.a].name))} → ${esc(short(byKey[e.b].name))} (${esc(what)})`).addTo(feedLayer);
    arrow(g, col).addTo(feedLayer);
  }
  return `<b>Feeder arrows:</b> ${E.size} links, ${esc(base === 'SQ' ? 'Status Quo' : LABEL[base])} feeder patterns${scen === 'C' ? ' (the custom scenario\\u2019s base)' : ''}${pick ? `, ${esc(short(byKey[pick].name))}\\u2019s chain only` : ''}: each school to the school its students go on to; dashed = program students only (immersion etc.). Schools that close are left out.`;
}
map.on('zoomend', () => { if (mlFeed) renderFeeders(); });""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
