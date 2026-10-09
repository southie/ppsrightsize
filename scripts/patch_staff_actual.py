"""Actual school staffing on the explorer: district-wide teachers and school administrators (principals and assistant
principals) from PPS's budget school reports (source/staffing/school-staff-budget.json, scripts/build_school_staff.py),
shown on the staffing summary card (Status Quo) and in the staffing section's summary, next to the staffing formula's
Status Quo figures for the same schools and year. Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
S = json.load(open(os.path.join(ROOT, 'source', 'staffing', 'school-staff-budget.json'), encoding='utf-8'))
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['staff_actual'] = {k: S[k] for k in ('source', 'years', 'budget_year', 'district', 'reports', 'not_on_explorer')}
D['staff_actual']['schools'] = {k: {f: v[f] for f in ('teachers', 'admin', 'clerical')} for k, v in S['schools'].items()}
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function staffActual' not in html:
    rep("function staffKPI() {", r"""// actual school staffing from PPS's budget school reports (D.staff_actual): budget year and the year before (actual),
// district-wide (every school report) and for the schools on this page, against the formula's Status Quo there
function staffActual() {
  const A = D.staff_actual; if (!A) return null;
  const j = A.years.indexOf(A.budget_year), keys = Object.keys(A.schools);
  const sum = (f, i) => keys.reduce((s, k) => s + (A.schools[k][f]?.[i] || 0), 0);
  const f = staffAgg(keys, 'SQ', D.years.indexOf(A.budget_year));
  return { y: A.budget_year, ya: A.years[j - 1], t: A.district.teachers[j], a: A.district.admin[j], ta: A.district.teachers[j - 1], aa: A.district.admin[j - 1],
           n: A.reports, others: A.not_on_explorer, k: keys.length, mt: sum('teachers', j), ma: sum('admin', j), mc: sum('clerical', j),
           ft: f.homeroom + f.specialists + f.t68 + f.t912, fa: f.principal + f.ap, fo: f.office };
}
const n0s = v => Math.round(v).toLocaleString();
function staffKPI() {""")
    rep("""      `Cost: <b>${pos(s.base.usd)}</b> a year (salary + benefits, 2026-27 $)</div></div>`;
  }""", """      `Cost: <b>${pos(s.base.usd)}</b> a year (salary + benefits, 2026-27 $)` +
      ((x) => x ? `<br><span title="${esc(`PPS ${x.y} budget, Volume 2 school reports (${x.n} schools and programs; 1.00 FTE = 40 hours a week). ${x.ya} actual: ${n0s(x.ta)} teachers, ${n0s(x.aa)} administrators.`)}">PPS budget, ${x.y}: <b>${n0s(x.t)}</b> teachers, <b>${n0s(x.a)}</b> principals &amp; APs district-wide</span>` : '')(staffActual()) +
      `</div></div>`;
  }""")
    rep("""  document.getElementById('staffsum').innerHTML = isSQ""", """  const sa = staffActual();
  const saLine = sa ? `<span style="display:block;margin-top:6px">Check against PPS's ${sa.y} budget (school reports, 1.00 FTE = 40 hours a week): at the ${sa.k} schools on this page, <b>${n0s(sa.mt)}</b> teachers vs the formula's ${n0s(sa.ft)} (homeroom, specialist and 6-12 teachers, Status Quo ${sa.y}), and <b>${n0s(sa.ma)}</b> principals and assistant principals vs the formula's ${n0s(sa.fa)}; ${n0s(sa.mc)} clerical staff vs the formula's ${sa.fo.toFixed(0)} licensed-equivalent office FTE (about ${n0s(2 * sa.fo)} positions). ` +
    `District-wide, with ${sa.others.length} programs this page does not model, the budget has <b>${n0s(sa.t)}</b> teachers and <b>${n0s(sa.a)}</b> administrators (${sa.ya} actual: ${n0s(sa.ta)} and ${n0s(sa.aa)}).</span>` : '';
  document.getElementById('staffsum').innerHTML = (isSQ""")
    # close the parenthesis opened above and append the line, whichever branch
    i = html.index("  document.getElementById('staffsum').innerHTML = (isSQ")
    j = html.index(";\n", i)
    html = html[:j] + ") + saLine" + html[j:]
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
