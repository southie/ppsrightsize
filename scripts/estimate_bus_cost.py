"""Estimate the annual cost per daily bus-mile and per daily student-mile of PPS general (yellow bus, home-to-school) transportation,
from the current route PDFs (scripts/fetch_pps_bus.py) and the 2026-27 budget.

1. Locate every stop of every current route run.
     intersections ("NE FREMONT ST @ NE 45TH AV")  matched by street name against OpenStreetMap (source/osm/streets.json)
     street addresses                               US Census geocoder (batch, public)
     "<street> No Intersection"                     the point on that street nearest the run's neighbouring stops
     the school end of each run                     the school's location in the explorer (matched by school page)
2. Measure each run along the drive network (shortest path stop to stop, then to / from the school), and each stop's
   ride to school along the run.
3. Estimate the buses the general routes need: the most morning (or afternoon) runs under way at once, each run
   padded by BUFFER_MIN for the drive to the next run.
4. Cost of the general routes: function 2550 Student Transportation Services (General Fund, 2026-27 proposed,
   Volume 1 p. 101), less the TriMet high school pass payment, x general buses / all PPS bus routes (293 in 2023-24,
   per First Student). The 2026-27 budget does not show the TriMet payment, so it is taken at its 2018-19 share of
   Student Transportation: object 533140 Reimb - Tri-Met $2,114,332 of $25,458,264 (2018-19 Adopted Budget, General
   Fund requirements by account p. 90 and by program p. 87). Function 2550 also pays for taxis and administration,
   so this is still an upper estimate. A second value adjusts that 2018-19 share for enrollment since then: TriMet
   passes follow high school enrollment (+9% at the eight comprehensive high schools, 2018-19 to 2025-26) and yellow
   buses serve grades K-8 (-23% at 65 matched schools), from the 2018-19 budget's school enrollment table (pp. 40-42)
   and the explorer's 2025-26 enrollment. The two values bound the estimate. Route miles are service miles (first stop
   to school and back); trips from the garage and between runs are not in the route PDFs, so cost per bus-mile is
   higher than it would be with them included.
5. Daily student-miles = riders x their ride along the route x 2 trips. Costs are annual and miles are per school day,
   so no school-year length is needed: the rate is the annual cost per daily student-mile, and a scenario's added
   daily student-miles times that rate is its added annual cost. Students are enrollment (actual 2025-26 for the
   rate; every year 2025-26 to 2035-36 for scenarios, from the explorer's series, K-8 schools split by the district's
   K-5 share); the share of each school's students beyond bus distance, and their walking miles, come from the 2020
   Census school-age residents of its attendance area. Riders are not published: the central case assumes RIDE_SHARE
   of the bus-eligible students of the schools these routes serve ride, with a low and high case.

6. Scenario cost, for every year (scenarios use Status Quo's attendance areas before they take effect): the change in bus-eligible K-8 students' walking miles to school (K-5 beyond 1 mile, 6-8 beyond
   1.5 miles; source/block-access, scripts/build_block_access.py), turned into bus ride miles with the ratio of the
   measured stop-to-school ride to the eligible students' walking distance under Status Quo, x the annual cost per
   daily student-mile. Rider and PPS-share assumptions cancel (they scale both the cost per mile and the added miles), so the
   range comes from the two TriMet values. Assumes cost grows in proportion to student-miles.

Outputs: source/pps-bus/stop-locations.csv, source/pps-bus/bus-cost-estimate.json
"""
import csv, json, math, os, re, sys, time, io
import numpy as np
import requests
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.spatial import cKDTree
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(ROOT, 'source', 'pps-bus')
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
STREETS = os.path.join(ROOT, 'source', 'osm', 'streets.json')
ACC = os.path.join(ROOT, 'source', 'block-access', 'school-access.csv')
GEOCACHE = os.path.join(BUS, 'geocode-cache.json')

