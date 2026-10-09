"""Candidate yellow-bus routes for Status Quo and the scenarios, generated with Google OR-Tools and calibrated on PPS's
posted general-transportation routes (scripts/fetch_pps_bus.py, measured by scripts/estimate_bus_cost.py).

1. Riders. Each school's bus-eligible students (K-5 walking more than 1 mile, 6-8 more than 1.5 miles; enrollment from
   the explorer, K-8s split by the district K-5 share) are spread over the Census blocks of its attendance area in
   that scenario by the block's residents of those ages (source/block-access/block-access.csv); RIDE_SHARE of them ride.
2. Stops. Each block's riders go to the nearest stop PPS uses today (any route) within MAX_WALK_M, otherwise to a stop of
   their own at the block; stops closer than MERGE_M are then merged. MERGE_M is calibrated so the generated Status Quo
   has as many stops as the posted routes.
3. Run time. Fitted on the posted morning runs: minutes = a x road miles + b x stops (scheduled first stop to school
   arrival, road miles measured as in estimate_bus_cost.py).
4. Routes. For each school, a vehicle-routing problem: every stop picked up once, each run ending at the school, at
   most CAPACITY riders, MAX_STOPS stops (the posted runs' 90th percentile) and MAX_RIDE minutes a run, fewest runs
   first, then least time. MAX_RIDE is calibrated so the
   generated Status Quo has as many runs as the posted routes at the same schools. Afternoon runs mirror the morning.
5. Buses. Each run occupies a bus from its first stop to the bell plus BUFFER_MIN; bells are each school's posted
   morning arrival (else the explorer's start time for its type); buses = the most runs under way at once.
Scenarios are compared with the generated Status Quo for the same year, so the generator's own bias largely cancels.
6. Heuristic. A school's bus-minutes a day are fitted on every generated school and scenario (see fit() below) so the
   explorer can estimate any scenario, year or custom scenario from its eligible students and their walking miles.

Outputs: source/pps-bus/generated-routes.json (calibration, totals and every generated run by scenario and school)
Usage: python scripts/build_bus_routes.py [--year 2027-28] [--quick]   (--fit-only: refit the heuristic on the routes already generated)
"""
import csv, json, math, os, re, sys, time
from collections import defaultdict
import numpy as np
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEAR = sys.argv[sys.argv.index('--year') + 1] if '--year' in sys.argv else '2027-28'
QUICK = '--quick' in sys.argv
CAL_YEAR = '2025-26'
CAPACITY = 60            # riders a run (71-passenger bus, elementary seating, less a margin)
MAX_WALK_M = 805         # half a mile to an existing stop
MERGE_GRID = [0, 150, 250, 400]
RIDE_GRID = [25, 30, 35, 40, 45, 50] if not QUICK else [35]
SOLVE_S = 1 if QUICK else 2

# ---------- the estimate script's processing (stops located, runs measured, students) ----------
src = open(os.path.join(ROOT, 'scripts', 'estimate_bus_cost.py'), encoding='utf-8').read()
cut = src.index('eligible, m_served = elig(')
g = {'__file__': os.path.join(ROOT, 'scripts', 'estimate_bus_cost.py'), '__name__': 'bus_routes'}
exec(compile(src[:cut], 'estimate_bus_cost.py', 'exec'), g)
D, R, runs, geo, G, node_at, MILE, stu, school_at, mins = (g[k] for k in ('D', 'R', 'runs', 'geo', 'G', 'node_at', 'MILE', 'stu', 'school_at', 'mins'))
RIDE_SHARE, BUFFER_MIN = g['RIDE_SHARE']['central'], g['BUFFER_MIN']
log = g['log']
SCH = {s['key']: s for s in school_at.values()}

