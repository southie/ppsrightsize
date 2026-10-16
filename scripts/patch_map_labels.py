"""School names in small text on the maps.
  - Main map: a small label right of each school marker (non-interactive, white halo); hidden when zoomed out past the
    starting zoom (12), where they would overlap.
  - School report map: the related schools (gaining or giving area, new school) labelled permanently in small text
    (they were hover-only).
  - Bus route map: each school shown labelled.
Code added once.
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

if 'schLabel' not in html:
    rep(""".leaflet-tooltip.rpmlabel { font-size: 11px; font-weight: 600; padding: 1px 5px; }""",
        """.leaflet-tooltip.rpmlabel { font-size: 11px; font-weight: 600; padding: 1px 5px; }
.schlbl { pointer-events: none; } .schlbl span { position: absolute; left: 0; top: 0; white-space: nowrap; font: 600 10px/1.1 system-ui, sans-serif; color: #26241f;
  text-shadow: 0 0 2px #fff, 0 0 2px #fff, 0 0 3px #fff, 0 0 4px #fff; transform: translateY(-50%); }
.lblhide .schlbl { display: none; }""")
    rep("""const map = L.map('map', { scrollWheelZoom: false }).setView([45.535, -122.65], 12);""",
        """const map = L.map('map', { scrollWheelZoom: false }).setView([45.535, -122.65], 12);
// small school-name labels beside markers (scripts/patch_map_labels.py); hidden on the main map when zoomed out past 12
const schLabel = (ll, name, dx = 8) => L.marker(ll, { interactive: false, keyboard: false, zIndexOffset: -1000,
  icon: L.divIcon({ className: 'schlbl', iconSize: [0, 0], iconAnchor: [-dx, 0], html: `<span>${esc(name)}</span>` }) });
map.on('zoomend', () => map.getContainer().classList.toggle('lblhide', map.getZoom() < 12));""")
    rep(""".bindTooltip(`${esc(short(s.name))}: ${{ closes: 'closes', receives: 'receives students', other: 'other change', none: scen === 'SQ' ? 'no change' : 'no change' }[rl]}`).addTo(layer);""",
        """.bindTooltip(`${esc(short(s.name))}: ${{ closes: 'closes', receives: 'receives students', other: 'other change', none: scen === 'SQ' ? 'no change' : 'no change' }[rl]}`).addTo(layer);
    schLabel(ll(s), short(s.name), r + 3).addTo(layer);""")
    rep(""".bindTooltip(`<b>${esc(rpName(key))}</b>${closed ? ' (new school)' : to ? ' (gains area)' : ' (gives area)'}`, { direction: 'top', offset: [0, -6], className: 'rpmlabel' })   // hover only; the school itself is labelled""",
        """.bindTooltip(`<b>${esc(rpName(key))}</b>${closed ? ' (new school)' : to ? ' (gains area)' : ' (gives area)'}`, { direction: 'top', offset: [0, -6], className: 'rpmlabel' })""")
    rep("""      .addTo(rpLayer);
    all.push(L.latLngBounds([p, p]));""", """      .addTo(rpLayer);
    schLabel(p, rpName(key), 10).addTo(rpLayer);
    all.push(L.latLngBounds([p, p]));""")
    rep(""".bindTooltip(`${esc(short(byKey[k]?.name || k))}${cl ? (gone ? ' (closed)' : ` (closes in ${LABEL[after]})`) : ''}`).addTo(bmLayer);""",
        """.bindTooltip(`${esc(short(byKey[k]?.name || k))}${cl ? (gone ? ' (closed)' : ` (closes in ${LABEL[after]})`) : ''}`).addTo(bmLayer);
    schLabel(ll, short(byKey[k]?.name || k), 8).addTo(bmLayer);""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
