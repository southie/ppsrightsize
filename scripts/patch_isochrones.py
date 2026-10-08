"""Add walk / bike / drive travel-time areas (10 and 15 min isochrones) to
rightsizing-scenario-explorer.html, shown for the school whose popup is open, and
make the school markers smaller so the map is easier to read at the default zoom.

Polygons come from pps-data/web/isochrones.json (built by pps-data/scripts/isochrones.py:
openrouteservice, with a Valhalla fallback where the ORS free-tier quota ran out). They are
embedded as D.iso keyed by school key. Safe to rerun: the data is always refreshed, the page
code is only added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
ISO = os.path.join(ROOT, 'source', 'pps-data', 'web', 'isochrones.json')
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
html = open(PAGE, encoding='utf-8').read()

# ---------- data: isochrones aligned to D.schools ----------
def rnd(c, nd=4):   # ~10 m, plenty for a 10/15-minute area
    return [round(c[0], nd), round(c[1], nd)] if isinstance(c[0], (int, float)) else [rnd(x, nd) for x in c]

m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
src = json.load(open(ISO, encoding='utf-8'))
byname = {k.strip(): v for k, v in src['schools'].items()}
D['iso'] = {}
for s in D['schools']:
    modes = byname.get(s['name'].strip())
    if not modes:
        print('no isochrones for', s['name']); continue
    D['iso'][s['key']] = {mode: {band: {'type': g['type'], 'coordinates': rnd(g['coordinates'])} for band, g in bands.items()}
                          for mode, bands in modes.items()}
# schools whose areas came from the Valhalla fallback
vk = {s['name'].strip(): s['key'] for s in D['schools']}
D['iso_valhalla'] = {vk[n.strip()]: modes for n, modes in src.get('valhalla', {}).items() if n.strip() in vk}
for mode in src['modes']:
    ks = [s['key'] for s in D['schools'] if mode not in D['iso'].get(s['key'], {})]
    if ks: print(f'{mode}: missing for {len(ks)} schools: {", ".join(ks)}')
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderIso' not in html:
    # ---------- smaller markers ----------
    rep("const radiusOf = s => Math.max(6, Math.min(26, Math.sqrt(s.enroll_2526 || 100) * 0.62));",
        "const radiusOf = s => Math.max(4, Math.min(14, Math.sqrt(s.enroll_2526 || 100) * 0.36));")
    rep("if (rl === 'closes' || rl === 'receives') L.circleMarker(ll(s), { radius: r + 2.5,",
        "if (rl === 'closes' || rl === 'receives') L.circleMarker(ll(s), { radius: r + 2,")
    rep("color: rl === 'closes' || rl === 'receives' ? '#ffffff' : css('--change'), weight: rl === 'closes' || rl === 'receives' ? 2.5 : 1,",
        "color: rl === 'closes' || rl === 'receives' ? '#ffffff' : css('--change'), weight: rl === 'closes' || rl === 'receives' ? 1.8 : 1,")
    rep("const sz = Math.round(Math.max(9, Math.min(24, Math.sqrt(x.students || 50) * 0.62)) * 1.25);",
        "const sz = Math.round(Math.max(7, Math.min(16, Math.sqrt(x.students || 50) * 0.5)));")

    # ---------- styles ----------
    rep(".legend label { cursor: pointer; }",
""".legend label { cursor: pointer; }
.isoctl { margin: 0 0 10px; }
.isoctl .seg2 { display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
.isoctl .seg2 button { font: inherit; font-size: 12.5px; border: 0; background: var(--surface-1); color: var(--text-primary); padding: 3px 11px; cursor: pointer; }
.isoctl .seg2 button + button { border-left: 1px solid var(--line); }
.isoctl .seg2 button[aria-pressed="true"] { background: var(--text-primary); color: var(--surface-1); }
.isoctl .isw { display: inline-block; width: 11px; height: 11px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }""")

    # ---------- control row above the map ----------
    rep("""    <p class="sub" id="mapsub"></p>
    <div id="map"></div>""",
"""    <p class="sub" id="mapsub"></p>
    <div class="controls isoctl"><span>Travel time to school</span><span class="seg2" id="isoseg"></span><span id="isolegend"></span></div>
    <div id="map"></div>""")

    # ---------- layer ----------
    rep("const layer = L.layerGroup().addTo(map), flowLayer = L.layerGroup().addTo(map);",
"""const layer = L.layerGroup().addTo(map), flowLayer = L.layerGroup().addTo(map);

// ---------- travel-time areas (isochrones, D.iso) for the school whose popup is open ----------
const ISO_COLORS = { walk: '#1a9e77', bike: '#e08a1e', drive: '#b0369a' };
const ISO_LABEL = { '': 'Off', walk: 'Walk', bike: 'Bike', drive: 'Drive' };
const ISO_VERB = { walk: 'on foot', bike: 'by bike', drive: 'by car' };
map.createPane('iso').style.zIndex = 350;   // under flows (390) and school circles (overlayPane, 400)
const isoRenderer = L.svg({ pane: 'iso' }), isoLayer = L.layerGroup().addTo(map);
let isoMode = 'walk', isoSel = null;
try { isoMode = localStorage.getItem('rsIso') ?? 'walk'; } catch (e) {}
function renderIso() {
  isoLayer.clearLayers();
  const seg2 = document.getElementById('isoseg');
  seg2.innerHTML = Object.entries(ISO_LABEL).map(([k, l]) => `<button data-m="${k}" aria-pressed="${k === isoMode}">${l}</button>`).join('');
  seg2.onclick = e => { const b = e.target.closest('button'); if (!b) return; isoMode = b.dataset.m; try { localStorage.setItem('rsIso', isoMode); } catch (e) {} renderIso(); };
  const lg = document.getElementById('isolegend');
  if (!isoMode) { lg.innerHTML = ''; return; }
  const s = isoSel && byKey[isoSel], areas = s && D.iso[s.key]?.[isoMode];
  if (!s) { lg.innerHTML = `<span class="muted">Click a school to see how far you can get ${ISO_VERB[isoMode]} in 10 and 15 minutes.</span>`; return; }
  if (!areas) { lg.innerHTML = `<span class="muted">No ${ISO_LABEL[isoMode].toLowerCase()} area for ${esc(short(s.name))}.</span>`; return; }
  const col = ISO_COLORS[isoMode], mix = p => `color-mix(in srgb, ${col} ${p}%, #f2efe9)`;
  const draw = (band, style) => areas[band] && L.geoJSON(areas[band], { renderer: isoRenderer, interactive: false, style }).addTo(isoLayer);
  draw('15', { color: col, weight: 2, opacity: .9, fillColor: col, fillOpacity: .22 });
  draw('10', { stroke: false, fillColor: col, fillOpacity: .3 });
  const closes = role(s, scen) === 'closes';
  lg.innerHTML = `<b>${esc(short(s.name))}</b>${closes ? ` <span class="stag closes">closes in ${LABEL[scen]}</span>` : ''}: ` +
    `<span class="isw" style="background:${mix(62)}"></span>within 10 min &nbsp;<span class="isw" style="background:${mix(30)}"></span>within 15 min ${ISO_VERB[isoMode]}` +
    `<span class="muted">${isoMode === 'drive' ? ' (free-flow traffic)' : ''}${D.iso_valhalla?.[s.key]?.includes(isoMode) ? ' (Valhalla routing)' : ''}</span>`;
}""")

    # open a school's popup -> show its areas
    rep("}).on('contextmenu', ev => openMenu(s, ev)).bindPopup(popup(s)",
        "}).on('contextmenu', ev => openMenu(s, ev)).on('popupopen', () => { isoSel = s.key; renderIso(); }).on('popupclose', () => { if (isoSel === s.key) { isoSel = null; renderIso(); } }).bindPopup(popup(s)")

    # redraw with the map (scenario changes)
    rep("""  wirePrivate(); renderPrivate();
}
map.on('zoomend', renderFlows);""",
"""  wirePrivate(); renderPrivate(); renderIso();
}
map.on('zoomend', renderFlows);""")

    # ---------- method note ----------
    rep("  'Private schools: ",
        "  'Travel time: with Walk, Bike or Drive selected, clicking a school shades everywhere within 10 and 15 minutes of it. Isochrones are from openrouteservice on the OpenStreetMap road and path network (foot-walking, cycling-regular and driving-car profiles; driving is free-flow with no traffic); where the openrouteservice free-tier quota ran out, the public Valhalla server (same OpenStreetMap data) was used and the legend says so. Built by pps-data/scripts/isochrones.py and embedded by scripts/patch_isochrones.py.',\n  'Private schools: ")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB, isochrones for {len(D["iso"])} of {len(D["schools"])} schools)')