BUDGET_2550 = 47_647_560        # 2026-27 proposed, General Fund function 2550 (Volume 1, p. 101)
BUDGET_2550_PRIOR = 44_125_736  # 2025-26 column on the same page
TRIMET_2018, TRANSPORT_2018 = 2_114_332, 25_458_264   # 2018-19 adopted: 533140 Reimb - Tri-Met; subtotal Student Transportation
TRIMET_SHARE = TRIMET_2018 / TRANSPORT_2018
# enrollment since 2018-19: 2018-19 Adopted Budget school table (pp. 40-42) vs 2025-26 enrollment in the explorer
HS_2018, HS_2526 = 10_978, 11_965      # the eight comprehensive high schools (Wilson = Ida B. Wells, Madison = McDaniel)
K8_2018, K8_2526 = 31_177, 24_128      # 65 elementary, K-8 and middle schools matched by name
_h, _k = HS_2526 / HS_2018, K8_2526 / K8_2018
TRIMET_SHARES = {'budget ratio': TRIMET_SHARE, 'enrollment-adjusted': TRIMET_SHARE * _h / (TRIMET_SHARE * _h + (1 - TRIMET_SHARE) * _k)}
LEGCACHE = os.path.join(ROOT, 'source', 'osm', 'bus-leg-cache.json')   # derived from streets.json node order
ALL_BUS_ROUTES = 293            # PPS school bus routes, 2023-24 (First Student, strike make-up days article)
BUFFER_MIN = 10                 # minutes between runs for one bus (deadhead to the next first stop)
RIDE_SHARE = {'low': 0.35, 'central': 0.5, 'high': 0.65}   # of bus-eligible PPS K-8 students, who ride
RATE_YEAR = '2025-26'   # rate calibrated on actual enrollment; scenario years come from the explorer (below)
MILE = 1609.344
T0 = time.time()
def log(m): print(f'[{time.time() - T0:5.0f}s] {m}')

