"""rightsizing-scenario-explorer.html: full-width layout with a taller map, and school details in a
floating panel on the left of the page, over the content (bottom sheet on narrow screens) instead of map popups.
The right-click custom-scenario menu stays a map popup. Safe to rerun: the code is only added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function openDock' not in html:
    # ---------- layout ----------
    rep("main { max-width: 1200px; margin: 0 auto; padding: 24px 16px 64px; }",
        "main { max-width: none; margin: 0; padding: 24px 24px 64px; }\n"
        "@media (max-width: 600px) { main { padding: 20px 16px 64px; } }")
    rep("#map { height: 560px; border-radius: 10px; }",
        "#map { height: clamp(560px, 78vh, 1100px); border-radius: 10px; }")

    # ---------- dock styles ----------
    rep(".pop .row { margin: 1px 0; }",
""".pop .row { margin: 1px 0; }
.dock { position: fixed; left: 16px; top: 16px; width: 360px; max-height: calc(100vh - 32px); z-index: 1002; background: var(--surface-1); color: var(--text-primary);
  border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 10px 32px rgba(0,0,0,.22); overflow-y: auto; padding: 18px 18px 22px; font-size: 13.5px; line-height: 1.45; }
.dock[hidden] { display: none; }
.dock .dock-x { position: sticky; top: 0; float: right; margin: -6px -6px 0 8px; width: 32px; height: 32px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--surface-1); color: var(--text-primary); font-size: 20px; line-height: 1; cursor: pointer; }
.dock .pop b { font-size: 16px; margin-bottom: 4px; }
.dock .pop h4 { font-size: 11px; color: var(--text-muted); border-bottom-color: var(--line); margin: 14px 0 4px; }
.dock .pop .row { margin: 3px 0; }
.dock .pop .near span, .dock [style*="#57606a"] { color: var(--text-muted) !important; }
@media (max-width: 899px) {
  .dock { top: auto; left: 0; right: 0; bottom: 0; width: auto; max-height: 55vh; border-width: 1px 0 0; border-radius: 14px 14px 0 0; box-shadow: 0 -4px 18px rgba(0,0,0,.15); }
}""")

    # ---------- dock element ----------
    rep('<div class="tip" id="tip"></div>',
        '<aside class="dock" id="dock" hidden aria-label="School details"><button class="dock-x" id="dockx" type="button" aria-label="Close details">&times;</button><div id="dockbody"></div></aside>\n<div class="tip" id="tip"></div>')

    # ---------- dock logic (next to the map code) ----------
    rep("function renderMap() {",
"""// ---------- school details in a floating panel on the left ----------
const selLayer = L.layerGroup().addTo(map);
let dockFn = null, dockAt = null;
function openDock(fn, at, key) {
  dockFn = fn; dockAt = at;
  document.getElementById('dockbody').innerHTML = fn();
  const d = document.getElementById('dock'); d.hidden = false; d.scrollTop = 0;
  isoSel = key || null; renderIso(); markSel();
}
function closeDock() {
  if (!dockFn) return;
  dockFn = dockAt = null;
  document.getElementById('dock').hidden = true;
  isoSel = null; renderIso(); markSel();
}
function markSel() {
  selLayer.clearLayers();
  if (dockAt) L.circleMarker(dockAt, { radius: 15, color: '#0b0b0b', weight: 2.5, opacity: .9, fill: false, interactive: false }).addTo(selLayer);
}
document.getElementById('dockx').onclick = closeDock;
addEventListener('keydown', e => { if (e.key === 'Escape') closeDock(); });
function renderMap() {""")

    # PPS schools: click opens the dock (replaces the popup and its travel-time hooks)
    rep(".on('popupopen', () => { isoSel = s.key; renderIso(); }).on('popupclose', () => { if (isoSel === s.key) { isoSel = null; renderIso(); } }).bindPopup(popup(s), { maxWidth: 340, minWidth: 260 })",
        ".on('click', () => openDock(() => popup(s), ll(s), s.key))")
    # private schools
    rep(".bindPopup(() => privPopup(x), { maxWidth: 340, minWidth: 260 })",
        ".on('click', () => openDock(() => privPopup(x), L.latLng(x.lat, x.lng)))")
    # scenario changes refresh the open panel
    rep("  wirePrivate(); renderPrivate(); renderIso(); renderBounds();",
        "  wirePrivate(); renderPrivate(); renderIso(); renderBounds();\n  if (dockFn) document.getElementById('dockbody').innerHTML = dockFn();")

    # wording
    html = html.replace("Click a school for details.", "Click a school for details (they open on the left).")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
