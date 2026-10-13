"""Bus routes by grade range on the district bus routes map (getting-to-school section): a Grades filter (all, K-5,
6-8, high school) shows only routes to schools serving those grades in the view shown (K-8s count for both K-5 and
6-8; high school students mostly ride TriMet, so there are almost no yellow-bus high school runs), and switches the
attendance-area outlines to match (adding a 9-12 option). Also the styles for the school report map's bus routes
(scripts/school_report.js rpBusLayer). Runs after patch_bus_map and patch_school_report. Code added once.
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

if 'function bmGradeOK' not in html:
    rep("""<label>Attendance areas <select id="bm-band"><option value="k5">K-5</option><option value="68">6-8</option><option value="">Off</option></select></label></div>""",
        """<label>Grades <select id="bm-grade"><option value="">All</option><option value="k5">K-5 (incl. K-8)</option><option value="68">6-8 (incl. K-8)</option><option value="hs">High school</option></select></label>
        <label>Attendance areas <select id="bm-band"><option value="k5">K-5</option><option value="68">6-8</option><option value="912">9-12</option><option value="">Off</option></select></label></div>""")
    rep("""const bmHue = k => { let h = 0; for (const c of k) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };""",
        """const bmHue = k => { let h = 0; for (const c of k) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
// grade filter: the school's type in the view shown (K-8s serve both K-5 and 6-8)
function bmGradeOK(k, sc) {
  const g = document.getElementById('bm-grade')?.value; if (!g) return true;
  const t = (D.types[sc] || {})[k] || D.types.SQ[k];
  return g === 'k5' ? t === 'ES' || t === 'K8' : g === '68' ? t === 'MS' || t === 'K8' : t === 'HS';
}""")
    rep("""    ['bm-src', 'bm-band'].forEach(id => document.getElementById(id).onchange = renderBusMap);""",
        """    ['bm-src', 'bm-band'].forEach(id => document.getElementById(id).onchange = renderBusMap);
    // picking grades also shows the matching attendance areas
    document.getElementById('bm-grade').onchange = e => { const v = e.target.value, b = document.getElementById('bm-band'); if (v && b.value) b.value = v === 'hs' ? '912' : v; renderBusMap(); };""")
    rep("""  for (const [k, runs] of Object.entries(R)) {
    const sll = B.schools[k]; if (!sll) continue;""", """  for (const [k, runs] of Object.entries(R)) {
    const sll = B.schools[k]; if (!sll || !bmGradeOK(k, sc)) continue;""")
    rep("""    if (!here && !cl) continue;
    const gone = cl && bmView === 'after';""", """    if (!here && !cl) continue;
    if (!bmGradeOK(k, sc)) continue;
    const gone = cl && bmView === 'after';""")
    rep("""    `${band ? `Lines: ${bmView === 'before' ? 'Status Quo' : esc(LABEL[after])} ${band === 'k5' ? 'K-5' : '6-8'} attendance areas.` : ''} Generated routes""",
        """    `${band ? `Lines: ${bmView === 'before' ? 'Status Quo' : esc(LABEL[after])} ${{ k5: 'K-5', 68: '6-8', 912: '9-12' }[band]} attendance areas.` : ''} ` +
    (() => { const g = document.getElementById('bm-grade').value; return !g ? '' : g === 'hs'
      ? '<b>High school:</b> PPS high school students ride TriMet (student passes) rather than yellow buses, so there are almost no high school runs; the simulated routes cover K-8 only. '
      : `Showing routes to schools serving grades ${g === 'k5' ? 'K-5' : '6-8'} in this view (K-8 schools count for both). `; })() +
    `Generated routes""")
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
.rpbusctl { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12px; margin: 8px 0 2px; } .rpbusctl label { cursor: pointer; }
.rpbusctl .k { display: inline-block; width: 16px; height: 0; border-top: 2.5px solid; vertical-align: 3px; margin: 0 4px 0 2px; }
.rpbusctl .k.bcur { border-color: #4b5563; border-top-style: dashed; } .rpbusctl .k.bsim { border-color: #7c3aed; }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
