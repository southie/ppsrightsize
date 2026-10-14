"""Enrollment uncertainty section, school pop-up: the grade segment is shown on the school's own chart as the average
school of the same type (K-5, 6-8, 9-12 or K-8, in the scenario being viewed): the simulated median and 90% range of
the average enrollment of the open schools of that type each year (each simulation's schools averaged), and the
actual average from fall 2016 (PSU-reported enrollment of the schools of that type). The separate district charts
(patch_mc_fan_district.py) are removed from the pop-up. The chart's fixed axis also covers the average school.
Code changed once.
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

HELPER = r'''// the average school of a type, for the school pop-up (scripts/patch_mc_avg_school.py)
const mcTypeAt = (k, sc, yi) => (yi < D.years.indexOf(D.impl_year) ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k];
function mcAvgPath(grp, sc) {   // [year][draw] average enrollment of the open schools of type grp; also .page and .hist
  const ck = ['avg', grp, sc, mcVar, adjOn].join('|'); if (mcPathCache[ck]) return mcPathCache[ck];
  const out = D.years.map((y, yi) => {
    const ks = D.mc.schools.filter(k => mcTypeAt(k, sc, yi) === grp && D.series[sc]?.[k]?.[yi] != null); if (!ks.length) return null;
    const paths = ks.map(k => mcSchoolPath(k, sc)[yi]), n = paths[0].length, a = new Array(n).fill(0);
    for (const p of paths) for (let i = 0; i < n; i++) a[i] += p[i] / ks.length;
    a.page = ks.reduce((t, k) => t + D.series[sc][k][yi], 0) / ks.length; a.count = ks.length;
    return a;
  });
  out.hist = Array.from({ length: 10 }, (_, i) => { const f = 2016 + i, lab = `${f}-${String((f + 1) % 100).padStart(2, '0')}`;
    const v = D.mc.schools.filter(k => D.types.SQ[k] === grp).map(k => D.fcacc?.sch?.[k]?.a?.[lab]).filter(x => x != null);
    return v.length ? [f, v.reduce((t, x) => t + x, 0) / v.length] : null; }).filter(Boolean);
  return mcPathCache[ck] = out;
}
function mcSchoolFan(k, sc) {'''

if 'mcAvgPath' not in html:
    rep("function mcSchoolFan(k, sc) {", HELPER)
    # compute the average school's ranges
    rep("""  const thr = F.map((f, yi) => mcThr(k, sc, yi));
  const vals = [""", """  const thr = F.map((f, yi) => mcThr(k, sc, yi));
  const grp = (D.types[sc] || {})[k] || D.types.SQ[k], glab = TYPE_LABEL[grp] || grp, AP = mcAvgPath(grp, sc);
  const AQ = AP.map(p => p ? mcQ(p, wd, [0.05, 0.5, 0.95]) : null);
  const vals = [""")
    # draw it under the school's ranges
    rep("""  // ranges
  for (const [a, b, op] of [[0, 4, 0.14], [1, 3, 0.26]]) for (const p of seg(F, i => Q[i] ? 1 : null)) {""",
        """  // the average school of this type: 90% range, median, actual average
  for (const p of seg(F, i => AQ[i] ? 1 : null)) { const idx = p.map(q => q[0] - 2025);
    s += `<polygon points="${idx.map(i => `${x(F[i])},${y(AQ[i][2])}`).join(' ')} ${idx.map(i => `${x(F[i])},${y(AQ[i][0])}`).reverse().join(' ')}" fill="#7c3aed" opacity=".12"/>`; }
  s += seg(F, i => AQ[i]?.[1]).map(p => `<polyline points="${p.map(q => `${x(q[0])},${y(q[1])}`).join(' ')}" fill="none" stroke="#7c3aed" stroke-width="1.8" stroke-dasharray="6 3"><title>Average ${esc(glab)} school (simulated median)</title></polyline>`).join('');
  if (AP.hist.length) s += `<polyline points="${AP.hist.map(h => `${x(h[0])},${y(h[1])}`).join(' ')}" fill="none" stroke="#7c3aed" stroke-width="1.6" opacity=".8"/>` + AP.hist.map(h => `<circle cx="${x(h[0])}" cy="${y(h[1])}" r="2" fill="#7c3aed"><title>Fall ${h[0]}: average ${esc(glab)} school ${Math.round(h[1]).toLocaleString()} actual</title></circle>`).join('');
  // ranges
  for (const [a, b, op] of [[0, 4, 0.14], [1, 3, 0.26]]) for (const p of seg(F, i => Q[i] ? 1 : null)) {""")
    # hover text
    rep("""; threshold ${thr[i]}; chance below ${Math.round(100 * pb[i])}%</title></rect>`; });""",
        """; threshold ${thr[i]}; chance below ${Math.round(100 * pb[i])}%${AQ[i] ? `; average ${glab} school median ${Math.round(AQ[i][1]).toLocaleString()} (90% range ${Math.round(AQ[i][0]).toLocaleString()}-${Math.round(AQ[i][2]).toLocaleString()}, ${AP[i].count} schools)` : ''}</title></rect>`; });""")
    # table row
    rep("""    `<tr><td style="text-align:left">Below threshold</td>""",
        """    `<tr><td style="text-align:left;white-space:nowrap">Average ${esc(glab)} school</td>${AQ.map(q => `<td style="text-align:right;color:#7c3aed">${q ? Math.round(q[1]) : '&mdash;'}</td>`).join('')}</tr>` +
    `<tr><td style="text-align:left">Below threshold</td>""")
    # legend
    rep("""<span><i class="k" style="border-top:1.6px dashed var(--down);width:18px"></i>size threshold</span></div>` + tbl +""",
        """<span><i class="k" style="border-top:1.6px dashed var(--down);width:18px"></i>size threshold</span><span><i class="k" style="border-top:1.8px dashed #7c3aed;width:18px"></i>average ${esc(glab)} school: simulated median, 90% range shaded; solid: actual</span></div>` + tbl +""")
    # remove the separate district charts
    m = re.search(r"\n    \(\(t => `<div style=\"display:grid;grid-template-columns:repeat\(auto-fit,minmax\(280px,1fr\)\);gap:12px;margin-top:12px\">\$\{mcBandFan\(t\)\}.*?\|\| 'K-5'\)\) \+ `</div>`;", html, re.S)
    assert m, 'district charts block'
    html = html[:m.start()] + " `</div>`;" + html[m.end():]
    # fixed axis covers the average school
    rep("""  for (const v of ['district', 'school']) { mcVar = v; mcSchoolPath(k, sc).forEach(p => { if (p) pts.push(...mcQ(p, p.map(() => 1), [0.05, 0.95])); }); }""",
        """  const grp = (D.types[sc] || {})[k] || D.types.SQ[k];
  for (const v of ['district', 'school']) { mcVar = v; mcSchoolPath(k, sc).forEach(p => { if (p) pts.push(...mcQ(p, p.map(() => 1), [0.05, 0.95])); });
    const ap = mcAvgPath(grp, sc); ap.forEach(p => { if (p) pts.push(...mcQ(p, p.map(() => 1), [0.05, 0.95])); }); ap.hist.forEach(h => pts.push(h[1])); }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