# ---------- run-time model from the posted morning runs ----------
mr = [x for x in runs if x['period'] == 'morning' and x['school_t'] and x['stop_t']]
X = np.array([[x['miles'], len(x['stops'])] for x in mr]); Y = np.array([x['school_t'] - min(x['stop_t']) for x in mr], float)
ok = (Y > 0) & (Y < 120)
(A_MIN_MI, B_MIN_STOP), *_ = np.linalg.lstsq(X[ok], Y[ok], rcond=None)
log(f'run time = {A_MIN_MI:.2f} min per road mile + {B_MIN_STOP:.2f} min per stop ({ok.sum()} posted morning runs)')
# stops a run: at most the 90th percentile of the posted morning runs
MAX_STOPS = int(np.percentile([len(x['stops']) for x in mr], 90))
log(f'at most {MAX_STOPS} stops a run (posted 90th percentile)')
# bells: each school's posted morning arrival (median), else the explorer's start time for its type less 10 minutes
bell = defaultdict(list)
for x in mr: bell[x['school']].append(x['school_t'])
BELL = {k: float(np.median(v)) for k, v in bell.items()}
TYPE_BELL = {'ES': 8 * 60 - 10, 'K8': 8 * 60 + 35, 'MS': 9 * 60 + 5, 'HS': 8 * 60 + 20}
def bell_of(k, sc): return BELL.get(k) or TYPE_BELL.get(D['types'][sc].get(k) or D['types']['SQ'].get(k), 8 * 60)

# posted routes by school (calibration targets): morning runs and their distinct stops
post_runs = defaultdict(int); post_stops = defaultdict(set)
for x in mr: post_runs[x['school']] += 1; post_stops[x['school']].update(x['stops'])

# ---------- blocks ----------
gj = json.load(open(os.path.join(ROOT, 'source', 'census-blocks', 'blocks_2020.geojson'), encoding='utf-8'))
def cen(geom):
    c = geom['coordinates']; ring = c[0][0] if geom['type'] == 'MultiPolygon' else c[0]
    return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
BC = {f['properties']['GEOID']: cen(f['geometry']) for f in gj['features']}
BLK = defaultdict(list)   # (scenario, band) -> [(geoid, school, residents, walk_mi)]
for r in csv.DictReader(open(os.path.join(ROOT, 'source', 'block-access', 'block-access.csv'), encoding='utf-8')):
    if r['band'] in ('k5', '68') and r['school'] and float(r['band_age_residents'] or 0) > 0:
        BLK[r['scenario'], r['band']].append((r['GEOID'], r['school'], float(r['band_age_residents']), float(r['walk_mi'] or 0)))
THR_MI = {'k5': 1.0, '68': 1.5}

# candidate stops: every located stop on the posted routes
cand = sorted({geo[l][:2] for x in runs for l in x['stops'] if l in geo})
CAND = np.array(cand); KX, KY = g['KX'], g['KY']
def xy(p): return ((p[0] + 122.65) * KX, (p[1] - g['LAT0']) * KY)
ctree = cKDTree(np.array([xy(p) for p in cand]))

def riders(sc, yr):
    """riders by school -> {point: riders}; point = an existing stop or the block itself"""
    area = sc if D['years'].index(yr) >= D['years'].index(D['impl_year']) else 'SQ'
    out = defaultdict(lambda: defaultdict(float))
    for band in ('k5', '68'):
        rows = BLK[area, band]; res = defaultdict(float)
        for _, k, n, _ in rows: res[k] += n
        for gid, k, n, w in rows:
            if w <= THR_MI[band] or gid not in BC or k not in SCH: continue
            if D['detail'][sc].get(k, {}).get('closed'): continue
            v = stu(sc, k, band, yr) * n / res[k] * RIDE_SHARE
            if v <= 0: continue
            d, j = ctree.query(xy(BC[gid]))
            out[k][tuple(cand[j]) if d <= MAX_WALK_M else BC[gid]] += v
    return out

def merge(pts, m):
    """greedy merge of stops closer than m metres: the busiest stop absorbs its neighbours"""
    if not m or len(pts) < 2: return dict(pts)
    P = list(pts); T = cKDTree(np.array([xy(p) for p in P])); done, out = set(), {}
    for i in sorted(range(len(P)), key=lambda i: -pts[P[i]]):
        if i in done: continue
        grp = [j for j in T.query_ball_point(xy(P[i]), m) if j not in done]
        done.update(grp); out[P[i]] = sum(pts[P[j]] for j in grp)
    return out

# ---------- road times ----------
NODE = {}
def nd(p):
    if p not in NODE: NODE[p] = node_at(p[0], p[1])
    return NODE[p]
