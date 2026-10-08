"""Estimated yellow-bus cost on the explorer: a line on the getting-to-school summary card, an "Estimated yellow-bus
cost" block under the getting-to-school table (scenario change, cost-per-student-mile range, how it is estimated,
caveats) and a method note. Data from source/pps-bus/bus-cost-estimate.json (scripts/estimate_bus_cost.py).
Safe to rerun: the data is always refreshed, the page code is added once.
"""
import csv, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
E = json.load(open(os.path.join(ROOT, 'source', 'pps-bus', 'bus-cost-estimate.json'), encoding='utf-8'))
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))

# ---------- data ----------
# walking miles of each school's bus-eligible K-8 residents (K-5 beyond 1 mile, 6-8 beyond 1.5), per scenario and band
M = {}
for r in csv.DictReader(open(os.path.join(ROOT, 'source', 'block-access', 'school-access.csv'), encoding='utf-8')):
    col = {'k5': 'beyond_1mi_walkmi', '68': 'beyond_1.5mi_walkmi'}.get(r['band'])
    if col and r[col]: M.setdefault(r['scenario'], {}).setdefault(r['school'], {})[r['band']] = int(float(r[col]))
V = ['upper', 'lower']   # general-route cost: less TriMet only / less all non-route transportation
A, R = E['assumptions'], E['routes']
D['buscost'] = dict(
    budget=A['budget_2550'], budget_prior=A['budget_2550_prior'], all_routes=A['all_bus_routes'],
    acct=A['accounts'], removed=[A['removed'][v] for v in V],
    ride_share=A['ride_share'], rate_year=A['rate_year'], eligible=R['eligible_students'],
    runs=R['runs'], runs_measured=R['runs_measured'], buses=R['buses_estimated'], schools=R['schools_served'],
    daily_miles=R['daily_route_miles'], mean_ride=R['mean_ride_miles'],
    median_ride=R['median_ride_miles'], walk_mean=R['eligible_mean_walk_miles'], ratio=R['ride_to_walk_ratio'],
    min_per_mile=R['min_per_bus_mile'], ride_stops=R['ride_time_stops'], mean_ride_min=R['mean_ride_min'],
    gt=[E['cost'][v]['general_routes_cost'] for v in V],
    per_mile=[E['cost'][v]['per_daily_bus_mile'] for v in V],
    cases={k: dict(riders=c['riders'], per_run=c['riders_per_run'], psm=[c['per_daily_student_mile'][v] for v in V],
                   rider=[c['per_rider_year'][v] for v in V]) for k, c in E['cases'].items()},
    box=E['box_per_daily_student_mile'],
    M=M)
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderBusCost' not in html:
    # ---- summary card line ----
    rep("""(${wd > 0 ? '+' : '&minus;'}${Math.abs(wd)} pts)</span>`}</div></div>`;""",
        """(${wd > 0 ? '+' : '&minus;'}${Math.abs(wd)} pts)</span>`}${busLine()}</div></div>`;""")

    # ---- block under the getting-to-school table ----
    rep("""    <div class="tablewrap" id="commute"></div>
  </section>""", """    <div class="tablewrap" id="commute"></div>
    <div id="buscost" class="buscost"></div>
  </section>""")
    rep("""  document.getElementById('commutesum').innerHTML = (scen === 'SQ'""",
        """  renderBusCost();
  document.getElementById('commutesum').innerHTML = (scen === 'SQ'""")

    rep("// building costs (D.costs, 2026 dollars)", r"""// ---------- yellow-bus cost (D.buscost, from scripts/estimate_bus_cost.py) ----------
// Two values for the general-route cost bound every figure (adopted budget accounts): index 0 = transportation less
// the TriMet high school pass payment (upper); index 1 = also less taxis, field trips and other non-route transport (lower).
const BC = D.buscost;
const bcM = v => '$' + (Math.abs(v) / 1e6).toFixed(Math.abs(v) >= 1e7 ? 1 : 2) + 'M';
const bcD = v => '$' + Math.round(v).toLocaleString();
const bcK = v => '$' + Math.round(v / 1000).toLocaleString() + 'k';
const bcKRange = (a, b) => `${bcK(Math.min(a, b))}&ndash;${bcK(Math.max(a, b))}`;
const bcRange = (a, b) => { const lo = Math.min(a, b), hi = Math.max(a, b); return bcM(lo) === bcM(hi) ? bcM(lo) : `${bcM(lo)}&ndash;${bcM(hi)}`; };
// scenario change in bus-eligible K-8 students and their bus student-miles, district-wide, in the table's year
// (cmYear): student-miles a school day = eligible students' walking miles x ride-to-walk ratio x central ridership
// x 2 trips; cost = that x the annual cost per daily student-mile (one value per general-route cost bound)
function busScen() {
  const keys = Object.keys(D.region_of), f = BC.ratio * BC.ride_share.central * 2;
  const agg = sc => ['k5', '68'].map(b => cmAgg(sc, keys, b)).reduce((a, o) => ({ n: a.n + o.beyond, m: a.m + o.bm }), { n: 0, m: 0 });
  const c = agg(scen), q = agg('SQ'), d_sm = (c.m - q.m) * f;
  const cost = BC.cases.central.psm.map(p => d_sm * p);
  return { d_elig: c.n - q.n, d_walk: q.m ? (c.m - q.m) / q.m : 0, d_sm, lo: Math.min(...cost), hi: Math.max(...cost), mid: (cost[0] + cost[1]) / 2 };
}
// run fn as if the getting-to-school table showed year y (cmStu / cmAgg read cmYear)
function cmAtYear(y, fn) { const keep = cmYear; cmYear = y; try { return fn(); } finally { cmYear = keep; } }
// summary card: the immediate impact, in the year the scenarios take effect (D.impl_year), plus the table's year if different
function busLine() {
  if (scen === 'SQ') return `<br>General yellow-bus routes: about <b>${bcRange(...BC.gt)}</b> a year (est.)`;
  const s = cmAtYear(D.impl_year, busScen), more = s.d_elig >= 0;
  let h = `<br>Added yellow-bus cost in ${D.impl_year}, the first year: <b>${bcRange(s.lo, s.hi)}</b> a year (est.; ` +
    `${cmN(Math.abs(s.d_elig))} ${more ? 'more' : 'fewer'} K-8 students beyond bus distance)`;
  if (cmYear !== D.impl_year) { const t = busScen(); h += `<br><span class="pcs">${cmYear}: ${bcRange(t.lo, t.hi)} a year</span>`; }
  return h;
}
function renderBusCost() {
  const host = document.getElementById('buscost'); if (!host) return;
  const s = scen === 'SQ' ? null : busScen(), perBus = BC.gt.map(g => g / BC.buses), n = v => Math.round(v).toLocaleString();
  const pct = v => (100 * v).toFixed(1) + '%';
  let h = '<h3>Estimated yellow-bus cost</h3>';
  h += scen === 'SQ'
    ? `<p class="sub">PPS's general (home-to-school) yellow-bus routes cost an estimated <b>${bcRange(...BC.gt)}</b> a year, about <b>${bcD(BC.box.low)}&ndash;${bcD(BC.box.high)}</b> a year per daily student-mile (central ${bcD(BC.box.central)}). Pick Scenario A or B to see the added cost of longer trips.</p>`
    : `<p class="sub">Under ${LABEL[scen]} in ${cmYear}${scen === 'C' ? ` (your custom scenario's enrollment with ${LABEL[custom.base]}'s attendance areas)` : ''}, <b>${n(s.d_elig)}</b> ${s.d_elig >= 0 ? 'more' : 'fewer'} K-8 students live beyond bus distance than under Status Quo, and their walks to school are <b>${Math.round(100 * Math.abs(s.d_walk))}%</b> ${s.d_walk >= 0 ? 'longer' : 'shorter'} in total. ` +
      `That adds about <b>${n(s.d_sm)}</b> student-miles a school day on the bus (central ridership) and, at ${bcD(Math.min(...BC.cases.central.psm))}&ndash;${bcD(Math.max(...BC.cases.central.psm))} a year per daily student-mile, about <b>${bcRange(s.lo, s.hi)}</b> a year in general yellow-bus cost. ` +
      `At today's cost per bus (${bcKRange(...perBus)} a year), that is the cost of roughly <b>${Math.round(s.mid / (perBus[0] + perBus[1]) * 2)}</b> more buses, if the extra riders cannot fit on existing runs (see caveats).</p>`;
  // range table: cost per student-mile
  const cols = [['high', 'More riders'], ['central', 'Central'], ['low', 'Fewer riders']];
  h += `<div class="tablewrap"><table class="bctable"><thead><tr><th>Annual cost per daily student-mile</th>${cols.map(([k, l]) => `<th>${l}<br><span style="font-weight:400">${n(BC.cases[k].riders)} riders a day, ${Math.round(100 * BC.ride_share[k])}% of eligible</span></th>`).join('')}</tr></thead><tbody>` +
    [0, 1].map(i => `<tr><td>General routes ${bcM(BC.gt[i])} a year <span class="muted">(${i ? 'transportation less TriMet, taxis, field trips and other non-route transport' : 'transportation less TriMet passes'})</span></td>${cols.map(([k]) => `<td>${bcD(BC.cases[k].psm[i])}</td>`).join('')}</tr>`).join('') +
    `<tr class="dist"><td>Range</td><td>${bcD(BC.box.low)}</td><td>${bcD(BC.box.central)}</td><td>${bcD(BC.box.high)}</td></tr></tbody></table></div>`;
  // how it is estimated
  h += `<details class="bcdet"><summary>How the cost per daily student-mile is estimated</summary><ol>` +
    `<li><b>Transportation budget.</b> General Fund function 2550, Student Transportation Services: <b>${bcM(BC.budget)}</b> in the 2026-27 adopted budget (Volume 1, p. 108; unchanged from the proposed budget; ${bcM(BC.budget_prior)} in 2025-26). It also pays for special-education transportation, TriMet passes, taxis and administration.</li>` +
    `<li><b>Less transportation that is not yellow-bus routes.</b> The adopted budget's General Fund accounts (Volume 1, p. 110) show <b>${bcM(BC.acct.trimet)}</b> for high school TriMet passes, ${bcM(BC.acct.taxi)} for taxis, ${bcM(BC.acct.field_trips)} for field trips and ${bcM(BC.acct.other_transport)} for other student transport. The upper value takes out TriMet passes only; the lower value takes out all of these (${bcM(BC.removed[1])}).</li>` +
    `<li><b>Share for general routes.</b> The ${BC.runs} current general route runs posted on PPS's bus schedule site (${BC.schools} schools) need about <b>${BC.buses}</b> buses at the busiest time of day (runs under way at once, plus 10 minutes between runs). PPS ran ${BC.all_routes} bus routes in all in 2023-24, most of the rest special education, so general routes get ${pct(BC.buses / BC.all_routes)} of the rest of the budget: <b>${bcRange(...BC.gt)}</b> a year (${bcKRange(...perBus)} per bus).</li>` +
    `<li><b>Bus miles.</b> Each run's stops were located (street intersections from OpenStreetMap, addresses by the US Census geocoder) and the run measured along the street network: about <b>${n(BC.daily_miles)}</b> route miles a school day (${bcD(Math.min(...BC.per_mile))}&ndash;${bcD(Math.max(...BC.per_mile))} a year per daily route mile). A student's ride from their stop to school averages <b>${BC.mean_ride} miles</b> along the route (median ${BC.median_ride}).</li>` +
    `<li><b>Riders.</b> PPS does not publish ridership. About <b>${n(BC.eligible)}</b> K-8 students at the schools these routes serve live beyond bus distance (${BC.rate_year} enrollment &times; the census share of each school's area beyond bus distance); the central case assumes half of them ride (35% and 65% for the other cases), so <b>${n(BC.cases.central.riders)}</b> riders a day, about ${BC.cases.central.per_run} per run.</li>` +
    `<li><b>Annual cost per daily student-mile</b> = general-route cost a year &divide; (riders &times; ride miles &times; 2 trips). Costs are annual and miles are per school day, so the length of the school year is not needed.</li>` +
    `<li><b>Scenarios.</b> The change in bus-eligible K-8 students' total walking miles to school in the selected year (projected enrollment &times; each area's census walking miles beyond bus distance per resident; the table above) is turned into bus miles with the ratio of the measured ride to those students' walking distance under Status Quo (${BC.ratio.toFixed(1)}&times;: ${BC.mean_ride} miles on the bus for ${BC.walk_mean} miles on foot), then multiplied by the annual cost per daily student-mile. Ridership drops out: more riders means more added miles but a lower cost per mile, so the scenario range comes from the two general-route cost values.</li></ol></details>`;
  // caveats
  h += `<details class="bcdet" open><summary>Caveats</summary><ul>` +
    `<li><b>Bus utilization is unknown, and it matters most.</b> The estimate assumes cost grows in step with student-miles, as if buses ran at today's average load. PPS does not publish how full its buses are. If current runs have empty seats along the new students' paths, many added riders could be carried for little more than extra stops and miles, and the real added cost would be well below this estimate. If runs are full, or the new riders live off existing routes, each added bus costs about ${bcKRange(...perBus)} a year, and bell times, driver availability and tiering decide how many are needed, so the cost could also be higher. Read the scenario figure as the cost of the added student-miles at today's average, not a routing plan.</li>` +
    `<li><b>Ridership is assumed.</b> It cancels out of the scenario cost only if newly eligible students ride at the same rate as current riders. Families who now walk or drive may not switch to the bus.</li>` +
    `<li><b>Cost split.</b> Giving general routes a share by bus count assumes a general bus costs the same as a special-education bus; the ${BC.all_routes}-route total is from 2023-24. Taxis and administration are still included, which overstates general-route cost.</li>` +
    `<li><b>Miles.</b> Route miles exclude trips from the garage and between runs (not in the route PDFs), so cost per route mile is overstated. ${BC.runs - BC.runs_measured} of ${BC.runs} runs could not be measured and are assumed to be average length.</li>` +
    `<li><b>Not included:</b> grades 9-12 (TriMet passes; distances barely change in A or B), special-education transportation and hazard-based busing. Custom scenarios use their own enrollment but their starting scenario's attendance areas.</li></ul></details>`;
  host.innerHTML = h;
}
// building costs (D.costs, 2026 dollars)""")

    # ---- styles ----
    rep("#commute table { scroll-margin-top: 72px; }",
        "#commute table { scroll-margin-top: 72px; }\n"
        ".buscost { margin-top: 18px; } .buscost h3 { margin: 0 0 6px; font-size: 15px; }\n"
        ".bctable { min-width: 560px; } .bctable td, .bctable th { white-space: nowrap; }\n"
        ".bcdet { margin: 10px 0 0; font-size: 13px; line-height: 1.45; } .bcdet summary { cursor: pointer; font-weight: 600; }\n"
        ".bcdet ol, .bcdet ul { margin: 8px 0 0; padding-left: 20px; } .bcdet li { margin: 0 0 6px; }")

    # ---- method note ----
    rep("  'Travel time:", "  " + json.dumps(
        "Busing cost: estimated cost of PPS's general (home-to-school) yellow-bus routes and the added cost of each scenario. "
        "The 2026-27 adopted Student Transportation budget (function 2550), less the TriMet high school pass payment ($2.1M; for "
        "the lower value also taxis, field trips and other non-route transport, from the adopted budget's accounts), is split to general routes by buses needed (peak "
        "simultaneous runs from PPS's posted schedules) over all bus routes (293 in 2023-24). The rate divides that by "
        "riders x measured stop-to-school ride miles x 2 trips, giving an annual cost per daily student-mile (no school-year "
        "length needed); ridership is not published and is assumed (35-65% of "
        "bus-eligible PPS K-8 students: 2025-26 enrollment x the census share beyond bus distance). Scenario cost, in the "
        "selected year = change in bus-eligible K-8 students' walking miles (projected enrollment x census walking miles per "
        "resident) x the measured "
        "ride-to-walk ratio x the annual cost per daily student-mile. Bus utilization is unknown: added riders may fit on existing runs (lower cost) "
        "or need new buses (higher). Built by scripts/estimate_bus_cost.py; embedded by scripts/patch_buscost.py.") + ",\n  'Travel time:")
    rep("  ['Buildings, costs and land', ['Functional capacity', 'Building costs', 'Building operating cost', 'Land value']],",
        "  ['Buildings, costs and land', ['Functional capacity', 'Building costs', 'Building operating cost', 'Land value']],\n"
        "  ['Busing cost', ['Busing cost']],")

