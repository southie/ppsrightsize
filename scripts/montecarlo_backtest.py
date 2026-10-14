"""Backtest of the Monte Carlo enrollment model (scripts/montecarlo_enrollment.js) against actual PPS enrollment.
For each base fall b (2009-2024), the district grade model is fitted only to data available then (enrollment by grade
since fall 2004, births) and simulated 1-5 years ahead with the same structure as the explorer simulation:
  Kindergarten = births five years earlier x capture rate. Capture point path converges from the base-year rate to the
  mean of the last 10 non-COVID years (PSU: "gradual convergence toward the pre-COVID 10-year average") at the main
  model's pace; the long-run level is triangular around that target, half-width = the larger of its gap to the recent
  3-year mean and 1.645 x the annual noise; plus annual noise (sd of year-to-year log changes, COVID years removed).
  Grades 1-12: GPR = mean of the last 3 non-COVID years (PSU: district GPRs use prior 3-year averages) + a persistent
  offset per grade (sd from the standard error of the historical mean and half the gap between the long-run and 3-year
  means) + annual noise (historical sd), with a common factor at the historical cross-grade correlation.
Births are taken as known (PSU uses actual and preliminary births for the first years of a forecast); 2022-2025 births
are the ZIP-based estimates (source/demographics/pps-births-by-year.json).
Scores, by horizon and period (pre-COVID targets through fall 2019, COVID-affected targets fall 2020-2021, post-COVID
bases 2022-2024): error of the median forecast, coverage of the 50% and 90% ranges, and the percentile rank of the
actual (should be spread evenly 0-100 if the ranges are right); compared with PSU's own forecast errors (D.fcacc).
Output: source/montecarlo/backtest.json
"""
import json, os, re, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 2000
rng = np.random.default_rng(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1)
HG = json.load(open(os.path.join(ROOT, 'source', 'pps-forecast', 'historic-grades.json')))
FALLS = HG['falls']; GR = ['K'] + [str(i) for i in range(1, 13)]
E = {f: np.array([HG['grades'][g][i] for g in GR], float) for i, f in enumerate(FALLS)}
BJ = json.load(open(os.path.join(ROOT, 'source', 'demographics', 'pps-births-by-year.json')))
BIRTHS = {int(y): v for y, v in BJ['estimate'].items()}; BIRTHS.update({int(y): v for y, v in BJ['psu_annual_births'].items()})
CAP_SCALE = float(sys.argv[sys.argv.index('--cap-scale') + 1]) if '--cap-scale' in sys.argv else 1.0   # widen capture uncertainty
COVID = {2020, 2021}                    # fall enrollment years affected
LAMBDA = 0.39                           # capture convergence pace (fitted to PSU's 2026-27 path in the main model)
html = open(os.path.join(ROOT, 'rightsizing-scenario-explorer.html'), encoding='utf-8').read()
FC = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))['fcacc']['dist']['tot']

def fit(b):
    """Parameters from data available at base fall b."""
    tr = [f for f in FALLS if FALLS[0] < f <= b and f not in COVID]               # transitions into fall f
    G = np.array([E[f][1:] / E[f - 1][:-1] for f in tr])                           # (years, 12)
    last3 = G[-3:].mean(0); mean_ = G.mean(0); sd = G.std(0, ddof=1)
    lvl = np.sqrt((sd / np.sqrt(len(G))) ** 2 + ((mean_ - last3) / 2) ** 2)
    dev = G - mean_; C = np.corrcoef(dev.T); rho = max(0.0, (C.sum() - 12) / 132) if len(G) > 3 else 0.0
    caps = {f: E[f][0] / BIRTHS[f - 5] for f in FALLS if f <= b}
    ok = [f for f in caps if f not in COVID]
    target = np.mean([caps[f] for f in ok[-10:]]); recent = np.mean([caps[f] for f in ok[-3:]])
    lc = [np.log(caps[f] / caps[f - 1]) for f in ok if f - 1 in caps and f - 1 not in COVID and f != 2022]
    noise = np.std(lc, ddof=1) / np.sqrt(2) if len(lc) > 2 else 0.02
    half = CAP_SCALE * max(abs(target - recent), 1.645 * noise * target); noise = CAP_SCALE * noise
    return dict(gpr=last3, sd=sd, lvl=lvl, rho=rho, cap0=caps[b], target=target, half=half, noise=noise)

def simulate(b, H, p, zero=False):
    n = 1 if zero else N
    L = np.full(n, p['target']) if zero else rng.triangular(p['target'] - p['half'], p['target'], p['target'] + p['half'], n)
    off = np.zeros((n, 12)) if zero else rng.standard_normal((n, 12)) * p['lvl']
    cur = np.tile(E[b], (n, 1)); out = {}
    for h in range(1, H + 1):
        f = b + h
        capm = p['target'] + (p['cap0'] - p['target']) * LAMBDA ** h                  # point path
        cap = capm + (L - p['target']) * (1 - LAMBDA ** h)
        if not zero: cap = cap * np.exp(p['noise'] * rng.standard_normal(n))
        k = BIRTHS[f - 5] * cap
        if zero: e = np.zeros((n, 12))
        else:
            c = rng.standard_normal((n, 1)); e = p['sd'] * (np.sqrt(p['rho']) * c + np.sqrt(1 - p['rho']) * rng.standard_normal((n, 12)))
        g = p['gpr'] + off + e
        cur = np.column_stack([k, cur[:, :-1] * g]); out[f] = cur.copy()
    return out