R = [r for r in json.load(open(os.path.join(BUS, 'pps-bus-routes.json'), encoding='utf-8'))['routes'] if r['current'] and not r['snow']]
html = open(PAGE, encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
SCEN_YEARS, IMPL_YEAR = D['years'], D['impl_year']

# ---------- street names -> nodes ----------
S = json.load(open(STREETS, encoding='utf-8'))
ids = list(S['nodes']); idx = {k: i for i, k in enumerate(ids)}
LON = np.array([S['nodes'][k][0] for k in ids]); LAT = np.array([S['nodes'][k][1] for k in ids])
LAT0 = 45.53; KX, KY = math.cos(math.radians(LAT0)) * 111320.0, 110540.0
NX, NY = (LON + 122.65) * KX, (LAT - LAT0) * KY
ABBR = {'N': 'NORTH', 'NE': 'NORTHEAST', 'NW': 'NORTHWEST', 'S': 'SOUTH', 'SE': 'SOUTHEAST', 'SW': 'SOUTHWEST', 'E': 'EAST', 'W': 'WEST',
        'ST': 'STREET', 'AV': 'AVENUE', 'AVE': 'AVENUE', 'BLVD': 'BOULEVARD', 'DR': 'DRIVE', 'RD': 'ROAD', 'CT': 'COURT', 'PL': 'PLACE',
        'LN': 'LANE', 'WY': 'WAY', 'TER': 'TERRACE', 'TERR': 'TERRACE', 'PKWY': 'PARKWAY', 'HWY': 'HIGHWAY', 'LP': 'LOOP', 'CIR': 'CIRCLE',
        'TRL': 'TRAIL', 'PT': 'POINT', 'HTS': 'HEIGHTS', 'JR': 'JUNIOR', 'MT': 'MOUNT', 'CRES': 'CRESCENT', 'SQ': 'SQUARE', 'BR': 'BRANCH',
        'MLK': 'MARTIN LUTHER KING JUNIOR', 'CV': 'COVE', 'XING': 'CROSSING', 'VW': 'VIEW', 'BV': 'BOULEVARD'}
def norm(n):
    n = re.sub(r"[.'’,]", '', n.upper()); n = re.sub(r'\s+', ' ', n).strip()
    return ' '.join(ABBR.get(t, t) for t in n.split(' '))
byname = {}
for w in S['ways']:
    nm = w['tags'].get('name')
    if not nm or w['tags'].get('highway') in ('footway', 'path', 'steps', 'cycleway', 'pedestrian', 'track', 'bridleway', 'corridor'): continue
    byname.setdefault(norm(nm), set()).update(idx[str(n)] for n in w['nodes'] if str(n) in idx)
log(f'{len(byname):,} named streets')

def clean(loc):
    loc = re.sub(r'\s*\[[NSEW]{0,2}\]?\s*$', '', loc).strip()
    m = re.match(r'^[^()]*\((\d[^()]*)\)\s*$', loc)   # 'CHIEF JOSEPH SCHOOL (2409 N SARATOGA ST)'
    if m: return m.group(1)
    return re.sub(r'\s*\([^)]*\)', '', loc).strip()

def street_nodes(name):
    n = norm(name)
    if n in byname: return byname[n]
    if not re.search(r'\b(STREET|AVENUE|BOULEVARD|DRIVE|ROAD|COURT|PLACE|LANE|WAY|TERRACE|PARKWAY|HIGHWAY|LOOP|CIRCLE|TRAIL)$', n):
        for suf in ('AVENUE', 'STREET'):   # 'SW 45TH@...' (no type)
            if f'{n} {suf}' in byname: return byname[f'{n} {suf}']
    return None

def intersection(a, b):
    A, B = street_nodes(a), street_nodes(b)
    if not A or not B: return None
    common = A & B
    if common: k = next(iter(common)); return float(LON[k]), float(LAT[k]), 'osm-intersection'
    A, B = np.array(sorted(A)), np.array(sorted(B))
    d, j = cKDTree(np.c_[NX[B], NY[B]]).query(np.c_[NX[A], NY[A]])
    i = int(np.argmin(d))
    if d[i] > 120: return None
    k = A[i]; return float(LON[k]), float(LAT[k]), 'osm-nearest-pair'

cache = json.load(open(GEOCACHE, encoding='utf-8')) if os.path.exists(GEOCACHE) else {}
locs = sorted({s['location'] for r in R for s in r['stops'] if not s['loading_zone']})
geo, pending_addr, street_only = {}, {}, {}
for loc in locs:
    c = clean(loc)
    if re.search(r'No Intersection$', c, re.I):
        street_only[loc] = re.sub(r'\s*No Intersection$', '', c, flags=re.I); continue
    m = re.split(r'\s*(?:@|&| AND )\s*', c, maxsplit=1)
    if len(m) == 2 and not re.match(r'^\d', c):
        g = intersection(m[0], m[1])
        if g: geo[loc] = g
        continue
    am = re.match(r'^(\d+)(?:/\d+)?\s+(.*)$', c)
    if am: pending_addr[loc] = f'{am.group(1)} {am.group(2)}'
# addresses: US Census batch geocoder (cached)
todo = {loc: a for loc, a in pending_addr.items() if a not in cache}
if todo:
    buf = io.StringIO(); w = csv.writer(buf)
    keys = list(todo)
    for i, loc in enumerate(keys): w.writerow([i, todo[loc], 'Portland', 'OR', ''])
    r = requests.post('https://geocoding.geo.census.gov/geocoder/locations/addressbatch',
                      files={'addressFile': ('a.csv', buf.getvalue())}, data={'benchmark': 'Public_AR_Current'}, timeout=600)
    for row in csv.reader(io.StringIO(r.text)):
        if len(row) >= 6 and row[2] == 'Match':
            lon, lat = map(float, row[5].split(',')); cache[todo[keys[int(row[0])]]] = [lon, lat]
        elif row: cache[todo[keys[int(row[0])]]] = None
    json.dump(cache, open(GEOCACHE, 'w', encoding='utf-8'), indent=0)
for loc, a in pending_addr.items():
    if cache.get(a): geo[loc] = (cache[a][0], cache[a][1], 'census-address')
log(f'{len(locs):,} stop locations: {sum(1 for v in geo.values() if v[2].startswith("osm"))} intersections, '
    f'{sum(1 for v in geo.values() if v[2] == "census-address")} addresses located; {len(street_only)} street-only')

# ---------- school end of each run ----------
def snorm(n): return re.sub(r'[^a-z0-9]+', ' ', re.sub(r"\b(elementary|middle|high|school|k-8|k8|academy|program|of|the)\b", ' ', n.lower())).strip()
school_at = {snorm(s['name']): s for s in D['schools']} | {snorm(s['key']): s for s in D['schools']}
def school_of(r):
    for p in r['pages']:
        s = school_at.get(snorm(p.replace('-', ' ')))
        if s: return s
    an = snorm(re.sub(r'\b(GT|ST|CAB|LOADING|LOAD|ZONE|LZ|ON|AND)\b.*', '', (r['anchor'] or '').upper(), flags=re.I))
    return school_at.get(an)

# ---------- drive network by length ----------
DRIVE = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link',
         'tertiary', 'tertiary_link', 'unclassified', 'residential', 'living_street', 'service', 'road'}
