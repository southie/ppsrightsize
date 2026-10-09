"""Private schools on the map: larger markers (easier to click; 12-22 px by enrollment, was 7-16) and no "closes in
Scenario X" note after the nearest PPS school in the private school summary. Runs after patch_isochrones. Code changed
once.
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

if 'Math.max(7, Math.min(16, Math.sqrt(x.students || 50) * 0.5))' in html:
    rep("const sz = Math.round(Math.max(7, Math.min(16, Math.sqrt(x.students || 50) * 0.5)));",
        "const sz = Math.round(Math.max(12, Math.min(22, Math.sqrt(x.students || 50) * 0.7)));")
if 'closes in ${LABEL[scen]}</b>' in html:
    rep("""  const n = nearestPPS(x), rl = role(n.s, scen);
  const fate = scen === 'SQ' ? '' : rl === 'closes' ? ` &middot; <b style="color:#c2410c">closes in ${LABEL[scen]}</b>` : '';
""", "  const n = nearestPPS(x);\n")
    rep("${n.road ? `${n.d.toFixed(1)} mi / ${Math.round(n.min)} min by road` : `${n.d.toFixed(1)} mi straight-line`}${fate}${n.road ? mbLink(n.s, x) : ''}",
        "${n.road ? `${n.d.toFixed(1)} mi / ${Math.round(n.min)} min by road` : `${n.d.toFixed(1)} mi straight-line`}${n.road ? mbLink(n.s, x) : ''}")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
