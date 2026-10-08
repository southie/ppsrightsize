"""rightsizing-scenario-explorer.html: two more district summary cards at the top of the page:
school-years over 2021 functional capacity (2025-26 to 2035-36) and the share of attendance-area residents
within 15 minutes of their school (walk, with bike and drive), each with the change from Status Quo.
Uses the same definitions as the over-capacity list and the endpoints table's 15-minute column
(reachRoll, added by patch_reach.py). Safe to rerun: the code is only added once.
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

if 'function extraKPIs' not in html:
    rep(".kpi .d { font-size: 12.5px; margin-left: 6px; font-weight: 600; }",
        ".kpi .d { font-size: 12.5px; margin-left: 6px; font-weight: 600; }\n"
        ".kpi .s { font-size: 12.5px; color: var(--text-secondary); margin-top: 2px; } .kpi .s b { color: var(--text-primary); }")
    rep("function renderKPIs() {",
"""// school-years over 2021 functional capacity, and residents within 15 minutes of their school (district)
function overSchoolYears(sc) {
  const s = D.series[sc] || {}; let n = 0;
  for (const k of Object.keys(s)) { const c = byKey[k]?.fc; if (c) for (const v of s[k]) if (v != null && v > c) n++; }
  return n;
}
function extraKPIs() {
  const delta = (d, unit, worseUp) => scen === 'SQ' || !d ? '' :
    `<span class="d" style="color:${(worseUp ? d < 0 : d > 0) ? 'var(--up)' : 'var(--down)'}">${d > 0 ? '+' : '&minus;'}${Math.abs(d)}${unit}</span>`;
  const ov = overSchoolYears(scen), ovSq = overSchoolYears('SQ');
  const keys = Object.keys(D.region_of), r = reachRoll(scen, keys), rs = reachRoll('SQ', keys);
  const sub = (m, l) => r[m] == null ? '' : `${l} <b>${r[m]}%</b>${scen !== 'SQ' && rs[m] != null && r[m] !== rs[m] ? ` (${r[m] > rs[m] ? '+' : '&minus;'}${Math.abs(r[m] - rs[m])})` : ''}`;
  return `<div class="kpi"><div class="v">${ov}${delta(ov - ovSq, ' vs SQ', true)}</div>` +
      `<div class="l">School-years over 2021 functional capacity, ${D.years[0]} to ${D.years[D.years.length - 1]}</div></div>` +
    `<div class="kpi"><div class="v">${r.w == null ? '&mdash;' : r.w + '%'}${r.w != null && rs.w != null ? delta(r.w - rs.w, ' pts', false) : ''}</div>` +
      `<div class="l">District: attendance-area residents within a 15-minute walk of their school</div>` +
      `<div class="s">${[sub('b', 'Bike'), sub('d', 'Drive')].filter(Boolean).join(' &middot; ')}</div></div>`;
}
function renderKPIs() {""")
    rep("""  }).join('');
  document.getElementById('desc').textContent = scen === 'SQ'""",
        """  }).join('') + extraKPIs();
  document.getElementById('desc').textContent = scen === 'SQ'""")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
