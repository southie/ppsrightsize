"""Class sizes and teacher loads by grade: split each school's projected enrollment into grades with the grade
progression ratios of PPS's district enrollment forecast (Portland Public Schools Enrollment Forecast 2026-27,
Population Research Center, PSU, Table 5.2, medium scenario; source/pps-forecast/table-5.2-medium.json) instead of
holding each school's 2025-26 grade mix fixed, and cross-check the district totals by grade against that table.

Each school starts from its 2025-26 enrollment by grade. Every year its cohorts move up a grade at the district's
ratio of this year's grade to last year's grade below; its entry grade (K; grade 6 in a middle school; grade 9 in a
high school) is its 2025-26 share of the district's entering grade. The shares within each grade band are then applied
to the school's projected band total, so school totals and scenario moves are unchanged. Runs after
patch_class_sizes / patch_class_kpi. Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
F = json.load(open(os.path.join(ROOT, 'source', 'pps-forecast', 'table-5.2-medium.json'), encoding='utf-8'))
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['forecast52'] = dict(source=F['source'], years=F['years'], grades=F['grades'])
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function gradeProgress' not in html:
    rep("const CS_GRADES = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];",
        r"""const CS_GRADES = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
// grade progression (PPS enrollment forecast 2026-27, Table 5.2, medium scenario): a school's cohorts move up a grade
// each year at the district's ratio of this year's grade to last year's grade below; its entry grade (K; 6 in a middle
// school; 9 in a high school) is its 2025-26 share of the district's entering grade
const F52 = D.forecast52, F52Y = Object.fromEntries(F52.years.map((y, i) => [y, i])), CS_ENTRY = { ES: [0], K8: [0], MS: [6], HS: [9] };
const f52 = (gi, y) => F52.grades[CS_GRADES[gi]]?.[F52Y[y]];
const GP_CACHE = {};
function gradeProgress(k, yi) {
  const key = k + '@' + yi; if (GP_CACHE[key]) return GP_CACHE[key];
  const g0 = (D.staff.schools[k]?.grades_2526 || []).slice(0, 13), ent = CS_ENTRY[D.types.SQ[k]] || [0], y0 = D.years[0];
  let cur = CS_GRADES.map((_, i) => g0[i] || 0);
  for (let j = 1; j <= yi; j++) {
    const y = D.years[j], p = D.years[j - 1];
    cur = cur.map((_, i) => ent.includes(i) ? (g0[i] || 0) / f52(i, y0) * f52(i, y)
      : i > 0 && cur[i - 1] > 0 ? cur[i - 1] * f52(i, y) / f52(i - 1, p) : 0);
  }
  return GP_CACHE[key] = cur;
}""")
    rep("""  const g = D.staff.schools[k]?.grades_2526 || [];
  const mix = (lo, hi) => { const s = CS_GRADES.slice(lo, hi + 1).map((_, i) => g[lo + i] || 0), tot = s.reduce((a, b) => a + b, 0);
    return tot ? s.map(x => x / tot) : s.map(() => 1 / s.length); };""",
        """  const gp = gradeProgress(k, yi), yr = D.years[yi];
  // shares of each grade within a band: the school's progressed grades, or the district forecast's if it has none
  const mix = (lo, hi) => { const s = CS_GRADES.slice(lo, hi + 1).map((_, i) => gp[lo + i] || 0), tot = s.reduce((a, b) => a + b, 0);
    if (tot) return s.map(x => x / tot);
    const d = CS_GRADES.slice(lo, hi + 1).map((_, i) => f52(lo + i, yr) || 1), dt = d.reduce((a, b) => a + b, 0); return d.map(x => x / dt); };""")
    rep("  if (k5) k5Shares(k).forEach((s, i) => {", "  if (k5) mix(0, 5).forEach((s, i) => {")
    rep('<td colspan="18" style="text-align:left"><span class="stag closes">Closes</span> <span class="muted">no students in ${csYear}</span>',
        '<td colspan="16" style="text-align:left"><span class="stag closes">Closes</span> <span class="muted">no students in ${csYear}</span>')
    # ---- cross-check rows: Table 5.2 by grade, and these schools' share of it ----
    rep("  h += `<tr class=\"dist\"><td>District</td>${sumCells(sumRows(all))}</tr>`;",
        r"""  h += `<tr class="dist"><td>District</td>${sumCells(sumRows(all))}</tr>`;
  // cross-check against the district forecast by grade (all PPS schools, including those not on this page)
  const fg = CS_GRADES.map((_, i) => f52(i, csYear));
  if (fg.every(v => v != null)) {
    const dist = sumRows(all), ft = fg.reduce((a, b) => a + b, 0), ours = i => dist.grades[i].n, pc = v => Math.round(100 * v) + '%';
    const cells = f => [...fg.slice(0, 9).map((v, i) => f(v, i)), '<td></td>', ...fg.slice(9).map((v, i) => f(v, 9 + i)), '<td></td>'].join('');
    h += `<tr class="csfc"><td>PPS forecast, Table 5.2<span class="cssub">medium scenario, all PPS schools</span></td><td>${n0(ft)}</td>` +
      cells(v => `<td>${n0(v)}</td>`) + '</tr>';
    h += `<tr class="csfc"><td>These schools' share<span class="cssub">of the forecast, by grade</span></td><td>${pc(dist.E / ft)}</td>` +
      cells((v, i) => `<td title="${esc(`${n0(ours(i))} students at the schools on this page in grade ${CS_GRADES[i]}, of ${n0(v)} in the district forecast`)}">${pc(ours(i) / v)}</td>`) + '</tr>';
  }""")
    rep("(this page's projection, split by each school's 2025-26 grade mix)",
        "(this page's projection, split into grades with the grade progression ratios of PPS's district enrollment forecast, Table 5.2 medium scenario, starting from each school's 2025-26 grades)")
    rep("Click a region to see its schools; hover a cell for details.</p>",
        "Click a region to see its schools; hover a cell for details. The last two rows check the district totals by grade against the forecast's Table 5.2 (all PPS schools, including those not on this page): within each grade band the share should be about even.</p>")
    rep(".csover-key { padding: 0 4px; border-radius: 3px; }",
        ".csover-key { padding: 0 4px; border-radius: 3px; }\n.cstable tr.csfc td { color: var(--text-secondary); font-size: 12.5px; } .cstable tr.csfc:first-of-type td { border-top: 2px solid var(--line); }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
