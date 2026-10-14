// Monte Carlo enrollment simulation: uncertainty in the kindergarten capture rate and in grade progression ratios
// (GPRs), from Portland State University's PPS enrollment forecast (2026-27 edition), carried through the explorer's
// own staffing formula and sustainability-threshold measures for Status Quo and Scenarios A and B.
//
// District model, by grade, fall 2026 to fall 2035 (school years 2026-27 to 2035-36), starting from actual fall 2025:
//   Kindergarten. K = PSU medium K x (simulated capture rate / PSU's capture rate). Capture rate = K / births five years
//   earlier (PSU Fig. 4.2; births: PSU Table 2.3 five-year totals, interpolated by year). PSU projects capture
//   converging back toward the pre-COVID level; each simulation draws the long-run level L from a triangular
//   distribution: minimum = the post-COVID average (fall 2022-25), mode = PSU's own long-run capture, maximum = the
//   larger of the pre-COVID high and PSU's level plus its step above the pre-COVID average (--cap-max overrides). The path moves from PSU's toward L at PSU's own pace (fitted), plus independent
//   annual noise (relative sd from the historical year-to-year variation, COVID years removed).
//   Grades 1-12. GPR(g, t) = PSU medium GPR (Table 5.2) + a persistent offset for the grade + annual noise. Annual noise
//   sd = the grade's historical sd (PSU Table 3.1, fall 2017-2025, COVID transitions into 2020 and 2021 removed),
//   with a common factor across grades at the historical cross-grade correlation. The persistent offset's sd combines
//   the standard error of the historical mean and half the gap between the long-run historical mean and the recent
//   three-year mean PSU uses (PSU: district GPRs use the prior 3-year averages).
// Births are held at PSU's (they are known through 2025; the simulation is about capture and progression).
// Schools: each school's explorer enrollment (Status Quo, A, B) is scaled by its grade band's simulated / medium ratio
//   (K-5, 6-8, 9-12; K-8 schools by their K-5 share). Students from new affordable housing (PSU's exogenous school-level
//   additions: Table 2.7 developments x Table 4.1 yields, source/pps-forecast/affordable-housing.json, built by
//   scripts/build_affordable_housing.py) are held fixed: only the rest of each school's enrollment is scaled, and the
//   district ratios are taken net of them. In a scenario, a closing school's housing students go to its receivers.
//   Variant "school" adds school-level forecast error at PSU's
//   post-COVID typical school miss by forecast horizon (D.fcacc), rescaled so band totals still match the district.
// Outputs per simulation, for 2027-28 (scenarios take effect), 2031-32 and 2035-36: enrollment, staffing formula cost
//   and positions (Status Quo, A, B; savings vs Status Quo), General Fund estimate (each school's actual 2026-27
//   General Fund-to-formula ratio), schools below the size threshold, share of schools and of students at or above it.
// Sensitivity: standardized regression coefficients (share of variance explained) and Spearman rank correlations of
//   each output with the drawn inputs.
//
// Usage: node scripts/montecarlo_enrollment.js [--n 200] [--seed 1] [--cap-max 0.845] [--cap-noise-scale 2] [--export]
//   --export also writes source/montecarlo/mc-embed.json (every draw's district bands, key outputs and per-school below-threshold
//   flags) for the explorer's uncertainty section (scripts/patch_mc_section.py).
// Output: source/montecarlo/mc-summary.json, source/montecarlo/mc-draws.csv
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const N = +arg('--n', 200), SEED = +arg('--seed', 1), EXPORT = process.argv.includes('--export');

// ---------- load the explorer's script with a stub DOM / Leaflet (as in test_explorer.js) ----------
const html = fs.readFileSync(path.join(ROOT, 'rightsizing-scenario-explorer.html'), 'utf8');
const full = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
const cut = full.lastIndexOf('renderAll();');
const script = full.slice(0, cut) + full.slice(cut + 'renderAll();'.length);
const el = () => ({ innerHTML: '', textContent: '', style: {}, value: '', checked: false, options: [], dataset: {}, appendChild() {}, querySelectorAll: () => [], querySelector: () => null, addEventListener() {}, setAttribute() {}, getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 300 }), clientWidth: 900, offsetWidth: 100 });
const chain = new Proxy(function () {}, { get: () => chain, apply: () => chain });
Object.assign(global, { window: global, L: chain, innerWidth: 1200, addEventListener() {}, confirm: () => true,
  document: { getElementById: el, querySelectorAll: () => [], createElement: el, createElementNS: el, documentElement: {} },
  getComputedStyle: () => ({ getPropertyValue: () => '#000' }), localStorage: { getItem: () => null, setItem() {} },
  location: { hash: '', pathname: '/x.html', search: '', href: '' }, history: { replaceState() {} } });
const T = new Function(script + ';return { D, staffAgg, staffCost, staffGF, staffGFRatio, k5Of };')();
const { D } = T;

