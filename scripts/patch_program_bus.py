"""Immersion (DLI) program busing on the page, from source/pps-bus/program-bus.json (scripts/build_program_bus.py), and a
"not affiliated with PPS" note under the title.
  - Getting to school: a table under the bus cost: Status Quo: program busing by school (runs, out-of-area stops, daily
    program bus-miles); a scenario: each receiving site (program, programs moving in, stops, runs now and after,
    daily bus-miles routed the same way now and after, mean and longest ride per stop), totals and cost, and a method
    note (program stops = posted stops outside a school's attendance area at schools with immersion; moved programs'
    stops plus a stop at the sending school re-routed to the new site; Status Quo routed the same way for comparison).
Data: D.progbus (refreshed on rerun); code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
P = json.load(open(os.path.join(ROOT, 'source', 'pps-bus', 'program-bus.json'), encoding='utf-8'))
for s in P['scen'].values():
    for x in s['sites']: x.pop('new_runs', None)
for v in P['sq'].values(): v.pop('out_stops', None)
D['progbus'] = P
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

JS = r'''// ---------- immersion (DLI) program busing (scripts/patch_program_bus.py) ----------
const pbM = v => (v < 0 ? '&minus;' : '+') + '$' + (Math.abs(v) / 1e6).toFixed(2) + 'M';
function renderProgBus() {
  const host = document.getElementById('progbus'), P = D.progbus; if (!host || !P) return;
  const sc = scen === 'C' ? custom.base : scen, n1 = v => (+v).toFixed(1), nm = k => esc(short(byKey[k]?.name || k));
  if (sc === 'SQ' || !P.scen[sc]) {
    const rows = Object.entries(P.sq).sort((a, b) => b[1].miles_daily - a[1].miles_daily);
    host.innerHTML = `<h3 class="cshead">Immersion program busing today</h3><div class="tablewrap"><table style="min-width:0"><thead><tr><th style="text-align:left">School</th><th>Posted runs</th><th>Stops outside its area</th><th>Daily program bus-miles</th></tr></thead><tbody>` +
      rows.map(([k, v]) => `<tr><td style="text-align:left">${nm(k)}</td><td style="text-align:right">${v.runs}</td><td style="text-align:right">${v.n_out} of ${v.stops}</td><td style="text-align:right">${n1(v.miles_daily)}</td></tr>`).join('') +
      `<tr class="dist"><td style="text-align:left">All</td><td style="text-align:right">${P.sq_total.runs}</td><td></td><td style="text-align:right">${n1(P.sq_total.miles_daily)}</td></tr></tbody></table></div>` + pbNote(P);
    return;
  }
  const S = P.scen[sc];
  host.innerHTML = `<h3 class="cshead">Immersion program busing, ${esc(LABEL[sc])}</h3><div class="tablewrap"><table style="min-width:0"><thead><tr><th style="text-align:left">New site</th><th style="text-align:left">Programs moving in</th><th>Stops</th><th>Runs<br><span style="font-weight:400">now &rarr; after</span></th><th>Daily bus-miles<br><span style="font-weight:400">now &rarr; after</span></th><th>Change</th><th>Ride per stop<br><span style="font-weight:400">mean, now &rarr; after; longest</span></th></tr></thead><tbody>` +
    S.sites.map(x => `<tr><td style="text-align:left"><b>${nm(x.site)}</b> <span class="muted">${esc(x.program)}</span></td><td style="text-align:left">${x.senders.map(nm).join(', ')}</td><td style="text-align:right">${x.stops}</td><td style="text-align:right">${x.sq_runs_involved} &rarr; ${x.runs}</td>` +
      `<td style="text-align:right">${n1(x.sq_miles_daily)} &rarr; ${n1(x.miles_daily)}</td><td style="text-align:right;color:${x.change_miles_daily > 0 ? 'var(--down)' : 'var(--up)'}">${x.change_miles_daily > 0 ? '+' : '&minus;'}${n1(Math.abs(x.change_miles_daily))}</td>` +
      `<td style="text-align:right">${n1(x.sq_ride_mean)} &rarr; ${n1(x.ride_mean)} mi; ${n1(x.ride_max)}</td></tr>`).join('') +
    `<tr class="dist"><td style="text-align:left" colspan="3">All moves</td><td style="text-align:right">${S.sites.reduce((a, x) => a + x.sq_runs_involved, 0)} &rarr; ${S.sites.reduce((a, x) => a + x.runs, 0)}</td><td></td><td style="text-align:right">${S.change_miles_daily > 0 ? '+' : '&minus;'}${n1(Math.abs(S.change_miles_daily))}</td><td style="text-align:right">${pbM(S.change_cost.lower)} to ${pbM(S.change_cost.upper)} a year</td></tr></tbody></table></div>` + pbNote(P);
}
function pbNote(P) {
  return `<p class="muted" style="font-size:12px">Estimated from PPS's posted bus routes (not in the bus cost above, which covers neighborhood students). Program stops: posted stops outside a school's own attendance area at schools with an immersion program (at schools without one, about 11% of stops fall outside the traced areas, which is not counted). Today's program bus-miles: each run's miles times its share of such stops, doubled for the afternoon. In a scenario, a moving program's stops, plus a stop at the school it leaves (its students who live there), are routed to the new site together with that site's own program stops: fewest runs, then fewest miles, at most ${P.max_stops} stops and ${P.max_miles} miles a run (the posted runs' 90th percentiles), road distance = straight line &times; ${P.circuity} (the posted runs' circuity). "Now" routes the same schools' program stops the same way, each school alone, so the comparison is like with like. Cost: the change in daily bus-miles &times; $${P.per_daily_bus_mile.lower.toLocaleString()}-${P.per_daily_bus_mile.upper.toLocaleString()} a year per daily bus-mile of general routes. Riders per stop are not published, and families who leave a program when it moves are not modeled. Combining programs shares runs, so total miles can fall even when some families ride farther.</p>`;
}
function renderAll() {'''

if 'renderProgBus' not in html:
    rep("function renderAll() {", JS)
    rep("renderMap(); renderEndpoints(); renderRoom();", "renderMap(); renderEndpoints(); renderRoom(); renderProgBus();")
    rep("""    <div id="buscost" class="buscost"></div>""", """    <div id="buscost" class="buscost"></div>
    <div id="progbus"></div>""")
if 'pps-disclaimer' not in html:
    rep("""  <p class="lede">The purpose of this tool""",
        """  <p class="pps-disclaimer" style="margin:2px 0 8px;padding:6px 10px;border-left:4px solid var(--down);background:var(--surface-2);font-size:13.5px"><b>Not affiliated with Portland Public Schools.</b> Right Size Portland is an independent project; it is not endorsed by or operated by PPS, and its estimates are not PPS figures or plans. Source data are PPS, PSU and public records, cited throughout.</p>
  <p class="lede">The purpose of this tool""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
