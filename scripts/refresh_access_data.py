"""Refresh the getting-to-school data on the page after rerunning scripts/build_block_access.py (and
scripts/build_closure_access.py), without replaying the page-code patches: D.commute.S (patch_commute), .BH / .bh_mi /
.X (patch_bus_hist, patch_custom_access) and .R (patch_report_travel), in the layouts those patches use. Everything else
on the page (code, D.commute.runs / SW, bus costs) is left as is. patch_commute itself rebuilds D.commute from scratch
and must be followed by every later patch that adds to it, so use this instead for a data-only refresh.
"""
import csv, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
ACC = os.path.join(ROOT, 'source', 'block-access')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
C = D['commute']
meta = json.load(open(os.path.join(ACC, 'district-access.json'), encoding='utf-8'))
BUS = meta['bus_headline_miles']
S, BH = {}, {}
for r in csv.DictReader(open(os.path.join(ACC, 'school-access.csv'), encoding='utf-8')):
    thr = f"beyond_{BUS[r['band']]:g}mi_share"
    S.setdefault(r['scenario'], {}).setdefault(r['school'], {})[r['band']] = [
        int(r['residents']), float(r[thr]), float(r['mean_walk_mi']), float(r['walk_min_mean']), float(r['bike_min_mean']),
        float(r['drive_min_mean']), float(r['walk_15min_share']), float(r['bike_15min_share']), float(r['drive_15min_share']),
        float(r['nearest_is_assigned_share']), *[[int(x) for x in r[f'{m_}_hist'].split(';')] for m_ in ('walk', 'bike', 'drive')]]
    if r['band'] in ('k5', '68') and r.get('beyond_mi_hist'):
        BH.setdefault(r['scenario'], {}).setdefault(r['school'], {})[r['band']] = [float(x) for x in r['beyond_mi_hist'].split(';')]
pairs = json.load(open(os.path.join(ACC, 'school-pairs.json'), encoding='utf-8'))
old = {k: len(json.dumps(C[k])) for k in ('S', 'BH', 'X', 'R')}
assert set(S) == set(C['S']) and all(set(S[s]) == set(C['S'][s]) for s in S), 'school list changed: rerun patch_commute and the patches after it'
C.update(S=S, BH=BH, bh_mi=pairs['bh_mi'], X=pairs['pairs'], walk_mph=meta['walk_mph'], bike_mph=meta['bike_mph'], drive_factor=meta['drive_factor_vs_osrm'],
         R=json.load(open(os.path.join(ACC, 'closure-access.json'), encoding='utf-8')))
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('refreshed', {k: f'{old[k]:,} -> {len(json.dumps(C[k])):,} chars' for k in old})