// ---------- PSU inputs ----------
// Table 3.1: historic K-12 enrollment, fall 2016-2025 (PPS Enrollment Forecast 2026-27, p. 16)
const H_YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];
const H = [
  [4073, 3948, 3899, 3874, 3244, 3195, 3152, 2995, 2837, 2919], [4141, 4106, 3916, 3930, 3696, 3282, 3376, 3213, 3070, 2950],
  [4211, 4070, 4040, 3861, 3738, 3476, 3319, 3360, 3207, 3078], [4160, 4133, 4011, 3971, 3646, 3486, 3502, 3320, 3365, 3158],
  [4128, 4137, 4051, 3961, 3747, 3388, 3485, 3464, 3296, 3351], [3916, 4087, 4036, 3963, 3764, 3497, 3358, 3461, 3410, 3239],
  [3568, 3704, 3844, 3797, 3614, 3375, 3405, 3205, 3270, 3305], [3605, 3523, 3619, 3811, 3665, 3420, 3355, 3334, 3200, 3233],
  [3523, 3553, 3500, 3524, 3738, 3550, 3457, 3285, 3336, 3215], [3240, 3344, 3500, 3463, 3442, 3652, 3601, 3439, 3394, 3480],
  [3203, 3228, 3354, 3472, 3473, 3474, 3621, 3593, 3434, 3401], [3102, 3220, 3234, 3299, 3439, 3379, 3381, 3558, 3546, 3364],
  [3439, 3631, 3704, 3726, 3730, 3831, 3786, 3778, 4010, 3929]];
// Table 2.3: births to PPS residents, five-year totals (p. 9), placed at the middle year
const BIRTHS = { x: [2013, 2018, 2023], y: [26882 / 5, 22462 / 5, 18901 / 5] };
const births = y => { const { x, y: v } = BIRTHS; if (y <= x[0]) return v[0];
  for (let i = 1; i < x.length; i++) if (y <= x[i]) return v[i - 1] + (v[i] - v[i - 1]) * (y - x[i - 1]) / (x[i] - x[i - 1]);
  return v[2] + (v[2] - v[1]) / 5 * (y - x[2]); };   // past 2023: the 2018-2023 trend
const MED = JSON.parse(fs.readFileSync(path.join(ROOT, 'source', 'pps-forecast', 'table-5.2-medium.json'), 'utf8'));
const GR = ['K', ...Array.from({ length: 12 }, (_, i) => String(i + 1))];
const SIM_YEARS = Array.from({ length: 10 }, (_, i) => 2026 + i);              // fall 2026 ... fall 2035
const syLabel = y => `${y}-${String((y + 1) % 100).padStart(2, '0')}`;
const medAt = (g, y) => MED.grades[GR[g]][MED.years.indexOf(syLabel(y))];

