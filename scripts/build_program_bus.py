"""Immersion (DLI) program busing, Status Quo and the scenarios, from PPS's posted bus routes.
1. Program stops today. Each posted morning run (D.busmap.posted: located stops and the drive path to the school) is
   split by its stops: inside the school's own Status Quo attendance area (neighborhood busing) or outside it. At
   schools with an immersion program, out-of-area stops are taken as program busing; at schools without one, 11% of
   stops lie outside the traced areas anyway (edge stops, tracing error, transfers), so that background is not counted.
   A school's program bus-miles = each run's path miles x its share of out-of-area stops; daily = x 2 (the afternoon
   runs mirror the morning ones).
2. Program moves in each scenario (the scenario files): Spanish DLI from Beach, James John and Sitton to Cesar Chavez;
   Spanish 6-8 from Ockley Green to George; Mandarin from MLK Jr to Boise-Eliot/Humboldt; Vietnamese from Rose City
   Park to Vestal (A only); Spanish from Scott to Rigler; Spanish 6-8 from Beaumont to Roseway Heights; Mandarin from
   Clark to Woodstock; Spanish from Atkinson to Lent. Moving stops = the sending school's out-of-area stops plus a
   stop at the sending school (its program students who live in its own area, now bused to the new site).
3. New program runs to each receiving site (compared with the same sites' Status Quo program stops routed the same way,
   each school alone, so the optimizer's efficiency over the posted routes does not count as a saving): its own out-of-area stops plus the moved stops, routed with OR-Tools (all
   stops picked up once, runs end at the school; at most the posted runs' 90th-percentile stops and route miles a run;
   fewest runs, then least miles). Distances: straight line x the posted runs' circuity (their path miles over the
   straight-line chain of their stops). Status Quo for the same sites = the receiving and sending schools' program
   bus-miles today; the difference is the scenario's change.
4. Cost: change in daily bus-miles x the annual cost per daily bus-mile of general routes (bus-cost-estimate.json:
   lower and upper budget cases).
Riders per stop are not published; runs are limited by stops and miles, not seats. Output: source/pps-bus/program-bus.json
"""
import json, math, os, re, sys
import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', open(os.path.join(ROOT, 'rightsizing-scenario-explorer.html'), encoding='utf-8').read(), re.S).group(1))
BC = json.load(open(os.path.join(ROOT, 'source', 'pps-bus', 'bus-cost-estimate.json')))
POSTED, SCH = D['busmap']['posted'], D['busmap']['schools']
mi = lambda a, b: 3958.8 * 2 * math.asin(math.sqrt(math.sin(math.radians(b[0] - a[0]) / 2) ** 2 + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2))
def dec(p):
    out, a, b = [], p[0], p[1]; out.append((a / 1e5, b / 1e5))
    for i in range(2, len(p), 2): a += p[i]; b += p[i + 1]; out.append((a / 1e5, b / 1e5))
    return out
def plen(pts): return sum(mi(pts[i - 1], pts[i]) for i in range(1, len(pts)))
def inpoly(lat, lon, g):
    c = False
    for poly in (g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]):
        for ring in poly:
            for i in range(len(ring)):
                x1, y1 = ring[i]; x2, y2 = ring[i - 1]
                if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1: c = not c
    return c
n = lambda s: re.sub(r'[^a-z]', '', s.lower())
AREA = {}
for band in ('sq_k5', 'sq_68', 'sq_912'):
    for nm, g in D['bounds'][band]['areas']: AREA.setdefault(band, []).append((nm, g))
def own(k):
    band = {'ES': 'sq_k5', 'K8': 'sq_k5', 'MS': 'sq_68', 'HS': 'sq_912'}.get(D['types']['SQ'].get(k))
    c = [g for nm, g in AREA.get(band, []) if n(nm).startswith(n(k)[:8])]
    return c[0] if c else None
DLI = {k: sum((v.get('dli') or {}).values()) for k, v in D['progs']['sch'].items()}

# ---- 1. program stops and miles today ----
runs_all, circ = [], []
prog = {}
for k, runs in POSTED.items():
    g = own(k); sl = SCH.get(k)
    for r in runs:
        st = [tuple(s) for s in r['s']]; pts = dec(r['p']) if r.get('p') else st + ([tuple(sl)] if sl else [])
        miles = plen(pts); chain = plen(st + ([tuple(sl)] if sl else []))
        if chain > 0.3: circ.append(miles / chain)
        out = [s for s in st if g and not inpoly(s[0], s[1], g)] if g else []
        runs_all.append((k, len(st), miles))
        if DLI.get(k, 0) > 0 and st:
            e = prog.setdefault(k, {'runs': 0, 'stops': 0, 'out_stops': [], 'miles_am': 0.0})
            e['runs'] += 1; e['stops'] += len(st); e['out_stops'] += out; e['miles_am'] += miles * len(out) / len(st)
