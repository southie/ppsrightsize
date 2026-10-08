"""Add attendance-boundary layers (K-5, 6-8, 9-12; Status Quo, Scenario A, Scenario B) to
rightsizing-scenario-explorer.html.

Boundaries come from Jason Brown's PPS attendance-boundary explorer
(https://pps-explorer.codedaily.workers.dev/data/<scenario>_<band>[_changed].geojson), traced from
PPS's October 6, 2026 scenario maps; saved in source/pps-explorer-boundaries/. Embedded as D.bounds.
Safe to rerun: the data is always refreshed, the page code is only added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
SRC = os.path.join(ROOT, 'source', 'pps-explorer-boundaries')
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
html = open(PAGE, encoding='utf-8').read()

# ---------- data ----------
def ring(r, nd=4):   # ~10 m; drop points that round onto the previous one
    out = []
    for x, y in r:
        p = [round(x, nd), round(y, nd)]
        if not out or p != out[-1]: out.append(p)
    return out if len(out) >= 4 else None

def geom(g):
    polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    polys = [[r for r in map(ring, p) if r] for p in polys]
    polys = [p for p in polys if p]
    return {'type': 'MultiPolygon', 'coordinates': polys} if polys else None

def load(name):
    return json.load(open(os.path.join(SRC, name), encoding='utf-8'))['features']

m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['bounds'] = {}
for sc in ['sq', 'a', 'b']:
    for band in ['k5', '68', '912']:
        key = f'{sc}_{band}'
        areas = [[f['properties'].get('school_label') or f['properties']['name'], geom(f['geometry'])] for f in load(f'{key}.geojson')]
        changed = [] if sc == 'sq' else [[f['properties']['from'], f['properties']['to'], geom(f['geometry'])] for f in load(f'{key}_changed.geojson')]
        D['bounds'][key] = {'areas': [a for a in areas if a[1]], 'changed': [c for c in changed if c[2]]}
        print(f"{key}: {len(D['bounds'][key]['areas'])} areas, {len(D['bounds'][key]['changed'])} changed")
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderBounds' not in html:
    # ---------- control row (reuses the travel-time row styles) ----------
    rep("""    <div id="map"></div>""",
"""    <div class="controls isoctl"><span>Attendance boundaries</span><span class="seg2" id="bseg"></span><span id="blegend"></span></div>
    <div id="map"></div>""")

    # ---------- layer ----------
    rep("function renderIso() {",
"""// ---------- attendance boundaries (D.bounds, traced from PPS's scenario maps) ----------
const B_LABEL = [['', 'Off'], ['k5', 'K-5'], ['68', '6-8'], ['912', '9-12']];   // array: object keys '68'/'912' would sort first
map.createPane('bounds').style.zIndex = 340;   // under travel-time areas (350)
const bRenderer = L.svg({ pane: 'bounds' }), bLayer = L.layerGroup().addTo(map);
let bBand = '', bChanged = true;
// hover without capturing clicks: the map finds the boundary under the pointer and shows the page tooltip
let bHits = [], bHover = null, bRaf = 0;
const ptInGeom = (x, y, g) => { let c = false;
  for (const poly of g.type === 'Polygon' ? [g.coordinates] : g.coordinates) for (const r of poly)
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, yi] = r[i], [xj, yj] = r[j]; if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c; }
  return c; };