// ---------- distributions from the history ----------
const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
const sd = a => { const m = mean(a); return Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / (a.length - 1)); };
const COVID = [2020, 2021];
const gprHist = g => H_YEARS.slice(1).map((y, i) => ({ y, v: H[g][i + 1] / H[g - 1][i] })).filter(o => !COVID.includes(o.y)).map(o => o.v);
const GPR = Array.from({ length: 13 }, (_, g) => {
  if (!g) return null;
  const h = gprHist(g), last3 = [7, 8, 9].map(i => H[g][i] / H[g - 1][i - 1]);
  const s = sd(h), gap = mean(h) - mean(last3);
  return { sdAnnual: s, sdLevel: Math.sqrt((s / Math.sqrt(h.length)) ** 2 + (gap / 2) ** 2), histMean: mean(h), last3: mean(last3) };
});
// cross-grade correlation of annual GPR deviations (non-COVID years)
const devs = Array.from({ length: 12 }, (_, i) => { const h = gprHist(i + 1), m = mean(h); return h.map(v => v - m); });
let cs = 0, cn = 0;
for (let a = 0; a < 12; a++) for (let b = a + 1; b < 12; b++) {
  const x = devs[a], y = devs[b], mx = mean(x), my = mean(y);
  const c = x.reduce((s, v, i) => s + (v - mx) * (y[i] - my), 0) / Math.sqrt(x.reduce((s, v) => s + (v - mx) ** 2, 0) * y.reduce((s, v) => s + (v - my) ** 2, 0));
  cs += c; cn++;
}
const RHO_COMMON = Math.max(0, cs / cn);
// kindergarten capture rate
const capHist = H_YEARS.map((y, i) => H[0][i] / births(y - 5));
const preCap = capHist.slice(0, 4), postCap = capHist.slice(6);
const CAP_2025 = capHist[9];
const capMed = y => medAt(0, y) / births(y - 5);                                   // PSU's implied capture
const CAP_MED = Object.fromEntries(SIM_YEARS.map(y => [y, y <= 2030 ? capMed(y) : capMed(2030)]));   // births past 2025 not known: hold PSU's 2030 capture
const CAP_LONG = CAP_MED[2030];
// PSU's pace of convergence: CAP_MED(y) - CAP_LONG ~ (CAP_2025 - CAP_LONG) x lambda^(y - 2025), least squares over 2026-29
let LAMBDA = 0.6, best = Infinity;
for (let l = 0.05; l < 0.99; l += 0.01) { const e = [2026, 2027, 2028, 2029].reduce((s, y) => s + (CAP_MED[y] - CAP_LONG - (CAP_2025 - CAP_LONG) * l ** (y - 2025)) ** 2, 0); if (e < best) { best = e; LAMBDA = l; } }
const logCh = capHist.slice(1).map((v, i) => Math.log(v / capHist[i])).filter((_, i) => !COVID.includes(H_YEARS[i + 1]) && H_YEARS[i + 1] !== 2022);   // 2022 = the post-COVID rebound
// x2 calibrated by the backtest (scripts/montecarlo_backtest.py --cap-scale 2: 90% ranges cover ~90-100% of past K and K-5 outcomes)
const CAP_NOISE = +arg('--cap-noise-scale', 2) * sd(logCh) / Math.SQRT2;            // relative sd of an annual capture level
// upside: above PSU by as much as PSU's long-run level sits above the pre-COVID average (or --cap-max)
const CAP_TRI = { a: Math.min(mean(postCap), CAP_LONG), m: CAP_LONG, b: +arg('--cap-max', 0) || Math.max(Math.max(...preCap), CAP_LONG + Math.abs(CAP_LONG - mean(preCap))) };
// school-level forecast error, PSU's post-COVID typical school miss by horizon (mean absolute % error -> sd x 1.25)
const TYP = D.fcacc?.dist?.typ?.post || {};
const schoolSD = h => { const m = TYP[h]?.[1] ?? TYP[4]?.[1] * Math.sqrt(h / 4); return 1.25 * m / 100; };