U, V, F, B = [], [], [], []
for w in S['ways']:
    t = w['tags']; hw = t.get('highway')
    if hw not in DRIVE or t.get('access') in ('no', 'private') or t.get('service') == 'drive-through': continue
    one = t.get('oneway'); fo = one in ('yes', 'true', '1') or t.get('junction') == 'roundabout' or hw == 'motorway'; ro = one == '-1'
    ns = [idx[str(n)] for n in w['nodes'] if str(n) in idx]
    for a, b in zip(ns[:-1], ns[1:]): U.append(a); V.append(b); F.append(not ro); B.append(not fo)
U, V, F, B = map(np.array, (U, V, F, B)); L = np.hypot(NX[U] - NX[V], NY[U] - NY[V]) + 1e-3
G = csr_matrix((np.r_[L[F], L[B]], (np.r_[U[F], V[B]], np.r_[V[F], U[B]])), shape=(len(ids), len(ids)))
_, lab = connected_components(G, directed=True, connection='strong'); ok = np.nonzero(lab == np.bincount(lab).argmax())[0]
tree = cKDTree(np.c_[NX[ok], NY[ok]])
def node_at(lon, lat): return int(ok[tree.query([(lon + 122.65) * KX, (lat - LAT0) * KY])[1]])

# street-only stops: the point on that street nearest the neighbouring located stops
for r in R:
    st = [s for s in r['stops'] if not s['loading_zone']]
    for i, s in enumerate(st):
        if s['location'] not in street_only or s['location'] in geo: continue
        nb = [geo[x['location']] for x in st[max(0, i - 1):i + 2] if x['location'] in geo]
        nodes = street_nodes(street_only[s['location']])
        if not nb or not nodes: continue
        cx, cy = np.mean([(g[0] + 122.65) * KX for g in nb]), np.mean([(g[1] - LAT0) * KY for g in nb])
        A = np.array(sorted(nodes)); k = A[np.argmin(np.hypot(NX[A] - cx, NY[A] - cy))]
        geo[s['location']] = (float(LON[k]), float(LAT[k]), 'osm-street-near-neighbours')

# ---------- runs ----------
def mins(t):
    h, m = map(int, re.match(r'(\d+):(\d+)', t).groups()); return (h % 12 + 12 * t.endswith('pm')) * 60 + m
runs, skipped = [], {'no school match': 0, 'stops not located': 0}
for r in R:
    sch = school_of(r)
    if not sch: skipped['no school match'] += 1; continue
    st = [s for s in r['stops'] if not s['loading_zone']]
    pts = [geo.get(s['location']) for s in st]
    if not st or sum(p is None for p in pts) > len(pts) / 2: skipped['stops not located'] += 1; continue
    keep = [(s, p) for s, p in zip(st, pts) if p]
    seq = [node_at(p[0], p[1]) for _, p in keep]; sn = node_at(sch['lng'], sch['lat'])
    times = [mins(s['time']) for s in r['stops']]
    runs.append(dict(route=r['route'], period=r['period'], school=sch['key'], stops=[s['location'] for s, _ in keep],
                     nodes=(seq + [sn]) if r['period'] == 'morning' else ([sn] + seq), n_missing=len(st) - len(keep),
                     start=min(times), end=max(times)))
log(f'{len(runs)} runs measured; skipped {skipped}')

legs = {(a, b) for x in runs for a, b in zip(x['nodes'][:-1], x['nodes'][1:]) if a != b}
by_src = {}
for a, b in legs: by_src.setdefault(a, []).append(b)
lc = json.load(open(LEGCACHE)) if os.path.exists(LEGCACHE) else {}
dist = {(a, b): lc[f'{a},{b}'] for a, b in legs if f'{a},{b}' in lc}
srcs = sorted({a for a, b in legs if (a, b) not in dist})
for i in range(0, len(srcs), 25):
    bt = srcs[i:i + 25]
    d = dijkstra(G, directed=True, indices=bt, limit=40000)
    for j, a in enumerate(bt):
        for y in by_src[a]: dist[a, y] = d[j, y]