function setBHover(hit, ev) {
  if (bHover && bHover !== hit) bHover.l.resetStyle();
  if (!hit) { if (bHover) hideTip(); bHover = null; return; }
  if (bHover !== hit) hit.l.setStyle(hit.hl);
  bHover = hit; showTip(ev, hit.h);
}
function hoverAt(e) {
  {
    const t = e.originalEvent.target;
    if (!bHits.length || (t.closest && t.closest('.leaflet-marker-icon, .leaflet-interactive, .leaflet-popup, .leaflet-control'))) return setBHover(null);
    const { lng: x, lat: y } = e.latlng;
    for (let i = bHits.length - 1; i >= 0; i--) {   // changed areas were added last and sit on top
      const h = bHits[i];
      if (x >= h.bb[0] && x <= h.bb[2] && y >= h.bb[1] && y <= h.bb[3] && h.gs.some(g => ptInGeom(x, y, g))) return setBHover(h, e.originalEvent);
    }
    setBHover(null);
  }
}
let bLast = null;   // throttle: at most every 30 ms, always finishing with the latest position
map.on('mousemove', e => {
  if (bRaf) { bLast = e; return; }
  hoverAt(e);
  bRaf = setTimeout(() => { bRaf = 0; if (bLast) { const x = bLast; bLast = null; hoverAt(x); } }, 30);
});
map.on('mouseout', () => setBHover(null));
try { bBand = localStorage.getItem('rsBand') || ''; bChanged = localStorage.getItem('rsBandChanged') !== '0'; } catch (e) {}
function renderBounds() {
  bLayer.clearLayers(); bHits = []; bHover = null;
  const seg2 = document.getElementById('bseg');
  seg2.innerHTML = B_LABEL.map(([k, l]) => `<button data-b="${k}" aria-pressed="${k === bBand}">${l}</button>`).join('');
  seg2.onclick = e => { const b = e.target.closest('button'); if (!b) return; bBand = b.dataset.b; try { localStorage.setItem('rsBand', bBand); } catch (e) {} renderBounds(); };
  const lg = document.getElementById('blegend');
  if (!bBand) { lg.innerHTML = ''; return; }
  const sc = scen === 'C' ? custom.base : scen, d = D.bounds[`${sc.toLowerCase()}_${bBand}`];
  // shapes are not interactive (clicks pass through); register them for the hover lookup instead
  const reg = (l, h, hl) => { const gs = l.toGeoJSON().features.map(f => f.geometry), bb = [Infinity, Infinity, -Infinity, -Infinity];
    for (const g of gs) for (const poly of g.type === 'Polygon' ? [g.coordinates] : g.coordinates) for (const [x, y] of poly[0]) { bb[0] = Math.min(bb[0], x); bb[1] = Math.min(bb[1], y); bb[2] = Math.max(bb[2], x); bb[3] = Math.max(bb[3], y); }
    bHits.push({ l, h, hl, gs, bb }); return l; };
  for (const [label, g] of d.areas)
    reg(L.geoJSON(g, { renderer: bRenderer, interactive: false, style: { color: '#33312c', weight: 1.4, opacity: .75, fillColor: '#33312c', fillOpacity: 0 } }), esc(label), { weight: 3, opacity: 1 }).addTo(bLayer);
  if (bChanged) for (const [from, to, g] of d.changed)
    reg(L.geoJSON(g, { renderer: bRenderer, interactive: false, style: { stroke: false, fillColor: '#d4a017', fillOpacity: .38 } }), `Moves from ${esc(short(from))} to ${esc(short(to))}`, { fillOpacity: .6 }).addTo(bLayer);
  lg.innerHTML = `${LABEL[sc]}${scen === 'C' ? ' (your custom changes are not redrawn)' : ''}, 2027-28` +
    (d.changed.length ? ` &nbsp;<label><input type="checkbox" id="bchg" ${bChanged ? 'checked' : ''}> <span class="isw" style="background:color-mix(in srgb, #d4a017 45%, #f2efe9)"></span>areas that change school</label>` : '') +
    ` &nbsp;<span class="muted">Traced from PPS maps by <a href="https://pps-explorer.codedaily.workers.dev/" target="_blank" rel="noopener">Jason Brown</a>; confirm addresses near a line with PPS.</span>`;
  const cb = document.getElementById('bchg'); if (cb) cb.onchange = () => { bChanged = cb.checked; try { localStorage.setItem('rsBandChanged', bChanged ? '1' : '0'); } catch (e) {} renderBounds(); };
}
function renderIso() {""")

    # redraw with the map (scenario changes)
    rep("  wirePrivate(); renderPrivate(); renderIso();",
        "  wirePrivate(); renderPrivate(); renderIso(); renderBounds();")

    # ---------- method note ----------
    rep("  'Travel time:",
        "  'Attendance boundaries: K-5, 6-8 and 9-12 areas for Status Quo, Scenario A and Scenario B in 2027-28, from Jason Brown\\'s PPS attendance-boundary explorer (pps-explorer.codedaily.workers.dev), which traces them from the vector paths in PPS\\'s October 6, 2026 scenario maps; its Status Quo areas match the City of Portland\\'s school boundary data for 98% of the district at K-5 and 9-12. Shaded areas are the parts of the district that change school. A custom scenario shows its starting scenario\\'s boundaries; custom closures are not redrawn. Embedded by scripts/patch_boundaries.py.',\n  'Travel time:")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
