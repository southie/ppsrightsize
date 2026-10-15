"""School report: "What would sustain this school" as a table (replaces the sentence from patch_rp_psu_range.py).
Rows: the school's projection in the last year, its size threshold and its 2021 capacity. For each:
  - the incoming class the school would need: kindergarten (elementary, K-8), 6th grade (middle) or 9th grade (high), at
    steady state (each grade band at the district's steady state for a district kindergarten K, PSU's grade progression
    ratios, at the school's share of the district's students in that band in that year);
  - the 5-year-olds that class takes in the school's enrollment area at today's capture (kindergarten / 5-year-olds
    living in PPS, D.pfa.capture) and at a high capture rate (today's x the pre-COVID high / fall 2025 kindergarten
    capture of births, from the Monte Carlo inputs), with the fertility rate behind each: the area's 5-year-olds scaled
    to the district (the area's share held), x 5-year-olds per birth five years earlier (today's: capture of births /
    capture of 5-year-olds), over about 3,650 births at a rate of about 1.0 (PSU, Multnomah County 2024).
  - Middle and high schools: the 5-year-olds that grow into the incoming class (grade progression from kindergarten).
Below the table: PSU's high projection for the school. roomMult also keeps the cumulative progression (ch).
Code changed once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'rpSustainRows' not in html:
    rep("""  return roomMultCache = { k5: sum(0, 5), m68: sum(6, 8), h912: sum(9, 12) };""",
        """  return roomMultCache = { k5: sum(0, 5), m68: sum(6, 8), h912: sum(9, 12), ch };""")
    a = html.index('// what it would take for the school to reach its size threshold in the last year')
    b = html.index('function rpPlot(k, sc) {')
    html = html[:a] + r"""// what would sustain the school: incoming class, 5-year-olds in its area and fertility rate (scripts/patch_rp_sustain_table.py)
function rpSustain(k, sc) {
  if (typeof roomFill !== 'function' || !D.pfa || !D.mc?.params?.capture) return '';
  const yi = D.years.length - 1, yr = D.years[yi], f = roomFill(sc, yi)[k], dist = roomDist(yi); if (!f || !f.th || !dist) return '';
  const M = roomMult(), sp = roomSplit(k, sc, yi, f.v), idx = { k5: 1, m68: 2, h912: 3 }, Kproj = dist[0];
  // the school's entering band: K-5 for elementary and K-8, else its only band
  const eb = sp.k5 ? 'k5' : sp.m68 ? 'm68' : 'h912', entry = { k5: 0, m68: 6, h912: 9 }[eb], gname = { k5: 'Kindergarten', m68: '6th grade', h912: '9th grade' }[eb];
  const share = sp[eb] / dist[idx[eb]];                      // the school's share of the district's students in that band
  const C = D.mc.params.capture, capNow = D.pfa.capture, capHigh = capNow * C.tri.b / C.fall_2025;
  const n0 = v => Math.round(v).toLocaleString(), tfr = pop5 => (pop5 / share * capNow / (2919 / 4121) / 3650).toFixed(2);
  // a district kindergarten K -> the school's incoming class and its area's 5-year-olds at a capture rate
  const inc = K => K * share * M.ch[entry], pop5 = (K, cap) => K * share / cap;
  const lab = sc === 'SQ' ? 'Status Quo' : LABEL[sc], R = rpPsuRange(k, sc)?.[yi];
  const rpSustainRows = [[`Projected, ${yr}`, f.v, Kproj], [`Size threshold`, f.th, f.Kt], [`2021 capacity`, f.fc, f.K]];
  const row = ([l, n, K]) => `<tr><td style="text-align:left">${l}</td><td style="text-align:right">${n0(n)}</td><td style="text-align:right"><b>${n0(inc(K))}</b></td>` +
    `<td style="text-align:right;border-left:2px solid var(--line)">${n0(pop5(K, capNow))}</td><td style="text-align:right">${tfr(pop5(K, capNow))}</td>` +
    `<td style="text-align:right;border-left:2px solid var(--line);background:var(--surface-2)">${n0(pop5(K, capHigh))}</td><td style="text-align:right;background:var(--surface-2)">${tfr(pop5(K, capHigh))}</td></tr>`;
  return `<h4>What would sustain this school (${esc(lab)}, ${yr})</h4><div class="tablewrap"><table style="min-width:0"><thead><tr><th style="text-align:left" rowspan="2"></th><th rowspan="2">Students</th><th rowspan="2">${gname} class needed</th>` +
    `<th colspan="2" style="text-align:center;border-left:2px solid var(--line);border-bottom:1px solid var(--line)">At today's ${Math.round(100 * capNow)}% capture</th><th colspan="2" style="text-align:center;border-left:2px solid var(--line);background:var(--surface-2);border-bottom:1px solid var(--line)">At a high ${Math.round(100 * capHigh)}% capture</th></tr>` +
    `<tr><th style="border-left:2px solid var(--line);font-weight:400">5-year-olds in its area</th><th style="font-weight:400">Fertility rate</th><th style="border-left:2px solid var(--line);background:var(--surface-2);font-weight:400">5-year-olds in its area</th><th style="font-weight:400;background:var(--surface-2)">Fertility rate</th></tr></thead><tbody>` +
    rpSustainRows.map(row).join('') + `</tbody></table></div>` +
    `<p class="muted rpnote">${f.v >= f.th ? (f.Kt <= Kproj ? 'At or above its size threshold at the projection.' : `Above its size threshold in ${yr}, but below it once today's smaller classes reach every grade (the threshold row is what keeps it there).`) : 'Below its size threshold at the projection.'}` +
    `${R ? ` PSU's high projection: about ${n0(R[1])} students in ${yr}${R[1] >= f.th ? ', at or above the threshold' : ', still below the threshold'}.` : ''} ` +
    `Each row at steady state: every grade at the size that ${gname.toLowerCase()} class grows into (PSU's grade progression ratios), at the school's ${yr} share of the district's ${eb === 'k5' ? 'K-5' : eb === 'm68' ? '6-8' : '9-12'} students; boundary or program changes would change that share. ` +
    `${eb === 'k5' ? '' : `For a ${eb === 'm68' ? 'middle' : 'high'} school, the 5-year-olds are those who grow into the incoming class. `}` +
    `Capture: kindergartners as a share of the 5-year-olds living in PPS (${Math.round(100 * capNow)}% today; ${Math.round(100 * capHigh)}% matches the pre-COVID high, ${Math.round(100 * C.tri.b)}% of births five years earlier vs ${Math.round(100 * C.fall_2025)}% in fall 2025). ` +
    `Fertility rate (children per woman): births behind those 5-year-olds if the area's share of the district holds, scaled from about 1.0 in 2024 (PSU, Multnomah County) for about 3,650 births to PPS-area residents in 2025; for comparison the U.S. is about 1.6 and replacement 2.1. A higher capture rate means fewer births are needed for the same class.</p>`;
}
""" + html[b:]
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