DIST = {}
def need_dist(problems):
    want = defaultdict(set)
    for pts, sch in problems:
        ns = [nd(p) for p in pts] + [nd((sch['lng'], sch['lat']))]
        for a in ns:
            for b in ns:
                if a != b and (a, b) not in DIST: want[a].add(b)
    srcs = sorted(want)
    for i in range(0, len(srcs), 40):
        bt = srcs[i:i + 40]; d = dijkstra(G, directed=True, indices=bt, limit=60000)
        for j, a in enumerate(bt):
            for b in want[a]: DIST[a, b] = float(d[j, b]) if np.isfinite(d[j, b]) else 1e9
    if srcs: log(f'road distances: {len(srcs):,} sources')

def solve(pts, sch, max_ride):
    """morning runs for one school: list of runs, each [stop points in order]"""
    P = list(pts); n = len(P)
    if not n: return []
    sn = nd((sch['lng'], sch['lat'])); ns = [nd(p) for p in P]
    def tmin(a, b): return 0.0 if a == b else DIST.get((a, b), 1e9) / MILE * A_MIN_MI
    # nodes: 0 start (anywhere), 1 school, 2.. stops
    T = np.zeros((n + 2, n + 2))
    for i in range(n):
        T[i + 2, 1] = tmin(ns[i], sn) + B_MIN_STOP
        for j in range(n): T[i + 2, j + 2] = tmin(ns[i], ns[j]) + B_MIN_STOP if i != j else 0
    T[0, 1] = 0
    # a stop that cannot reach the school within max_ride alone gets its own run
    solo = [i for i in range(n) if T[i + 2, 1] > max_ride]
    keep = [i for i in range(n) if i not in solo]
    result = [[P[i]] for i in solo]
    if not keep: return result
    idx = [0, 1] + [i + 2 for i in keep]; m = len(idx); Tm = (T[np.ix_(idx, idx)] * 10).round().astype(int)
    dem = [0, 0] + [max(1, int(round(pts[P[i]]))) for i in keep]
    nv = len(keep)
    man = pywrapcp.RoutingIndexManager(m, nv, [0] * nv, [1] * nv)
    rt = pywrapcp.RoutingModel(man)
    cb = rt.RegisterTransitCallback(lambda a, b: int(Tm[man.IndexToNode(a), man.IndexToNode(b)]))
    rt.SetArcCostEvaluatorOfAllVehicles(cb)
    rt.AddDimension(cb, 0, int(max_ride * 10), True, 'time')
    dc = rt.RegisterUnaryTransitCallback(lambda a: dem[man.IndexToNode(a)])
    rt.AddDimensionWithVehicleCapacity(dc, 0, [CAPACITY] * nv, True, 'load')
    sc_ = rt.RegisterUnaryTransitCallback(lambda a: 1 if man.IndexToNode(a) >= 2 else 0)
    rt.AddDimensionWithVehicleCapacity(sc_, 0, [MAX_STOPS] * nv, True, 'stops')
    rt.SetFixedCostOfAllVehicles(100000)
    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.FromMilliseconds(int(SOLVE_S * 1000) if m > 6 else 200)
    sol = rt.SolveWithParameters(prm)
    if not sol: return result + [[P[i]] for i in keep]
    for v in range(nv):
        i = rt.Start(v); seq = []
        while not rt.IsEnd(i):
            node = man.IndexToNode(i)
            if node >= 2: seq.append(P[keep[node - 2]])
            i = sol.Value(rt.NextVar(i))
        if seq: result.append(seq)
    return result

def describe(run, pts, sch):
    ns = [nd(p) for p in run] + [nd((sch['lng'], sch['lat']))]
    mi = sum(DIST.get((a, b), 0) for a, b in zip(ns[:-1], ns[1:]) if a != b) / MILE
    return dict(stops=[[round(p[1], 5), round(p[0], 5), round(pts[p], 1)] for p in run], miles=round(mi, 2),
                minutes=round(mi * A_MIN_MI + len(run) * B_MIN_STOP, 1), riders=round(sum(pts[p] for p in run), 1))

def generate(sc, yr, merge_m, max_ride, schools=None):
    rd = riders(sc, yr); probs = {k: merge(v, merge_m) for k, v in rd.items() if (schools is None or k in schools)}
    need_dist([(list(v), SCH[k]) for k, v in probs.items()])
    out = {}
    for k, pts in probs.items():
        out[k] = [describe(r, pts, SCH[k]) for r in solve(pts, SCH[k], max_ride)]
    return out