CIRC = float(np.median(circ)); MAXSTOPS = int(np.percentile([r[1] for r in runs_all], 90)); MAXMI = float(np.percentile([r[2] for r in runs_all], 90))
print(f'circuity {CIRC:.2f}; a run: at most {MAXSTOPS} stops, {MAXMI:.1f} miles (posted 90th percentiles)')
for k, e in prog.items(): e['miles_daily'] = round(2 * e['miles_am'], 2); e['n_out'] = len(e['out_stops'])
print('program busing today:', sum(e['runs'] for e in prog.values()), 'runs at', len(prog), 'DLI schools;', round(sum(e['miles_daily'] for e in prog.values()), 1), 'daily program bus-miles')

# ---- 2-3. moves and new runs ----
MOVES = {'A': [('Beach', 'César Chávez'), ('James John', 'César Chávez'), ('Sitton', 'César Chávez'), ('Ockley Green', 'George'), ('MLK Jr', 'Boise-Eliot/Humboldt'),
               ('Rose City Park', 'Vestal'), ('Scott', 'Rigler'), ('Beaumont', 'Roseway Heights'), ('Clark', 'Woodstock'), ('Atkinson', 'Lent')]}
MOVES['B'] = [m for m in MOVES['A'] if m[0] != 'Rose City Park']
PROG = {'César Chávez': 'Spanish', 'George': 'Spanish (6-8)', 'Boise-Eliot/Humboldt': 'Mandarin', 'Vestal': 'Vietnamese', 'Rigler': 'Spanish', 'Roseway Heights': 'Spanish (6-8)', 'Woodstock': 'Mandarin', 'Lent': 'Spanish'}
for s, mv in MOVES.items():
    for a, b in mv: assert a in D['region_of'] and b in D['region_of'] and b in SCH, (s, a, b)
def route(stops, school):
    """fewest runs, then least miles; returns runs as lists of stop indexes and their miles"""
    if not stops: return [], 0.0
    pts = [tuple(school)] + stops; N = len(pts)
    M = [[int(round(CIRC * mi(pts[i], pts[j]) * 1000)) for j in range(N)] for i in range(N)]
    for i in range(1, N): M[0][i] = 0            # runs start at their first stop (no deadhead from the school)
    V = N - 1
    man = pywrapcp.RoutingIndexManager(N, V, 0); rt = pywrapcp.RoutingModel(man)
    # a run: school (free start) -> stops -> school; distances are symmetric, so this equals first stop -> ... -> school
    cb = rt.RegisterTransitCallback(lambda i, j: M[man.IndexToNode(i)][man.IndexToNode(j)])
    rt.SetArcCostEvaluatorOfAllVehicles(cb)
    rt.AddDimension(cb, 0, int(MAXMI * 1000), True, 'mi')
    one = rt.RegisterUnaryTransitCallback(lambda i: 1 if man.IndexToNode(i) else 0)
    rt.AddDimensionWithVehicleCapacity(one, 0, [MAXSTOPS] * V, True, 'stops')
    rt.SetFixedCostOfAllVehicles(20000)          # a run costs as much as 20 miles: fewest runs first
    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.FromSeconds(3)
    sol = rt.SolveWithParameters(prm)
    out, tot = [], 0.0
    for v in range(V):
        i = rt.Start(v); seq = []
        while not rt.IsEnd(i):
            nd = man.IndexToNode(i)
            if nd: seq.append(nd)
            i = sol.Value(rt.NextVar(i))
        if seq:
            m = sum(CIRC * mi(pts[seq[i]], pts[seq[i + 1]]) for i in range(len(seq) - 1)) + CIRC * mi(pts[seq[-1]], pts[0])   # first stop -> ... -> school
            rides, acc = [], CIRC * mi(pts[seq[-1]], pts[0])                                                                  # each stop's ride to school
            for i in range(len(seq) - 1, -1, -1):
                rides.append(acc)
                if i: acc += CIRC * mi(pts[seq[i - 1]], pts[seq[i]])
            out.append({'stops': [list(pts[x]) for x in seq], 'miles': round(m, 2), 'rides': [round(x, 2) for x in rides]}); tot += m
    return out, tot