// ---------- random numbers ----------
let st = SEED >>> 0;
const rnd = () => { st = (st + 0x6D2B79F5) >>> 0; let t = st; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
let spare = null;
const nrm = () => { if (spare != null) { const s = spare; spare = null; return s; } let u, v, r; do { u = 2 * rnd() - 1; v = 2 * rnd() - 1; r = u * u + v * v; } while (!r || r >= 1); const f = Math.sqrt(-2 * Math.log(r) / r); spare = v * f; return u * f; };
const tri = ({ a, m, b }) => { const u = rnd(), c = (m - a) / (b - a); return u < c ? a + Math.sqrt(u * (b - a) * (m - a)) : b - Math.sqrt((1 - u) * (b - a) * (b - m)); };

// ---------- one simulated district path ----------
function drawDistrict(zero) {
  const L = zero ? CAP_LONG : tri(CAP_TRI);
  const capEps = SIM_YEARS.map(() => zero ? 0 : CAP_NOISE * nrm());
  const lvl = GPR.map(p => p && !zero ? p.sdLevel * nrm() : 0);
  const common = SIM_YEARS.map(() => zero ? 0 : nrm());
  const E = { 2025: H.map(r => r[9]) };
  const gprUsed = [];
  SIM_YEARS.forEach((y, j) => {
    const cap = CAP_MED[y] + (L - CAP_LONG) * (1 - LAMBDA ** (y - 2025));
    const row = [medAt(0, y) * cap / CAP_MED[y] * Math.exp(capEps[j])];
    for (let g = 1; g <= 12; g++) {
      const gm = medAt(g, y) / medAt(g - 1, y - 1);
      const e = zero ? 0 : GPR[g].sdAnnual * (Math.sqrt(RHO_COMMON) * common[j] + Math.sqrt(1 - RHO_COMMON) * nrm());
      const v = gm + lvl[g] + e; gprUsed.push(v - gm);
      row.push(E[y - 1][g - 1] * v);
    }
    E[y] = row;
  });
  const band = (y, a, b) => E[y].slice(a, b + 1).reduce((s, v) => s + v, 0);
  const medBand = (y, a, b) => GR.slice(a, b + 1).reduce((s, _, i) => s + medAt(a + i, y), 0);
  const ratio = {}, med = {};
  for (const y of [2025, ...SIM_YEARS]) ratio[syLabel(y)] = y === 2025 ? { k5: 1, m68: 1, h912: 1 }
    : { k5: band(y, 0, 5) / medBand(y, 0, 5), m68: band(y, 6, 8) / medBand(y, 6, 8), h912: band(y, 9, 12) / medBand(y, 9, 12) };
  for (const y of SIM_YEARS) med[syLabel(y)] = { k5: medBand(y, 0, 5), m68: medBand(y, 6, 8), h912: medBand(y, 9, 12) };
  const avg = a => a.reduce((s, v) => s + v, 0) / a.length;
  return { E, ratio, med, inputs: { capture_long_run: L, capture_noise_mean: avg(capEps),
    gpr_k5: avg(lvl.slice(1, 6)), gpr_68: avg(lvl.slice(6, 9)), gpr_912: avg(lvl.slice(9, 13)), gpr_common: avg(common) * GPR.slice(1).reduce((s, p) => s + p.sdAnnual, 0) / 12 * Math.sqrt(RHO_COMMON) } };
}

// ---------- apply to the explorer's schools and measure ----------
const BASE = JSON.parse(JSON.stringify(D.series)), BASE_K5 = { ...D.k5_share };
const keys = Object.keys(D.region_of), SCEN = ['SQ', 'A', 'B'], impl = D.years.indexOf(D.impl_year);
keys.forEach(k => T.staffGFRatio(k));                                               // freeze each school's General Fund ratio at the medium forecast
const OUT_YEARS = ['2027-28', '2031-32', '2035-36'];
// affordable-housing students by scenario, school and year (held fixed)
const AH = JSON.parse(fs.readFileSync(path.join(ROOT, 'source', 'pps-forecast', 'affordable-housing.json'), 'utf8'));
const HOUSE = {};
for (const s of SCEN) {
  HOUSE[s] = {};
  for (const [k, a] of Object.entries(AH.students_by_school)) a.forEach((v, yi) => {
    if (!v) return;
    const add = (t, x) => { (HOUSE[s][t] = HOUSE[s][t] || D.years.map(() => 0))[yi] += x; };
    if (BASE[s]?.[k]?.[yi] != null) return add(k, v);
    const rc = (D.flows[s]?.receivers || []).filter(r => r.from_key === k && BASE[s]?.[r.to_key]?.[yi] != null);
    const tot = rc.reduce((t, r) => t + (r.share ?? 1), 0);
    rc.forEach(r => add(r.to_key, v * (r.share ?? 1) / (tot || 1)));
  });
}
const houseOf = (s, k, yi, v) => Math.min(v, HOUSE[s]?.[k]?.[yi] || 0);
// district totals by band net of housing students (Status Quo), for the flexible part's ratio
const HBAND = D.years.map((y, yi) => { const b = { k5: 0, m68: 0, h912: 0 };
  for (const k of keys) { const h = HOUSE.SQ[k]?.[yi] || 0, t = D.types.SQ[k], f = T.k5Of(k, y) ?? 0.66;
    if (t === 'ES') b.k5 += h; else if (t === 'MS') b.m68 += h; else if (t === 'HS') b.h912 += h; else if (t === 'K8') { b.k5 += f * h; b.m68 += (1 - f) * h; } }
  return b; });
const typeOf = (s, k, yi) => (yi < impl ? D.types.SQ[k] : D.types[s]?.[k]) || D.types.SQ[k];
function applyPath(dp, schoolNoise) {
  // school noise: a random walk in log enrollment with PSU's typical school miss at each horizon
  const z = {};
  if (schoolNoise) for (const k of keys) { let acc = 0; z[k] = D.years.map((_, h) => { if (!h) return 0; const v = schoolSD(h) ** 2 - (h > 1 ? schoolSD(h - 1) ** 2 : 0); acc += Math.sqrt(Math.max(0, v)) * nrm(); return acc; }); }
  // the flexible part (everything but affordable-housing students) takes the district ratio, net of housing students
  const FLEX = {}, HS_ = {};
  for (const s of SCEN) { FLEX[s] = {}; HS_[s] = {}; for (const k of keys) {
    const b = BASE[s]?.[k]; if (!b) continue;
    HS_[s][k] = b.map((v, yi) => v == null ? null : houseOf(s, k, yi, v));
    FLEX[s][k] = b.map((v, yi) => {
      if (v == null) return v;
      const y = D.years[yi], r0 = dp.ratio[y] || { k5: 1, m68: 1, h912: 1 }, hb = HBAND[yi], md = dp.med[y];
      const r = md ? { k5: (r0.k5 * md.k5 - hb.k5) / (md.k5 - hb.k5), m68: (r0.m68 * md.m68 - hb.m68) / (md.m68 - hb.m68), h912: (r0.h912 * md.h912 - hb.h912) / (md.h912 - hb.h912) } : r0;
      const t = typeOf(s, k, yi), f = BASE_K5[y] != null ? (T.k5Of(k, y) ?? 0.66) : 0.66;
      const m = t === 'ES' ? r.k5 : t === 'MS' ? r.m68 : t === 'HS' ? r.h912 : f * r.k5 + (1 - f) * r.m68;
      return (v - HS_[s][k][yi]) * m * (schoolNoise ? Math.exp(z[k][yi]) : 1);
    });
  } }
  if (schoolNoise) {   // keep each band's flexible total at the district path: rescale the noisy schools (Status Quo totals; same factor for A and B)
    D.years.forEach((y, yi) => {
      for (const band of ['ES', 'MS', 'HS', 'K8']) {
        const ks = keys.filter(k => D.types.SQ[k] === band && FLEX.SQ[k]?.[yi] != null);
        const noisy = ks.reduce((t, k) => t + FLEX.SQ[k][yi], 0), clean = ks.reduce((t, k) => t + FLEX.SQ[k][yi] / Math.exp(z[k][yi]), 0);
        const c = noisy ? clean / noisy : 1;
        for (const s of SCEN) for (const k of keys) if (D.types.SQ[k] === band && FLEX[s]?.[k]?.[yi] != null) FLEX[s][k][yi] *= c;
      }
    });
  }
  for (const s of SCEN) for (const k of keys) if (FLEX[s][k]) D.series[s][k] = FLEX[s][k].map((v, yi) => v == null ? v : v + HS_[s][k][yi]);
  for (const y of Object.keys(dp.ratio)) if (BASE_K5[y] != null) { const r = dp.ratio[y], d = BASE_K5[y]; D.k5_share[y] = d * r.k5 / (d * r.k5 + (1 - d) * r.m68); }
}
function measure() {
  const o = {};
  for (const y of OUT_YEARS) {
    const yi = D.years.indexOf(y);
    for (const s of SCEN) {
      const a = T.staffAgg(keys, s, yi), open = keys.filter(k => D.series[s]?.[k]?.[yi] != null);
      const above = open.filter(k => D.series[s][k][yi] >= (D.thresholds[typeOf(s, k, yi)] ?? 0) - 1e-9);
      const stu = open.reduce((t, k) => t + D.series[s][k][yi], 0), stuAbove = above.reduce((t, k) => t + D.series[s][k][yi], 0);
      o[`${y}|${s}|students`] = stu;
      o[`${y}|${s}|fte`] = a.total;
      o[`${y}|${s}|cost`] = T.staffCost(a);
      o[`${y}|${s}|gf`] = T.staffGF(keys, s, yi);
      o[`${y}|${s}|below`] = open.length - above.length;
      o[`${y}|${s}|enrollset`] = keys.map(k => D.series[s]?.[k]?.[yi] ?? null);
      if (EXPORT) { const ab = new Set(above); o[`${y}|${s}|belowset`] = keys.map(k => D.series[s]?.[k]?.[yi] != null && !ab.has(k) ? 1 : 0); }
      o[`${y}|${s}|schools_above_pct`] = 100 * above.length / open.length;
      o[`${y}|${s}|students_above_pct`] = 100 * stuAbove / stu;
    }
    for (const s of ['A', 'B']) for (const m of ['fte', 'cost', 'gf']) o[`${y}|${s}|${m}_saved`] = o[`${y}|SQ|${m}`] - o[`${y}|${s}|${m}`];
  }
  return o;
}
function restore() { for (const s of SCEN) for (const k of keys) if (BASE[s]?.[k]) D.series[s][k] = BASE[s][k].slice(); Object.assign(D.k5_share, BASE_K5); }

// ---------- run ----------
const t0 = Date.now();
const baseOut = (() => { const dp = drawDistrict(true); applyPath(dp, false); const o = measure(); restore(); return o; })();
const pageOut = measure();
const runs = {};
for (const variant of ['district', 'school']) {
  runs[variant] = [];
  for (let i = 0; i < N; i++) {
    const dp = drawDistrict(false); applyPath(dp, variant === 'school');
    const bands = [2025, ...SIM_YEARS].map(y => { const e = dp.E[y]; const sm = (a, b) => Math.round(e.slice(a, b + 1).reduce((t, v) => t + v, 0)); return [sm(0, 0), sm(0, 5), sm(6, 8), sm(9, 12)]; });
    runs[variant].push({ bands, inputs: dp.inputs, k12: Object.fromEntries(OUT_YEARS.map(y => { const yr = +y.slice(0, 4); return [y, dp.E[yr].reduce((s, v) => s + v, 0)]; })), out: measure() });
    restore();
  }
}

// ---------- summarize ----------
const q = (a, p) => { const s = [...a].sort((x, y) => x - y), i = (s.length - 1) * p, lo = Math.floor(i); return s[lo] + (s[Math.min(lo + 1, s.length - 1)] - s[lo]) * (i - lo); };
const stats = a => ({ mean: mean(a), sd: sd(a), p5: q(a, 0.05), p50: q(a, 0.5), p95: q(a, 0.95) });
const rank = a => { const idx = a.map((v, i) => [v, i]).sort((x, y) => x[0] - y[0]), r = new Array(a.length); idx.forEach(([, i], j) => { r[i] = j; }); return r; };
const corr = (x, y) => { const mx = mean(x), my = mean(y); let n = 0, dx = 0, dy = 0; for (let i = 0; i < x.length; i++) { n += (x[i] - mx) * (y[i] - my); dx += (x[i] - mx) ** 2; dy += (y[i] - my) ** 2; } return dx && dy ? n / Math.sqrt(dx * dy) : 0; };
function src(X, y) {   // standardized regression coefficients by least squares (normal equations), and R^2
  const p = X[0].length, n = y.length, mx = Array.from({ length: p }, (_, j) => mean(X.map(r => r[j]))), sx = Array.from({ length: p }, (_, j) => sd(X.map(r => r[j])) || 1);
  const my = mean(y), sy = sd(y) || 1, Z = X.map(r => r.map((v, j) => (v - mx[j]) / sx[j])), w = y.map(v => (v - my) / sy);
  const A = Array.from({ length: p }, (_, i) => Array.from({ length: p }, (_, j) => Z.reduce((s, r) => s + r[i] * r[j], 0)));
  const b = Array.from({ length: p }, (_, i) => Z.reduce((s, r, k) => s + r[i] * w[k], 0));
  for (let i = 0; i < p; i++) { let m = i; for (let r = i + 1; r < p; r++) if (Math.abs(A[r][i]) > Math.abs(A[m][i])) m = r; [A[i], A[m]] = [A[m], A[i]]; [b[i], b[m]] = [b[m], b[i]];
    for (let r = 0; r < p; r++) if (r !== i && A[i][i]) { const f = A[r][i] / A[i][i]; for (let c = i; c < p; c++) A[r][c] -= f * A[i][c]; b[r] -= f * b[i]; } }
  const beta = b.map((v, i) => A[i][i] ? v / A[i][i] : 0), fit = Z.map(r => r.reduce((s, v, j) => s + v * beta[j], 0));
  return { beta, r2: 1 - w.reduce((s, v, i) => s + (v - fit[i]) ** 2, 0) / w.reduce((s, v) => s + v * v, 0) };
}
const INPUTS = ['capture_long_run', 'capture_noise_mean', 'gpr_k5', 'gpr_68', 'gpr_912', 'gpr_common'];
const metrics = Object.keys(baseOut).filter(m => !m.endsWith('belowset') && !m.endsWith('enrollset'));
const summary = { generated: new Date().toISOString(), n: N, seed: SEED, runtime_s: (Date.now() - t0) / 1000,
  parameters: { capture: { history: Object.fromEntries(H_YEARS.map((y, i) => [y, +capHist[i].toFixed(4)])), pre_covid_mean: mean(preCap), post_covid_mean: mean(postCap),
      fall_2025: CAP_2025, psu_path: CAP_MED, psu_long_run: CAP_LONG, convergence_lambda: LAMBDA, long_run_triangular: CAP_TRI, annual_relative_sd: CAP_NOISE },
    gpr: Object.fromEntries(GPR.slice(1).map((p, i) => [`grade ${i + 1}`, { hist_mean: p.histMean, last3_mean: p.last3, sd_annual: p.sdAnnual, sd_level: p.sdLevel }])), gpr_cross_grade_corr: RHO_COMMON,
    school_error_sd_by_horizon: Object.fromEntries(D.years.slice(1).map((y, h) => [y, schoolSD(h + 1)])) },
  check_medium_vs_page: Object.fromEntries(metrics.filter(m => /cost|below|students\b/.test(m)).map(m => [m, [baseOut[m], pageOut[m]]])),
  medium: baseOut, variants: {} };
// projected enrollment by school: medium (page) value and simulated percentiles, by variant, scenario and year
summary.school_enrollment = {};
for (const [v, R] of Object.entries(runs)) {
  summary.school_enrollment[v] = {};
  for (const y of OUT_YEARS) for (const s of SCEN) {
    const base = baseOut[`${y}|${s}|enrollset`];
    summary.school_enrollment[v][`${y}|${s}`] = Object.fromEntries(keys.map((k, ki) => {
      if (base[ki] == null) return [k, null];
      const a = R.map(r => r.out[`${y}|${s}|enrollset`][ki]); const st = stats(a);
      return [k, { medium: Math.round(base[ki]), p5: Math.round(st.p5), p25: Math.round(q(a, 0.25)), p50: Math.round(st.p50), p75: Math.round(q(a, 0.75)), p95: Math.round(st.p95) }];
    }));
  }
}
for (const [v, R] of Object.entries(runs)) {
  const X = R.map(r => INPUTS.map(k => r.inputs[k]));
  summary.variants[v] = { k12: Object.fromEntries(OUT_YEARS.map(y => [y, stats(R.map(r => r.k12[y]))])), metrics: {} };
  for (const m of metrics) {
    const y = R.map(r => r.out[m]), s = stats(y), fit = src(X, y);
    summary.variants[v].metrics[m] = { ...s, medium: baseOut[m], r2: fit.r2,
      src: Object.fromEntries(INPUTS.map((k, j) => [k, fit.beta[j]])), spearman: Object.fromEntries(INPUTS.map((k, j) => [k, corr(rank(X.map(r => r[j])), rank(y))])) };
  }
}
const OUT = path.join(ROOT, 'source', 'montecarlo'); fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'mc-school-enrollment.csv'), ['variant,year,scenario,school,medium,p5,p25,p50,p75,p95', ...Object.entries(summary.school_enrollment).flatMap(([v, S]) =>
  Object.entries(S).flatMap(([ys, sch]) => Object.entries(sch).filter(([, x]) => x).map(([k, x]) => [v, ...ys.split('|'), `"${k}"`, x.medium, x.p5, x.p25, x.p50, x.p75, x.p95].join(','))))].join('\n'));