json.dump({f'{a},{b}': (float(v) if np.isfinite(v) else 1e18) for (a, b), v in dist.items()}, open(LEGCACHE, 'w'))
dist = {k: (v if v < 1e17 else np.inf) for k, v in dist.items()}
bad = sum(1 for v in dist.values() if not np.isfinite(v))
log(f'{len(legs):,} legs measured ({bad} unreachable within 40 km)')
for x in runs:
    L_ = [0.0 if a == b else dist.get((a, b), np.inf) for a, b in zip(x['nodes'][:-1], x['nodes'][1:])]
    L_ = [v if np.isfinite(v) else 0.0 for v in L_]
    x['miles'] = sum(L_) / MILE
    # ride of each stop's students: to school (morning, rest of the run) or from school (afternoon, run so far)
    if x['period'] == 'morning': x['ride_mi'] = [sum(L_[i:]) / MILE for i in range(len(L_))]
    else: x['ride_mi'] = [sum(L_[:i + 1]) / MILE for i in range(len(L_))]

# ---------- buses needed ----------
ALL_RUNS = [dict(period=r['period'], start=min(mins(s['time']) for s in r['stops']), end=max(mins(s['time']) for s in r['stops'])) for r in R if r['stops']]
def peak(period):
    ev = sorted([(x['start'], 1) for x in ALL_RUNS if x['period'] == period] + [(x['end'] + BUFFER_MIN, -1) for x in ALL_RUNS if x['period'] == period])
    c = m = 0
    for _, e in ev: c += e; m = max(m, c)
    return m
buses = max(peak('morning'), peak('afternoon'))
daily_runs = len(ALL_RUNS); measured_miles = sum(x['miles'] for x in runs)
daily_bus_miles = measured_miles * daily_runs / len(runs)   # unmeasured runs assumed to be average length
stop_rides = [v for x in runs for v in x['ride_mi']]
avg_ride = float(np.mean(stop_rides)); med_ride = float(np.median(stop_rides))
log(f'peak runs under way: morning {peak("morning")}, afternoon {peak("afternoon")} -> about {buses} buses')
log(f'{daily_bus_miles:,.0f} route miles a day; mean run {daily_bus_miles / daily_runs:.1f} mi; stop-to-school ride mean {avg_ride:.2f} mi, median {med_ride:.2f} mi')

# ---------- students ----------
# students of school k in grade band b: enrollment (D.series), K-8 schools split by the district's K-5 share; each
# school's census residents give the share beyond bus distance and their walking miles per resident
acc = list(csv.DictReader(open(ACC, encoding='utf-8')))
served = {x['school'] for x in runs}
THR = {'k5': '1', '68': '1.5'}
CEN = {}
for a in acc:
    if a['band'] in THR and int(a['residents']) > 0:
        res = int(a['residents'])
        CEN[a['scenario'], a['school'], a['band']] = (float(a[f'beyond_{THR[a["band"]]}mi'] or 0) / res, float(a[f'beyond_{THR[a["band"]]}mi_walkmi'] or 0) / res)
def stu(sc, k, b, yr):
    ser = D['series'][sc].get(k); v = ser[D['years'].index(yr)] if ser else None
    if not v: return 0.0
    pre = D['years'].index(yr) < D['years'].index(D['impl_year'])   # scenarios not yet in effect: Status Quo grade spans
    t = (D['types']['SQ'].get(k) if pre else D['types'][sc].get(k)) or D['types']['SQ'].get(k); f = D['k5_share'][yr]
    if b == 'k5': return v if t == 'ES' else v * f if t == 'K8' else 0.0
    if b == '68': return v if t == 'MS' else v * (1 - f) if t == 'K8' else 0.0
    return 0.0
def elig(sc, yr, schools=None):
    """bus-eligible K-8 students and their total walking miles to school"""
    n = m = 0.0
    area = 'SQ' if D['years'].index(yr) < D['years'].index(IMPL_YEAR) else sc   # scenarios' areas apply from IMPL_YEAR
    for (s_, k, b), (share, wm) in CEN.items():
        if s_ != area or (schools is not None and k not in schools): continue
        x = stu(sc, k, b, yr); n += x * share; m += x * wm
    return n, m
eligible, m_served = elig('SQ', RATE_YEAR, served)
log(f'bus-eligible K-8 students ({RATE_YEAR} enrollment x census share) at the {len(served)} schools these routes serve: {eligible:,.0f}')