if 'function cmBus' not in html:
    rep("""  if (!c.r) return '<td class="muted">&mdash;</td>'.repeat(7);""", """  if (!c.r) return '<td class="muted">&mdash;</td>'.repeat(9);""")
    rep("""    `<td class="reach">${w15}</td>` + cmHist(c, q, 'walk')""", """    cmBus(c, q) + `<td class="reach">${w15}</td>` + cmHist(c, q, 'walk')""")
    rep("""<td colspan="7" style="text-align:left">""", """<td colspan="9" style="text-align:left">""")
    rep("""    `<th>Beyond bus distance<br><span style="font-weight:400">(walking route, ${thr})</span></th>` +""",
        """    `<th>Beyond bus distance<br><span style="font-weight:400">(walking route, ${thr})</span></th>` +
    `<th>Bus student-miles a day<br><span style="font-weight:400">(eligible K-8 students, est.)</span></th>` +
    `<th>Yellow-bus cost a year<br><span style="font-weight:400">(est., ${bcD(BC.box.central)} per daily student-mile)</span></th>` +""")
    rep("function renderBusCost() {", r"""// bus columns of the getting-to-school table: student-miles a school day = eligible K-8 students' walking miles x
// ride-to-walk ratio x central ridership x 2 trips; cost a year = that x the central annual cost per daily
// student-mile (the TriMet range is in the tooltip). Grades 9-12 get TriMet passes.
function cmBus(c, q) {
  if (cmBand === '912') return '<td class="muted" title="High school students get TriMet passes, not yellow buses">TriMet</td>'.repeat(2);
  if (!c.bn && !q?.bn) return '<td class="muted" title="No K-8 attendance area (high school students get TriMet passes)">&mdash;</td>'.repeat(2);
  const f = BC.ratio * BC.ride_share.central * 2, rate = BC.box.central, ps = BC.cases.central.psm;
  const sm = c.bm * f, sq = q ? q.bm * f : null;
  const fm = v => Math.round(v).toLocaleString();
  const fc = v => v >= 995000 ? '$' + (v / 1e6).toFixed(2) + 'M' : '$' + Math.round(v / 1000) + 'k';
  const tip = `${fc(sm * Math.min(...ps))}&ndash;${fc(sm * Math.max(...ps))} a year (general routes ${bcM(BC.gt[1])}&ndash;${bcM(BC.gt[0])} a year)`;
  return `<td><span class="main">${fm(sm)}</span>${cmD(sm, sq, fm, 'down')}</td>` +
    `<td title="${tip}"><span class="main">${fc(sm * rate)}</span>${q ? cmD(sm * rate, sq * rate, fc, 'down') : ''}</td>`;
}
function renderBusCost() {""")

open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
