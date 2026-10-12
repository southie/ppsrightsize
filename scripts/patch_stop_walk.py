"""Bus trips split into time on the bus and the walk to the bus stop.

The getting-to-school table's bus column was already time on the bus (scheduled minutes from the student's stop to the
school's loading zone, scripts/patch_bus_hist.py). This embeds the walk from home to that stop
(source/block-access/stop-walk.json, from scripts/build_stop_walk.py) as D.commute.SW and shows it beside the ride:
a "Walk to bus stop" histogram column in the table, a mode in the detail pane, a line on the busing-cost card and a
method note. The school report's travel table (scripts/school_report.js) uses the same data. Custom scenarios work as
for the other columns (moved students walk to their receiving school's stops). Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.environ.get('EXPLORER_PAGE') or os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
SW = os.environ.get('STOP_WALK') or os.path.join(ROOT, 'source', 'block-access', 'stop-walk.json')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
sw = json.load(open(SW, encoding='utf-8'))
assert sw['sw_min'] == D['commute']['hist_min'], 'walk-to-stop bins must match the travel-time bins'
D['commute']['SW'] = {k: sw[k] for k in ('S', 'X', 'R')}
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]


def rep(a, b, n=1):
    global html
    assert html.count(a) == n, (html.count(a), a[:110])
    html = html.replace(a, b)


NOTE = ("Getting to school, walk to the bus stop: for K-8 students eligible for bus service, the walk from where they live "
        "(2020 Census residents, as above) to the nearest stop of their school's yellow-bus routes, along the OpenStreetMap "
        "walking network at the same 3 mph. Stops are those of this page's candidate routes (see Busing cost: riders board at "
        "the nearest stop PPS uses today within half a mile, otherwise at a new stop in their block), used the same way for "
        "Status Quo and the scenarios; a school with no candidate routes uses the nearest stop of any school. The table's "
        "On the bus column is time on the bus only, from the stop to the school's loading zone; waiting at the stop is not "
        "included. Built by scripts/build_stop_walk.py and embedded by scripts/patch_stop_walk.py.")

if 'function cmSw(' not in html:
    # ---- aggregation: eligible students' walk to the stop, alongside the bus ride ----
    rep("function cmAgg(sc, keys, band) {",
        "// walk from home to the bus stop (D.commute.SW, scripts/build_stop_walk.py): sw = [eligible residents, mean minutes,\n"
        "// residents per travel-time bin] for an area; n = its students eligible for bus service\n"
        "function cmSw(o, sw, n) { const y = n / sw[0]; o.swn += n; o.sws += n * sw[1]; sw[2].forEach((z, i) => { o.h.stop[i] += z * y; }); }\n"
        "function cmAgg(sc, keys, band) {")
    rep("drive: Array(nb).fill(0) } };\n  // r students living like",
        "drive: Array(nb).fill(0), stop: Array(nb).fill(0) }, swn: 0, sws: 0 };\n  // r students living like")
    rep("  const add = (v, r, mb, bh) => {", "  const add = (v, r, mb, bh, sw) => {")
    rep("    if (mb != null) { o.bm += mb * x; o.bn++; o.be8 += r * v[1]; if (bh) bh.forEach((y, i) => { o.bh[i] += y * x; }); }\n",
        "    if (mb != null) { o.bm += mb * x; o.bn++; o.be8 += r * v[1]; if (bh) bh.forEach((y, i) => { o.bh[i] += y * x; }); }\n"
        "    if (mb != null && sw && sw[0]) cmSw(o, sw, r * v[1]);\n")
    rep("add(pv, a, b === '912' ? null : pv[13], b === '912' ? null : pv[14]);",
        "add(pv, a, b === '912' ? null : pv[13], b === '912' ? null : pv[14], b === '912' ? null : D.commute.SW?.X?.[Sc]?.[m.from]?.[b]?.[k]);")
    rep("    add(v, r, kept ? MBsq[k]?.[b] : MB[k]?.[b], b === '912' ? null : ((kept ? D.commute.BH.SQ : D.commute.BH[Sc]) || {})[k]?.[b]);",
        "    add(v, r, kept ? MBsq[k]?.[b] : MB[k]?.[b], b === '912' ? null : ((kept ? D.commute.BH.SQ : D.commute.BH[Sc]) || {})[k]?.[b],\n"
        "      b === '912' ? null : D.commute.SW?.S?.[kept ? 'SQ' : Sc]?.[k]?.[b]);")
    rep("  o.busmin = o.be8 ? o.bm * K / o.be8 : 0;\n  return o;\n}\n// value with change",
        "  o.busmin = o.be8 ? o.bm * K / o.be8 : 0;\n  o.swmin = o.swn ? o.sws / o.swn : 0;\n  return o;\n}\n// value with change")
    # ---- table: "On the bus" and a "Walk to bus stop" column ----
    rep("  if (m === 'bus' && (cmBand === '912' || !c.be8))", "  if ((m === 'bus' || m === 'stop') && (cmBand === '912' || !c.be8))")
    rep('title="Show ${m} times in detail"` : \'\'}><svg',
        'title="Show ${m === \'stop\' ? \'walk-to-stop\' : m} times in detail"` : \'\'}><svg')
    rep("`<th>Bus ride<br><span style=\"font-weight:400\">(minutes, eligible K-8)</span></th>` +",
        "`<th>On the bus<br><span style=\"font-weight:400\">(minutes, eligible K-8; stop to school)</span></th>` +\n"
        "    `<th>Walk to bus stop<br><span style=\"font-weight:400\">(minutes, eligible K-8; home to stop)</span></th>` +")
    rep("cmHist(c, q, 'bus', ri) +", "cmHist(c, q, 'bus', ri) + cmHist(c, q, 'stop', ri) +")
    rep("""  if (!c.r) return '<td class="muted">&mdash;</td>'.repeat(10);""", """  if (!c.r) return '<td class="muted">&mdash;</td>'.repeat(11);""")
    rep('<td colspan="9" style="text-align:left"><span class="stag other">Program school</span>',
        '<td colspan="10" style="text-align:left"><span class="stag other">Program school</span>')
    rep('<td colspan="10" style="text-align:left">${closed ?', '<td colspan="11" style="text-align:left">${closed ?')
    # ---- detail pane ----
    rep("bus: ['Bus', 'busmin'] };", "bus: ['On the bus', 'busmin'], stop: ['Walk to stop', 'swmin'] };")
    rep("minutes (${CM_MODE[m][0].toLowerCase()}, home to school)",
        "minutes (${m === 'bus' ? 'on the bus, stop to school' : m === 'stop' ? 'walk, home to bus stop' : CM_MODE[m][0].toLowerCase() + ', home to school'})")
    rep("${m === 'bus' ? 'No bus-eligible K-8 students'", "${m === 'bus' || m === 'stop' ? 'No bus-eligible K-8 students'")
    rep("(Status Quo: ${cmN(m === 'bus' ? q.be8 : q.r)})", "(Status Quo: ${cmN(m === 'bus' || m === 'stop' ? q.be8 : q.r)})")
    rep("nOf = o => m === 'bus' ? o.be8 : o.r;", "nOf = o => m === 'bus' || m === 'stop' ? o.be8 : o.r;")
    rep("[m === 'bus' ? 'Bus-eligible students' : 'Students',", "[m === 'bus' || m === 'stop' ? 'Bus-eligible students' : 'Students',")
    rep("(m === 'bus' ? `Bus ride: K-8 students", "(m === 'stop' ? `Walk to the bus stop: K-8 students eligible for bus service only (K-5 over 1 mile, 6-8 over 1.5 miles), one way, "
        "from where they live to the nearest stop of their school's candidate yellow-bus routes, along the OpenStreetMap walking network at ${D.commute.walk_mph} mph. "
        "Waiting at the stop is not included; the time on the bus is the On the bus mode.` : m === 'bus' ? `Time on the bus, from the student's stop to the school's loading zone "
        "(the walk to the stop is the Walk to stop mode): K-8 students")
    # ---- busing-cost card ----
    rep("`Average bus ride, eligible K-8: <b>${rq.busmin.toFixed(0)} min</b> one way <span class=\"pcs\">at ${K}</span><br>` +",
        "`Average trip, eligible K-8: <b>${rq.busmin.toFixed(0)} min</b> on the bus <span class=\"pcs\">at ${K}</span><br>` +\n"
        "      `plus <b>${rq.swmin.toFixed(0)} min</b> walking to the stop, one way<br>` +")
    rep("  sub += `<br>Average bus ride, eligible K-8: <b>${rc.busmin.toFixed(0)} min</b> one way` +",
        "  const dw = rc.swmin - rq.swmin;\n"
        "  sub += `<br>Average trip, eligible K-8: <b>${rc.busmin.toFixed(0)} min</b> on the bus` +")
    rep("(Math.abs(dm) >= 0.05 ? ` <span class=\"pcs\">(${dm > 0 ? '+' : '&minus;'}${Math.abs(dm).toFixed(1)} min)</span>` : '') + ` <span class=\"pcs\">at ${K}</span>`;",
        "(Math.abs(dm) >= 0.05 ? ` <span class=\"pcs\">(${dm > 0 ? '+' : '&minus;'}${Math.abs(dm).toFixed(1)} min)</span>` : '') + ` <span class=\"pcs\">at ${K}</span>` +\n"
        "    `<br>plus <b>${rc.swmin.toFixed(0)} min</b> walking to the stop, one way` +\n"
        "    (Math.abs(dw) >= 0.05 ? ` <span class=\"pcs\">(${dw > 0 ? '+' : '&minus;'}${Math.abs(dw).toFixed(1)} min)</span>` : '');")
    # ---- method note ----
    rep('  "Busing cost: estimated cost of', '  ' + json.dumps(NOTE) + ',\n  "Busing cost: estimated cost of')
    print('page code updated')

open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
n = {sc: sum(v[b][0] for v in sw['S'][sc].values() for b in v) for sc in sw['S']}
print('walk to stop, eligible K-8 residents:', ', '.join(
    f"{sc} {sum(v[b][0] * v[b][1] for v in sw['S'][sc].values() for b in v) / n[sc]:.1f} min" for sc in sw['S']))
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
