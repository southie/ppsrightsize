"""rightsizing-scenario-explorer.html: flow lines, program-move lines and private-alternative lines
(and the arrows on them) show their labels on hover but are not clickable. The lines are drawn
non-interactive and registered for the map's hover lookup (added by patch_boundaries.py), which checks
lines first (within LINE_PX pixels) and boundary areas second. Safe to rerun: the code is only added once.
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

if 'function regLine' not in html:
    # ---------- line registry and lookup ----------
    rep("let bHits = [], bHover = null, bRaf = 0;",
"""let bHits = [], bHover = null, bRaf = 0;
// lines (flows, moves, private alternatives) are registered here; set 'f' = flows, 'a' = alternatives
let lHits = [];
const LINE_PX = 7;
function regLine(set, l, h) { lHits.push({ set, l, h, hl: { weight: l.options.weight + 2.5, opacity: 1 }, base: { weight: l.options.weight, opacity: l.options.opacity } }); return l; }
function lineAt(p) {
  let best = null, bd = LINE_PX;
  for (const h of lHits) {
    const pts = h.l.getLatLngs().map(ll => map.latLngToContainerPoint(ll));
    for (let i = 1; i < pts.length; i++) {
      const d = L.LineUtil.pointToSegmentDistance(p, pts[i - 1], pts[i]);
      if (d < bd) { bd = d; best = h; }
    }
  }
  return best;
}""")
    rep("  if (bHover && bHover !== hit) bHover.l.resetStyle();",
        "  if (bHover && bHover !== hit) { if (bHover.base) bHover.l.setStyle(bHover.base); else bHover.l.resetStyle(); }")
    rep("    if (!bHits.length || (t.closest && t.closest('.leaflet-marker-icon, .leaflet-interactive, .leaflet-popup, .leaflet-control'))) return setBHover(null);",
        "    if (t.closest && t.closest('.leaflet-marker-icon:not(.rs-arrow), .leaflet-interactive, .leaflet-popup, .leaflet-control')) return setBHover(null);\n"
        "    const ln = lHits.length && lineAt(e.containerPoint); if (ln) return setBHover(ln, e.originalEvent);\n"
        "    if (!bHits.length) return setBHover(null);")

    # ---------- flows and program moves ----------
    rep("  flowLayer.clearLayers();\n", "  flowLayer.clearLayers(); lHits = lHits.filter(h => h.set !== 'f'); if (bHover && bHover.set === 'f') setBHover(null);\n")
    rep("    L.polyline(g.pts, { pane: 'flows', color: '#199e70', weight: 2.5, opacity: .9, dashArray: '4 5' }).bindTooltip(esc(mv.text), { sticky: true }).addTo(flowLayer);",
        "    regLine('f', L.polyline(g.pts, { pane: 'flows', interactive: false, color: '#199e70', weight: 2.5, opacity: .9, dashArray: '4 5' }), esc(mv.text)).addTo(flowLayer);")
    rep("""    L.polyline(g.pts, { pane: 'flows', color: c, weight: 3.5, opacity: .95, dashArray: isProgram(r) ? '7 6' : null }).addTo(flowLayer);
    L.polyline(g.pts, { pane: 'flows', weight: 14, opacity: 0 }).bindTooltip(`${esc(short(r.from))} → ${esc(short(r.to))}: ${esc(flowText(r))}`, { sticky: true }).addTo(flowLayer);""",
        """    regLine('f', L.polyline(g.pts, { pane: 'flows', interactive: false, color: c, weight: 3.5, opacity: .95, dashArray: isProgram(r) ? '7 6' : null }), `${esc(short(r.from))} → ${esc(short(r.to))}: ${esc(flowText(r))}`).addTo(flowLayer);""")

    # ---------- private alternatives ----------
    rep("  altLayer.clearLayers();\n", "  altLayer.clearLayers(); lHits = lHits.filter(h => h.set !== 'a'); if (bHover && bHover.set === 'a') setBHover(null);\n")
    rep("""      L.polyline(ln, { pane: 'flows', color: col, weight: 2, opacity: .8, dashArray: '2 5', lineCap: 'round' }).addTo(altLayer);
      L.polyline(ln, { pane: 'flows', weight: 12, opacity: 0 }).bindTooltip(
""", """      regLine('a', L.polyline(ln, { pane: 'flows', interactive: false, color: col, weight: 2, opacity: .8, dashArray: '2 5', lineCap: 'round' }),
""")
    rep("""to ${esc(short(a.r.to.name))}`, { sticky: true }).addTo(altLayer);""",
        """to ${esc(short(a.r.to.name))}`).addTo(altLayer);""")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
