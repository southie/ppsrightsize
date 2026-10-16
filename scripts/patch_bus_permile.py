"""Yellow-bus cost from bus-miles: the change in daily bus-miles x the general-route cost per daily bus-mile (the
general-route share of the transportation budget / the posted routes' daily route miles: BC.per_mile).
  - Status Quo, Scenario A and Scenario B in the year the candidate routes were generated (BC.gen.year): the routed
    miles of the generated neighborhood routes (scripts/build_bus_routes.py; A and B from PPS's model when the "PPS model
    results" switch is on), by school (D.buscost.gen.school_miles, morning; afternoon mirrors it).
  - Custom scenarios, other years, single grade bands, and A/B with the switch off: a student-based estimate, each
    school's morning bus-miles fitted on the generated routes from its bus-eligible neighborhood students and their
    walking miles (BC.gen.coef_miles).
  - Card, bus cost section and the getting-to-school table's cost column all use it; bus-minutes stay as they were
    (student-based) for the ride-time figures.
Data: D.buscost.gen.school_miles and riders basis (refreshed on rerun); code changed once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
J = json.load(open(os.path.join(ROOT, 'source', 'pps-bus', 'generated-routes.json'), encoding='utf-8'))
D['buscost']['gen']['school_miles'] = {sc: {k: round(sum(r['miles'] for r in rs), 2) for k, rs in by.items()} for sc, by in J['runs'].items()}
D['buscost']['gen']['riders'] = J.get('riders', 'all')
H = J['heuristic']; D['buscost']['gen']['mi_per_min'] = round(sum(H['miles']['routed'].values()) / sum(H['minutes']['routed'].values()), 4)   # routed bus-miles per bus-minute
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function busMi' not in html:
    rep("""// Status Quo bus-minutes for the whole district in a year""", r"""// daily bus-miles of the neighborhood routes for these schools (scripts/patch_bus_permile.py): routed (the generated
