"""Share of each school's Status Quo attendance area that a scenario assigns to another school, by grade band, for
counting students who change school (the explorer's "displaced students"). From the per-block assignments of
scripts/build_block_access.py (source/block-access/block-access.csv): residents of the band's ages in blocks whose
school differs between Status Quo and the scenario, over all the band's residents in the school's Status Quo area.
Covers closures (every block moves), boundary changes and grade moves (a K-8's 6-8 area going to a middle school).
For a school that stays open, only moves to a school PPS lists as a changed area count (D.bounds <scenario>_<band>
.changed): the Status Quo layer also holds immersion-program areas (Kelly, Lent, Rigler, Scott) that would otherwise
look like whole areas moving.
Program relocations (immersion and other programs moving) are added on the page from the scenario's program moves.
Output: source/block-access/move-shares.json  {scenario: {school: {band: share}}}
"""
import csv, json, os, re, sys
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', open(os.path.join(ROOT, 'rightsizing-scenario-explorer.html'), encoding='utf-8').read(), re.S).group(1))
norm = lambda n: re.sub(r'(elementary|middle school|high school|k-?8|school|[^a-z])', '', n.lower())
NK = {norm(k): k for k in D['series']['SQ']}
def key(n):
    n = norm(n); return NK.get(n) or next((k for nk, k in NK.items() if nk and (nk in n or n in nk)), None)
rows = defaultdict(dict)
for r in csv.DictReader(open(os.path.join(ROOT, 'source', 'block-access', 'block-access.csv'), encoding='utf-8')):
    rows[r['GEOID'], r['band']][r['scenario']] = (r['school'], float(r['band_age_residents'] or 0))
out = {}
for sc in ('A', 'B'):
    tot, moved = defaultdict(float), defaultdict(float)
    closed = {k for k, d in D['detail'][sc].items() if d.get('closed')}
    listed = {(key(c[0]), key(c[1]), b) for b in ('k5', '68', '912') for c in D['bounds'][f'{sc.lower()}_{b}']['changed']}
    for (g, b), v in rows.items():
        if 'SQ' not in v or sc not in v: continue
        k, n = v['SQ']; tot[k, b] += n
        t = v[sc][0]
        if t != k and (k in closed or (k, t, b) in listed): moved[k, b] += n
    out[sc] = {}
    for (k, b), n in tot.items():
        if n > 0 and moved[k, b] > 0: out[sc].setdefault(k, {})[b] = round(moved[k, b] / n, 4)
    print(sc, len(out[sc]), 'schools with some area moving; e.g.', {k: out[sc][k] for k in list(out[sc])[:4]})
json.dump(out, open(os.path.join(ROOT, 'source', 'block-access', 'move-shares.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, separators=(',', ':'))
