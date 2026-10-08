"""Separate summary card for yellow-bus cost and bus ride time (from the getting-to-school card): the added general
yellow-bus cost in the year the scenarios take effect (Status Quo: what the general routes cost), the change in
bus-eligible K-8 students, the table year's cost when different, and the average bus ride. Clicking it opens the
"Estimated yellow-bus cost" block. Runs after patch_bus_hist. Safe to rerun: added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function busKPI' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# the bus line leaves the getting-to-school card; its own card follows it
rep("pts)</span>`}${busLine()}</div></div>`;", "pts)</span>`}</div></div>`;")
rep("    commuteKPI() +\n", "    commuteKPI() + busKPI() +\n")
a = html.index('function busLine() {'); b = html.index('\n}\n', a) + 3
html = html[:a] + r"""// summary card: yellow-bus cost and bus ride time. Scenarios: the immediate impact, in the year they take effect
// (D.impl_year), plus the getting-to-school table's year when different. Status Quo: what the general routes cost.
function busKPI() {
  const keys = Object.keys(D.region_of), K = `${BC.min_per_mile.toFixed(1)} min per bus-mile`;
  if (scen === 'SQ') {
    const rq = cmAgg('SQ', keys, 'all');
    return `<div class="kpi"><div class="v">${bcM((BC.gt[0] + BC.gt[1]) / 2)}<span class="d" style="color:var(--text-muted)">a year</span></div>` +
      `<div class="l">General yellow-bus routes (est.; home-to-school, 2026-27 budget)</div>` +
      `<div class="s">Range: ${bcRange(...BC.gt)} a year<br>${cmN(rq.be8)} K-8 students beyond bus distance, ${cmYear}<br>` +
      `Average bus ride, eligible K-8: <b>${rq.busmin.toFixed(0)} min</b> one way <span class="pcs">at ${K}</span><br>` +
      `${bcD(BC.box.low)}&ndash;${bcD(BC.box.high)} a year per daily student-mile</div></div>`;
  }
  const s = cmAtYear(D.impl_year, busScen), save = s.hi < 0;
  const rc = cmAtYear(D.impl_year, () => cmAgg(scen, keys, 'all')), rq = cmAtYear(D.impl_year, () => cmAgg('SQ', keys, 'all'));
  const dm = rc.busmin - rq.busmin;
  let sub = `Range: ${bcMoney(s.lo, s.hi)} a year<br>K-8 students beyond bus distance: <b>${s.d_elig >= 0 ? '+' : '&minus;'}${cmN(Math.abs(s.d_elig))}</b> <span class="pcs">(${cmN(rc.be8)} in all)</span>`;
  if (cmYear !== D.impl_year) { const t = busScen(); sub += `<br>${cmYear}: <b>${bcMoney(t.lo, t.hi)}</b> a year`; }
  sub += `<br>Average bus ride, eligible K-8: <b>${rc.busmin.toFixed(0)} min</b> one way` +
    (Math.abs(dm) >= 0.05 ? ` <span class="pcs">(${dm > 0 ? '+' : '&minus;'}${Math.abs(dm).toFixed(1)} min)</span>` : '') + ` <span class="pcs">at ${K}</span>`;
  return `<div class="kpi"><div class="v">${save ? '&minus;' : '+'}${bcM(s.mid)}<span class="d" style="color:var(--text-muted)">a year</span></div>` +
    `<div class="l">${save ? 'Change in' : 'Added'} general yellow-bus cost in ${D.impl_year}, the first year (est.)${scen === 'C' ? `; ${esc(custom.name || 'custom scenario')}` : ''}</div>` +
    `<div class="s">${sub}</div></div>`;
}
""" + html[b:]

# card links to the bus-cost block
rep("const KPI_TARGETS = ['closures', 'schools_above', 'students_above', 'change', 'overcap', 'commute', 'cost', 'land', 'staff'];",
    "const KPI_TARGETS = ['closures', 'schools_above', 'students_above', 'change', 'overcap', 'commute', 'bus', 'cost', 'land', 'staff'];")
rep("  if (target === 'commute') {", """  if (target === 'bus') {
    const b = document.getElementById('buscost'); if (!b) return;
    b.scrollIntoView({ behavior: 'smooth', block: 'start' }); flash([b]); return;
  }
  if (target === 'commute') {""")
rep("t === 'commute' ? 'Show getting to school by region' :", "t === 'commute' ? 'Show getting to school by region' : t === 'bus' ? 'Show how the bus cost is estimated' :")
rep(".buscost { margin-top: 18px; }", ".buscost { margin-top: 18px; scroll-margin-top: 72px; }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
