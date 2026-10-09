"""Yellow-bus cost from generated routes: the scenario cost on the explorer (summary card, the estimated yellow-bus cost
block and the getting-to-school table's bus columns) now comes from bus time, using the heuristic fitted on the
OR-Tools candidate routes (D.buscost.gen, scripts/build_bus_routes.py, embedded by scripts/patch_buscost.py):
  bus-minutes a day of a school with bus-eligible K-8 students = c0 + c1 x eligible students + c2 x their walking miles
summed over schools for the selected scenario, year or custom scenario (cmAgg per school, so custom closures and moves
count), and the cost change = general-route cost x (bus-minutes - Status Quo's) / Status Quo's. Replaces the
student-mile method (change in walking miles x ride-to-walk ratio x cost per daily student-mile). Runs after
patch_buscost and patch_bus_hist. Code added once.
"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)
def rep_line(start, new):
    """replace the one whole line that starts with `start` (after its indentation)"""
    global html
    ms = list(re.finditer(r'(?m)^[ \t]*' + re.escape(start) + r'.*$', html))
    assert len(ms) == 1, (len(ms), start[:80])
    html = html[:ms[0].start()] + new + html[ms[0].end():]

if 'function busH' not in html:
    # ---- the estimate: bus-minutes from the generated-route heuristic ----
    a = html.index('function busScen() {'); b = html.index('\n}\n', a) + 3
    html = html[:a] + r"""// bus-minutes a school day (both trips) from the heuristic fitted on the generated candidate routes (D.buscost.gen):