# Status Quo routed the same way (each school's own program stops alone), so the change compares like with like
def merge(stops):
    out = []
    for p in stops:
        if not any(mi(p, q) < 0.093 for q in out): out.append(p)   # stops within 150 m share a corner
    return out
SQM = {}
for k in sorted({x for mv in MOVES.values() for pair in mv for x in pair}):
    st = merge(prog.get(k, {}).get('out_stops', []))
    r, t = route(st, SCH[k]); rd = [x for run in r for x in run['rides']]
    SQM[k] = dict(runs=len(r), miles_daily=round(2 * t, 2), stops=len(st), ride_sum=sum(rd), ride_n=len(rd))
print('Status Quo program runs, modeled:', {k: (v['runs'], v['miles_daily']) for k, v in SQM.items()})
res = {}
for s, mv in MOVES.items():
    rec = {}
    for a, b in mv: rec.setdefault(b, []).append(a)
    sites = []
    for b, senders in rec.items():
        stops = list(prog.get(b, {}).get('out_stops', []))
        for a in senders: stops += prog.get(a, {}).get('out_stops', []) + [tuple(SCH[a])]
        merged = merge(stops)
        runs, tot = route(merged, SCH[b])
        sq = SQM[b]['miles_daily'] + sum(SQM[a]['miles_daily'] for a in senders)            # Status Quo, routed the same way
        sq_runs = SQM[b]['runs'] + sum(SQM[a]['runs'] for a in senders)
        posted = prog.get(b, {}).get('miles_daily', 0) + sum(prog.get(a, {}).get('miles_daily', 0) for a in senders)   # posted runs' program share
        new_daily = 2 * tot
        rd = [x for run in runs for x in run['rides']]
        sq_rs = SQM[b]['ride_sum'] + sum(SQM[a]['ride_sum'] for a in senders); sq_rn = SQM[b]['ride_n'] + sum(SQM[a]['ride_n'] for a in senders)
        sites.append(dict(site=b, program=PROG.get(b, ''), senders=senders, stops=len(merged), runs=len(runs), miles_daily=round(new_daily, 1),
                          sq_runs_involved=sq_runs, sq_miles_daily=round(sq, 1), sq_posted_miles_daily=round(posted, 1), ride_mean=round(sum(rd) / max(1, len(rd)), 2), ride_max=round(max(rd or [0]), 2), sq_ride_mean=round(sq_rs / max(1, sq_rn), 2), change_miles_daily=round(new_daily - sq, 1), new_runs=runs))
        print(f'{s}: {"+".join(senders)} -> {b}: {len(merged)} stops, {len(runs)} runs ({sq_runs} today), {new_daily:.1f} daily miles (Status Quo routed the same way {sq:.1f}, posted {posted:.1f}; change {new_daily - sq:+.1f})')
    ch = sum(x['change_miles_daily'] for x in sites)
    cost = {c: round(ch * BC['cost'][c]['per_daily_bus_mile']) for c in ('lower', 'upper')}
    res[s] = dict(sites=sites, change_miles_daily=round(ch, 1), change_cost=cost, change_runs=sum(x['runs'] - x['sq_runs_involved'] for x in sites))
    for x in sites: print(f'   {x["site"]}: mean ride per stop {x["sq_ride_mean"]:.1f} -> {x["ride_mean"]:.1f} miles (longest {x["ride_max"]:.1f})')
    print(f'{s}: program busing change {ch:+.1f} daily bus-miles, {cost["lower"]:+,}-{cost["upper"]:+,} a year')
OUT = dict(source="PPS posted bus routes (fall 2026; D.busmap.posted), attendance areas (D.bounds), scenario program moves (scenario files)",
           circuity=round(CIRC, 3), max_stops=MAXSTOPS, max_miles=round(MAXMI, 2), per_daily_bus_mile={c: BC['cost'][c]['per_daily_bus_mile'] for c in ('lower', 'upper')},
           sq={k: {kk: (v if kk != 'out_stops' else [list(p) for p in v]) for kk, v in e.items()} for k, e in prog.items()},
           sq_total=dict(runs=sum(e['runs'] for e in prog.values()), miles_daily=round(sum(e['miles_daily'] for e in prog.values()), 1),
                         cost={c: round(sum(e['miles_daily'] for e in prog.values()) * BC['cost'][c]['per_daily_bus_mile']) for c in ('lower', 'upper')}),
           scen=res)
json.dump(OUT, open(os.path.join(ROOT, 'source', 'pps-bus', 'program-bus.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote source/pps-bus/program-bus.json')
