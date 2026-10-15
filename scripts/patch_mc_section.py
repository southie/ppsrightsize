"""Explorer section "How certain are these numbers? Enrollment uncertainty": the Monte Carlo enrollment model
(scripts/montecarlo_enrollment.js --export; calibrated by scripts/montecarlo_backtest.py) shown beside the page's figures,
without changing them (every other figure on the page stays on PSU's medium forecast).
Shows, for the scenario being viewed (a custom scenario: its base scenario) and a chosen year:
  - summary cards: the page's (medium-forecast) value against the simulated median and 90% range, with a probability;
  - a fan chart of district enrollment by grade band (actual history, PSU's low / medium / high forecasts, the simulated
    50% and 90% ranges) with an optional overlay of the backtest's past forecasts;
  - ranges for staffing savings, schools below their size threshold and students in schools at or above it (Status Quo,
    A, B), with the medium forecast marked;
  - what drives each range (share of variance by input);
  - each school's chance of being below its size threshold.
Controls: year, whether to include school-level forecast error, and the long-run kindergarten capture rate range: the
stored draws are filtered to that range (no re-simulation), so every chart shows the outcomes given that assumption.
Data: D.mc (rebuilt on rerun from source/montecarlo/mc-embed.json, backtest.json, source/pps-forecast/historic-grades.json
and PSU Tables 5.2-5.4); code added once. Runs after patch_split_feeders.
"""
import json, os, re, sys
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
MC = json.load(open(os.path.join(ROOT, 'source', 'montecarlo', 'mc-embed.json'), encoding='utf-8'))
BT = json.load(open(os.path.join(ROOT, 'source', 'montecarlo', 'backtest.json'), encoding='utf-8'))
HG = json.load(open(os.path.join(ROOT, 'source', 'pps-forecast', 'historic-grades.json'), encoding='utf-8'))
GR = ['K'] + [str(i) for i in range(1, 13)]
band_of = lambda grades, idx: [sum(grades[GR[g]][i] for g in idx) for i in range(len(next(iter(grades.values()))))]
BIDX = {'K': [0], 'K-5': range(0, 6), '6-8': range(6, 9), '9-12': range(9, 13)}
hist = {b: band_of(HG['grades'], ix) for b, ix in BIDX.items()}
# PSU Tables 5.2-5.4 (medium / low / high), all PPS, fall 2021-2040
def psu_table(page):
    t = ' '.join(pymupdf.open(os.path.join(ROOT, 'archive', 'PPS_Forecast_2026_27.pdf'))[page].get_text().split())
    g = {}
    for gr in GR:
        mm = re.search(r'(?:^|\s)' + gr + r' ((?:[\d,]+ ){19}[\d,]+)', t); g[gr] = [int(x.replace(',', '')) for x in mm.group(1).split()]
    return {b: band_of(g, ix) for b, ix in BIDX.items()}
psu = {'medium': psu_table(33), 'low': psu_table(34), 'high': psu_table(35)}
for sc in psu.values(): assert sc['K'][4] == 2919, 'PSU table parse'
bt_bands = ['K', 'K-5', '6-8', '9-12', 'K-12']
bt = [[r['base'], r['fall'], bt_bands.index(r['band']), round(r['p5']), round(r['p50']), round(r['p95']), round(r['actual'])] for r in BT['records']]
bts = {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in BT['summary'].items() if k.split('|')[1] == 'K-12'}
D['mc'] = dict(n=MC['n'], generated=MC['generated'][:10], years=MC['years'], out_years=MC['out_years'], scen=MC['scen'], schools=MC['schools'], combos=MC['combos'],
               mk=MC['metric_keys'], medium=MC['medium'], medium_bands=MC['medium_bands'], params=MC['params'], variants=MC['variants'],
               house=MC.get('house'), hband=MC.get('hband'), school_sd=MC.get('school_sd'),
               house_all=MC.get('house_all'), hband_all=MC.get('hband_all'), school_sd_all=MC.get('school_sd_all'),
               basis=MC.get('basis', 'psu'),
               hist=dict(falls=HG['falls'], bands=hist), psu=dict(falls=list(range(2021, 2041)), **psu), bt=bt, bt_summary=bts,
               bt_psu_pre=BT.get('psu_pre_covid_k12_table44'), bt_psu_post=BT.get('psu_district_error', {}).get('post'), bt_cap_scale=BT.get('cap_scale'))
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
print('D.mc embedded:', round(len(json.dumps(D['mc'], separators=(',', ':'))) / 1e6, 2), 'MB')

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

