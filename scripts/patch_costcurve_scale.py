"""Cost per student by school size ("The sustainability threshold impact on cost per student by school size"): one
y-axis scale for all four panels (K-5, K-8, middle, high), so their costs compare at a glance. Each panel's data is
prepared first; the shared range covers every panel's curves, schools and target. Code changed once.
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

if 'CC_SHARED_Y' not in html:
    rep("""  host.innerHTML = TYPES.map(([t, title]) => {
    const pts = keys.filter(k => D.types.SQ[k] === t && D.series.SQ[k]?.[yi] > 0).map(k => ({ k, E: D.series.SQ[k][yi], c: per(k, D.series.SQ[k][yi], t), t1: !!D.staff.schools[k]?.title1 }));
    if (!pts.length) return '';""",
        """  // each panel's data first, then one y scale shared by all panels (CC_SHARED_Y, scripts/patch_costcurve_scale.py)
  const PREP = TYPES.map(([t, title]) => {
    const pts = keys.filter(k => D.types.SQ[k] === t && D.series.SQ[k]?.[yi] > 0).map(k => ({ k, E: D.series.SQ[k][yi], c: per(k, D.series.SQ[k][yi], t), t1: !!D.staff.schools[k]?.title1 }));
    if (!pts.length) return null;""")
    rep("""    const all = [...cNT, ...(same ? [] : cT1), ...pts.map(p => p.c), ...(gT ? [gT.target] : [])].filter(v => v != null);
    const yLo = Math.floor(Math.min(...all) / 1000) * 1000, yHi = Math.ceil(Math.max(...all) / 1000) * 1000;""",
        """    const all = [...cNT, ...(same ? [] : cT1), ...pts.map(p => p.c), ...(gT ? [gT.target] : [])].filter(v => v != null);
    return { t, title, pts, avgG, thr, eMin, eMax, gs, lo, hi, step, xs, cNT, cT1, same, gT, all };
  });
  const ALLY = PREP.filter(Boolean).flatMap(P => P.all);
  const yLo = Math.floor(Math.min(...ALLY) / 1000) * 1000, yHi = Math.ceil(Math.max(...ALLY) / 1000) * 1000;
  host.innerHTML = PREP.map(P => {
    if (!P) return '';
    const { t, title, pts, avgG, thr, eMin, eMax, gs, lo, hi, step, xs, cNT, cT1, same, gT } = P;
    for (const c of ['__cc_nt', '__cc_t1']) D.staff.schools[c].grades_2526 = avgG;   // later per() calls use this type's grade mix""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
