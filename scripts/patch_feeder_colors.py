"""Feeder arrows colored by grade transition: elementary to middle (purple), middle to high (teal), K-8 or elementary to
high with no middle school between (magenta). The layer's checkbox and the map note carry the key. Runs after
patch_feeder_arrows. Code added once.
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

if 'FEED_COL' not in html:
    sw = lambda c: f'<span class="ln" style="border-top:3px solid {c};width:8px;margin-right:1px"></span>'
    rep("""<input type="checkbox" id="ml-feed"> <span class="ln" style="border-top:3px solid #7c3aed;width:16px"></span>Feeder arrows</label>""",
        f"""<input type="checkbox" id="ml-feed"> {sw('#7c3aed')}{sw('#0e7490')}{sw('#be185d')}Feeder arrows</label>""")
    rep("""const feedLayer = L.layerGroup().addTo(map);   // feeder arrows (scripts/patch_feeder_arrows.py)""",
        """const feedLayer = L.layerGroup().addTo(map);   // feeder arrows (scripts/patch_feeder_arrows.py)
// by grade transition (scripts/patch_feeder_colors.py)
const FEED_COL = { em: ['#7c3aed', 'elementary to middle'], mh: ['#0e7490', 'middle to high'], kh: ['#be185d', 'K-8 or elementary to high'] };""")
    rep("""  const col = '#7c3aed';
  for (const e of E.values()) {
    const g = flowGeometry(byKey[e.a], byKey[e.b]), progOnly = !e.nb;""",
        """  const used = new Set();
  for (const e of E.values()) {
    const g = flowGeometry(byKey[e.a], byKey[e.b]), progOnly = !e.nb;
    const tr = typ(e.b) === 'HS' ? (typ(e.a) === 'MS' ? 'mh' : 'kh') : 'em', col = FEED_COL[tr][0]; used.add(tr);""")
    rep("""      `Feeder: ${esc(short(byKey[e.a].name))} → ${esc(short(byKey[e.b].name))} (${esc(what)})`).addTo(feedLayer);""",
        """      `Feeder, ${FEED_COL[tr][1]}: ${esc(short(byKey[e.a].name))} → ${esc(short(byKey[e.b].name))} (${esc(what)})`).addTo(feedLayer);""")
    rep("""each school to the school its students go on to; dashed""",
        """each school to the school its students go on to (${Object.keys(FEED_COL).filter(t => used.has(t)).map(t => `<span style="color:${FEED_COL[t][0]};font-weight:600">&#9632;</span> ${FEED_COL[t][1]}`).join(', ')}); dashed""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
