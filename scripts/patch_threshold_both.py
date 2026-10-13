"""Both threshold figures on both charts. The two charts value a school at the sustainability threshold size differently:
"General Fund cost per student by school" fits each type's actual 2026-27 General Fund staffing (budget school
reports) and reads it at the threshold (the target); "The sustainability threshold impact on cost per student by
school size" reads PPS's base staffing formula at the threshold for a non-Title I school with the type's average grade
mix. Now the General Fund chart (per student) also marks the formula figure (gray dash-dot line, in each group's
heading), and each cost curve also marks the General Fund target (hollow diamond, in its label), with a note on why
they differ. Helpers: ccThrCost(t, yi) (formula at the threshold) and gfFit(g, t) (the General Fund fit), shared by
both charts. Code added once.
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

if 'ccThrCost' not in html:
    # shared helpers, before the General Fund chart
    rep("""function renderGFPer() {""", """// both threshold figures on both charts (scripts/patch_threshold_both.py)
// the General Fund target for a school type: cost per student = a + b / enrollment, least squares over the type's
// schools (actual 2026-27 General Fund staffing), at the threshold size; the group average where there is no size trend
function gfFit(g, t) {
  const avg = g.reduce((a, r) => a + r.gf, 0) / g.reduce((a, r) => a + r.e, 0);
  const thr = D.thresholds[t], n = g.length, xs = g.map(r => 1 / r.e), ys = g.map(r => r.c);
  const mx = xs.reduce((a, v) => a + v, 0) / n, my = ys.reduce((a, v) => a + v, 0) / n;
  const sxx = xs.reduce((a, v) => a + (v - mx) ** 2, 0), b = n > 2 && sxx > 0 ? xs.reduce((a, v, j) => a + (v - mx) * (ys[j] - my), 0) / sxx : 0;
  const fitOK = b > 0, a = my - b * mx;
  return { avg, thr, target: fitOK ? a + b / thr : avg, a, b, fitOK };
}
function gfTargetOf(t) { const g = (gfPerData() || []).filter(r => r.t === t); return g.length ? gfFit(g, t) : null; }
// PPS's base staffing formula cost per student at the threshold size: a non-Title I school with the type's average
// grade mix (the cost curve's solid line)
function ccThrCost(t, yi) {
  const ks = Object.keys(D.region_of).filter(k => D.types.SQ[k] === t && D.series.SQ[k]?.[yi] > 0);
  const gs = ks.map(k => D.staff.schools[k]?.grades_2526).filter(Boolean);
  D.staff.schools.__cc_nt = { title1: false, grades_2526: gs.length ? gs[0].map((_, i) => gs.reduce((a, g) => a + (g[i] || 0), 0) / gs.length) : null };
  const thr = D.thresholds[t], r = schoolFTE('__cc_nt', 'SQ', yi, thr, t);
  return r ? staffCost(r) / thr : null;
}
function renderGFPer() {""")
    # General Fund chart: use the shared fit, add the formula figure
    rep("""    const avg = g.reduce((a, r) => a + r.gf, 0) / g.reduce((a, r) => a + r.e, 0);
    // target: cost per student = a + b / enrollment, least squares over the type's schools, at the threshold size
    const thr = D.thresholds[t], n = g.length, xs = g.map(r => 1 / r.e), ys = g.map(r => r.c);
    const mx = xs.reduce((a, v) => a + v, 0) / n, my = ys.reduce((a, v) => a + v, 0) / n;
    const sxx = xs.reduce((a, v) => a + (v - mx) ** 2, 0), b = n > 2 && sxx > 0 ? xs.reduce((a, v, j) => a + (v - mx) * (ys[j] - my), 0) / sxx : 0;
    const fitOK = b > 0, a = my - b * mx, target = fitOK ? a + b / thr : avg;""",
        """    // target: cost per student = a + b / enrollment, least squares over the type's schools, at the threshold size
    const { avg, thr, target, a, b, fitOK } = gfFit(g, t);
    const form = typeof schoolFTE === 'function' ? ccThrCost(t, D.years.indexOf('2026-27')) : null;   // formula at the threshold""")
    rep("""    return { t, lab, g, avg, avg1, n1: g1.length, thr, target, a, b, fitOK };""",
        """    return { t, lab, g, avg, avg1, n1: g1.length, thr, target, a, b, fitOK, form };""")
    rep("""...(SUB ? [] : [G.avg - Z, G.target - Z, ...(G.avg1 != null ? [G.avg1 - Z] : [])])])];""",
        """...(SUB ? [] : [G.avg - Z, G.target - Z, ...(G.avg1 != null ? [G.avg1 - Z] : []), ...(G.form != null ? [G.form - Z] : [])])])];""")
    rep("""per student at the ${G.thr}-student threshold &middot; group average ${usd(G.avg)} (2026-27)""",
        """per student at the ${G.thr}-student threshold${G.form != null ? ` <tspan fill="var(--text-secondary)">(formula ${usd(G.form)})</tspan>` : ''} &middot; group average ${usd(G.avg)} (2026-27)""")
    rep("""      (G.avg1 != null ? `<line x1="${x(G.avg1 - Z)}\"""",
        """      (G.form != null ? `<line x1="${x(G.form - Z)}" x2="${x(G.form - Z)}" y1="${top - 2}" y2="${bot + 2}" stroke="var(--text-secondary)" stroke-width="1.6" stroke-dasharray="8 3 2 3"><title>${esc(`${G.lab}, PPS base staffing formula at the ${G.thr}-student threshold: ${usd(G.form)} per student (2026-27; non-Title I, the type's average grade mix; the marker on the cost-by-size chart). Lower than the target (${usd(G.target)}), which is fit to actual General Fund staffing: schools carry General Fund positions beyond the base formula.`)}</title></line>` : '') +
      (G.avg1 != null ? `<line x1="${x(G.avg1 - Z)}\"""")
    rep("""<span><i class="k" style="border-top:2px dashed var(--text-primary);width:18px"></i>group average${SC ? ', 2026-27' : ''}</span>""",
        """<span><i class="k" style="border-top:2px dashed var(--text-primary);width:18px"></i>group average${SC ? ', 2026-27' : ''}</span><span><i class="k" style="border-top:2px dashed var(--text-secondary);width:18px"></i>formula cost at the threshold (base staffing formula, as on the cost-by-size chart)</span>""")
    # cost-by-size chart: add the General Fund target
    rep("""    const all = [...cNT, ...(same ? [] : cT1), ...pts.map(p => p.c)].filter(v => v != null);""",
        """    const gT = gfTargetOf(t);   // the General Fund chart's target (scripts/patch_threshold_both.py)
    const all = [...cNT, ...(same ? [] : cT1), ...pts.map(p => p.c), ...(gT ? [gT.target] : [])].filter(v => v != null);""")
    rep("""      `<text x="${x(thr) + (x(thr) > W - 120 ? -6 : 6)}" y="${T + 11}" font-size="10.5" font-weight="600" text-anchor="${x(thr) > W - 120 ? 'end' : 'start'}" fill="var(--change)">threshold ${thr}: ${usd(cThr)}</text>`;""",
        """      `<text x="${x(thr) + (x(thr) > W - 120 ? -6 : 6)}" y="${T + 11}" font-size="10.5" font-weight="600" text-anchor="${x(thr) > W - 120 ? 'end' : 'start'}" fill="var(--change)">threshold ${thr}: ${usd(cThr)} formula</text>` +
      (gT ? `<path d="M${x(thr)},${y(gT.target) - 6} l6,6 l-6,6 l-6,-6 Z" fill="var(--surface-1)" stroke="var(--change)" stroke-width="1.8"><title>${esc(`General Fund target at ${thr} students: ${usd(gT.target)} per student (the General Fund cost per student chart's target: a fit of ${title.toLowerCase()}' actual 2026-27 General Fund staffing${gT.fitOK ? `, ${usd(gT.a)} + ${usd(gT.b)} / enrollment` : '; no size trend, group average'}). Higher than the formula (${usd(cThr)}): schools carry General Fund positions beyond the base formula.`)}</title></path>` +
        `<text x="${x(thr) + (x(thr) > W - 120 ? -6 : 6)}" y="${T + 24}" font-size="10.5" font-weight="600" text-anchor="${x(thr) > W - 120 ? 'end' : 'start'}" fill="var(--change)">&#9671; ${usd(gT.target)} General Fund (actual)</text>` : '');""")
    rep("""The shaded line marks the sustainability threshold.""",
        """The shaded line marks the sustainability threshold: the filled dot is the formula's cost per student there, and the hollow diamond is the General Fund cost per student chart's target (a fit of each type's actual 2026-27 General Fund staffing at the threshold size), which runs higher because schools carry General Fund positions beyond the base formula.""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
