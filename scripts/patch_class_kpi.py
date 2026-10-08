"""Summary card: classes over the PAT contract's overload-pay thresholds at the budget's largest class sizes and staffing
ratios, in the class-size table's school year (scripts/patch_class_sizes.py): K-5 homerooms over (with the change vs
Status Quo), students over, and schools / teachers over the daily-load thresholds in grades 6-8 and 9-12. Clicking it
opens the class-size table. Runs after patch_class_sizes. Safe to rerun: added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function classKPI' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

rep("  }).join('') + extraKPIs() + staffKPI();", "  }).join('') + extraKPIs() + staffKPI() + classKPI();")
rep("const KPI_TARGETS = ['closures', 'schools_above', 'students_above', 'change', 'overcap', 'commute', 'bus', 'cost', 'land', 'staff'];",
    "const KPI_TARGETS = ['closures', 'schools_above', 'students_above', 'change', 'overcap', 'commute', 'bus', 'cost', 'land', 'staff', 'classsize'];")
rep("  if (target === 'bus') {", """  if (target === 'classsize') {
    const t = document.getElementById('classsize'); if (!t) return;
    t.scrollIntoView({ behavior: 'smooth', block: 'start' }); flash([t]); return;
  }
  if (target === 'bus') {""")
rep("t === 'bus' ? 'Show how the bus cost is estimated' :", "t === 'bus' ? 'Show how the bus cost is estimated' : t === 'classsize' ? 'Show class sizes and teacher loads by grade' :")
rep("sel.onchange = () => { csYear = sel.value; try { localStorage.setItem('rsCsYear', csYear); } catch (e) {} renderClassSizes(); };",
    "sel.onchange = () => { csYear = sel.value; try { localStorage.setItem('rsCsYear', csYear); } catch (e) {} renderClassSizes(); renderKPIs(); };")
rep("function renderClassSizes() {", r"""// district totals over the PAT thresholds for a scenario in the class-size table's year
function classTotals(sc) {
  const yi = D.years.indexOf(csYear), o = { h: 0, over: 0, overStu: 0, ms: 0, msOver: 0, msFte: 0, hs: 0, hsOver: 0, hsFte: 0 };
  for (const k of Object.keys(D.region_of)) {
    const r = classSizes(k, sc, yi); if (!r) continue;
    r.grades.slice(0, 6).forEach(g => { if (g?.h) { o.h += g.h; o.over += g.overCls; o.overStu += g.overStu; } });
    if (r.fte68) { o.ms++; if (r.load68 > PAT_MS) { o.msOver++; o.msFte += r.fte68; } }
    if (r.fte912) { o.hs++; if (r.load912 > PAT_HS) { o.hsOver++; o.hsFte += r.fte912; } }
  }
  return o;
}
function classKPI() {
  const c = classTotals(scen), q = scen === 'SQ' ? null : classTotals('SQ'), d = q ? c.over - q.over : 0;
  const pct = c.h ? Math.round(100 * c.over / c.h) : 0;
  return `<div class="kpi"><div class="v">${c.over.toLocaleString()}${q && d ? `<span class="d" style="color:${d > 0 ? 'var(--down)' : 'var(--up)'}">${d > 0 ? '+' : '&minus;'}${Math.abs(d)} vs SQ</span>` : ''}</div>` +
    `<div class="l">K-5 classes over the PAT overload-pay threshold, ${csYear}, at the budget's largest class sizes (K over 24, grades 1-3 over 26, 4-5 over 28)</div>` +
    `<div class="s">${pct}% of ${c.h.toLocaleString()} K-5 homerooms &middot; ${Math.round(c.overStu).toLocaleString()} students over the thresholds` +
    `${q ? ` <span class="pcs">(Status Quo ${q.over.toLocaleString()} of ${q.h.toLocaleString()})</span>` : ''}<br>` +
    `Grades 6-8: <b>${c.msOver} of ${c.ms}</b> schools over ${PAT_MS} students a day per teacher <span class="pcs">(about ${Math.round(c.msFte)} teachers)</span><br>` +
    `Grades 9-12: <b>${c.hsOver} of ${c.hs}</b> schools over ${PAT_HS} <span class="pcs">(about ${Math.round(c.hsFte)} teachers)</span><br>` +
    `<span class="pcs" style="white-space:normal">Base staffing formula only; equity, SIA, Measure 98 and grant FTE lower actual loads.</span></div></div>`;
}
function renderClassSizes() {""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
