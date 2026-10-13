"""Main map: the Grades selector floats over the top centre of the map (a white bar with larger buttons), instead of
sitting in the controls above it; the note on what is shown stays under the selector, in the bar. Clicks on it do not
reach the map. Runs after patch_map_layers. Code added once.
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

if 'id="gfloat"' not in html:
    rep("""    <div class="controls isoctl"><span>Grades</span><span class="seg2" id="gseg"></span><span class="muted" id="gnote"></span></div>
""", "")
    rep("""    <div id="map"></div>""", """    <div class="mapwrap"><div id="map"></div>
      <div class="gfloat isoctl" id="gfloat"><span class="gl">Grades</span><span class="seg2" id="gseg"></span><span class="muted gn" id="gnote"></span></div></div>""")
    rep("""map.zoomControl.setPosition('topright');""", """map.zoomControl.setPosition('topright');
{ const gf = document.getElementById('gfloat'); if (gf) { L.DomEvent.disableClickPropagation(gf); L.DomEvent.disableScrollPropagation(gf); } }""")
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
.mapwrap { position: relative; }
.gfloat { position: absolute; top: 10px; left: 50%; transform: translateX(-50%); z-index: 1000; display: flex; flex-direction: column; align-items: center; gap: 2px;
  background: var(--surface-1); border: 1px solid var(--line); border-radius: 10px; padding: 6px 10px 5px; box-shadow: 0 3px 14px rgba(0, 0, 0, .22); max-width: calc(100% - 120px); }
.gfloat .gl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--text-muted); }
.gfloat .seg2 button { font-size: 14px; font-weight: 600; padding: 5px 16px; }
.gfloat .gn { font-size: 11px; text-align: center; } .gfloat .gn:empty { display: none; }
@media (max-width: 640px) { .gfloat { top: 54px; max-width: calc(100% - 24px); } .gfloat .seg2 button { padding: 4px 10px; font-size: 13px; } .gfloat .gn { display: none; } }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
