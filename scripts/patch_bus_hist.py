"""Bus ride time in the getting-to-school table: a histogram column (bus-eligible K-8 students' one-way ride, in
minutes) like walk / bike / drive, a "Bus" mode in the detail pane, and the average ride on the summary card.
Ride time = walking distance x the measured ride-to-walk ratio of PPS's posted routes x scheduled minutes per bus-mile
(stop times to the loading zone, scripts/estimate_bus_cost.py). Eligible students are binned by walking miles
(source/block-access: beyond_mi_hist; school-pairs.json element 14 for custom moves), so scenarios, custom moves and
years work as for the other columns. Runs after patch_custom_access. Data refreshed on rerun; code added once.
"""
import csv, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
ACC = os.path.join(ROOT, 'source', 'block-access')
EST = os.path.join(ROOT, 'source', 'pps-bus', 'bus-cost-estimate.json')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
pairs = json.load(open(os.path.join(ACC, 'school-pairs.json'), encoding='utf-8'))
BH = {}
for r in csv.DictReader(open(os.path.join(ACC, 'school-access.csv'), encoding='utf-8')):
    if r['band'] in ('k5', '68') and r.get('beyond_mi_hist'):
        BH.setdefault(r['scenario'], {}).setdefault(r['school'], {})[r['band']] = [float(x) for x in r['beyond_mi_hist'].split(';')]
