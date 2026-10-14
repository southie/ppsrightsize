"""Enrollment uncertainty section: fixed axes. Every chart's value axis is set from all simulations (no capture filter,
both uncertainty options) together with history, PSU's forecasts and the page's values, so filtering the long-run
capture range or switching options never rescales a chart, and a district band (K-12, K, K-5, 6-8, 9-12, K-8) has the
same axis in the main fan chart and in the school pop-up. Code added once.
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

HELPER = r'''// fixed axes (scripts/patch_mc_fixed_axes.py): ranges from all simulations, history and PSU's forecasts, never the filtered set
const mcRangeCache = {};
function mcBandRange(band) {   // [lo, hi] for a district band, shared by the main fan chart and the school pop-up
  if (mcRangeCache[band]) return mcRangeCache[band];
  const pick = { K: [0], 'K-5': [1], '6-8': [2], '9-12': [3], 'K-8': [1, 2], 'K-12': [1, 2, 3] }[band], hb = { 0: 'K', 1: 'K-5', 2: '6-8', 3: '9-12' };
  const sims = D.mc.variants.district.bands, ones = sims.map(() => 1), pts = [];
  D.years.forEach((_, j) => pts.push(...mcQ(sims.map(s => pick.reduce((t, i) => t + s[j][i], 0)), ones, [0.05, 0.95])));
  const H_ = D.mc.hist; H_.falls.forEach((f, i) => { if (f >= 2009) pts.push(pick.reduce((t, i2) => t + H_.bands[hb[i2]][i], 0)); });
  const PS = D.mc.psu; PS.falls.forEach((f, i) => { if (f <= 2035) for (const s of ['low', 'medium', 'high']) pts.push(pick.reduce((t, i2) => t + PS[s][hb[i2]][i], 0)); });
  const bix = { K: 0, 'K-5': 1, '6-8': 2, '9-12': 3, 'K-12': 4 }[band];
  if (bix != null) D.mc.bt.filter(r => r[2] === bix).forEach(r => pts.push(r[4]));
  const v = pts.filter(x => x != null && isFinite(x));
  return mcRangeCache[band] = [Math.min(...v) * 0.97, Math.max(...v) * 1.02];
}
const mcColV = (key, v) => { const j = D.mc.mk.indexOf(key); if (j < 0) return null; const dec = /cost|gf/.test(key) ? 1000 : /pct/.test(key) ? 0.1 : 1; return D.mc.variants[v].m.map(r => r[j] * dec); };
function mcSchoolRange(k, sc) {   // [lo, hi] for a school's chart: both uncertainty options, unfiltered, with history, the page and the threshold
  const ck = [k, sc, adjOn].join('|'); if (mcRangeCache[ck]) return mcRangeCache[ck];
  const keep = mcVar, pts = [];
  for (const v of ['district', 'school']) { mcVar = v; mcSchoolPath(k, sc).forEach(p => { if (p) pts.push(...mcQ(p, p.map(() => 1), [0.05, 0.95])); }); }
  mcVar = keep;
  Object.entries(D.fcacc?.sch?.[k]?.a || {}).forEach(([y, v]) => { if (+y.slice(0, 4) >= 2016) pts.push(v); });
  D.years.forEach((y, yi) => { pts.push(D.series[sc]?.[k]?.[yi], D.series.SQ?.[k]?.[yi], mcThr(k, sc, yi)); });
  const v = pts.filter(x => x != null && isFinite(x));
  return mcRangeCache[ck] = [Math.max(0, Math.min(...v) * 0.9), Math.max(...v) * 1.06];
}
function renderMC() {'''

if 'mcBandRange' not in html:
    rep("function renderMC() {", HELPER)
    # main fan chart
    rep("""  if (mcBT) D.mc.bt.filter(r => r[2] === bix).forEach(r => pts.push(r[4], r[6]));
  const ylo = Math.min(...pts) * 0.97, yhi = Math.max(...pts) * 1.02;""",
        """  const [ylo, yhi] = mcBandRange(mcBand);   // fixed: the same whatever the capture filter or overlay""")
    # pop-up district charts
    rep("""  const pts = [...Q.flatMap(q => [q[0], q[4]]), ...Array.from({ length: 10 }, (_, i) => hv(2016 + i)), ...F.flatMap(f => ['low', 'medium', 'high'].map(s => pv(s, f)))].filter(v => v != null && isFinite(v));
  const ylo = Math.min(...pts) * 0.97, yhi = Math.max(...pts) * 1.02;""",
        """  const [ylo, yhi] = mcBandRange(band);""")
    # pop-up school chart
    rep("""  const ylo = Math.max(0, Math.min(...vals) * 0.9), yhi = Math.max(...vals) * 1.06;""",
        """  const [ylo, yhi] = mcSchoolRange(k, sc);   // fixed across capture filters and uncertainty options""")
    # range plots: both options, unfiltered
    rep("""all = cols.flatMap(c => mcQ(c, w, [0.02, 0.98])).concat(rows.map(([, key]) => mcMed(key)).filter(v => v != null));""",
        """all = rows.flatMap(([, key]) => ['district', 'school'].flatMap(v => { const c = mcColV(key, v); return c ? mcQ(c, c.map(() => 1), [0.02, 0.98]) : []; })).concat(rows.map(([, key]) => mcMed(key)).filter(v => v != null));   // fixed axis""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