# ---------- cost ----------
GT = {v: (BUDGET_2550 * (1 - sh)) * buses / ALL_BUS_ROUTES for v, sh in TRIMET_SHARES.items()}
out = dict(built=time.strftime('%Y-%m-%d'), assumptions=dict(
    budget_2550=BUDGET_2550, budget_2550_prior=BUDGET_2550_PRIOR, all_bus_routes=ALL_BUS_ROUTES,
    buffer_min=BUFFER_MIN, trimet_2018=TRIMET_2018, transport_2018=TRANSPORT_2018,
    trimet_shares={k: round(v, 4) for k, v in TRIMET_SHARES.items()},
    enrollment=dict(hs_2018=HS_2018, hs_2526=HS_2526, k8_2018=K8_2018, k8_2526=K8_2526),
    ride_share=RIDE_SHARE, rate_year=RATE_YEAR),
    routes=dict(runs=daily_runs, runs_measured=len(runs), measured_route_miles=round(measured_miles), runs_skipped=skipped, schools_served=len(served), buses_estimated=buses,
                daily_route_miles=round(daily_bus_miles),
                mean_run_miles=round(daily_bus_miles / daily_runs, 2), mean_ride_miles=round(avg_ride, 2), median_ride_miles=round(med_ride, 2)),
    cost={v: dict(trimet_estimate_2026_27=round(BUDGET_2550 * TRIMET_SHARES[v]), general_routes_share=round(buses / ALL_BUS_ROUTES, 3),
                  general_routes_cost=round(g), per_daily_bus_mile=round(g / daily_bus_miles), per_bus=round(g / buses))
          for v, g in GT.items()},
    cases={})
for k, rs in RIDE_SHARE.items():
    riders = eligible * rs
    smiles = riders * avg_ride * 2   # student-miles a school day
    out['cases'][k] = dict(riders=round(riders), riders_per_run=round(riders * 2 / daily_runs, 1), daily_student_miles=round(smiles),
                           per_daily_student_mile={v: round(g / smiles) for v, g in GT.items()},
                           per_rider_year={v: round(g / riders) for v, g in GT.items()})
psm = [c['per_daily_student_mile'][v] for c in out['cases'].values() for v in GT]
out['box_per_daily_student_mile'] = dict(low=min(psm), central=round(float(np.mean(list(out['cases']['central']['per_daily_student_mile'].values())))), high=max(psm))

# ---------- scenarios: change in eligible students' miles ----------
circuity = avg_ride / (m_served / eligible)   # bus ride miles per walking mile of an eligible student
out['routes']['eligible_students'] = round(eligible)
out['routes']['eligible_mean_walk_miles'] = round(m_served / eligible, 2)
out['routes']['ride_to_walk_ratio'] = round(circuity, 3)
out['scenarios'] = {}
for yr in SCEN_YEARS:
    n0, m0 = elig('SQ', yr)
    for sc in ['SQ', 'A', 'B']:
        n, m = elig(sc, yr)
        dsm = (m - m0) * circuity * RIDE_SHARE['central'] * 2   # added student-miles a school day, central riders
        dcost = {v: round(g * (m - m0) * circuity / (eligible * avg_ride)) for v, g in GT.items()}   # = annual cost per daily student-mile x added daily student-miles
        out['scenarios'].setdefault(yr, {})[sc] = dict(eligible_students=round(n), eligible_walk_miles=round(m), change_eligible=round(n - n0),
                                    change_eligible_pct=round((n - n0) / n0, 3), change_walk_miles_pct=round((m - m0) / m0, 3),
                                    added_daily_student_miles_central=round(dsm), added_cost=dcost,
                                    added_cost_box=dict(low=min(dcost.values()), high=max(dcost.values()), central=round(float(np.mean(list(dcost.values()))))))
        log(f'{yr} {sc}: eligible K-8 students {n:,.0f} ({n - n0:+,.0f}); walking miles {m:,.0f} ({(m - m0) / m0:+.1%}); '
            f'added cost ${min(dcost.values()) / 1e6:.2f}M-${max(dcost.values()) / 1e6:.2f}M a year')
json.dump(out, open(os.path.join(BUS, 'bus-cost-estimate.json'), 'w', encoding='utf-8'), indent=1)
with open(os.path.join(BUS, 'stop-locations.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['location', 'lon', 'lat', 'method'])
    for loc in locs: g = geo.get(loc); w.writerow([loc, *(g if g else ('', '', 'not located'))])
print(json.dumps(out, indent=1))