D['commute']['BH'] = BH; D['commute']['bh_mi'] = pairs['bh_mi']; D['commute']['X'] = pairs['pairs']
R = json.load(open(EST, encoding='utf-8'))['routes']
D['buscost']['min_per_mile'] = R['min_per_bus_mile']; D['buscost']['ride_stops'] = R['ride_time_stops']; D['buscost']['mean_ride_min'] = R['mean_ride_min']
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if "bus: ['Bus', 'busmin']" not in html:
    # ---- aggregation: eligible students by walking miles -> bus ride minutes ----
    rep("pn: 0, pAt: new Set(),", "pn: 0, pAt: new Set(), be8: 0, bh: Array(D.commute.bh_mi.length + 1).fill(0),")
    rep("  const add = (v, r, mb) => {", "  const add = (v, r, mb, bh) => {")
    rep("    if (mb != null) { o.bm += mb * x; o.bn++; }",
        "    if (mb != null) { o.bm += mb * x; o.bn++; o.be8 += r * v[1]; if (bh) bh.forEach((y, i) => { o.bh[i] += y * x; }); }")
    rep("add(pv, a, b === '912' ? null : pv[13]);", "add(pv, a, b === '912' ? null : pv[13], b === '912' ? null : pv[14]);")
    rep("    add(v, r, kept ? MBsq[k]?.[b] : MB[k]?.[b]);",
        "    add(v, r, kept ? MBsq[k]?.[b] : MB[k]?.[b], b === '912' ? null : ((kept ? D.commute.BH.SQ : D.commute.BH[Sc]) || {})[k]?.[b]);")
    rep("""  if (o.r) for (const f of ['wmi', 'wmin', 'bmin', 'dmin', 'w15', 'b15', 'd15', 'near']) o[f] /= o.r;
  return o;
}""", """  if (o.r) for (const f of ['wmi', 'wmin', 'bmin', 'dmin', 'w15', 'b15', 'd15', 'near']) o[f] /= o.r;
  // bus ride of the bus-eligible K-8 students: walking miles x ride-to-walk ratio x scheduled minutes per bus-mile
  const K = (D.buscost?.ratio || 0) * (D.buscost?.min_per_mile || 0), E = D.commute.hist_min, BM = D.commute.bh_mi;
  o.h.bus = Array(E.length + 1).fill(0);
  o.bh.forEach((y, i) => {
    if (!y) return;
    const mi = i === 0 ? BM[0] / 2 : i < BM.length ? (BM[i - 1] + BM[i]) / 2 : BM[BM.length - 1] + 0.5;   // bin middle
    o.h.bus[E.filter(e => e <= mi * K).length] += y;
  });
  o.busmin = o.be8 ? o.bm * K / o.be8 : 0;
  return o;
}""")

    # ---- table column ----
    rep("function cmHist(c, q, m, ri = -1) {",
        "function cmHist(c, q, m, ri = -1) {\n"
        "  if (m === 'bus' && (cmBand === '912' || !c.be8))\n"
        "    return cmBand === '912' ? '<td class=\"muted\" title=\"High school students get TriMet passes, not yellow buses\">TriMet</td>' : '<td class=\"muted\">&mdash;</td>';")
    rep("""  if (!c.r) return '<td class="muted">&mdash;</td>'.repeat(9);""", """  if (!c.r) return '<td class="muted">&mdash;</td>'.repeat(10);""")
    rep("cmHist(c, q, 'drive', ri) +", "cmHist(c, q, 'drive', ri) + cmHist(c, q, 'bus', ri) +")
    rep("""['Walk', 'Bike', 'Drive'].map(l => `<th>${l} time<br><span style="font-weight:400">(minutes)</span></th>`).join('') +""",
        """['Walk', 'Bike', 'Drive'].map(l => `<th>${l} time<br><span style="font-weight:400">(minutes)</span></th>`).join('') +
    `<th>Bus ride<br><span style="font-weight:400">(minutes, eligible K-8)</span></th>` +""")
    rep('<td colspan="8" style="text-align:left"><span class="stag other">Program school</span>', '<td colspan="9" style="text-align:left"><span class="stag other">Program school</span>')
    rep('<td colspan="9" style="text-align:left">${closed ?', '<td colspan="10" style="text-align:left">${closed ?')

    # ---- detail pane: Bus mode ----
    rep("const CM_MODE = { walk: ['Walk', 'wmin'], bike: ['Bike', 'bmin'], drive: ['Drive', 'dmin'] };",
        "const CM_MODE = { walk: ['Walk', 'wmin'], bike: ['Bike', 'bmin'], drive: ['Drive', 'dmin'], bus: ['Bus', 'busmin'] };")
    rep("if (!cs) return h + `<p class=\"muted\">No students in these grades here in this scenario${qs ? ` (Status Quo: ${cmN(q.r)})` : ''}.</p></div>`;",
        "if (!cs) return h + `<p class=\"muted\">${m === 'bus' ? 'No bus-eligible K-8 students' : 'No students in these grades'} here in this scenario${qs ? ` (Status Quo: ${cmN(m === 'bus' ? q.be8 : q.r)})` : ''}.</p></div>`;")
    rep("""  const mean = o => o[CM_MODE[m][1]];
  const rows = [
    ['Students', cmN(c.r), qs ? cmN(q.r) : '', qs ? cmDelta(c.r - q.r, '', 0, true) : ''],""",
        """  const mean = o => o[CM_MODE[m][1]], nOf = o => m === 'bus' ? o.be8 : o.r;
  const rows = [
    [m === 'bus' ? 'Bus-eligible students' : 'Students', cmN(nOf(c)), qs ? cmN(nOf(q)) : '', qs ? cmDelta(nOf(c) - nOf(q), '', 0, true) : ''],""")
    rep("""Mean is exact; median and percentiles are interpolated within the time bands shown. ${CM_MODE[m][0]} times are along the OpenStreetMap network at ${m === 'walk' ? D.commute.walk_mph + ' mph' : m === 'bike' ? D.commute.bike_mph + ' mph' : 'free-flow speeds (no traffic)'}.</p></div>`;""",
        """Mean is exact; median and percentiles are interpolated within the time bands shown. ` +
    (m === 'bus' ? `Bus ride: K-8 students beyond bus distance only (K-5 over 1 mile, 6-8 over 1.5 miles), one way. Estimated as their walking distance &times; ${D.buscost.ratio.toFixed(1)} (buses wind past other stops; measured on PPS's posted routes) &times; ${D.buscost.min_per_mile.toFixed(1)} minutes per bus-mile (scheduled times from each stop to the school's loading zone on ${D.buscost.ride_stops.toLocaleString()} stops).`
      : `${CM_MODE[m][0]} times are along the OpenStreetMap network at ${m === 'walk' ? D.commute.walk_mph + ' mph' : m === 'bike' ? D.commute.bike_mph + ' mph' : 'free-flow speeds (no traffic)'}.`) + `</p></div>`;""")

    # ---- summary card: average ride in the first year ----
    rep("""  if (cmYear !== D.impl_year) { const t = busScen(); h += `<br><span class="pcs">${cmYear}: ${bcMoney(t.lo, t.hi)} a year</span>`; }
  return h;""", """  if (cmYear !== D.impl_year) { const t = busScen(); h += `<br><span class="pcs">${cmYear}: ${bcMoney(t.lo, t.hi)} a year</span>`; }
  const keys = Object.keys(D.region_of), rc = cmAtYear(D.impl_year, () => cmAgg(scen, keys, 'all')), rq = cmAtYear(D.impl_year, () => cmAgg('SQ', keys, 'all'));
  const dm = rc.busmin - rq.busmin;
  h += `<br>Average bus ride, eligible K-8, ${D.impl_year}: <b>${rc.busmin.toFixed(0)} min</b> one way` +
    (Math.abs(dm) >= 0.05 ? ` <span class="pcs">(${dm > 0 ? '+' : '&minus;'}${Math.abs(dm).toFixed(1)} min)</span>` : '') +
    ` <span class="pcs">at ${BC.min_per_mile.toFixed(1)} min per bus-mile</span>`;
  return h;""")
    rep("""  if (scen === 'SQ') return `<br>General yellow-bus routes: about <b>${bcRange(...BC.gt)}</b> a year (est.)`;
  const s = cmAtYear(D.impl_year, busScen)""", """  if (scen === 'SQ') { const rq = cmAgg('SQ', Object.keys(D.region_of), 'all');
    return `<br>General yellow-bus routes: about <b>${bcRange(...BC.gt)}</b> a year (est.)<br>Average bus ride, eligible K-8: <b>${rq.busmin.toFixed(0)} min</b> one way <span class="pcs">at ${BC.min_per_mile.toFixed(1)} min per bus-mile</span>`; }
  const s = cmAtYear(D.impl_year, busScen)""")

    # ---- how it is estimated: ride time step ----
    rep("""`<li><b>Annual cost per daily student-mile</b>""",
        """`<li><b>Ride time.</b> PPS's schedules give each stop's time and the school's loading-zone time; against each stop's measured ride, buses take <b>${BC.min_per_mile.toFixed(1)} minutes per bus-mile</b> (about ${(60 / BC.min_per_mile).toFixed(0)} mph with stops; ${BC.ride_stops.toLocaleString()} stops, average ride ${BC.mean_ride_min} min). The table's bus ride column applies this to each eligible student's estimated ride.</li>` +
    `<li><b>Annual cost per daily student-mile</b>""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