BANDS = {'K-12': slice(0, 13), 'K': slice(0, 1), 'K-5': slice(0, 6), '6-8': slice(6, 9), '9-12': slice(9, 13)}
T44 = {2013: {2012: -0.3}, 2014: {2012: -0.2, 2013: -0.1}, 2015: {2012: -0.2, 2013: -0.4, 2014: -0.5}, 2016: {2012: 1.3, 2013: 1.4, 2014: 1.2, 2015: 1.3},
       2017: {2012: 1.7, 2013: 2.0, 2014: 1.8, 2015: 2.0, 2016: 0.9}, 2018: {2012: 2.5, 2013: 3.1, 2014: 2.9, 2015: 3.1, 2016: 1.8, 2017: 1.3},
       2019: {2012: 3.6, 2013: 4.2, 2014: 4.0, 2015: 4.2, 2016: 2.9, 2017: 2.4, 2018: 1.1}}
PSU_PRE = {h: float(np.mean([abs(v) for f, row in T44.items() for b, v in row.items() if f - b == h])) for h in range(1, 6)}
rec = []
for b in range(2009, 2025):
    p = fit(b); H = min(5, 2025 - b)
    sims, point = simulate(b, H, p), simulate(b, H, p, zero=True)
    for h in range(1, H + 1):
        f = b + h
        period = 'post-COVID' if b >= 2022 else 'pre-COVID' if f <= 2019 else 'COVID-affected'
        for band, sl in BANDS.items():
            s = sims[f][:, sl].sum(1); act = E[f][sl].sum(); pt = point[f][0, sl].sum()
            q = np.percentile(s, [5, 25, 50, 75, 95])
            rec.append(dict(base=b, fall=f, h=h, period=period, band=band, actual=act, point=pt, p5=q[0], p25=q[1], p50=q[2], p75=q[3], p95=q[4],
                            pit=float((s < act).mean() * 100), err_pct=float((q[2] - act) / act * 100), point_err_pct=float((pt - act) / act * 100)))

def summ(rs):
    if not rs: return None
    return dict(n=len(rs), mape=float(np.mean([abs(r['err_pct']) for r in rs])), bias=float(np.mean([r['err_pct'] for r in rs])),
                in50=float(np.mean([r['p25'] <= r['actual'] <= r['p75'] for r in rs]) * 100), in90=float(np.mean([r['p5'] <= r['actual'] <= r['p95'] for r in rs]) * 100),
                width90=float(np.mean([(r['p95'] - r['p5']) / r['actual'] * 100 for r in rs])))
res = {}
for period in ['pre-COVID', 'COVID-affected', 'post-COVID']:
    for band in BANDS:
        for h in range(1, 6):
            s = summ([r for r in rec if r['period'] == period and r['band'] == band and r['h'] == h])
            if s: res[f'{period}|{band}|{h}'] = s
pits = {period: np.histogram([r['pit'] for r in rec if r['period'] == period and r['band'] != 'K-12'], bins=[0, 20, 40, 60, 80, 100])[0].tolist() for period in ['pre-COVID', 'post-COVID']}
os.makedirs(os.path.join(ROOT, 'source', 'montecarlo'), exist_ok=True)
json.dump(dict(cap_scale=CAP_SCALE, psu_pre_covid_k12_table44=PSU_PRE, n=N, records=rec, summary=res, pit_hist_quintiles=pits, psu_district_error=FC), open(os.path.join(ROOT, 'source', 'montecarlo', 'backtest.json'), 'w'), indent=1)

print(f'Backtest: bases fall 2009-2024, {N} simulations each; history from fall 2004; capture uncertainty x{CAP_SCALE}')
print('PSU pre-COVID K-12 error: Table 4.4 (editions 2012-13 to 2018-19, targets through fall 2019); post-COVID: D.fcacc')
for period, psu in [('pre-COVID', 'pre'), ('post-COVID', 'post'), ('COVID-affected', None)]:
    print(f'\n=== {period} ' + {'pre-COVID': '(targets through fall 2019)', 'post-COVID': '(bases fall 2022-2024)', 'COVID-affected': '(targets fall 2020-2022 from pre-2020 bases)'}[period])
    print('  band   h   n | model median error (abs / bias) | PSU abs err | in 50% / 90% range | 90% width')
    for band in BANDS:
        for h in range(1, 6):
            s = res.get(f'{period}|{band}|{h}')
            if not s: continue
            pe = ([0, PSU_PRE[h]] if psu == 'pre' else FC.get(psu, {}).get(str(h))) if psu and band == 'K-12' else None
            print(f"  {band:5s} {h}  {s['n']:3d} |  {s['mape']:5.2f}% / {s['bias']:+5.2f}%{'':10s}| {(f'{pe[1]:.1f}%' if pe else '-'):>6s}      |  {s['in50']:4.0f}% / {s['in90']:4.0f}%     | ±{s['width90'] / 2:.1f}%")
print('\nPercentile rank of actuals (by quintile, all bands but K-12; even = well calibrated):', pits)
print('Wrote source/montecarlo/backtest.json')
