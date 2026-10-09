"""Getting to school for the areas a scenario takes away from a school: for every school a scenario closes (and every
grade band a school stops serving, such as a K-8's 6-8 when it becomes K-5), the census blocks of its Status Quo
attendance area grouped by the school each block is assigned to under the scenario, with that group's travel to its
new school. Built from the per-block results of scripts/build_block_access.py (source/block-access/block-access.csv:
block residents of the band's ages and the block's mean walking distance, walk / bike / drive minutes and share beyond
bus distance), so histograms bin block averages rather than every grid point.
Layout per group, as the explorer's per-area arrays (D.commute.X): residents, beyond share, mean walk mi, mean walk /
bike / drive min, within 15 min walk / bike / drive, nearest share, walk / bike / drive histogram (D.commute.hist_min
bins), walking miles beyond bus distance, bus-eligible residents by walking miles (D.commute.bh_mi bins).
Output: source/block-access/closure-access.json  {scenario: {school: {band: {new school: array}}}}
"""
import csv, json, os, re, sys
from collections import defaultdict
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
HIST, BH = D['commute']['hist_min'], D['commute']['bh_mi']
BANDS_OF = {'ES': {'k5'}, 'K8': {'k5', '68'}, 'MS': {'68'}, 'HS': {'912'}}

rows = defaultdict(dict)   # (geoid, band) -> {scenario: row}
for r in csv.DictReader(open(os.path.join(ROOT, 'source', 'block-access', 'block-access.csv'), encoding='utf-8')):
    rows[r['GEOID'], r['band']][r['scenario']] = r

def vec(g):
    w = np.array([float(r['band_age_residents'] or 0) for r in g]); W = w.sum()
    if W <= 0: return None
    f = lambda c: np.array([float(r[c] or 0) for r in g])
    wm, wn, bn, dn, be = f('walk_mi'), f('walk_min'), f('bike_min'), f('drive_min'), f('beyond_bus_distance_share')
    near = np.array([r['nearest_school'] == r['school'] for r in g], float)
    hist = lambda t: [int(round(x)) for x in np.bincount(np.searchsorted(HIST, t, 'right'), w, len(HIST) + 1)]
    return [round(W), round(float((w * be).sum() / W), 3), round(float((w * wm).sum() / W), 2),
            *[round(float((w * t).sum() / W), 1) for t in (wn, bn, dn)], *[round(float(w[t <= 15].sum() / W), 3) for t in (wn, bn, dn)],
            round(float((w * near).sum() / W), 3), hist(wn), hist(bn), hist(dn),
            round(float((w * be * wm).sum())),
            [round(float(x), 1) for x in np.bincount(np.searchsorted(BH, wm, 'right'), w * be, len(BH) + 1)]]

out = {}
for sc in ('A', 'B'):
    lost = {(k, b) for k, d in D['detail'][sc].items() for b in BANDS_OF.get(D['types']['SQ'].get(k), ())
            if d.get('closed') or b not in BANDS_OF.get(D['types'][sc].get(k) or D['types']['SQ'].get(k), set())}
    grp = defaultdict(list)
    for (gid, b), v in rows.items():
        if 'SQ' in v and sc in v and (v['SQ']['school'], b) in lost:
            grp[v['SQ']['school'], b, v[sc]['school']].append(v[sc])
    for (k, b, t), g in sorted(grp.items()):
        x = vec(g)
        if x: out.setdefault(sc, {}).setdefault(k, {}).setdefault(b, {})[t] = x
    print(sc, len({k for k, b in lost}), 'schools lose an area;', sum(len(v) for v in out.get(sc, {}).values()), 'school-bands with travel to new schools')
json.dump(out, open(os.path.join(ROOT, 'source', 'block-access', 'closure-access.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, separators=(',', ':'))
print('e.g. A Buckman:', {b: {t: v[0] for t, v in d.items()} for b, d in out.get('A', {}).get('Buckman', {}).items()})
