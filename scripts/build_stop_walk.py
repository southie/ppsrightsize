"""Walk from home to the bus stop for bus-eligible K-8 students, under Status Quo and Scenarios A and B.

The explorer's bus ride time (scripts/patch_bus_hist.py) is time on the bus: scheduled minutes from the student's stop
to the school's loading zone. This adds the walk to that stop, so the two can be shown apart.

Method
  Residents   the 40 m grid of 2020 Census resident points and their attendance-area school per scenario and grade band,
              exactly as scripts/build_block_access.py builds them (its code is run up to the travel-time step).
              Bus-eligible = walking route to the assigned school over 1 mile (K-5) or 1.5 miles (6-8).
  Stops       the stops of the school's yellow-bus routes in that scenario from source/pps-bus/generated-routes.json
              (scripts/build_bus_routes.py: riders board at the nearest stop PPS uses today within half a mile, or, beyond
              that, a new stop in their block). The same generated stops are used for Status Quo, A and B so the
              scenarios compare like with like. A school with no generated runs uses the nearest stop of any school.
  Walk        along the OpenStreetMap walking network at the explorer's 3 mph, from each resident point (via its nearest
              intersection) to the nearest of those stops.
  Custom      for each area and each school in its region that could take its grades, the walk from that area's
              eligible residents to the receiving school's stops (for custom closures).

Output  source/block-access/stop-walk.json
  S[sc][school][band] = [eligible residents, mean walk to stop (min), residents per walk-time bin (edges sw_min)]
  X[sc][school][band][receiver] = the same for the area's residents riding to the receiver
  R[sc][school][band][new school] = the same for the part of a school's Status Quo area that a scenario assigns to
                                    another school (as scripts/build_closure_access.py's D.commute.R)
Embedded by scripts/patch_stop_walk.py. Takes a few minutes (one walk search per school, plus one per school's stops).
"""
import json, os, sys, time
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BBA = os.path.join(ROOT, 'scripts', 'build_block_access.py')
GEN = os.path.join(ROOT, 'source', 'pps-bus', 'generated-routes.json')
OUTF = os.path.join(ROOT, 'source', 'block-access', 'stop-walk.json')
YB = ('k5', '68')               # yellow-bus grade bands (high school students get TriMet passes)

# residents, attendance areas and the walking network: build_block_access.py up to its travel-time step
src = open(BBA, encoding='utf-8').read()
src = src[:src.index('# ---------- travel time, every point to every school ----------')]
# only the walking network is needed: skip building the bike and drive graphs (saves memory)
for m in ("    'bike': graph(RL[R, 1], RL[R, 2], ones * BIKE_MPH * MPH),\n", "    'drive': graph(RL[R, 3], RL[R, 4], seg_mph * MPH),\n"):
    assert src.count(m) == 1, m
    src = src.replace(m, '')
g = {'__file__': BBA, '__name__': 'build_block_access'}
exec(compile(src, BBA, 'exec'), g)
np, dijkstra, log = g['np'], g['dijkstra'], g['log']
SW_MIN = g['HIST_MIN']   # walk-to-stop histogram bins: the explorer's travel-time bins
D, SK, NS, NP, PW, PX, PY = g['D'], g['SK'], g['NS'], g['NP'], g['PW'], g['PX'], g['PY']
AREAS, inside, proj, MILE, BUS_HEADLINE = g['AREAS'], g['inside'], g['proj'], g['MILE'], g['BUS_HEADLINE']
V = g['WALK_MPH'] * g['MPH']   # m/s
G = g['MODES']['walk']; cand, tree = g['TREES']['walk']
pd_, pi = tree.query(np.c_[g['PXm'], g['PYm']]); pnode = cand[pi]
sd_, si = tree.query(np.c_[g['SXm'], g['SYm']]); snode = cand[si]

# walking metres from every point to every school (for bus eligibility), as build_block_access.py
Gt = G.T.tocsr()
WALK_M = np.empty((NS, NP), np.float32)
for b0 in range(0, NS, 8):
    dist = dijkstra(Gt, directed=True, indices=snode[b0:b0 + 8])
    WALK_M[b0:b0 + 8] = dist[:, pnode] + pd_ / V + sd_[b0:b0 + 8, None] / V
WALK_M *= V
log('walk distances to schools done')

