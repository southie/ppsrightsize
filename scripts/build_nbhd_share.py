"""Share of each school's students who are neighborhood residents (PPS group "Residents Attending Neighborhood Program"),
by grade band, for the bus cost: only neighborhood students ride the general (neighborhood) yellow-bus routes;
immersion, transfer and special-program students do not (immersion routes are costed separately, transfers are not
bused). Output: source/pps-powerbi/neighborhood-share.json
  SQ: {school: {k5: [share by page year], 68: [...]}} from PPS's projections by school, grade, group and year
      (projections (2) table, 2025-26 .. 2035-36).
  A, B (PPS runs Seventy Percent, Fifty Percent): {school: {k5: share, 68: share}} from PPS's 2027-28 results after the
      changes (2027 Summary table, modeled counts), used from the year the changes take effect.
  Bands: K-5 = grades K-5, 68 = grades 6-8. A school with no students in a band has no entry for it.
"""
import json, os, re, sys, unicodedata, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TB = os.path.join(ROOT, 'source', 'pps-powerbi', 'tables')
html = open(os.path.join(ROOT, 'rightsizing-scenario-explorer.html'), encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
L = lambda t: (lambda d: [dict(zip(d['cols'], r)) for r in d['rows']])(json.load(open(os.path.join(TB, t + '.json'), encoding='utf-8')))
norm = lambda s: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
OURS = {norm(k): k for k in D['region_of']}
ALIAS = {'Brentwood': 'Lane', 'Sunrise': 'Lee'}
key = lambda s: ALIAS.get(s) or OURS.get(norm(s or ''))
num = lambda v: float(v) if v not in (None, '') else 0.0
band = lambda g: 'k5' if int(g) <= 5 else '68' if int(g) <= 8 else None
RES = 'Residents Attending Neighborhood Program'
YEARS = [int(y[:4]) for y in D['years']]

out = {'source': "PPS Rightsizing Scenarios Schools dashboard (Power BI, version 1.0, October 14, 2026): projections by school, grade and student group; 2027-28 results after changes",
       'years': D['years'], 'SQ': {}, 'A': {}, 'B': {}}
# Status Quo, by year
tot, res = collections.defaultdict(float), collections.defaultdict(float)
for r in L('projections (2)'):
    k, b, y = key(r['school']), band(r['grade']), int(r['year'])
    if not k or not b or y not in YEARS: continue
    n = num(r['count']); tot[(k, b, y)] += n
    if r['group'] == RES: res[(k, b, y)] += n
for (k, b, y), n in tot.items():
    if n <= 0: continue
    out['SQ'].setdefault(k, {}).setdefault(b, [None] * len(YEARS))[YEARS.index(y)] = round(res[(k, b, y)] / n, 4)
# scenarios, 2027-28 after the changes
for sc, run in (('A', 'Seventy Percent'), ('B', 'Fifty Percent')):
    tot, res = collections.defaultdict(float), collections.defaultdict(float)
    for r in L('2027 Summary'):
        if r['eval_scenario'] != run: continue
        k, b = key(r['school']), band(r['grade'])
        if not k or not b: continue
        n = num(r['Modeled']); tot[(k, b)] += n
        if r['group'] == RES: res[(k, b)] += n
    for (k, b), n in tot.items():
        if n > 0: out[sc].setdefault(k, {})[b] = round(res[(k, b)] / n, 4)
json.dump(out, open(os.path.join(ROOT, 'source', 'pps-powerbi', 'neighborhood-share.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
yi = D['years'].index('2027-28')
def dist(d, sc):
    t = n = 0
    for k, bs in d.items():
        for b, v in bs.items():
            s = v[yi] if isinstance(v, list) else v
            if s is None: continue
            e = D['series']['SQ' if sc == 'SQ' else sc][k][yi] if k in D['series']['SQ'] else None
            if not e: continue
            t += e; n += e * s
    return round(100 * n / t) if t else None
print('schools: SQ', len(out['SQ']), 'A', len(out['A']), 'B', len(out['B']))
print('enrollment-weighted neighborhood share, K-8, 2027-28: SQ', dist(out['SQ'], 'SQ'), '% | A', dist(out['A'], 'A'), '% | B', dist(out['B'], 'B'), '%')
print('examples SQ 2027:', {k: {b: v[yi] for b, v in out['SQ'][k].items()} for k in ('César Chávez', 'Lent', 'Rigler', 'Beach', 'Creston') if k in out['SQ']})
print('examples A:', {k: out['A'].get(k) for k in ('César Chávez', 'Lent', 'Rigler', 'Rosa Parks')})