fs.writeFileSync(path.join(OUT, 'mc-summary.json'), JSON.stringify(summary, null, 1));
const cols = ['variant', 'sim', ...INPUTS, ...OUT_YEARS.map(y => `k12|${y}`), ...metrics];
fs.writeFileSync(path.join(OUT, 'mc-draws.csv'), [cols.join(','), ...Object.entries(runs).flatMap(([v, R]) => R.map((r, i) =>
  [v, i, ...INPUTS.map(k => r.inputs[k].toFixed(5)), ...OUT_YEARS.map(y => r.k12[y].toFixed(1)), ...metrics.map(m => (+r.out[m].toFixed(3)))].join(',')))].join('\n'));

// ---------- report ----------
const M = v => '$' + (v / 1e6).toFixed(1) + 'M', f1 = v => v.toFixed(1), pct = v => v.toFixed(1) + '%';
const FMT = { students: v => Math.round(v).toLocaleString(), fte: f1, cost: M, gf: M, below: f1, schools_above_pct: pct, students_above_pct: pct, fte_saved: f1, cost_saved: M, gf_saved: M };
console.log(`Monte Carlo: ${N} simulations per variant, seed ${SEED}, ${summary.runtime_s.toFixed(1)} s`);
console.log(`Capture rate: fall 2025 ${CAP_2025.toFixed(3)}; PSU long-run ${CAP_LONG.toFixed(3)} (pace ${LAMBDA.toFixed(2)}/yr); long-run draw triangular(${CAP_TRI.a.toFixed(3)}, ${CAP_TRI.m.toFixed(3)}, ${CAP_TRI.b.toFixed(3)}); annual noise ${(100 * CAP_NOISE).toFixed(1)}%`);
console.log(`GPR: annual sd by grade ${GPR.slice(1).map(p => (100 * p.sdAnnual).toFixed(1)).join(' ')} (%); level sd ${GPR.slice(1).map(p => (100 * p.sdLevel).toFixed(1)).join(' ')}; cross-grade corr ${RHO_COMMON.toFixed(2)}`);
const chk = Object.entries(summary.check_medium_vs_page).filter(([, [a, b]]) => Math.abs(a - b) > 1e-6 * Math.max(1, Math.abs(b)));
console.log(`Affordable housing (held fixed): ${OUT_YEARS.map(y => { const yi = D.years.indexOf(y); return `${y} ${Math.round(Object.values(HOUSE.SQ).reduce((t, a) => t + a[yi], 0))}`; }).join(', ')} students (Status Quo)`);
console.log(chk.length ? `WARNING medium path differs from the page on ${chk.length} metrics` : 'Check: zero-shock path reproduces the page (medium forecast) exactly');
for (const [v, S] of Object.entries(summary.variants)) {
  console.log(`\n=== ${v === 'district' ? 'District uncertainty: kindergarten capture + grade progression' : 'Plus school-level forecast error'} ===`);
  console.log('K-12 (district, PSU grades) ' + OUT_YEARS.map(y => `${y}: ${Math.round(S.k12[y].p50).toLocaleString()} [${Math.round(S.k12[y].p5).toLocaleString()}-${Math.round(S.k12[y].p95).toLocaleString()}]`).join('  '));
  for (const y of OUT_YEARS) {
    console.log(`-- ${y}   metric: medium | median [5%-95%]   main drivers (share of variance)`);
    for (const m of ['SQ|students', 'SQ|cost', 'SQ|gf', 'A|cost_saved', 'B|cost_saved', 'A|gf_saved', 'B|gf_saved', 'A|fte_saved', 'SQ|below', 'A|below', 'B|below', 'SQ|students_above_pct', 'A|students_above_pct', 'B|students_above_pct']) {
      const x = S.metrics[`${y}|${m}`], fm = FMT[m.split('|')[1]];
      const drv = Object.entries(x.src).map(([k, b]) => [k, b * b]).sort((a, b) => b[1] - a[1]).filter(([, w]) => w >= 0.05).map(([k, w]) => `${k} ${Math.round(100 * w)}%`).join(', ');
      console.log(`   ${m.padEnd(24)} ${fm(x.medium).padStart(9)} | ${fm(x.p50).padStart(9)} [${fm(x.p5)} - ${fm(x.p95)}]   ${drv || '-'}${x.r2 < 0.5 ? ` (inputs explain ${Math.round(100 * x.r2)}%)` : ''}`);
    }
  }
}
if (EXPORT) {
  const MK = OUT_YEARS.flatMap(y => [...SCEN.flatMap(s => ['students', 'cost', 'gf', 'fte', 'below', 'students_above_pct'].map(m => `${y}|${s}|${m}`)), ...['A', 'B'].flatMap(s => ['cost_saved', 'gf_saved', 'fte_saved'].map(m => `${y}|${s}|${m}`))]);
  const enc = (m, v) => /cost|gf/.test(m) ? Math.round(v / 1000) : /pct/.test(m) ? Math.round(v * 10) : Math.round(v * 10) / 10;   // $k, tenths of a percent
  const zero = drawDistrict(true);
  const bandsOf = e => { const sm = (a, b) => Math.round(e.slice(a, b + 1).reduce((t, v) => t + v, 0)); return [sm(0, 0), sm(0, 5), sm(6, 8), sm(9, 12)]; };
  const pack = bits => { const b = Buffer.alloc(Math.ceil(bits.length / 8)); bits.forEach((v, i) => { if (v) b[i >> 3] |= 1 << (i & 7); }); return b.toString('base64'); };
  const combos = OUT_YEARS.flatMap(y => SCEN.map(s => `${y}|${s}`));
  const E = { generated: summary.generated, n: N, seed: SEED, years: D.years, out_years: OUT_YEARS, scen: SCEN, schools: keys, combos, metric_keys: MK,
    units: 'cost, gf: $ thousands; *_pct: tenths of a percent', medium: Object.fromEntries(MK.map(m => [m, enc(m, baseOut[m])])),
    medium_bands: [2025, ...SIM_YEARS].map(y => bandsOf(zero.E[y])),
    params: { capture: { fall_2025: CAP_2025, psu_long_run: CAP_LONG, tri: CAP_TRI, annual_sd: CAP_NOISE, pre_covid_mean: mean(preCap), post_covid_mean: mean(postCap) },
      housing: OUT_YEARS.map(y => Math.round(Object.values(HOUSE.SQ).reduce((t, a) => t + a[D.years.indexOf(y)], 0))) },
    house: Object.fromEntries(SCEN.map(s => [s, Object.fromEntries(keys.filter(k => HOUSE[s][k]).map(k => [k, OUT_YEARS.map(y => Math.round(HOUSE[s][k][D.years.indexOf(y)] * 10) / 10)]))])),
    hband: OUT_YEARS.map(y => { const b = HBAND[D.years.indexOf(y)]; return [b.k5, b.m68, b.h912].map(v => Math.round(v * 10) / 10); }),
    school_sd: OUT_YEARS.map(y => Math.round(schoolSD(D.years.indexOf(y)) * 1e4) / 1e4),
    // every year 2025-26 .. 2035-36, for the per-school fan charts
    house_all: Object.fromEntries(SCEN.map(s => [s, Object.fromEntries(keys.filter(k => HOUSE[s][k]).map(k => [k, HOUSE[s][k].map(v => Math.round(v * 10) / 10)]))])),
    hband_all: D.years.map((y, yi) => { const b = HBAND[yi]; return [b.k5, b.m68, b.h912].map(v => Math.round(v * 10) / 10); }),
    school_sd_all: D.years.map((y, yi) => yi ? Math.round(schoolSD(yi) * 1e4) / 1e4 : 0),
    variants: {} };
  for (const [v, R] of Object.entries(runs)) E.variants[v] = {
    cap: R.map(r => Math.round(r.inputs.capture_long_run * 1e4) / 1e4),
    bands: v === 'district' ? R.map(r => r.bands) : undefined,
    m: R.map(r => MK.map(m => enc(m, r.out[m]))),
    below: R.map(r => pack(combos.flatMap(c => r.out[`${c}|belowset`]))),
    drivers: Object.fromEntries(MK.map(m => [m, Object.fromEntries(Object.entries(summary.variants[v].metrics[m].src).map(([k, b]) => [k, Math.round(b * b * 100)]))])) };
  fs.writeFileSync(path.join(OUT, 'mc-embed.json'), JSON.stringify(E));
  console.log(`Wrote mc-embed.json (${(fs.statSync(path.join(OUT, 'mc-embed.json')).size / 1e6).toFixed(2)} MB)`);
}
console.log(`\nWrote ${path.relative(ROOT, path.join(OUT, 'mc-summary.json'))} and mc-draws.csv`);
