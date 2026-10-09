"""Bus route lines for the explorer's before-and-after bus map (getting-to-school section):
  posted     PPS's current general-transportation morning runs: each run's located stops in schedule order, then the
             school (the same processing as scripts/estimate_bus_cost.py)
  generated  the candidate morning runs for Status Quo, Scenario A and Scenario B (source/pps-bus/generated-routes.json,
             scripts/build_bus_routes.py): stops in pickup order, then the school, with riders per stop
Each run also gets its road path: the shortest drive path between consecutive stops and on to the school, on the same
OpenStreetMap drive network the cost estimate measures (scipy Dijkstra), simplified to SIMPLIFY_M metres
(Douglas-Peucker) and stored as integer steps of 1e-5 degrees from the first point (lat, lng, dlat, dlng, ...).
Output: source/pps-bus/bus-map.json  {schools: {key: [lat, lng]}, posted: {key: [{s: [[lat, lng], ...], p: path}, ...]},
        generated: {SQ|A|B: {key: [{s: [[lat, lng, riders], ...], p: path}, ...]}}, year}
"""
import json, os, sys
from collections import defaultdict
import numpy as np
from scipy.sparse.csgraph import dijkstra
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIMPLIFY_M = 12
src = open(os.path.join(ROOT, 'scripts', 'estimate_bus_cost.py'), encoding='utf-8').read()
g = {'__file__': os.path.join(ROOT, 'scripts', 'estimate_bus_cost.py'), '__name__': 'bus_map'}
exec(compile(src[:src.index('\nlegs = {')], 'estimate_bus_cost.py', 'exec'), g)
runs, geo, school_at, G, node_at, LON, LAT, NX, NY = (g[k] for k in ('runs', 'geo', 'school_at', 'G', 'node_at', 'LON', 'LAT', 'NX', 'NY'))
SCH = {s['key']: s for s in school_at.values()}
r4 = lambda v: round(float(v), 4)

# ---------- runs as node sequences (stops in order, then the school) ----------
posted, gen_runs = defaultdict(list), {}
for x in runs:
    if x['period'] != 'morning': continue
    pts = [[r4(geo[l][1]), r4(geo[l][0])] for l in x['stops'] if l in geo]
    if pts: posted[x['school']].append(dict(s=pts, nodes=x['nodes']))   # morning nodes: stops..., school
J = json.load(open(os.path.join(ROOT, 'source', 'pps-bus', 'generated-routes.json'), encoding='utf-8'))
for sc, by in J['runs'].items():
    gen_runs[sc] = {}
    for k, rs in by.items():
        if not rs or k not in SCH: continue
        sn = node_at(SCH[k]['lng'], SCH[k]['lat'])
        gen_runs[sc][k] = [dict(s=[[r4(p[0]), r4(p[1]), round(p[2], 1)] for p in r['stops']],
                                nodes=[node_at(p[1], p[0]) for p in r['stops']] + [sn]) for r in rs]

# ---------- road paths ----------
legs = defaultdict(set)
for rs in [*posted.values(), *(r for by in gen_runs.values() for r in by.values())]:
    for r in rs:
        for a, b in zip(r['nodes'][:-1], r['nodes'][1:]):
            if a != b: legs[a].add(b)
srcs, path = sorted(legs), {}
for i in range(0, len(srcs), 25):
    bt = srcs[i:i + 25]
    d, pred = dijkstra(G, directed=True, indices=bt, limit=60000, return_predecessors=True)
    for j, a in enumerate(bt):
        for b in legs[a]:
            if not np.isfinite(d[j, b]): continue
            seq, n = [b], b
            while n != a and n >= 0: n = pred[j, n]; seq.append(n)
            path[a, b] = seq[::-1]
    if i % 1000 == 0: print(f'paths: {i:,} / {len(srcs):,} sources')

def simplify(idx):
    """Douglas-Peucker on the projected node positions, tolerance SIMPLIFY_M metres"""
    P = np.c_[NX[idx], NY[idx]]; keep = np.zeros(len(idx), bool); keep[[0, -1]] = True; st = [(0, len(idx) - 1)]
    while st:
        a, b = st.pop()
        if b <= a + 1: continue
        seg = P[b] - P[a]; L = np.hypot(*seg)
        q = P[a + 1:b] - P[a]
        dist = np.abs(seg[0] * q[:, 1] - seg[1] * q[:, 0]) / L if L > 0 else np.hypot(q[:, 0], q[:, 1])
        m = int(np.argmax(dist))
        if dist[m] > SIMPLIFY_M: keep[a + 1 + m] = True; st += [(a, a + 1 + m), (a + 1 + m, b)]
    return [i for i, k in zip(idx, keep) if k]
def road(nodes):
    seq = []
    for a, b in zip(nodes[:-1], nodes[1:]):
        if a == b: continue
        p = path.get((a, b))
        if not p: return None
        seq += p if not seq else p[1:]
    if len(seq) < 2: return None
    s = simplify(seq)
    lat = np.round(LAT[s] * 1e5).astype(int); lng = np.round(LON[s] * 1e5).astype(int)
    return [int(lat[0]), int(lng[0])] + [int(v) for pair in zip(np.diff(lat), np.diff(lng)) for v in pair]

n_path = n_all = 0
def finish(r):
    global n_path, n_all
    n_all += 1; p = road(r.pop('nodes'))
    if p: r['p'] = p; n_path += 1
    return r
posted = {k: [finish(r) for r in rs] for k, rs in posted.items()}
generated = {sc: {k: [finish(r) for r in rs] for k, rs in by.items()} for sc, by in gen_runs.items()}
schools = {k: [r4(SCH[k]['lat']), r4(SCH[k]['lng'])] for k in set(posted) | {k for by in generated.values() for k in by} if k in SCH}
out = dict(year=J['year'], schools=schools, posted=posted, generated=generated)
OUT = os.path.join(ROOT, 'source', 'pps-bus', 'bus-map.json')
json.dump(out, open(OUT, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, separators=(',', ':'))
print(f"posted: {sum(len(v) for v in posted.values())} morning runs at {len(posted)} schools; generated: " +
      ', '.join(f'{sc} {sum(len(v) for v in by.values())} runs' for sc, by in generated.items()) +
      f"; road paths for {n_path} of {n_all} runs; {os.path.getsize(OUT) / 1e3:.0f} kB")
