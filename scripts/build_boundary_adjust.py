"""Census-based estimate of the attendance-area changes the enrollment model does not move (Duniway's southern area to
Llewellyn, the Alameda edge to Scott, Lincoln's area to Ida B. Wells-Barnett, and the other partial boundary edits in
Scenarios A and B). For each grade band, every Census block is assigned to its school under Status Quo and under the
scenario (source/block-access/block-access.csv, from scripts/build_block_access.py, with 2020 Census residents of that
band's ages). A block whose school changes is already in the model when:
  - its Status Quo school closes in the scenario (the closure flows move its students), or
  - grades 6-8, and its Status Quo school is a K-8 that becomes K-5 (its 6-8 students move to the receiving middle
    school), or its K-5 school is one of the elementary areas whose middle school PPS reassigns and the model moves
    (Maplewood, Irvington, Peninsula, Kelly, Atkinson, Creston), or
  - grades 9-12, and its K-5 school is Skyline, Sunnyside Environmental, Whitman or Woodmere (the high-school area
    moves the model makes).
Only moves between schools PPS lists as a changed area (D.bounds <scenario>_<band>.changed) count; this drops blocks the
Status Quo layer assigns to an immersion program's area (Kelly, Lent, Rigler, Scott). Rosa Parks' gain from César
Chávez's neighborhood is already in the model (Rosa Parks gains more than Peninsula's students), so it is skipped.
Every other changed block is a move the model leaves out. For each such (from, to, band), the share is the moved
band-age residents divided by all band-age residents in the from-school's Status Quo area; the page moves that share of
the from-school's Status Quo neighborhood students in that band (excluding immersion programs) in each year from 2027-28.
Output: source/block-access/boundary-adjust.json (read by scripts/patch_boundary_adjust.py)
"""
import csv, json, os, re, sys
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
MS_FEEDERS = {'Maplewood', 'Irvington', 'Peninsula', 'Kelly', 'Atkinson', 'Creston'}
HS_FEEDERS = {'Skyline', 'Sunnyside Environmental', 'Whitman', 'Woodmere'}
MODELLED = {('César Chávez', 'Rosa Parks')}
norm = lambda n: re.sub(r'(elementary|middle school|high school|k-?8|school|[^a-z])', '', n.lower())
NK = {norm(k): k for k in D['series']['SQ']}
def key(n):
    n = norm(n); return NK.get(n) or next((k for nk, k in NK.items() if nk and (nk in n or n in nk)), None)

rows = defaultdict(dict)   # (geoid, band) -> {scenario: (school, residents)}
for r in csv.DictReader(open(os.path.join(ROOT, 'source', 'block-access', 'block-access.csv'), encoding='utf-8')):
    rows[(r['GEOID'], r['band'])][r['scenario']] = (r['school'], float(r['band_age_residents'] or 0))
k5_sq = {g: v['SQ'][0] for (g, b), v in rows.items() if b == 'k5' and 'SQ' in v}
base = defaultdict(float)  # (band, school) -> Status Quo band-age residents in its area
for (g, b), v in rows.items():
    if 'SQ' in v: base[(b, v['SQ'][0])] += v['SQ'][1]

out = {}
for sc in ('A', 'B'):
    closed = {k for k, v in D['detail'][sc].items() if v.get('closed')}
    converts = {k for k, t in D['types']['SQ'].items() if t == 'K8' and D['types'][sc].get(k, t) != 'K8'}
    listed = {(key(c[0]), key(c[1]), b) for b in ('k5', '68', '912') for c in D['bounds'][f'{sc.lower()}_{b}']['changed']}
    moved = defaultdict(float)
    for (g, b), v in rows.items():
        if 'SQ' not in v or sc not in v: continue
        f, t, n = v['SQ'][0], v[sc][0], v['SQ'][1]
        if f == t or not n or f not in D['series']['SQ'] or t not in D['series']['SQ']: continue
        k5 = k5_sq.get(g)
        if f in closed: continue
        if b == '68' and (f in converts or k5 in MS_FEEDERS or k5 in converts): continue
        if b == '912' and k5 in HS_FEEDERS: continue
        if (f, t, b) not in listed or (f, t) in MODELLED: continue
        moved[(f, t, b)] += n
    out[sc] = [dict(frm=f, to=t, band=b, residents=round(n, 1), area_residents=round(base[(b, f)], 1), share=round(n / base[(b, f)], 4))
               for (f, t, b), n in sorted(moved.items(), key=lambda x: -x[1]) if base[(b, f)] and n >= 5]
    for m in out[sc]: print(sc, m)
J = dict(note=__doc__.split('Output')[0].strip(), source='2020 Census block residents by age (DHC) and attendance areas by scenario',
         moves=out)
json.dump(J, open(os.path.join(ROOT, 'source', 'block-access', 'boundary-adjust.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
print('wrote', sum(len(v) for v in out.values()), 'moves')