def buses(gen, sc):
    ev = []
    for k, rs in gen.items():
        b = bell_of(k, sc)
        for r in rs: ev += [(b - r['minutes'], 1), (b + BUFFER_MIN, -1)]
    c = m = 0
    for _, e in sorted(ev): c += e; m = max(m, c)
    return m
def totals(gen, sc):
    rs = [r for v in gen.values() for r in v]
    return dict(schools=len([k for k, v in gen.items() if v]), runs=len(rs), stops=sum(len(r['stops']) for r in rs),
                riders=round(sum(r['riders'] for r in rs)), miles=round(sum(r['miles'] for r in rs), 1),
                mean_minutes=round(float(np.mean([r['minutes'] for r in rs])), 1) if rs else 0,
                p90_minutes=round(float(np.percentile([r['minutes'] for r in rs], 90)), 1) if rs else 0,
                stops_per_run=round(sum(len(r['stops']) for r in rs) / max(1, len(rs)), 2), buses_morning=buses(gen, sc))

# ---------- heuristic for the explorer (any scenario, year or custom scenario) ----------
# A school's generated bus-minutes a day, fitted on every school in every generated scenario:
#   minutes = c0 (if it has bus-eligible K-8 students) + c1 x eligible students + c2 x their walking miles
# with eligible students and walking miles computed as the explorer does (enrollment x the census share and walking
# miles beyond bus distance per resident of the school's area; source/block-access/school-access.csv). The fixed
# per-school term carries the economy of merging schools: a closure drops it and the receiving school's runs absorb
# the students. Same form for route miles, shown for reference.
def eligible(sc, k, yr):
    area = sc if D['years'].index(yr) >= D['years'].index(D['impl_year']) else 'SQ'
    n = m = 0.0
    for b in ('k5', '68'):
        if (area, k, b) in g['CEN']:
            sh, wm = g['CEN'][area, k, b]; x = stu(sc, k, b, yr); n += x * sh; m += x * wm
    return n, m
def fit(runs_by, yr):
    rows = []
    for sc, by in runs_by.items():
        keys = {k for (s_, k, b) in g['CEN'] if s_ == (sc if D['years'].index(yr) >= D['years'].index(D['impl_year']) else 'SQ')} | set(by)
        for k in keys:
            n, m = eligible(sc, k, yr); rs = by.get(k, [])
            if n <= 0 and not rs: continue
            rows.append((sc, k, n, m, sum(r['minutes'] for r in rs), sum(r['miles'] for r in rs)))
    X = np.array([[1.0 if r[2] > 0.5 else 0.0, r[2], r[3]] for r in rows])
    out = dict(form='per school with bus-eligible K-8 students: c0 + c1 x eligible students + c2 x their walking miles (morning; afternoon mirrors it)',
               year=yr, samples=len(rows))
    for name, j in (('minutes', 4), ('miles', 5)):
        Y = np.array([r[j] for r in rows]); c, *_ = np.linalg.lstsq(X, Y, rcond=None); p = np.maximum(X @ c, 0)
        tot = {sc: (float(sum(Y[i] for i, r in enumerate(rows) if r[0] == sc)), float(sum(p[i] for i, r in enumerate(rows) if r[0] == sc))) for sc in runs_by}
        out[name] = dict(coef=[round(float(v), 5) for v in c], r2=round(float(1 - ((Y - p) ** 2).sum() / ((Y - Y.mean()) ** 2).sum()), 3),
                         routed={sc: round(t[0], 1) for sc, t in tot.items()}, fitted={sc: round(t[1], 1) for sc, t in tot.items()},
                         change_pct={sc: dict(routed=round(100 * (tot[sc][0] / tot['SQ'][0] - 1), 1), fitted=round(100 * (tot[sc][1] / tot['SQ'][1] - 1), 1))
                                     for sc in runs_by if sc != 'SQ'})
    return out