// each school with bus-eligible K-8 students = c0 + c1 x eligible students + c2 x their walking miles
function busH(sc, keys, bands = ['k5', '68']) {
  const [c0, c1, c2] = BC.gen.coef; let h = 0, n = 0, m = 0;
  for (const k of keys) {
    let nk = 0, mk = 0;
    for (const b of bands) { const o = cmAgg(sc, [k], b); nk += o.be8; mk += o.bm; }
    if (nk > 0.5) h += 2 * Math.max(0, c0 + c1 * nk + c2 * mk);
    n += nk; m += mk;
  }
  return { h, n, m };
}
// Status Quo bus-minutes for the whole district in a year (fixed: the adjustment and custom scenarios leave SQ alone)
const BUSH_SQ = {};
function busHsq() { return BUSH_SQ[cmYear] ??= busH('SQ', Object.keys(D.region_of)).h; }
function busScen() {
  const keys = Object.keys(D.region_of), c = busH(scen, keys), q = busH('SQ', keys);
  const d = q.h ? (c.h - q.h) / q.h : 0, cost = BC.gt.map(g => g * d);
  return { d_elig: c.n - q.n, d_walk: q.m ? (c.m - q.m) / q.m : 0, d_h: c.h - q.h, d_pct: d, h: c.h, hq: q.h,
           lo: Math.min(...cost), hi: Math.max(...cost), mid: (cost[0] + cost[1]) / 2 };
}
""" + html[b:]
    # ---- getting-to-school table: bus-minutes and their share of general-route cost ----
    rep("cmBus(c, q) + `<td class=\"reach\">", "cmBus(c, q, row?.keys) + `<td class=\"reach\">")
    a = html.index('function cmBus(c, q) {'); b = html.index('\n}\n', a) + 3
    html = html[:a] + r"""function cmBus(c, q, keys) {
  if (cmBand === '912') return '<td class="muted" title="High school students get TriMet passes, not yellow buses">TriMet</td>'.repeat(2);
  if (!keys || (!c.bn && !q?.bn)) return '<td class="muted" title="No K-8 attendance area (high school students get TriMet passes)">&mdash;</td>'.repeat(2);
  const bands = cmBand === 'all' ? ['k5', '68'] : [cmBand];
  const h = busH(scen, keys, bands).h, hq = q ? busH('SQ', keys, bands).h : null, all = busHsq();
  const rate = (BC.gt[0] + BC.gt[1]) / 2 / all;   // general-route cost per daily bus-minute, Status Quo, this year
  const fm = v => Math.round(v).toLocaleString();
  const fc = v => Math.abs(v) >= 995000 ? '$' + (v / 1e6).toFixed(2) + 'M' : '$' + Math.round(v / 1000) + 'k';
  const tip = `${fc(h * BC.gt[1] / all)}&ndash;${fc(h * BC.gt[0] / all)} a year: this area's share of Status Quo bus-minutes (${fm(all)} a day in ${cmYear}) x general routes ${bcM(BC.gt[1])}&ndash;${bcM(BC.gt[0])} a year`;
  return `<td title="Estimated from candidate routes: per school ${BC.gen.coef[0].toFixed(0)} min + ${BC.gen.coef[1].toFixed(2)} min per eligible student + ${BC.gen.coef[2].toFixed(2)} min per walking mile, both trips"><span class="main">${fm(h)}</span>${q ? cmD(h, hq, fm, 'down') : ''}</td>` +
    `<td title="${tip}"><span class="main">${fc(h * rate)}</span>${q ? cmD(h * rate, hq * rate, fc, 'down') : ''}</td>`;
}
""" + html[b:]
    rep("""<th>Bus student-miles a day<br><span style="font-weight:400">(eligible K-8 students, est.)</span></th>""",
        """<th>Bus-minutes a day<br><span style="font-weight:400">(both trips, est. from candidate routes)</span></th>""")
    rep("""`<th>Yellow-bus cost a year<br><span style="font-weight:400">(est., ${bcD(BC.box.central)} per daily student-mile)</span></th>`""",
        """`<th>Yellow-bus cost a year<br><span style="font-weight:400">(est., share of general-route cost by bus-minutes)</span></th>`""")
    # ---- estimated yellow-bus cost block ----
    rep_line(": `<p class=\"sub\">Under ${LABEL[scen]} in ${cmYear}",
        r"""    : `<p class="sub">Under ${LABEL[scen]} in ${cmYear}${scen === 'C' ? ` (your custom scenario's enrollment with ${LABEL[custom.base]}'s attendance areas)` : ''}, <b>${n(Math.abs(s.d_elig))}</b> ${s.d_elig >= 0 ? 'more' : 'fewer'} K-8 students live beyond bus distance than under Status Quo, and their walks to school are <b>${Math.round(100 * Math.abs(s.d_walk))}%</b> ${s.d_walk >= 0 ? 'longer' : 'shorter'} in total. ` +""")
    rep_line("`That ${s.d_sm >= 0 ? 'adds' : 'removes'}",
        r"""      `Candidate bus routes generated for each school put that at about <b>${n(Math.abs(s.d_h))}</b> ${s.d_h >= 0 ? 'more' : 'fewer'} bus-minutes a school day (${s.d_pct >= 0 ? '+' : '&minus;'}${(100 * Math.abs(s.d_pct)).toFixed(1)}% of Status Quo's ${n(s.hq)}), which at today's general-route cost (${bcRange(...BC.gt)} a year) ${s.hi < 0 ? 'saves' : 'costs'} about <b>${bcMoney(s.lo, s.hi).replace(' less', '')}</b> a year. ` +
      ((G, t, t0) => t && t0 && cmYear === G.year ? `Routed directly for ${G.year}, ${LABEL[scen]} needs ${t.runs} morning runs (Status Quo ${t0.runs}) and about ${t.buses_morning} buses at the busiest time (Status Quo ${t0.buses_morning}): later bell times let most added runs reuse buses, so the cost is bus time, not more buses. ` : '')(BC.gen, BC.gen.totals[scen], BC.gen.totals.SQ) +""")
    # the old "roughly N more buses" sentence used the student-mile cost; drop it
    rep_line("`` + (s.mid > 0 ? `At today's cost per bus",
        r"""      `</p>`;""")
    rep_line("`<li><b>Scenarios.</b> The change in bus-eligible K-8 students' total walking miles",
        r"""    `<li><b>Scenarios: generated bus routes.</b> Candidate morning routes were generated with Google OR-Tools for Status Quo, Scenario A and Scenario B in ${BC.gen.year}: riders are ${Math.round(100 * BC.gen.params.ride_share)}% of each school's bus-eligible K-8 students, placed in the census blocks of its attendance area; they board at the nearest stop PPS uses today (within half a mile) or a new stop at their block; each run takes at most ${BC.gen.params.max_stops} stops, ${BC.gen.params.capacity} riders and ${BC.gen.params.max_ride_min} minutes, at ${BC.gen.params.min_per_road_mile.toFixed(2)} minutes per road mile plus ${BC.gen.params.min_per_stop.toFixed(2)} per stop (fitted to the posted schedules), with the fewest runs. ` +
    `Checked on Status Quo against the ${BC.gen.posted.schools} schools' posted routes: ${BC.gen.posted.runs} posted morning runs with ${BC.gen.posted.stops_per_run} stops each vs ${BC.gen.cal.runs} generated with ${BC.gen.cal.stops_per_run}; generated runs are shorter (${BC.gen.cal.mean_minutes} vs ${BC.gen.posted.mean_minutes} minutes) because they serve only neighborhood areas. ` +
    `To cover any year and custom scenarios, each school's generated bus-minutes are fitted as <b>${BC.gen.coef[0].toFixed(1)} + ${BC.gen.coef[1].toFixed(3)} &times; eligible students + ${BC.gen.coef[2].toFixed(3)} &times; their walking miles</b> (R&sup2; ${BC.gen.r2}); the fixed per-school part is why closing a school saves bus time even when its students ride farther. The fit gives ${Object.entries(BC.gen.check).map(([k, v]) => `${LABEL[k]} ${v.fitted >= 0 ? '+' : ''}${v.fitted}% (routed ${v.routed >= 0 ? '+' : ''}${v.routed}%)`).join(', ')}. ` +
    `Cost change = general-route cost &times; change in bus-minutes &divide; Status Quo bus-minutes; the range is the two general-route cost values.</li></ol></details>`;""")
    rep_line("`<li><b>Bus utilization is unknown, and it matters most.</b>",
        r"""    `<li><b>Candidate routes, not PPS's plan.</b> The generated routes serve only neighborhood attendance areas (focus-option and immersion routes draw from wider areas), assume the afternoon mirrors the morning, and use posted bell times. Bus time stands in for cost (drivers and buses are paid by the hour or day); the generated A and B need about as many buses at the busiest time as Status Quo, so no added fleet is assumed. If bell times or driver availability force new buses, each costs about ${bcKRange(...perBus)} a year.</li>` +""")
    rep_line("`<li><b>Ridership is assumed.</b>",
        r"""    `<li><b>Ridership is assumed.</b> Half of bus-eligible students are assumed to ride; it sets how many runs a school needs. Scenarios are compared with a Status Quo generated the same way, which limits its effect. Families who now walk or drive may not switch to the bus.</li>` +""")
    rep_line('"Busing cost: estimated cost of PPS',
        r"""  "Busing cost: estimated cost of PPS's general (home-to-school) yellow-bus routes and the added cost of each scenario. The 2026-27 adopted Student Transportation budget (function 2550), less the TriMet high school pass payment ($2.1M; for the lower value also taxis, field trips and other non-route transport, from the adopted budget's accounts), is split to general routes by buses needed (peak simultaneous runs from PPS's posted schedules) over all bus routes (293 in 2023-24). Scenario cost = that general-route cost x the change in bus-minutes a day: candidate routes were generated with Google OR-Tools for Status Quo, A and B (riders = half of each area's bus-eligible K-8 students in its census blocks; today's stops; limits on stops, riders and minutes a run; checked against PPS's posted routes), and each school's bus-minutes fitted as a fixed amount plus amounts per eligible student and per walking mile, which applies to any year or custom scenario. Bus utilization and ridership are not published. Built by scripts/estimate_bus_cost.py and scripts/build_bus_routes.py; embedded by scripts/patch_buscost.py and scripts/patch_bus_routes.py.",""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
