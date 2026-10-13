"""Arterial hazards (D.corr .H / .hx, scripts/build_block_access.py): where walking and biking routes to school cross a
major arterial (state highways and primary or secondary arterials) or run along one for 40 m or more (bikes: outside
paths and protected, separated or buffered bike lanes; standard and advisory lanes count).
  - main map: walk corridors as a layer, and an "Arterial hazards" toggle (on) that marks the hazards of the walk and
    bike corridor layers shown: district-wide the hazards on at least 10% of a school's residents' routes; with a school
    clicked, all of that school's (or, for a closing school, its students' routes to their new schools)
  - getting to school table: under the walk and bike histograms of every region and school row, the students whose
    route crosses or runs along a major arterial (each school's share of residents x its students in the table's
    grades and year) and the number of hazard points on the routes
Runs after patch_map_layers / patch_map_select / patch_corridors. Code added once.
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

HZ_SVG = ('<svg width="16" height="14" viewBox="0 0 18 16"><path d="M9 1 L17 15 L1 15 Z" fill="#f2b705" stroke="#5a3d00" stroke-width="1.3" stroke-linejoin="round"/>'
          '<path d="M9 5.5 V10" stroke="#3a2a00" stroke-width="1.8" stroke-linecap="round"/><circle cx="9" cy="12.6" r="1" fill="#3a2a00"/></svg>')

if 'function mlHazards' not in html:
    # ---- main map: walk corridors and the hazards toggle ----
    rep("""      <label><input type="checkbox" id="ml-bike"> <span class="ln" style="border-top:3px solid #15803d;width:16px"></span>Bike corridors</label>""",
        """      <label><input type="checkbox" id="ml-walk"> <span class="ln" style="border-top:3px solid #2563eb;width:16px"></span>Walk corridors</label>
      <label><input type="checkbox" id="ml-bike"> <span class="ln" style="border-top:3px solid #15803d;width:16px"></span>Bike corridors</label>""")
    rep("""      <label><input type="checkbox" id="ml-drive"> <span class="ln" style="border-top:3px solid #b45309;width:16px"></span>Drive corridors</label></div>""",
        f"""      <label><input type="checkbox" id="ml-drive"> <span class="ln" style="border-top:3px solid #b45309;width:16px"></span>Drive corridors</label>
      <label title="Where walk and bike corridors cross a major arterial or run along one"><input type="checkbox" id="ml-hz"> {HZ_SVG} Arterial hazards</label></div>""")
    rep("let mlBus = '', mlBike = true, mlDrive = false;", "let mlBus = '', mlBike = true, mlDrive = false, mlWalk = false, mlHz = true;")
    rep("if (v) { mlBus = v.bus || ''; mlBike = !!v.bike; mlDrive = !!v.drive; }", "if (v) { mlBus = v.bus || ''; mlBike = !!v.bike; mlDrive = !!v.drive; mlWalk = !!v.walk; mlHz = v.hz !== false; }")
    rep("JSON.stringify({ bus: mlBus, bike: mlBike, drive: mlDrive })", "JSON.stringify({ bus: mlBus, bike: mlBike, drive: mlDrive, walk: mlWalk, hz: mlHz })")
    rep("""  dr.onchange = () => { mlDrive = dr.checked; mlSave(); renderMapLayers(); };""",
        """  dr.onchange = () => { mlDrive = dr.checked; mlSave(); renderMapLayers(); };
  const wk = document.getElementById('ml-walk'), hzb = document.getElementById('ml-hz');
  if (wk) { wk.checked = mlWalk; wk.onchange = () => { mlWalk = wk.checked; mlSave(); renderMapLayers(); }; }
  if (hzb) { hzb.checked = mlHz; hzb.onchange = () => { mlHz = hzb.checked; mlSave(); renderMapLayers(); }; }""")
    rep("""  for (const [m, on, col] of [['bike', mlBike, '#15803d'], ['drive', mlDrive, '#b45309']]) {""",
        """  for (const [m, on, col] of [['walk', mlWalk, '#2563eb'], ['bike', mlBike, '#15803d'], ['drive', mlDrive, '#b45309']]) {""")
    rep("""        .bindTooltip(`${nm}: ${['3-10%', '10-25%', '25-50%', '50%+'][lv]} of its attendance area's school-age residents ${m === 'bike' ? 'would ride' : 'would be driven'} along here`, { sticky: true }).addTo(mlLayer);
    }""", """        .bindTooltip(`${nm}: ${['3-10%', '10-25%', '25-50%', '50%+'][lv]} of its attendance area's school-age residents ${{ walk: 'would walk', bike: 'would ride', drive: 'would be driven' }[m]} along here`, { sticky: true }).addTo(mlLayer);
      if (m !== 'drive') mlHazards(r, m, nm, !!pick);
    }""")
    rep("""        .bindTooltip(`From ${esc(short(byKey[pick].name))}'s area to ${to}: ${['3-10%', '10-25%', '25-50%', '50%+'][lv]} of those residents ${m === 'bike' ? 'would ride' : 'would be driven'} along here`, { sticky: true }).addTo(mlLayer);
    }""", """        .bindTooltip(`From ${esc(short(byKey[pick].name))}'s area to ${to}: ${['3-10%', '10-25%', '25-50%', '50%+'][lv]} of those residents ${{ walk: 'would walk', bike: 'would ride', drive: 'would be driven' }[m]} along here`, { sticky: true }).addTo(mlLayer);
      if (m !== 'drive') mlHazards(r, m, `${esc(short(byKey[pick].name))}'s area to ${to}`, true);
    }""")
    rep("""    notes.push(`<b>${m === 'bike' ? 'Bike' : 'Drive'} corridors</b> for ${n} schools: the streets each school's attendance-area residents would use ${m === 'bike' ? 'by bike on the lowest-stress route' : 'by car on the fastest route'}; width = share of the school's residents (3-10%, 10-25%, 25-50%, 50%+). Modelled from 2020 Census residents, not counts of trips; the school report lists each school's streets.`);""",
        """    notes.push(`<b>${{ walk: 'Walk', bike: 'Bike', drive: 'Drive' }[m]} corridors</b> for ${n} schools: the streets each school's attendance-area residents would use ${{ walk: 'on foot by the shortest walking route', bike: 'by bike on the lowest-stress route', drive: 'by car on the fastest route' }[m]}; width = share of the school's residents (3-10%, 10-25%, 25-50%, 50%+). Modelled from 2020 Census residents, not counts of trips; the school report lists each school's streets.` +
      (m !== 'drive' && mlHz ? ` <span class="hzsym">&#9888;</span> Hazards: where these routes cross a major arterial or run along one${m === 'bike' ? ' outside a path or protected / buffered bike lane' : ''}${pick ? '' : ' (on at least 10% of a school\\'s residents\\' routes; click a school for all of its own)'}; signals and crosswalks are not known.` : ''));""")
    rep("""function renderMapLayers() {
  renderSelArea();""", """// arterial hazards of a walk or bike corridor (D.corr .H): x = crossing, f = along; district-wide only the larger ones
const mlHzIcon = () => L.divIcon({ className: 'hzicon', iconSize: [16, 14], iconAnchor: [8, 8], html: '""" + HZ_SVG + """' });
function mlHazards(r, m, who, all) {
  if (!mlHz || !r.H) return;
  for (const h of r.H) {
    if (!all && h[3] < 0.1) continue;
    const nm = esc(h[4] || 'a major arterial'), pct = Math.round(100 * h[3]);
    L.marker([h[1], h[2]], { icon: mlHzIcon(), keyboard: false, pane: 'flows', zIndexOffset: 400 })
      .bindTooltip(`${who}, ${m === 'bike' ? 'bike' : 'walking'} routes: ${h[0] === 'x' ? `cross ${nm} (major arterial), ${pct}% of residents` : `run along ${nm} (major arterial) for about ${Math.round(h[5]).toLocaleString()} m${m === 'bike' ? ' without a protected or buffered lane' : ''}, up to ${pct}% of residents`}`).addTo(mlLayer);
  }
}
function renderMapLayers() {
  renderSelArea();""")

    # ---- getting to school table: hazard counts under the walk and bike histograms ----
    rep("""function cmCells(c, q, row) {""", """// students whose walking / biking route crosses or runs along a major arterial: each school's share of its area's
// residents (D.corr .hx) x its students in the table's grades and year; and the hazard points on those routes
function cmHz(keys, m, sc) {
  const pre = D.years.indexOf(cmYear) < D.years.indexOf(D.impl_year), base = pre ? 'SQ' : sc === 'C' ? custom.base : sc;
  const bands = cmBand === 'all' ? ['k5', '68', '912'] : [cmBand];
  let n = 0, r = 0, pts = 0;
  for (const k of keys) {
    const c = D.corr?.S?.[m]?.[base]?.[k] || D.corr?.S?.[m]?.SQ?.[k]; if (!c || c.hx == null) continue;
    if (D.detail[base]?.[k]?.closed && !pre) continue;
    const s = bands.reduce((a, b) => a + cmStu(sc, k, b), 0); if (!s) continue;
    n += s * c.hx; r += s; pts += (c.H || []).length;
  }
  return r ? { n, r, pts } : null;
}
function cmHzCell(td, row, m) {
  if (!row?.keys?.length || cmBand === '912' && m === 'bike' && false) return td;
  const z = cmHz(row.keys, m, scen); if (!z) return td;
  const zq = scen === 'SQ' ? null : cmHz(row.keys, m, 'SQ'), d = zq ? Math.round(z.n - zq.n) : 0;
  const tip = `${Math.round(z.n).toLocaleString()} of ${Math.round(z.r).toLocaleString()} students (${Math.round(100 * z.n / z.r)}%) would ${m === 'bike' ? 'bike' : 'walk'} a route that crosses a major arterial or runs along one${m === 'bike' ? ' outside a path or protected / buffered bike lane' : ''}; ${z.pts} hazard point${z.pts === 1 ? '' : 's'} on these schools' routes` +
    (zq ? `. Status Quo: ${Math.round(zq.n).toLocaleString()} students, ${zq.pts} points` : '') + '. Modelled: every student assumed to make the trip this way; signals and crosswalks are not known.';
  return td.replace(/<\\/td>$/, `<span class="cmhz" title="${esc(tip)}"><span class="hzsym">&#9888;</span> ${cmN(z.n)} <span class="muted">(${Math.round(100 * z.n / z.r)}%) &middot; ${z.pts} pt${z.pts === 1 ? '' : 's'}</span>` +
    (d ? ` <span class="delta ${d > 0 ? 'down' : 'up'}" style="display:inline">${d > 0 ? '+' : '&minus;'}${cmN(Math.abs(d))}</span>` : '') + '</span></td>');
}
function cmCells(c, q, row) {""")
    rep("""cmHist(c, q, 'walk', ri) + cmHist(c, q, 'bike', ri) + cmHist(c, q, 'drive', ri)""",
        """cmHzCell(cmHist(c, q, 'walk', ri), row, 'walk') + cmHzCell(cmHist(c, q, 'bike', ri), row, 'bike') + cmHist(c, q, 'drive', ri)""")
    rep("""    `darker bars are within 15 minutes${scen === 'SQ' ? '' : ', and the <span style="color:var(--change);font-weight:600">outline</span> is Status Quo'}. Hover a bar for its count.`;""",
        """    `darker bars are within 15 minutes${scen === 'SQ' ? '' : ', and the <span style="color:var(--change);font-weight:600">outline</span> is Status Quo'}. Hover a bar for its count.` +
    ` <span class="hzsym">&#9888;</span> Under the walk and bike histograms: students whose route would cross a major arterial or run along one (bikes: outside paths and protected or buffered lanes; standard and advisory bike lanes count) and the number of such points on the routes (hover for details; modelled, signals and crosswalks not known).`;""")
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
.hzicon { background: none; border: 0; } .hzsym { color: #b98900; font-weight: 700; }
.cmhz { display: block; font-size: 11px; white-space: nowrap; cursor: help; margin-top: 1px; }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