if '--fit-only' in sys.argv:   # refit on the routes already generated, without solving them again
    J = json.load(open(os.path.join(ROOT, 'source', 'pps-bus', 'generated-routes.json'), encoding='utf-8'))
    J['heuristic'] = fit(J['runs'], J['year'])
    json.dump(J, open(os.path.join(ROOT, 'source', 'pps-bus', 'generated-routes.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, separators=(',', ':'))
    print(json.dumps(J['heuristic'], indent=1)); sys.exit()

# ---------- calibration on the posted routes (Status Quo, 2025-26, schools with posted routes) ----------
# schools with posted routes and an attendance area to draw riders from (not ACCESS or other district-wide programs
# without one)
rd0 = riders('SQ', CAL_YEAR)
cal_schools = {k for k in post_runs if rd0.get(k)}
cm = [x for x, okx in zip(mr, ok) if okx and x['school'] in cal_schools]
post = dict(schools=len(cal_schools), runs=sum(post_runs[k] for k in cal_schools), stops=sum(len(post_stops[k]) for k in cal_schools),
            miles=round(sum(x['miles'] for x in cm), 1), mean_minutes=round(float(np.mean([x['school_t'] - min(x['stop_t']) for x in cm])), 1),
            p90_minutes=round(float(np.percentile([x['school_t'] - min(x['stop_t']) for x in cm], 90)), 1),
            stops_per_run=round(float(np.mean([len(x['stops']) for x in cm])), 2), buses_morning=None)
log(f'posted morning routes at {len(cal_schools)} schools ({len(set(post_runs) - cal_schools)} without an attendance area left out): {post}')
stop_counts = {m: sum(len(merge(v, m)) for k, v in rd0.items() if k in cal_schools) for m in MERGE_GRID}
MERGE_M = min(MERGE_GRID, key=lambda m: abs(stop_counts[m] - post['stops']))
log(f'stops by merge distance {stop_counts} vs posted {post["stops"]} -> merge {MERGE_M} m')
cal = {}
for mx in RIDE_GRID:
    t0 = time.time(); gen = generate('SQ', CAL_YEAR, MERGE_M, mx, cal_schools); cal[mx] = totals(gen, 'SQ')
    log(f'max ride {mx} min: {cal[mx]} ({time.time() - t0:.0f}s)')
MAX_RIDE = min(RIDE_GRID, key=lambda mx: abs(cal[mx]['runs'] - post['runs']))
log(f'-> max ride {MAX_RIDE} min')

# ---------- scenarios ----------
res, tot = {}, {}
for sc in ('SQ', 'A', 'B'):
    t0 = time.time(); res[sc] = generate(sc, YEAR, MERGE_M, MAX_RIDE); tot[sc] = totals(res[sc], sc)
    log(f'{sc} {YEAR}: {tot[sc]} ({time.time() - t0:.0f}s)')
J = dict(built=time.strftime('%Y-%m-%d'), year=YEAR, note=__doc__.split('Outputs')[0].strip(),
         params=dict(capacity=CAPACITY, max_stops=MAX_STOPS, max_walk_m=MAX_WALK_M, ride_share=RIDE_SHARE, buffer_min=BUFFER_MIN, merge_m=MERGE_M, max_ride_min=MAX_RIDE,
                     min_per_road_mile=round(A_MIN_MI, 3), min_per_stop=round(B_MIN_STOP, 3)),
         calibration=dict(year=CAL_YEAR, posted=post, generated={str(k): v for k, v in cal.items()}, stops_by_merge=stop_counts,
                          posted_by_school={k: dict(runs=post_runs[k], stops=len(post_stops[k])) for k in sorted(post_runs)}),
         totals=tot, change={sc: {k: round(tot[sc][k] - tot['SQ'][k], 1) for k in ('runs', 'stops', 'riders', 'miles', 'buses_morning')} for sc in ('A', 'B')},
         runs={sc: {k: v for k, v in sorted(res[sc].items())} for sc in res},
         heuristic=fit(res, YEAR),
         schools={k: dict(name=SCH[k].get('name', k), ll=[SCH[k]['lat'], SCH[k]['lng']]) for sc in res for k in res[sc]})
json.dump(J, open(os.path.join(ROOT, 'source', 'pps-bus', 'generated-routes.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, separators=(',', ':'))
print(json.dumps(dict(params=J['params'], posted=post, calibration=J['calibration']['generated'], totals=tot, change=J['change']), indent=1))