SECTION = r'''  <section class="card" id="mccard">
    <h2>How certain are these numbers? Enrollment uncertainty</h2>
    <p class="sub" id="mcsub"></p>
    <div class="controls" id="mcctl"></div>
    <div class="kpis" id="mckpis"></div>
    <h3 class="cshead">District enrollment: history, PSU's forecasts and the simulated range</h3>
    <div class="controls" id="mcfanctl"></div>
    <div id="mcfan"></div>
    <h3 class="cshead" id="mcrangehead">Ranges for staffing and threshold measures</h3>
    <div id="mcranges"></div>
    <h3 class="cshead">What drives the range</h3>
    <div id="mcdrivers"></div>
    <h3 class="cshead">Each school's chance of being below its size threshold</h3>
    <div class="controls tabletools"><button id="mc-allsch">Show all schools</button></div>
    <div class="tablewrap" id="mcschools"></div>
    <details class="lineswrap" style="margin-top:10px"><summary>Method, calibration and limits</summary><div id="mcmethod" class="sub" style="margin-top:8px"></div></details>
  </section>

  <section class="card">
    <h2>Split feeders: schools whose students go on to different schools</h2>'''

JS = r'''// ---------- enrollment uncertainty: Monte Carlo (scripts/patch_mc_section.py) ----------
// Every other figure on the page uses PSU's medium forecast; this section shows the simulated range around it.
let mcYear = '2031-32', mcVar = 'district', mcBand = 'K-12', mcBT = false, mcAll = false, mcCap = null;
const MC_BANDS = ['K-12', 'K', 'K-5', '6-8', '9-12'];
const MC_INPUT = { capture_long_run: 'Kindergarten capture, long-run level', capture_noise_mean: 'Kindergarten capture, year-to-year', gpr_k5: 'Grade progression, K-5', gpr_68: 'Grade progression, 6-8', gpr_912: 'Grade progression, 9-12', gpr_common: 'Grade progression, all grades together' };
const mcBitsCache = {};
function mcBits(v) {   // decoded below-threshold flags per draw
  if (mcBitsCache[v]) return mcBitsCache[v];
  return mcBitsCache[v] = D.mc.variants[v].below.map(b64 => { const s = atob(b64), a = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) a[i] = s.charCodeAt(i); return a; });
}
function mcWeights() {
  const c = D.mc.variants[mcVar].cap, [lo, hi] = mcCap || [-1, 9];
  return c.map(v => v >= lo - 1e-9 && v <= hi + 1e-9 ? 1 : 0);
}
function mcQ(vals, w, ps) {   // weighted quantiles
  const ix = vals.map((v, i) => i).filter(i => w[i] > 0).sort((a, b) => vals[a] - vals[b]);
  const tot = ix.reduce((t, i) => t + w[i], 0); if (!tot) return ps.map(() => NaN);
  return ps.map(p => { let acc = 0; for (const i of ix) { acc += w[i]; if (acc >= p * tot - 1e-9) return vals[i]; } return vals[ix[ix.length - 1]]; });
}
const mcProb = (vals, w, f) => { let a = 0, t = 0; vals.forEach((v, i) => { if (w[i]) { t += w[i]; if (f(v)) a += w[i]; } }); return t ? a / t : NaN; };
function mcCol(key) { const j = D.mc.mk.indexOf(key); if (j < 0) return null; const dec = /cost|gf/.test(key) ? 1000 : /pct/.test(key) ? 0.1 : 1; return D.mc.variants[mcVar].m.map(r => r[j] * dec); }
const mcMed = key => { const v = D.mc.medium[key]; return v == null ? null : v * (/cost|gf/.test(key) ? 1000 : /pct/.test(key) ? 0.1 : 1); };
const mcM = v => '$' + (v / 1e6).toFixed(1) + 'M', mcPct = v => v.toFixed(1) + '%', mcN = v => Math.round(v).toLocaleString();
function renderMC() {
  const host = document.getElementById('mckpis'); if (!host || !D.mc) return;
  const P = D.mc.params.capture, tri = P.tri;
  if (!mcCap) mcCap = [tri.a, tri.b];
  const sc = scen === 'C' ? custom.base : scen, lab = sc === 'SQ' ? 'Status Quo' : LABEL[sc], w = mcWeights(), kept = w.filter(Boolean).length;
  // controls
  document.getElementById('mcctl').innerHTML = `<label>Year <select id="mc-year">${D.mc.out_years.map(y => `<option${y === mcYear ? ' selected' : ''}>${y}</option>`).join('')}</select></label>` +
    `<label>Uncertainty <select id="mc-var"><option value="district"${mcVar === 'district' ? ' selected' : ''}>District: kindergarten capture + grade progression</option><option value="school"${mcVar === 'school' ? ' selected' : ''}>Plus each school's own forecast error</option></select></label>` +
    `<label title="Keep only the simulations whose long-run kindergarten capture rate is in this range">Long-run K capture <input type="range" id="mc-lo" min="${tri.a}" max="${tri.b}" step="0.002" value="${mcCap[0]}"> to <input type="range" id="mc-hi" min="${tri.a}" max="${tri.b}" step="0.002" value="${mcCap[1]}"> <b id="mc-capv">${mcCap[0].toFixed(3)}&ndash;${mcCap[1].toFixed(3)}</b></label>` +
    `<button id="mc-reset" type="button">Reset</button> <span class="muted">${kept.toLocaleString()} of ${D.mc.n.toLocaleString()} simulations</span>`;
  document.getElementById('mc-year').onchange = e => { mcYear = e.target.value; renderMC(); };
  document.getElementById('mc-var').onchange = e => { mcVar = e.target.value; renderMC(); };
  const lo = document.getElementById('mc-lo'), hi = document.getElementById('mc-hi');
  const capSet = () => { let a = +lo.value, b = +hi.value; if (a > b) [a, b] = [b, a]; mcCap = [a, b]; renderMC(); };
  lo.onchange = capSet; hi.onchange = capSet;
  lo.oninput = hi.oninput = () => { document.getElementById('mc-capv').innerHTML = `${(+lo.value).toFixed(3)}&ndash;${(+hi.value).toFixed(3)}`; };
  document.getElementById('mc-reset').onclick = () => { mcCap = [tri.a, tri.b]; renderMC(); };
  document.getElementById('mcsub').innerHTML = `The figures elsewhere on this page use Portland State University's medium enrollment forecast. This section simulates ${D.mc.n.toLocaleString()} other plausible futures, varying the two things that drive PSU's forecast: the <b>kindergarten capture rate</b> (the share of the district's children who start kindergarten at PPS; long-run level drawn from ${tri.a.toFixed(3)} to ${tri.b.toFixed(3)}, most likely PSU's ${tri.m.toFixed(3)}, measured against births five years earlier) and the <b>grade progression ratios</b> (how each class grows or shrinks from one grade to the next). Each simulated future is run through this page's staffing formula and threshold measures. ` +
    `<b>It does not change any other figure on the page.</b>${scen === 'C' ? ` Custom scenarios are not simulated: showing ${esc(lab)}, the custom scenario's base.` : ''} Ranges are the middle 90% of the simulations (5th to 95th percentile).`;
  // cards
  const y = mcYear, card = (key, title, fmt, extra) => {
    const v = mcCol(key); if (!v) return '';
    const [p5, p50, p95] = mcQ(v, w, [0.05, 0.5, 0.95]), md = mcMed(key);
    return `<div class="kpi"><div class="v">${fmt(p50)}<span class="d" style="color:var(--text-muted)">median</span><span class="vt">${title}</span></div>` +
      `<div class="l">${y}, ${esc(lab)}: 90% range ${fmt(p5)} to ${fmt(p95)}</div><div class="s">Page value (PSU medium forecast): <b>${fmt(md)}</b>${extra ? '<br>' + extra(v, md) : ''}</div></div>`;
  };
  const pAbove = (v, md) => `Chance above the page value: <b>${Math.round(100 * mcProb(v, w, x => x > md + 1e-6))}%</b>`;
  let k = '';
  if (sc === 'SQ') {
    k = card(`${y}|SQ|students`, 'Students at PPS schools', mcN, pAbove) + card(`${y}|SQ|cost`, 'Staffing cost (formula)', mcM, pAbove) +
      card(`${y}|SQ|below`, 'Schools below size threshold', v => Math.round(v), pAbove) + card(`${y}|SQ|students_above_pct`, 'Students in schools at or above threshold', mcPct, pAbove);
  } else {
    const a = mcCol(`${y}|A|cost_saved`), b = mcCol(`${y}|B|cost_saved`);
    const ab = a && b ? `A saves more than B in <b>${Math.round(100 * mcProb(a.map((x, i) => x - b[i]), w, x => x > 0))}%</b> of simulations` : '';
    k = card(`${y}|${sc}|cost_saved`, 'Staffing savings vs Status Quo (formula)', mcM, (v, md) => `Chance below the page value: <b>${Math.round(100 * mcProb(v, w, x => x < md - 1e-6))}%</b>${ab ? '<br>' + ab : ''}`) +
      card(`${y}|${sc}|gf_saved`, 'General Fund savings (est.)', mcM) +
      card(`${y}|${sc}|below`, 'Schools below size threshold', v => Math.round(v), (v, md) => `Chance of more than the page value: <b>${Math.round(100 * mcProb(v, w, x => x > md + 1e-6))}%</b>`) +
      card(`${y}|${sc}|students_above_pct`, 'Students in schools at or above threshold', mcPct, (v, md) => `Chance below the page value: <b>${Math.round(100 * mcProb(v, w, x => x < md - 1e-6))}%</b>`);
  }
  host.innerHTML = k;
  renderMCFan(w); renderMCRanges(w, sc); renderMCDrivers(sc); renderMCSchools(w, sc); renderMCMethod();
}
function renderMCFan(w) {
  const ctl = document.getElementById('mcfanctl'), host = document.getElementById('mcfan'); if (!host) return;
  ctl.innerHTML = `<div class="seg" role="group">${MC_BANDS.map(b => `<button type="button" data-b="${b}" aria-pressed="${b === mcBand}">${b}</button>`).join('')}</div>` +
    `<label><input type="checkbox" id="mc-bt"${mcBT ? ' checked' : ''}> Past forecasts (backtest)</label>`;
  ctl.querySelectorAll('[data-b]').forEach(x => x.onclick = () => { mcBand = x.dataset.b; renderMCFan(mcWeights()); });
  document.getElementById('mc-bt').onchange = e => { mcBT = e.target.checked; renderMCFan(mcWeights()); };
  const bi = { K: 0, 'K-5': 1, '6-8': 2, '9-12': 3 }, val = arr => mcBand === 'K-12' ? arr[1] + arr[2] + arr[3] : arr[bi[mcBand]];
  const H = D.mc.hist, hv = f => { const i = H.falls.indexOf(f); if (i < 0) return null; return mcBand === 'K-12' ? H.bands['K-5'][i] + H.bands['6-8'][i] + H.bands['9-12'][i] : H.bands[mcBand][i]; };
  const PS = D.mc.psu, pv = (s, f) => { const i = PS.falls.indexOf(f); if (i < 0) return null; const b = PS[s]; return mcBand === 'K-12' ? b['K-5'][i] + b['6-8'][i] + b['9-12'][i] : b[mcBand][i]; };
  const sims = D.mc.variants.district.bands, wd = D.mc.variants.district.cap.map((c, i) => { const [lo, hi] = mcCap; return c >= lo - 1e-9 && c <= hi + 1e-9 ? 1 : 0; });
  const F = Array.from({ length: 11 }, (_, i) => 2025 + i), Q = F.map((f, j) => mcQ(sims.map(s => val(s[j])), wd, [0.05, 0.25, 0.5, 0.75, 0.95]));
  const x0 = mcBT ? 2009 : 2016, x1 = 2035, W = 760, Hh = 300, L = 62, R = 16, T = 14, B = 30;
  const pts = [...F.flatMap((_, j) => [Q[j][0], Q[j][4]]), ...Array.from({ length: 27 }, (_, i) => hv(2009 + i)).filter(v => v != null), ...F.flatMap(f => ['low', 'medium', 'high'].map(s => pv(s, f))).filter(v => v != null)];
  const bix = mcBand === 'K-12' ? 4 : { K: 0, 'K-5': 1, '6-8': 2, '9-12': 3 }[mcBand];
  if (mcBT) D.mc.bt.filter(r => r[2] === bix).forEach(r => pts.push(r[4], r[6]));
  const ylo = Math.min(...pts) * 0.97, yhi = Math.max(...pts) * 1.02;
  const x = f => L + (W - L - R) * (f - x0) / (x1 - x0), y = v => T + (Hh - T - B) * (1 - (v - ylo) / (yhi - ylo));
  let s = '';
  const step = (yhi - ylo) > 20000 ? 5000 : (yhi - ylo) > 6000 ? 2000 : (yhi - ylo) > 2500 ? 500 : 250;
  for (let v = Math.ceil(ylo / step) * step; v <= yhi; v += step) s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" font-size="10.5" fill="var(--text-muted)">${v.toLocaleString()}</text>`;
  for (let f = x0; f <= x1; f += mcBT ? 2 : 1) s += `<text x="${x(f)}" y="${Hh - B + 15}" text-anchor="middle" font-size="10" fill="var(--text-muted)">${f}</text>`;
  s += `<line x1="${x(2025.5)}" x2="${x(2025.5)}" y1="${T}" y2="${Hh - B}" stroke="var(--line)" stroke-dasharray="3 3"/><text x="${x(2025.5) + 4}" y="${T + 10}" font-size="10" fill="var(--text-muted)">forecast &rarr;</text>`;
  const poly = (lo, hi) => F.map((f, j) => `${x(f)},${y(Q[j][hi])}`).join(' ') + ' ' + F.map((f, j) => `${x(f)},${y(Q[j][lo])}`).reverse().join(' ');
  s += `<polygon points="${poly(0, 4)}" fill="var(--change)" opacity=".14"/><polygon points="${poly(1, 3)}" fill="var(--change)" opacity=".24"/>`;
  s += `<polyline points="${F.map((f, j) => `${x(f)},${y(Q[j][2])}`).join(' ')}" fill="none" stroke="var(--change)" stroke-width="2"/>`;
  for (const [sname, dash, wdt] of [['medium', '', 2], ['low', '5 4', 1.3], ['high', '5 4', 1.3]]) {
    const ps = F.map(f => [f, pv(sname, f)]).filter(p => p[1] != null);
    s += `<polyline points="${ps.map(p => `${x(p[0])},${y(p[1])}`).join(' ')}" fill="none" stroke="var(--text-primary)" stroke-width="${wdt}" ${dash ? `stroke-dasharray="${dash}"` : ''} opacity=".8"><title>PSU ${sname} forecast</title></polyline>`;
  }
  if (mcBT) {
    const byBase = {};
    D.mc.bt.filter(r => r[2] === bix).forEach(r => (byBase[r[0]] = byBase[r[0]] || []).push(r));
    for (const [b, rs] of Object.entries(byBase)) {
      const p = [[+b, hv(+b)], ...rs.map(r => [r[1], r[4]])];
      s += `<polyline points="${p.map(q => `${x(q[0])},${y(q[1])}`).join(' ')}" fill="none" stroke="#b45309" stroke-width="1.2" opacity=".75"><title>Model forecast from fall ${b} (data available then)</title></polyline>`;
    }
  }
  const hp = Array.from({ length: x1 - x0 + 1 }, (_, i) => [x0 + i, hv(x0 + i)]).filter(p => p[1] != null);
  s += `<polyline points="${hp.map(p => `${x(p[0])},${y(p[1])}`).join(' ')}" fill="none" stroke="var(--text-primary)" stroke-width="2.6"/>` + hp.map(p => `<circle cx="${x(p[0])}" cy="${y(p[1])}" r="2.4" fill="var(--text-primary)"><title>Fall ${p[0]}: ${p[1].toLocaleString()} actual</title></circle>`).join('');
  F.forEach((f, j) => { s += `<rect x="${x(f) - 8}" y="${T}" width="16" height="${Hh - T - B}" fill="transparent"><title>Fall ${f}: simulated median ${Math.round(Q[j][2]).toLocaleString()}; 50% range ${Math.round(Q[j][1]).toLocaleString()}-${Math.round(Q[j][3]).toLocaleString()}; 90% range ${Math.round(Q[j][0]).toLocaleString()}-${Math.round(Q[j][4]).toLocaleString()}${pv('medium', f) != null ? `; PSU medium ${pv('medium', f).toLocaleString()}` : ''}</title></rect>`; });
  host.innerHTML = `<svg viewBox="0 0 ${W} ${Hh}" style="width:100%;max-width:${W}px;height:auto" role="img" aria-label="District enrollment history, PSU forecasts and simulated range">${s}</svg>` +
    `<div class="rplegend"><span><i class="k" style="border-top:2.6px solid var(--text-primary);width:18px"></i>actual (all PPS, fall)</span><span><i class="k" style="border-top:2px solid var(--text-primary);width:18px;opacity:.8"></i>PSU medium</span><span><i class="k" style="border-top:2px dashed var(--text-primary);width:18px;opacity:.8"></i>PSU low / high</span>` +
    `<span><i class="k" style="height:10px;width:16px;background:var(--change);opacity:.35"></i>simulated 50% / 90% range</span><span><i class="k" style="border-top:2px solid var(--change);width:18px"></i>simulated median</span>${mcBT ? '<span><i class="k" style="border-top:1.4px solid #b45309;width:18px"></i>the model’s past forecasts (from each fall, with the data available then)</span>' : ''}</div>`;
}
function mcBox(label, v, w, md, fmt, lo, hi, W, Lm) {
  const [p5, p25, p50, p75, p95] = mcQ(v, w, [0.05, 0.25, 0.5, 0.75, 0.95]), x = t => Lm + (W - Lm - 70) * (t - lo) / ((hi - lo) || 1);
  return `<text x="${Lm - 8}" y="17" text-anchor="end" font-size="11.5" fill="var(--text-secondary)">${label}</text>` +
    `<line x1="${x(p5)}" x2="${x(p95)}" y1="13" y2="13" stroke="var(--change)" stroke-width="1.5"/><rect x="${x(p25)}" y="6" width="${Math.max(1, x(p75) - x(p25))}" height="14" fill="var(--change)" opacity=".3" stroke="var(--change)"/>` +
    `<line x1="${x(p50)}" x2="${x(p50)}" y1="4" y2="22" stroke="var(--change)" stroke-width="2.4"/>` +
    (md != null ? `<path d="M${x(md)},6 l6,7 l-6,7 l-6,-7 Z" fill="var(--surface-1)" stroke="var(--text-primary)" stroke-width="1.6"><title>Page value (PSU medium): ${fmt(md)}</title></path>` : '') +
    `<text x="${W - 64}" y="17" font-size="10.5" fill="var(--text-muted)">${fmt(p50)}</text><title>${label}: median ${fmt(p50)}; 50% range ${fmt(p25)}-${fmt(p75)}; 90% range ${fmt(p5)}-${fmt(p95)}${md != null ? `; page value ${fmt(md)}` : ''}</title>`;
}
function renderMCRanges(w, sc) {
  const host = document.getElementById('mcranges'); if (!host) return;
  document.getElementById('mcrangehead').textContent = `Ranges for staffing and threshold measures, ${mcYear}`;
  const y = mcYear, W = 640, Lm = 150;
  const group = (title, rows, fmt) => {
    const cols = rows.map(([, key]) => mcCol(key)).filter(Boolean), all = cols.flatMap(c => mcQ(c, w, [0.02, 0.98])).concat(rows.map(([, key]) => mcMed(key)).filter(v => v != null));
    const lo = Math.min(...all), hi = Math.max(...all), pad = (hi - lo) * 0.06 || 1;
    return `<div style="margin:8px 0 2px;font-weight:600;font-size:13px">${title}</div>` + rows.map(([l, key]) => { const v = mcCol(key); return v ? `<svg viewBox="0 0 ${W} 26" style="width:100%;max-width:${W}px;height:auto;display:block">${mcBox(l + (l === (sc === 'SQ' ? 'Status Quo' : LABEL[sc]) ? ' ◀' : ''), v, w, mcMed(key), fmt, lo - pad, hi + pad, W, Lm)}</svg>` : ''; }).join('');
  };
  host.innerHTML = group('Staffing savings vs Status Quo, a year (formula; General Fund est. below)', [['Scenario A', `${y}|A|cost_saved`], ['Scenario B', `${y}|B|cost_saved`], ['A, General Fund', `${y}|A|gf_saved`], ['B, General Fund', `${y}|B|gf_saved`]], mcM) +
    group('Schools below their size threshold', [['Status Quo', `${y}|SQ|below`], ['Scenario A', `${y}|A|below`], ['Scenario B', `${y}|B|below`]], v => Math.round(v)) +
    group('Students in schools at or above their threshold', [['Status Quo', `${y}|SQ|students_above_pct`], ['Scenario A', `${y}|A|students_above_pct`], ['Scenario B', `${y}|B|students_above_pct`]], mcPct) +
    `<div class="rplegend" style="margin-top:6px"><span><i class="k" style="height:10px;width:16px;background:var(--change);opacity:.4"></i>middle 50%; line: middle 90%; bar: median</span><span>&#9671; page value (PSU medium forecast)</span></div>`;
}
function renderMCDrivers(sc) {
  const host = document.getElementById('mcdrivers'); if (!host) return;
  const y = mcYear, ms = sc === 'SQ' ? [['SQ|cost', 'Status Quo staffing cost'], ['SQ|below', 'Status Quo schools below threshold']] : [[`${sc}|cost_saved`, `${LABEL[sc]} staffing savings`], [`${sc}|below`, `${LABEL[sc]} schools below threshold`]];
  host.innerHTML = `<p class="sub" style="margin:0 0 6px">Share of each range explained by each input (all ${D.mc.n.toLocaleString()} simulations${mcVar === 'school' ? '; the rest is each school’s own forecast error' : ''}).</p>` +
    ms.map(([m, l]) => { const d = D.mc.variants[mcVar].drivers[`${y}|${m}`] || {}, tot = Object.values(d).reduce((a, b) => a + b, 0);
      return `<div style="margin:6px 0"><div style="font-size:12.5px;font-weight:600">${esc(l)}</div>` + Object.entries(d).sort((a, b) => b[1] - a[1]).filter(([, v]) => v >= 2).map(([kk, v]) =>
        `<div style="display:flex;align-items:center;gap:8px;font-size:12px"><span style="width:260px;color:var(--text-secondary)">${MC_INPUT[kk] || kk}</span><span style="display:inline-block;height:9px;width:${v * 3}px;background:var(--change);opacity:.7;border-radius:2px"></span><span>${v}%</span></div>`).join('') +
        `<div style="font-size:11.5px;color:var(--text-muted)">${Math.max(0, 100 - tot)}% not explained by these inputs${mcVar === 'school' ? ' (school-level error)' : ' (interactions, thresholds)'}</div></div>`; }).join('');
}
function renderMCSchools(w, sc) {
  const host = document.getElementById('mcschools'); if (!host) return;
  const bits = mcBits(mcVar), nk = D.mc.schools.length, yi = D.years.indexOf(mcYear);
  const prob = (s, ki) => { const c = D.mc.combos.indexOf(`${mcYear}|${s}`); let a = 0, t = 0; bits.forEach((b, i) => { if (!w[i]) return; t += w[i]; const j = c * nk + ki; if (b[j >> 3] & (1 << (j & 7))) a += w[i]; }); return t ? a / t : NaN; };
  const typ = (s, k) => (D.types[s] || {})[k] || D.types.SQ[k];
  const rows = D.mc.schools.map((k, ki) => ({ k, p: Object.fromEntries(D.mc.scen.map(s => [s, D.series[s]?.[k]?.[yi] == null ? null : prob(s, ki)])),
    med: Object.fromEntries(D.mc.scen.map(s => { const v = D.series[s]?.[k]?.[yi]; return [s, v == null ? null : v < (D.thresholds[typ(s, k)] ?? 0) - 1e-9]; })) }));
  const key = r => r.p[sc] ?? -1;
  rows.sort((a, b) => key(b) - key(a) || short(byKey[a.k]?.name || a.k).localeCompare(short(byKey[b.k]?.name || b.k)));
  const show = mcAll ? rows : rows.filter(r => (r.p[sc] ?? 0) >= 0.05 && (r.p[sc] ?? 0) <= 0.95).slice(0, 25);
  const cell = (r, s) => r.p[s] == null ? '<td class="muted" style="text-align:right">closes</td>' :
    `<td style="text-align:right;background:color-mix(in srgb, var(--down) ${Math.round(r.p[s] * 45)}%, transparent)"${s === sc ? ' class="cur"' : ''}><b>${Math.round(100 * r.p[s])}%</b>${r.med[s] ? ' <span class="muted" title="Below its threshold in the page’s figures (PSU medium)">&#9679;</span>' : ''}</td>`;
  host.innerHTML = `<table style="min-width:520px"><thead><tr><th style="text-align:left">School</th>${D.mc.scen.map(s => `<th style="text-align:right">${s === 'SQ' ? 'Status Quo' : LABEL[s]}</th>`).join('')}<th style="text-align:right">Threshold</th></tr></thead><tbody>` +
    show.map(r => `<tr><td style="text-align:left"><b>${esc(short(byKey[r.k]?.name || r.k))}</b> <span class="muted">${TYPE_LABEL[typ(sc, r.k)] || ''}</span></td>${D.mc.scen.map(s => cell(r, s)).join('')}<td style="text-align:right">${D.thresholds[typ(sc, r.k)] ?? ''}</td></tr>`).join('') +
    `</tbody></table><p class="sub" style="margin:6px 0 0">Chance the school is below its size threshold in ${mcYear} (share of simulations). &#9679; below it in the page's figures. ${mcAll ? 'All schools.' : 'Schools whose outcome is uncertain (5% to 95% in the scenario being viewed), most at risk first.'}</p>`;
  const b = document.getElementById('mc-allsch'); if (b) { b.textContent = mcAll ? 'Show uncertain schools only' : 'Show all schools'; b.onclick = () => { mcAll = !mcAll; renderMCSchools(mcWeights(), scen === 'C' ? custom.base : scen); }; }
}
function renderMCMethod() {
  const host = document.getElementById('mcmethod'); if (!host || host.dataset.done) return; host.dataset.done = '1';
  const P = D.mc.params.capture, S = D.mc.bt_summary, pre = D.mc.bt_psu_pre || {}, post = D.mc.bt_psu_post || {};
  const row = (per, h) => S[`${per}|K-12|${h}`];
  host.innerHTML = `<p><b>District model.</b> Enrollment by grade from actual fall 2025. Kindergarten = PSU's medium kindergarten forecast scaled by the simulated capture rate relative to PSU's (capture measured against births to district residents five years earlier: ${P.pre_covid_mean.toFixed(3)} on average before COVID, ${P.post_covid_mean.toFixed(3)} since, ${P.fall_2025.toFixed(3)} in fall 2025; PSU's forecast implies about ${P.psu_long_run.toFixed(3)}). Each simulation draws a long-run capture level (triangular, ${P.tri.a.toFixed(3)} to ${P.tri.b.toFixed(3)}, most likely ${P.tri.m.toFixed(3)}), moves toward it at PSU's pace, and adds year-to-year noise (${(100 * P.annual_sd).toFixed(1)}%). Grades 1-12 use PSU's grade progression ratios plus a lasting offset per grade and annual noise, sized from fall 2017-2025 with the COVID years removed. Births are taken as known (they are, for kindergarten classes through fall 2030).</p>` +
    `<p><b>Schools.</b> Each school's projected enrollment on this page (Status Quo, A, B) is scaled by its grade band's simulated change; students PSU expects from new affordable housing (${D.mc.params.housing.join(', ')} students in ${D.mc.out_years.join(', ')}) are held fixed. The option "plus each school's own forecast error" adds PSU's post-COVID typical school-level miss for the forecast horizon (about 4% a year ahead to 12% four years ahead), keeping district totals. Staffing, General Fund estimates and threshold counts are this page's own formulas.</p>` +
    `<p><b>Backtest.</b> Refitted from each fall 2009-2024 with only the data available then, the model's K-12 forecasts missed by ${[1, 2, 3, 4, 5].map(h => row('pre-COVID', h)).filter(Boolean).map(r => r.mape.toFixed(1) + '%').join(', ')} one to five years ahead before COVID (PSU's own forecasts: ${[1, 2, 3, 4, 5].map(h => pre[h] ?? pre[String(h)]).filter(v => v != null).map(v => v.toFixed(1) + '%').join(', ')}) and ${[1, 2, 3].map(h => row('post-COVID', h)).filter(Boolean).map(r => r.mape.toFixed(1) + '%').join(', ')} since (PSU: ${[1, 2, 3].map(h => post[h] ?? post[String(h)]).filter(Boolean).map(v => v[1].toFixed(1) + '%').join(', ')}); its 90% ranges contained the actual K-12 enrollment in ${[1, 2, 3, 4, 5].map(h => row('pre-COVID', h)).filter(Boolean).map(r => Math.round(r.in90) + '%').join(', ')} of cases. Kindergarten uncertainty was doubled (x${D.mc.bt_cap_scale}) so that its ranges covered past kindergarten outcomes. Before COVID the model ran 2-5% low on kindergarten; since COVID it has run 3-4% high, as PSU's assumed recovery in capture has not yet happened.</p>` +
    `<p><b>Limits.</b> Births after 2025 and migration are not varied separately (migration is reflected in the historical swings of capture and progression, which are drawn independently, so broad moves across grades are understated). A pandemic-type shock is outside the model. Custom scenarios are not simulated. Probabilities describe this model's assumptions, not certainties. Simulated ${D.mc.generated}; scripts/montecarlo_enrollment.js, scripts/montecarlo_backtest.py.</p>`;
}
function renderAll() {'''

if 'renderMC()' not in html:
    rep("""  <section class="card">
    <h2>Split feeders: schools whose students go on to different schools</h2>""", SECTION)
    rep("function renderAll() {", JS)
    rep("renderLines(); renderSplitFeeders();", "renderLines(); renderMC(); renderSplitFeeders();")
    rep("['splitfeed', 'sftable'], ['pta', 'ptatable']];", "['splitfeed', 'sftable'], ['pta', 'ptatable'], ['mc', 'mckpis']];")
    rep("  if (key === 'classsize') p.set('csy', csYear);", "  if (key === 'classsize') p.set('csy', csYear);\n  if (key === 'mc') { p.set('mcy', mcYear); if (mcVar !== 'district') p.set('mcv', mcVar); if (mcBand !== 'K-12') p.set('mcb', mcBand); }")
    rep("  if (D.years.includes(q.get('csy'))) csYear = q.get('csy');", "  if (D.years.includes(q.get('csy'))) csYear = q.get('csy');\n  if (D.mc && D.mc.out_years.includes(q.get('mcy'))) mcYear = q.get('mcy');\n  if (q.get('mcv') === 'school') mcVar = 'school';\n  if (MC_BANDS.includes(q.get('mcb'))) mcBand = q.get('mcb');")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