// routes, the year they were generated, Status Quo and PPS's A and B) or student-based (the fit on those routes)
function busMi(sc, keys, bands = ['k5', '68'], students = false) {
  const G = BC.gen, R = G?.school_miles?.[sc];
  if (!students && R && cmYear === G.year && bands.length === 2 && (sc === 'SQ' || ((sc === 'A' || sc === 'B') && ppsOn && G.riders === 'neighborhood')))
    return { mi: 2 * keys.reduce((a, k) => a + (R[k] || 0), 0), src: 'routed' };
  // student-based: the bus-minutes fit (which tracks the routed change; the miles fit does not) at the generated routes'
  // bus-miles per bus-minute
  return { mi: busH(sc, keys, bands).h * (G.mi_per_min || 0.2), src: 'students' };
}
// Status Quo bus-minutes for the whole district in a year""")
    rep("""  const d = q.h ? (c.h - q.h) / q.h : 0, cost = BC.gt.map(g => g * d);""",
        """  const d = q.h ? (c.h - q.h) / q.h : 0;
  // cost: change in daily bus-miles x the general-route cost per daily bus-mile; both sides on the same basis
  let mc = busMi(scen, keys), mq = busMi('SQ', keys);
  if (mc.src !== mq.src) { mc = busMi(scen, keys, undefined, true); mq = busMi('SQ', keys, undefined, true); }
  const dm = mc.mi - mq.mi, cost = BC.per_mile.map(p => p * dm);""")
    rep("""  return { n: c.n, d_elig: c.n - q.n, d_walk:""", """  return { d_miles: dm, miles: mc.mi, milesq: mq.mi, src: mc.src, n: c.n, d_elig: c.n - q.n, d_walk:""")
    # summary card: say which basis
    rep("""    `<div class="l">${D.impl_year}, the first year (est.)${scen === 'C' ? `; ${esc(custom.name || 'custom scenario')}` : ''}</div>` +""",
        """    `<div class="l">${D.impl_year}, the first year (est.; ${s.src === 'routed' ? 'generated neighborhood routes' : 'estimated from students'})${scen === 'C' ? `; ${esc(custom.name || 'custom scenario')}` : ''}</div>` +""")
    rep("""  let sub = `Range: ${bcMoney(s.lo, s.hi)} a year<br>""", """  let sub = `Range: ${bcMoney(s.lo, s.hi)} a year<br>Daily bus-miles: <b>${s.d_miles >= 0 ? '+' : '&minus;'}${Math.round(Math.abs(s.d_miles)).toLocaleString()}</b> <span class="pcs">(${Math.round(s.miles).toLocaleString()} in all)</span><br>""")
    # table cost column: this area's daily bus-miles x cost per bus-mile
    rep("""  const rate = (BC.gt[0] + BC.gt[1]) / 2 / all;   // general-route cost per daily bus-minute, Status Quo, this year""",
        """  const pm = (BC.per_mile[0] + BC.per_mile[1]) / 2;   // general-route cost per daily bus-mile (scripts/patch_bus_permile.py)
  let mi = busMi(scen, keys, bands), miq = q ? busMi('SQ', keys, bands) : null;
  if (miq && mi.src !== miq.src) { mi = busMi(scen, keys, bands, true); miq = busMi('SQ', keys, bands, true); }""")
    rep("""  const tip = `${fc(h * BC.gt[1] / all)}&ndash;${fc(h * BC.gt[0] / all)} a year: this area's share of Status Quo bus-minutes (${fm(all)} a day in ${cmYear}) x general routes ${bcM(BC.gt[1])}&ndash;${bcM(BC.gt[0])} a year`;""",
        """  const tip = `${fc(mi.mi * Math.min(...BC.per_mile))}&ndash;${fc(mi.mi * Math.max(...BC.per_mile))} a year: about ${fm(mi.mi)} daily bus-miles of neighborhood routes (${mi.src === 'routed' ? `generated routes, ${BC.gen.year}` : 'estimated from bus-eligible neighborhood students'}) x ${bcD(Math.min(...BC.per_mile))}&ndash;${bcD(Math.max(...BC.per_mile))} a year per daily bus-mile`;""")
    rep("""    `<td title="${tip}"><span class="main">${fc(h * rate)}</span>${q ? cmD(h * rate, hq * rate, fc, 'down') : ''}</td>`;""",
        """    `<td title="${tip}"><span class="main">${fc(mi.mi * pm)}</span>${q ? cmD(mi.mi * pm, miq.mi * pm, fc, 'down') : ''}</td>`;""")
    # bus cost section text
    rep("""      `Candidate bus routes generated for each school put that at about <b>${n(Math.abs(s.d_h))}</b> ${s.d_h >= 0 ? 'more' : 'fewer'} bus-minutes a school day (${s.d_pct >= 0 ? '+' : '&minus;'}${(100 * Math.abs(s.d_pct)).toFixed(1)}% of Status Quo's ${n(s.hq)}), which at today's general-route cost (${bcRange(...BC.gt)} a year) ${s.hi < 0 ? 'saves' : 'costs'} about <b>${bcMoney(s.lo, s.hi).replace(' less', '')}</b> a year. ` +""",
        """      `${s.src === 'routed' ? `Candidate neighborhood bus routes generated for each school need` : `Estimated from those students, the neighborhood routes need`} about <b>${n(Math.abs(s.d_miles))}</b> ${s.d_miles >= 0 ? 'more' : 'fewer'} bus-miles a school day (${n(s.miles)} vs Status Quo's ${n(s.milesq)}), which at today's cost per daily bus-mile (${bcD(Math.min(...BC.per_mile))}&ndash;${bcD(Math.max(...BC.per_mile))} a year: the general routes' ${bcRange(...BC.gt)} &divide; ${n(BC.daily_miles)} daily route miles) ${s.hi < 0 ? 'saves' : 'costs'} about <b>${bcMoney(s.lo, s.hi).replace(' less', '')}</b> a year. ` +""")
    rep("""    `Cost change = general-route cost &times; change in bus-minutes &divide; Status Quo bus-minutes; the range is the two general-route cost values.</li></ol></details>`;""",
        """    `Cost change = change in daily bus-miles &times; the general-route cost per daily bus-mile (the general routes' share of the budget &divide; the posted routes' ${n(BC.daily_miles)} daily route miles); the range is the two general-route cost values. Status Quo, A and B in ${BC.gen.year} use the routed miles of the generated neighborhood routes (A and B from PPS's model results); custom scenarios, other years and single grade bands use the bus-minutes fit above at the generated routes' ${(BC.gen.mi_per_min || 0.2).toFixed(3)} bus-miles per bus-minute (fitting miles directly understates the change).</li></ol></details>`;""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
