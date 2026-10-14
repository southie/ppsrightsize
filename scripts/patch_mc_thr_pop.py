"""Enrollment uncertainty section, district fan chart: the threshold population for the grade band shown (K-5, 6-8,
9-12, K-12; none for kindergarten alone): the enrollment the district needs for the schools on this page to average
their size threshold. = the sum of the thresholds of the schools open that year in the scenario being viewed (K-8s
split between K-5 and 6-8 by their K-5 share; high schools 1,100, middle and K-8 500, K-5 360) plus the students at
schools and programs not on this page (PSU's medium forecast for the band less this page's schools, Status Quo).
Drawn for the scenario being viewed and, dashed, for Status Quo; the hover gives each year's chance that district
enrollment falls below it. Included in the chart's fixed axis. Code added once.
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

HELPER = r'''// threshold population by grade band (scripts/patch_mc_thr_pop.py)
const mcThrCache = {};
function mcThrPop(band, sc) {   // [year] enrollment at which this page's open schools average their size threshold, plus students not on the page
  const ck = [band, sc, adjOn].join('|'); if (mcThrCache[ck]) return mcThrCache[ck];
  const parts = { 'K-5': ['k5'], '6-8': ['m68'], '9-12': ['h912'], 'K-12': ['k5', 'm68', 'h912'] }[band]; if (!parts) return null;
  const nameOf = { k5: 'K-5', m68: '6-8', h912: '9-12' };
  const split = (k, t, v, y) => { const f = k5Of(k, y) ?? 0.66; return t === 'ES' ? { k5: v, m68: 0, h912: 0 } : t === 'MS' ? { k5: 0, m68: v, h912: 0 } : t === 'HS' ? { k5: 0, m68: 0, h912: v } : { k5: f * v, m68: (1 - f) * v, h912: 0 }; };
  const out = D.years.map((y, yi) => {
    const fall = 2025 + yi, pi = D.mc.psu.falls.indexOf(fall); if (pi < 0) return null;
    const tot = { k5: 0, m68: 0, h912: 0 }, pageSQ = { k5: 0, m68: 0, h912: 0 };
    for (const k of Object.keys(D.region_of)) {
      const v = D.series[sc]?.[k]?.[yi]; if (v != null) { const t = mcTypeAt(k, sc, yi), s = split(k, t, D.thresholds[t] ?? 0, y); for (const p in tot) tot[p] += s[p]; }
      const q = D.series.SQ?.[k]?.[yi]; if (q != null) { const s = split(k, D.types.SQ[k], q, y); for (const p in pageSQ) pageSQ[p] += s[p]; }
    }
    return parts.reduce((t, p) => t + tot[p] + (D.mc.psu.medium[nameOf[p]][pi] - pageSQ[p]), 0);
  });
  return mcThrCache[ck] = out;
}
function mcBandRange(band) {'''

if 'mcThrPop' not in html:
    rep("function mcBandRange(band) {", HELPER)
    # the fixed axis includes the threshold populations for every scenario
    rep("""  const v = pts.filter(x => x != null && isFinite(x));
  return mcRangeCache[band] = [Math.min(...v) * 0.97, Math.max(...v) * 1.02];""",
        """  for (const s of D.mc.scen) (mcThrPop(band, s) || []).forEach(x => pts.push(x));
  const v = pts.filter(x => x != null && isFinite(x));
  return mcRangeCache[band] = [Math.min(...v) * 0.97, Math.max(...v) * 1.02];""")
    # draw it on the main fan chart, after the PSU lines
    rep("""  if (mcBT) {
    const byBase = {};""",
        """  // threshold population: the scenario being viewed, and Status Quo dashed
  const scv = scen === 'C' ? custom.base : scen, TP = mcThrPop(mcBand, scv), TQ = scv !== 'SQ' ? mcThrPop(mcBand, 'SQ') : null;
  if (TQ) s += `<polyline points="${F.map((f, j) => `${x(f)},${y(TQ[j])}`).join(' ')}" fill="none" stroke="var(--down)" stroke-width="1.3" stroke-dasharray="2 4" opacity=".8"><title>Threshold population, Status Quo</title></polyline>`;
  if (TP) s += `<polyline points="${F.map((f, j) => `${x(f)},${y(TP[j])}`).join(' ')}" fill="none" stroke="var(--down)" stroke-width="2" stroke-dasharray="7 4"><title>Threshold population, ${esc(scv === 'SQ' ? 'Status Quo' : LABEL[scv])}</title></polyline>` +
    `<text x="${x(2035) - 2}" y="${y(TP[F.length - 1]) - 5}" text-anchor="end" font-size="10" fill="var(--down)">threshold population</text>`;
  if (mcBT) {
    const byBase = {};""")
    # hover: threshold population and the chance of falling below it
    rep("""; 90% range ${Math.round(Q[j][0]).toLocaleString()}-${Math.round(Q[j][4]).toLocaleString()}${pv('medium', f) != null ? `; PSU medium ${pv('medium', f).toLocaleString()}` : ''}</title></rect>`; });""",
        """; 90% range ${Math.round(Q[j][0]).toLocaleString()}-${Math.round(Q[j][4]).toLocaleString()}${pv('medium', f) != null ? `; PSU medium ${pv('medium', f).toLocaleString()}` : ''}${TP ? `; threshold population (${scv === 'SQ' ? 'Status Quo' : LABEL[scv]}) ${Math.round(TP[j]).toLocaleString()}, chance district is below it ${Math.round(100 * mcProb(sims.map(sm => val(sm[j])), wd, v => v < TP[j]))}%` : ''}</title></rect>`; });""")
    # legend
    rep("""<span><i class="k" style="border-top:2px solid var(--change);width:18px"></i>simulated median</span>${mcBT ?""",
        """<span><i class="k" style="border-top:2px solid var(--change);width:18px"></i>simulated median</span>${mcBand !== 'K' ? `<span title="The sum of the size thresholds of the schools on this page open that year (K-5 360, middle and K-8 500, high school 1,100; K-8s split by their K-5 share), plus students at schools and programs not on this page (PSU medium). Below it, this page\\u2019s schools average less than their threshold."><i class="k" style="border-top:2px dashed var(--down);width:18px"></i>threshold population (${esc((scen === 'C' ? custom.base : scen) === 'SQ' ? 'Status Quo' : LABEL[scen === 'C' ? custom.base : scen])}${(scen === 'C' ? custom.base : scen) !== 'SQ' ? '; dotted: Status Quo' : ''}): schools average their size threshold</span>` : ''}${mcBT ?""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