# generated stops per scenario and school
gen = json.load(open(GEN, encoding='utf-8'))['runs']
STOPS = {sc: {k: np.array([s[:2] for run in runs for s in run['stops']]) for k, runs in gen[sc].items() if runs} for sc in gen}
ALL = {sc: np.concatenate(list(STOPS[sc].values())) for sc in STOPS}
CACHE = {}
def stop_min(sc, k):
    """minutes from every point to the nearest stop of school k's routes in scenario sc"""
    key = (sc, k if k in STOPS[sc] else None)
    if key not in CACHE:
        pts = STOPS[sc][k] if key[1] else ALL[sc]
        x, y = proj(pts[:, 1], pts[:, 0])
        _, j = tree.query(np.c_[x, y])
        d = dijkstra(G, directed=False, indices=np.unique(cand[j]), min_only=True)
        CACHE[key] = ((d[pnode] + pd_ / V) / 60).astype(np.float32)
    return CACHE[key]

BCOL = {'k5': 1, '68': 2}
sidx = {k: i for i, k in enumerate(SK)}
ACC_T = {'k5': ('ES', 'K8'), '68': ('MS', 'K8')}
TAKERS = {b: sorted({k for s_ in D['types'] for k, t in D['types'][s_].items() if t in ACC_T[b]}) for b in YB}
def stats(w, t):
    n = float(w.sum())
    if n <= 0: return None
    h = np.bincount(np.searchsorted(SW_MIN, np.nan_to_num(t, posinf=99), 'right'), w, len(SW_MIN) + 1)
    return [round(n, 1), round(float(np.average(np.nan_to_num(t, posinf=99), weights=w)), 2), [round(float(x), 1) for x in h]]

def assign_of(sc, band):
    a = np.full(NP, -1)
    for k, polys in AREAS[sc, band].items():
        a[inside(PX, PY, polys) & (a < 0)] = sidx[k]
    return a

S, X, R, fallback = {}, {}, {}, set()
SQA = {band: assign_of('SQ', band) for band in YB}
for sc in g['SCENS']:
    for band in YB:
        areas = AREAS[sc, band]
        assign = assign_of(sc, band)
        thr = BUS_HEADLINE[band] * MILE
        for k in sorted(areas):
            i = sidx[k]; sel = assign == i
            if not sel.any(): continue
            if k not in STOPS[sc]: fallback.add((sc, k))
            w = PW[sel, BCOL[band]]
            r = stats(w * (WALK_M[i, sel] > thr), stop_min(sc, k)[sel])
            if r: S.setdefault(sc, {}).setdefault(k, {})[band] = r
            for rk in TAKERS[band]:   # custom closures: this area's residents riding to another school in the region
                if rk != k and D['region_of'].get(rk) == D['region_of'].get(k):
                    j = sidx[rk]
                    r = stats(w * (WALK_M[j, sel] > thr), stop_min(sc, rk)[sel])
                    if r: X.setdefault(sc, {}).setdefault(k, {}).setdefault(band, {})[rk] = r
        if sc != 'SQ':   # Status Quo areas a scenario hands to another school, by the new school
            thr = BUS_HEADLINE[band] * MILE
            for k in sorted(AREAS['SQ', band]):
                sq = SQA[band] == sidx[k]
                for j in np.unique(assign[sq & (assign >= 0) & (assign != sidx[k])]):
                    sel = sq & (assign == j); w = PW[sel, BCOL[band]]
                    r = stats(w * (WALK_M[j, sel] > thr), stop_min(sc, SK[j])[sel])
                    if r: R.setdefault(sc, {}).setdefault(k, {}).setdefault(band, {})[SK[j]] = r
    tot = [v[b] for v in S[sc].values() for b in v]
    n = sum(x[0] for x in tot); m = sum(x[0] * x[1] for x in tot) / n
    log(f'{sc}: {n:,.0f} bus-eligible K-8 residents, mean walk to stop {m:.1f} min; {len(STOPS[sc])} schools with stops')

json.dump(dict(method=__doc__.split('Output')[0].strip(), built=time.strftime('%Y-%m-%d'), sw_min=SW_MIN,
               walk_mph=g['WALK_MPH'], stops={sc: len(ALL[sc]) for sc in ALL},
               nearest_any_stop=sorted(f'{sc} {k}' for sc, k in fallback), S=S, X=X, R=R),
          open(OUTF, 'w', encoding='utf-8'), separators=(',', ':'))
log(f'wrote {os.path.relpath(OUTF, ROOT)}; {len(fallback)} school-scenarios used the nearest stop of any school')
