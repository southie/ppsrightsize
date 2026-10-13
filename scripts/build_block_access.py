"""Walking, biking and driving distance / time from every populated 2020 Census block to every PPS school, over the
OpenStreetMap street network, and who lives beyond Oregon's bus-eligibility distances under Status Quo and
Scenarios A and B.

Method
  Residents   2020 Census blocks (source/census-blocks) spread evenly over a GRID_M grid of points inside each block
              (a block smaller than a grid cell is one point at its centre). Each point carries its share of the
              block's total population and of its school-age counts by age (source/census-dhc/block-ages.csv, from
              scripts/extract_block_ages.py).
  Network     OpenStreetMap ways (source/osm/streets.json, from scripts/fetch_osm_streets.py) turned into three graphs:
                walk  every street and path pedestrians may use (no freeways, no foot=no), both directions, WALK_MPH
                bike  streets, paths and cycleways (no freeways, no steps, footways only where bikes are allowed),
                      one-way streets respected unless bikes are exempt. Routes minimise travel time x a stress factor:
                      the street's class (arterials 1.4-2.5x a residential street, more at 35 mph+ or 4+ lanes) eased
                      by its bike facility (PBOT's bicycle network, source/pbot, matched to OSM segments; else OSM's
                      cycleway tags): paths, protected lanes and neighborhood greenways 0.8-0.85, buffered lanes and
                      bike lanes reduce an arterial's stress but not below a side street's; plus a penalty for climbs
                      steeper than 3%. Travel time: BIKE_MPH on the flat, slower uphill (10 mph / (1 + 12 x grade)),
                      up to 1.3x faster downhill, grades from ground elevation (source/elevation; bridges and tunnels
                      flat); the reported minutes are the time along the chosen route
                drive streets cars may use, one-way streets respected, posted speed limit or a default by street
                      class; free-flow (no traffic, no signal delay) then scaled by one factor fitted so that
                      school-to-school drive times match the OSRM matrix the explorer already uses
  Distances   one shortest-path search per school per mode, run backwards over the graph, gives the travel time from
              every intersection to that school; each resident point takes the time at its nearest intersection plus
              the straight-line walk to it.
  Assignment  each point's school per scenario and grade band comes from the attendance-area layers
              (source/pps-explorer-boundaries: k5, 68, 912 for sq / a / b). K-8 schools appear in both the K-5 and
              6-8 layers.
  Ages        K-5 = ages 5-9 + 1/5 of 10-14; 6-8 = 3/5 of 10-14; 9-12 = 1/5 of 10-14 + 15-17 (single years spread
              evenly). These are all school-age residents, not PPS students: some attend private, charter or
              focus-option schools or are home-schooled.
  Bus         Oregon (ORS 327.043) reimburses transportation for elementary students who live more than 1 mile from
              school and secondary students more than 1.5 miles. Distances here are walking-route distances. Grades
              6-8 are reported at both 1.0 and 1.5 miles. PPS gives high school students TriMet passes rather than
              yellow buses, so 9-12 counts are students who would need transit, not yellow-bus riders.

Outputs (source/block-access/)
  block-access.csv     one row per block, scenario and grade band: assigned school, walk miles / minutes, bike and
                       drive minutes, share of the block beyond the bus distance, nearest school and its walk miles
  school-access.csv    one row per scenario, band and school: residents, distances, share and count beyond the bus
                       distance, share within 15 minutes by mode, share whose nearest school is their assigned school
  district-access.json the same rolled up by scenario and band, with changes from Status Quo
  block-school-matrix.npz  block x school travel time for every school and mode (for custom scenarios later)
  corridors.json       trip corridors by bike and by car for each school and scenario (street segments carrying at
                       least 3% of the school's residents, by share level, and the named streets carrying the most),
                       and for each closed school's area to its new schools
"""
import csv, glob, json, math, os, re, sys, time
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.spatial import cKDTree
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
SRC = os.path.join(ROOT, 'source', 'pps-explorer-boundaries')
BLOCKS = os.path.join(ROOT, 'source', 'census-blocks', 'blocks_2020.geojson')
AGES = os.path.join(ROOT, 'source', 'census-dhc', 'block-ages.csv')
STREETS = os.path.join(ROOT, 'source', 'osm', 'streets.json')
OSRM = os.path.join(ROOT, 'source', 'osrm', 'osrm-matrix.json')
OUT = os.path.join(ROOT, 'source', 'block-access'); os.makedirs(OUT, exist_ok=True)
GRID_M = 40
WALK_MPH, BIKE_MPH = 3.0, 10.0
MPH = 0.44704   # m/s per mph
MILE = 1609.344
BUS_MI = {'k5': [1.0], '68': [1.0, 1.5], '912': [1.5]}   # distances reported per band
BUS_HEADLINE = {'k5': 1.0, '68': 1.5, '912': 1.5}
HIST_MIN = [5, 10, 15, 20, 30, 45, 60]   # travel-time histogram bin edges (minutes); last bin is 60+
BH_MI = [round(0.25 * i, 2) for i in range(1, 25)]   # bus-eligible students by walking miles: 0.25-mile bins, last 6+ (bus ride time)
T0 = time.time()
def log(msg): print(f'[{time.time() - T0:6.0f}s] {msg}')

html = open(PAGE, encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
SCHOOLS = D['schools']; SK = [s['key'] for s in SCHOOLS]; NS = len(SK)

# ---------- local metric projection ----------
LAT0, LON0 = 45.53, -122.65
KX, KY = math.cos(math.radians(LAT0)) * 111320.0, 110540.0
def proj(lon, lat): return (np.asarray(lon) - LON0) * KX, (np.asarray(lat) - LAT0) * KY

def polys_of(g): return [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
def inside(px, py, polys):
    """even-odd point-in-polygon for arrays of points (lon/lat) against polygons, bounding-box filtered"""
    hit = np.zeros(px.shape, bool)
    for poly in polys:
        r0 = np.asarray(poly[0], float)
        (a, b), (c, d) = r0.min(0), r0.max(0)
        sel = np.nonzero((px >= a) & (px <= c) & (py >= b) & (py <= d))[0]
        if not len(sel): continue
        x, y, h = px[sel], py[sel], np.zeros(len(sel), bool)
        for ring in poly:
            r = np.asarray(ring, float)
            x1, y1, x2, y2 = r[:-1, 0], r[:-1, 1], r[1:, 0], r[1:, 1]
            for e in np.nonzero(y1 != y2)[0]:
                h ^= ((y1[e] > y) != (y2[e] > y)) & (x < (x2[e] - x1[e]) * (y - y1[e]) / (y2[e] - y1[e]) + x1[e])
        hit[sel] ^= h
    return hit

# ---------- attendance areas ----------
STRIP = r"\b(elementary|middle|high|school|k-8|k8|k-5|academy|program|of|the)\b"
def norm(n):
    n = n.lower().replace('’', "'").replace('.', '')
    return re.sub(r'[^a-z0-9]+', ' ', re.sub(STRIP, ' ', n)).strip()
ALIAS = {'brentwood': 'Lane', 'sunrise': 'Lee', 'martin luther king jr': 'MLK Jr', 'king': 'MLK Jr',
         'boise eliot humboldt': 'Boise-Eliot/Humboldt', 'boise eliot': 'Boise-Eliot/Humboldt', 'wells barnett': 'Ida B Wells-Barnett'}
bykey = {norm(n): s['key'] for s in SCHOOLS for n in {s['key'], s['name']}}
def key_of(name): n = norm(name); return ALIAS.get(n) or bykey.get(n)
SCENS, BANDS = ['SQ', 'A', 'B'], ['k5', '68', '912']
AREAS, unmatched = {}, set()
for sc in SCENS:
    for band in BANDS:
        a = {}
        for f in json.load(open(os.path.join(SRC, f'{sc.lower()}_{band}.geojson'), encoding='utf-8'))['features']:
            k = key_of(f['properties']['name'])
            if not k: unmatched.add(f['properties']['name']); continue
            a.setdefault(k, []).extend(polys_of(f['geometry']))
        AREAS[sc, band] = a
if unmatched: log('boundary names not matched: ' + ', '.join(sorted(unmatched)))
allpts = np.array([p for a in AREAS.values() for polys in a.values() for poly in polys for p in poly[0]])
(BX0, BY0), (BX1, BY1) = allpts.min(0), allpts.max(0)

# ---------- resident points ----------
ages = {r['GEOID']: r for r in csv.DictReader(open(AGES, encoding='utf-8'))}
DX, DY = GRID_M / KX, GRID_M / KY
XS, YS = np.arange(BX0 + DX / 2, BX1, DX), np.arange(BY0 + DY / 2, BY1, DY)
BG, BW = [], []   # block GEOIDs, block weights [pop, k5, 68, 912]
PX, PY, PB = [], [], []
for f in json.load(open(BLOCKS, encoding='utf-8'))['features']:
    g = f['properties']['GEOID']; a = ages.get(g)
    if not a or not int(a['pop']) or not f['geometry']: continue
    polys = polys_of(f['geometry'])
    r = np.array([p for poly in polys for p in poly[0]])
    (a0, b0), (c0, d0) = r.min(0), r.max(0)
    if c0 < BX0 or a0 > BX1 or d0 < BY0 or b0 > BY1: continue
    i0, i1 = np.searchsorted(YS, b0), np.searchsorted(YS, d0, 'right')
    j0, j1 = np.searchsorted(XS, a0), np.searchsorted(XS, c0, 'right')
    gx, gy = np.meshgrid(XS[j0:j1], YS[i0:i1]); gx, gy = gx.ravel(), gy.ravel()
    keep = inside(gx, gy, polys) if len(gx) else np.zeros(0, bool)
    if keep.any(): gx, gy = gx[keep], gy[keep]
    else: gx, gy = np.array([r[:, 0].mean()]), np.array([r[:, 1].mean()])
    b = len(BG)
    t = int(a['age10_14'])
    BG.append(g); BW.append([int(a['pop']), int(a['age5_9']) + t / 5, 3 * t / 5, t / 5 + int(a['age15_17'])])
    PX.append(gx); PY.append(gy); PB.append(np.full(len(gx), b))
PX, PY, PB = np.concatenate(PX), np.concatenate(PY), np.concatenate(PB)
BW = np.array(BW); NB, NP = len(BG), len(PX)
npts = np.bincount(PB, minlength=NB)
PW = BW[PB] / npts[PB, None]   # per point [pop, k5, 68, 912]
log(f'{NB:,} populated blocks, {NP:,} resident points; population {BW[:, 0].sum():,.0f}; '
    f'school-age K-5 {BW[:, 1].sum():,.0f}, 6-8 {BW[:, 2].sum():,.0f}, 9-12 {BW[:, 3].sum():,.0f}')

# ---------- street network ----------
S = json.load(open(STREETS, encoding='utf-8'))
ids = list(S['nodes']); idx = {k: i for i, k in enumerate(ids)}
NX, NY = proj([S['nodes'][k][0] for k in ids], [S['nodes'][k][1] for k in ids]); NN = len(ids)
SKIP = {'proposed', 'construction', 'abandoned', 'platform', 'raceway', 'bus_stop', 'elevator', 'rest_area', 'services',
        'escape', 'bus_guideway', 'razed', 'disused', 'emergency_bay', 'corridor', 'via_ferrata', 'busway', 'no'}
DRIVE = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link',
         'tertiary', 'tertiary_link', 'unclassified', 'residential', 'living_street', 'service', 'road'}
FAST = {'motorway', 'motorway_link', 'trunk', 'trunk_link'}
DEFAULT_MPH = {'motorway': 55, 'motorway_link': 35, 'trunk': 45, 'trunk_link': 30, 'primary': 35, 'primary_link': 25,
               'secondary': 30, 'secondary_link': 25, 'tertiary': 25, 'tertiary_link': 20, 'unclassified': 25,
               'residential': 20, 'living_street': 10, 'service': 10, 'road': 20}
NOPE, YES = {'no', 'private'}, {'yes', 'designated', 'permissive', 'destination'}
def mph(t, hw):
    m = re.match(r'\s*(\d+)\s*(mph)?', t.get('maxspeed', ''))
    if m: return float(m.group(1)) if m.group(2) else float(m.group(1)) / 1.609344   # OSM: a bare number is km/h
    return DEFAULT_MPH.get(hw, 20)

def rules(t):
    """(walk, bike_fwd, bike_back, drive_fwd, drive_back, drive_mph, fast) for one way's tags"""
    hw = t.get('highway', '')
    if hw in SKIP or t.get('area') == 'yes': return None
    acc = t.get('access', '')
    one = t.get('oneway', '')
    fwd_only = one in ('yes', 'true', '1') or t.get('junction') in ('roundabout', 'circular') or hw == 'motorway'
    rev_only = one == '-1'
    foot = t.get('foot', '')
    walk = hw not in ('motorway', 'motorway_link') and foot not in NOPE and (acc not in NOPE or foot in YES)
    bk = t.get('bicycle', '')
    bike = (hw not in ('motorway', 'motorway_link', 'steps') and bk not in NOPE and (acc not in NOPE or bk in YES)
            and (hw not in ('footway', 'pedestrian', 'bridleway') or bk in YES))
    exempt = t.get('oneway:bicycle') == 'no' or t.get('cycleway', '').startswith('opposite') or hw in ('cycleway', 'path', 'footway')
    bf, bb = bike and not (rev_only and not exempt), bike and not (fwd_only and not exempt)
    mv = t.get('motor_vehicle') or t.get('motorcar') or t.get('vehicle') or ''
    drive = hw in DRIVE and acc not in NOPE and mv not in NOPE and t.get('service') != 'drive-through'
    df, db = drive and not rev_only, drive and not fwd_only
    return walk, bf, bb, df, db, mph(t, hw), hw in FAST

U, V, R = [], [], []
rule_list = []
for w in S['ways']:
    r = rules(w['tags'])
    if not r or not any(r[:5]): continue
    ri = len(rule_list); rule_list.append(r)
    ns = [idx[str(n)] for n in w['nodes'] if str(n) in idx]
    U.extend(ns[:-1]); V.extend(ns[1:]); R.extend([ri] * (len(ns) - 1))
U, V, R = np.array(U), np.array(V), np.array(R)
RL = np.array([r[:5] for r in rule_list], bool); RS = np.array([r[5] for r in rule_list]); RF = np.array([r[6] for r in rule_list])
L = np.hypot(NX[U] - NX[V], NY[U] - NY[V])
log(f'{len(rule_list):,} usable ways, {len(U):,} segments, {L.sum() / 1000:,.0f} km')

def graph(fwd, back, speed):
    u = np.concatenate([U[fwd], V[back]]); v = np.concatenate([V[fwd], U[back]])
    w = np.concatenate([L[fwd] / speed[fwd], L[back] / speed[back]]) + 1e-3
    return csr_matrix((w, (u, v)), shape=(NN, NN))
ones = np.ones(len(U))
seg_mph = RS[R]

# ---------- low-stress, hill-aware bike routing ----------
# Route choice minimises travel time x a stress factor for the street and its bike facility (PBOT's bicycle network,
# else OpenStreetMap's bike tags); travel time slows on climbs and speeds up (capped) downhill, from ground elevation.
# Reported bike minutes are the travel time along the chosen route.
WTAGS = [w['tags'] for w in S['ways'] if rules(w['tags']) and any(rules(w['tags'])[:5])]   # same order as rule_list
assert len(WTAGS) == len(rule_list)
HW = np.array([t.get('highway', '') for t in WTAGS]); SEGW = R   # way index per segment
BIKE_STRESS_BASE = {'trunk': 3.5, 'trunk_link': 2.5, 'primary': 2.5, 'primary_link': 2.0, 'secondary': 2.0, 'secondary_link': 1.6,
                    'tertiary': 1.4, 'tertiary_link': 1.2, 'unclassified': 1.05, 'residential': 1.0, 'living_street': 0.95,
                    'service': 1.1, 'road': 1.2, 'track': 1.3, 'cycleway': 0.8, 'path': 0.9, 'footway': 1.15, 'pedestrian': 1.2,
                    'bridleway': 1.3}
# facility: multiplier on the street's stress, and a floor (a bike lane on an arterial is still busier than a side street)
FAC = {'TRL': (None, 0.8), 'PBL': (None, 0.85), 'SIR': (None, 0.85), 'NG': (None, 0.85), 'BBL': (0.55, 1.0), 'BBBL': (0.55, 1.0),
       'SBBL': (0.55, 1.0), 'BL': (0.7, 1.05), 'ABL': (0.8, 1.05), 'ESR': (0.85, 0.95), 'SHARED': (0.9, 1.0)}
FAC_RANK = ['TRL', 'PBL', 'SIR', 'NG', 'SBBL', 'BBBL', 'BBL', 'BL', 'ABL', 'ESR', 'SHARED']
def osm_fac(t):
    hw, bk = t.get('highway', ''), t.get('bicycle', '')
    vals = [t.get(k, '') for k in ('cycleway', 'cycleway:left', 'cycleway:right', 'cycleway:both')]
    if hw == 'cycleway' or (hw == 'path' and bk == 'designated') or t.get('bicycle_road') == 'yes' or t.get('cyclestreet') == 'yes': return 'TRL' if hw in ('cycleway', 'path') else 'NG'
    if any(v == 'track' for v in vals): return 'PBL'
    if any(v in ('lane', 'opposite_lane') for v in vals):
        sep = t.get('cycleway:right:separation', '') or t.get('cycleway:left:separation', '')
        return 'PBL' if sep and sep not in ('no', 'solid_line', 'dashed_line') else 'BL'
    if any(v in ('shared_lane', 'share_busway') for v in vals): return 'SHARED'
    return ''
seg_fac = np.array([osm_fac(t) for t in WTAGS], dtype=object)[SEGW]
PBOT = os.path.join(ROOT, 'source', 'pbot', 'bicycle-network.geojson')
if os.path.exists(PBOT):
    # PBOT bikeway lines, densified to points every 5 m with their bearing; an OSM segment takes the facility of a
    # bikeway point within 9 m of its midpoint running the same way (within 25 degrees), so cross streets don't match
    px_, py_, pb_, pf_ = [], [], [], []
    for f in json.load(open(PBOT, encoding='utf-8'))['features']:
        fc = f['properties'].get('Facility') or ''
        if fc not in FAC or not f.get('geometry'): continue
        g = f['geometry']; cs = g['coordinates']
        lines = cs if cs and isinstance(cs[0][0], list) else [cs]
        for ln in lines:
            a = np.array([q[:2] for q in ln if isinstance(q, list) and len(q) >= 2], float)
            if a.ndim != 2 or len(a) < 2: continue
            x, y = proj(a[:, 0], a[:, 1])
            for i in range(len(x) - 1):
                dx, dy = x[i + 1] - x[i], y[i + 1] - y[i]; n = max(1, int(math.hypot(dx, dy) // 5))
                tt = (np.arange(n) + .5) / n
                px_.append(x[i] + dx * tt); py_.append(y[i] + dy * tt); pb_.append(np.full(n, math.atan2(dy, dx) % math.pi)); pf_.append(np.full(n, FAC_RANK.index(fc)))
    px_, py_, pb_, pf_ = map(np.concatenate, (px_, py_, pb_, pf_))
    ptree = cKDTree(np.c_[px_, py_])
    mx, my = (NX[U] + NX[V]) / 2, (NY[U] + NY[V]) / 2
    sb = np.arctan2(NY[V] - NY[U], NX[V] - NX[U]) % math.pi
    bikeable = RL[R, 1] | RL[R, 2]
    best = np.full(len(U), 99)
    dd, ii = ptree.query(np.c_[mx, my], k=6, distance_upper_bound=9.0)
    for c in range(6):
        ok = np.isfinite(dd[:, c]) & bikeable
        j = np.where(ok, ii[:, c], 0)
        diff = np.abs(pb_[j] - sb); diff = np.minimum(diff, math.pi - diff)
        ok &= diff < math.radians(25)
        best = np.where(ok, np.minimum(best, pf_[j]), best)
    has = best < 99
    pbf = np.array(FAC_RANK, dtype=object)[np.where(has, best, 0)]
    # the better of PBOT's and OSM's facility
    seg_fac = np.where(has & ((seg_fac == '') | np.array([FAC_RANK.index(a) < FAC_RANK.index(b) if b else True for a, b in zip(pbf, seg_fac)])), pbf, seg_fac)
    log(f'bike facilities: PBOT matched {has.sum():,} segments ({L[has].sum() / 1000:,.0f} km); with OSM tags {(seg_fac != "").sum():,} segments')
base_stress = np.array([BIKE_STRESS_BASE.get(h, 1.2) for h in HW])[SEGW]
fast_road = (seg_mph >= 35) & np.isin(HW[SEGW], ['primary', 'secondary', 'tertiary', 'trunk', 'primary_link', 'secondary_link'])
lanes = np.array([int(re.match(r'\d+', t.get('lanes', '0') or '0').group()) if re.match(r'\d+', t.get('lanes', '') or '') else 0 for t in WTAGS])[SEGW]
stress = base_stress * np.where(fast_road, 1.2, 1.0) * np.where(lanes >= 4, 1.15, 1.0)
for fc, (mult, floor) in FAC.items():
    sel = seg_fac == fc
    stress[sel] = floor if mult is None else np.maximum(floor, stress[sel] * mult)
unpaved = np.array([t.get('surface', '') in ('gravel', 'dirt', 'ground', 'unpaved', 'grass', 'mud', 'sand', 'fine_gravel', 'compacted') for t in WTAGS])[SEGW]
stress *= np.where(unpaved, 1.25, 1.0)
# ground elevation at every node (terrarium tiles, scripts/fetch_elevation.py), bilinear
EL = os.path.join(ROOT, 'source', 'elevation')
NZ = np.zeros(NN)
if os.path.exists(os.path.join(EL, 'index.json')):
    from PIL import Image
    ei = json.load(open(os.path.join(EL, 'index.json'))); z = ei['z']; (x0, x1), (y0, y1) = ei['x'], ei['y']
    mos = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.float32)
    for tx_ in range(x0, x1 + 1):
        for ty_ in range(y0, y1 + 1):
            a = np.asarray(Image.open(os.path.join(EL, f'z{z}_{tx_}_{ty_}.png')).convert('RGB'), np.float32)
            mos[(ty_ - y0) * 256:(ty_ - y0 + 1) * 256, (tx_ - x0) * 256:(tx_ - x0 + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    lon_ = np.array([S['nodes'][k][0] for k in ids]); lat_ = np.array([S['nodes'][k][1] for k in ids])
    fx = (lon_ + 180) / 360 * 2 ** z * 256 - x0 * 256
    fy = (1 - np.log(np.tan(np.radians(lat_)) + 1 / np.cos(np.radians(lat_))) / math.pi) / 2 * 2 ** z * 256 - y0 * 256
    ix, iy = np.clip(np.floor(fx - .5).astype(int), 0, mos.shape[1] - 2), np.clip(np.floor(fy - .5).astype(int), 0, mos.shape[0] - 2)
    ax, ay = np.clip(fx - .5 - ix, 0, 1), np.clip(fy - .5 - iy, 0, 1)
    NZ = (mos[iy, ix] * (1 - ax) * (1 - ay) + mos[iy, ix + 1] * ax * (1 - ay) + mos[iy + 1, ix] * (1 - ax) * ay + mos[iy + 1, ix + 1] * ax * ay).astype(float)
    log(f'elevation: {NZ.min():.0f} to {NZ.max():.0f} m at street nodes')
flat = np.array([t.get('bridge', 'no') not in ('no', '') or t.get('tunnel', 'no') not in ('no', '') for t in WTAGS])[SEGW]
# grades from elevation smoothed along each way (mean over +/- GRADE_WIN m), since the ground model's ~13 m pixels make
# short segments noisy; a way's segments are consecutive in U / V / R
GRADE_WIN = 40.0
grade = np.zeros(len(U))
bounds = np.r_[0, np.nonzero(R[1:] != R[:-1])[0] + 1, len(R)]
for a0, b0 in zip(bounds[:-1], bounds[1:]):
    nd = np.r_[U[a0:b0], V[b0 - 1]]; z_ = NZ[nd]
    s_ = np.r_[0, np.cumsum(L[a0:b0])]
    if s_[-1] < 1: continue
    cz = np.r_[0, np.cumsum((z_[1:] + z_[:-1]) / 2 * np.diff(s_))]   # integral of elevation along the way
    lo, hi = np.maximum(s_ - GRADE_WIN, 0), np.minimum(s_ + GRADE_WIN, s_[-1])
    zs = np.where(hi - lo > 1, (np.interp(hi, s_, cz) - np.interp(lo, s_, cz)) / np.maximum(hi - lo, 1e-9), z_)
    grade[a0:b0] = np.diff(zs) / np.maximum(L[a0:b0], 1)
grade = np.clip(np.where(flat | (L < 1), 0, grade), -0.2, 0.2)   # U -> V
def bike_speed(g):   # m/s: slower uphill, faster downhill (capped at 1.3x)
    return BIKE_MPH * MPH * np.where(g > 0, 1 / (1 + 12 * g), np.minimum(1.3, 1 - 6 * g))
def climb(g): return 1 + 4 * np.maximum(0, g - 0.03)   # aversion to steep climbs beyond the time they take
BT_F, BT_B = L / bike_speed(grade), L / bike_speed(-grade)          # seconds, U->V and V->U
BC_F, BC_B = BT_F * stress * climb(grade), BT_B * stress * climb(-grade)
log(f'bike stress: median {np.median(stress[RL[R, 1]]):.2f}, arterials without facility {np.median(stress[(seg_fac == "") & np.isin(HW[SEGW], ["primary", "secondary"])]):.2f}; '
    f'grade beyond 5% on {(np.abs(grade) > .05).mean():.1%} of segments')

def graph_edges(fwd, back, cf, cb, tf, tb):
    """unique directed edges (the cheapest where two ways join the same nodes): cost csr, and sorted keys / times for
    looking up the travel time of a tree edge"""
    u = np.concatenate([U[fwd], V[back]]); v = np.concatenate([V[fwd], U[back]])
    c = np.concatenate([cf[fwd], cb[back]]) + 1e-3; t = np.concatenate([tf[fwd], tb[back]]) + 1e-3
    seg = np.concatenate([np.nonzero(fwd)[0], np.nonzero(back)[0]])
    key = u.astype(np.int64) * NN + v
    o = np.lexsort((c, key)); key, u, v, c, t, seg = key[o], u[o], v[o], c[o], t[o], seg[o]
    first = np.r_[True, key[1:] != key[:-1]]
    key, u, v, c, t, seg = key[first], u[first], v[first], c[first], t[first], seg[first]
    return csr_matrix((c, (u, v)), shape=(NN, NN)), key, t, seg
EDGES = {}
G_bike, *EDGES['bike'] = graph_edges(RL[R, 1], RL[R, 2], BC_F, BC_B, BT_F, BT_B)
dt = L / (seg_mph * MPH)
G_drive, *EDGES['drive'] = graph_edges(RL[R, 3], RL[R, 4], dt, dt, dt, dt)
wt = L / (WALK_MPH * MPH)
_, *EDGES['walk'] = graph_edges(RL[R, 0], RL[R, 0], wt, wt, wt, wt)   # lookups only: walk times use the walk graph below
MODES = {
    'walk': graph(RL[R, 0], RL[R, 0], ones * WALK_MPH * MPH),
    'bike': G_bike,
    'drive': G_drive,
}

# snapping targets: nodes in the graph's largest strongly connected piece (and, for driving, not on a freeway)
TREES = {}
for m, G in MODES.items():
    n, lab = connected_components(G, directed=True, connection='strong')
    big = np.bincount(lab).argmax()
    ok = lab == big
    if m == 'drive':
        local = np.zeros(NN, bool)
        sel = (RL[R, 3] | RL[R, 4]) & ~RF[R]
        local[U[sel]] = True; local[V[sel]] = True
        ok &= local
    cand = np.nonzero(ok)[0]
    TREES[m] = (cand, cKDTree(np.c_[NX[cand], NY[cand]]))
    log(f'{m}: {G.nnz:,} directed edges; snapping to {len(cand):,} nodes')

PXm, PYm = proj(PX, PY)
SXm, SYm = proj([s['lng'] for s in SCHOOLS], [s['lat'] for s in SCHOOLS])
SPEED = {'walk': WALK_MPH * MPH, 'bike': BIKE_MPH * MPH, 'drive': WALK_MPH * MPH}   # the snap leg is on foot

# ---------- travel time, every point to every school ----------
def tree_sum(pred, val):
    """sum of val along each node's path to the root of a shortest-path tree (pointer doubling); unreached -> inf"""
    P = np.where(pred < 0, -1, pred); acc = np.where(P >= 0, val, 0.0); Q = P.copy()
    while (Q >= 0).any():
        m_ = Q >= 0
        acc[m_] += acc[Q[m_]]; Q[m_] = Q[Q[m_]]
    return acc
def edge_lookup(m, n, p):
    """travel time and segment index of tree edges n -> p (p = next node toward the school)"""
    key, t, seg = EDGES[m]
    k = n.astype(np.int64) * NN + p; j = np.clip(np.searchsorted(key, k), 0, len(key) - 1)
    ok = key[j] == k
    return np.where(ok, t[j], 0.0), np.where(ok, seg[j], -1)
TT = {}   # mode -> (NS, NP) float32 seconds
SS = {}   # mode -> (NS, NS) seconds school -> school
PRED = {}   # mode -> (NS, NN) int32: next node toward each school (for the trip corridors)
PNODE, SNODE = {}, {}
for m, G in MODES.items():
    cand, tree = TREES[m]
    pd_, pi = tree.query(np.c_[PXm, PYm]); pnode = cand[pi]
    sd_, si = tree.query(np.c_[SXm, SYm]); snode = cand[si]
    PNODE[m], SNODE[m] = pnode, snode
    Gt = G.T.tocsr()
    out = np.empty((NS, NP), np.float32); ss = np.empty((NS, NS))
    if m in EDGES: PRED[m] = np.empty((NS, NN), np.int32)
    for b0 in range(0, NS, 8):
        if m in EDGES:
            dist, pred = dijkstra(Gt, directed=True, indices=snode[b0:b0 + 8], return_predecessors=True)   # node -> school
            PRED[m][b0:b0 + 8] = pred
            if m == 'bike':   # route chosen on cost; time measured along it
                nodes = np.arange(NN)
                for r_ in range(len(pred)):
                    et, _ = edge_lookup(m, nodes, np.maximum(pred[r_], 0))
                    tsum = tree_sum(pred[r_], np.where(pred[r_] >= 0, et, 0.0))
                    tsum[~np.isfinite(dist[r_])] = np.inf
                    dist[r_] = tsum
        else:
            dist = dijkstra(Gt, directed=True, indices=snode[b0:b0 + 8])   # node -> school
        out[b0:b0 + 8] = dist[:, pnode] + pd_ / SPEED[m] + sd_[b0:b0 + 8, None] / SPEED[m]
        ss[b0:b0 + 8] = (dist[:, snode] + sd_[None, :] / SPEED[m] + sd_[b0:b0 + 8, None] / SPEED[m])
    TT[m], SS[m] = out, ss
    log(f'{m}: travel times done; median snap {np.median(pd_):.0f} m; unreachable {np.mean(~np.isfinite(out)):.2%}')

# drive: fit one factor to the OSRM school-to-school matrix (free-flow OSRM includes turn and signal penalties)
om = json.load(open(OSRM, encoding='utf-8'))
okeys = [s['key'] for s in om['pps']]; oi = {k: i for i, k in enumerate(okeys)}
pairs = [(i, j, om['pps_to_pps'][oi[a]][oi[b]][1] * 60) for i, a in enumerate(SK) for j, b in enumerate(SK)
         if a in oi and b in oi and i != j and om['pps_to_pps'][oi[a]][oi[b]] and om['pps_to_pps'][oi[a]][oi[b]][1] > 0]
mine = np.array([SS['drive'][j, i] for i, j, _ in pairs])   # SS[m][to, from]: row = destination school
ref = np.array([r for _, _, r in pairs])
good = np.isfinite(mine)
DRIVE_FACTOR = float(np.median(ref[good] / mine[good]))
err = np.abs(mine[good] * DRIVE_FACTOR - ref[good]) / ref[good]
log(f'drive vs OSRM: factor {DRIVE_FACTOR:.2f}; after scaling, median error {np.median(err):.0%}, 90th pct {np.percentile(err, 90):.0%} ({good.sum()} pairs)')
TT['drive'] *= DRIVE_FACTOR

# ---------- scenarios ----------
sidx = {k: i for i, k in enumerate(SK)}
WALK_M = TT['walk'] * (WALK_MPH * MPH)   # walking-route metres
BCOL = {'k5': 1, '68': 2, '912': 3}
block_rows, school_rows, district = [], [], {}
# schools that could take each grade band in any scenario (receivers of a custom closure), and the area -> school stats
ACC_T = {'k5': ('ES', 'K8'), '68': ('MS', 'K8'), '912': ('HS',)}
TAKERS = {b: sorted({k for s_ in D['types'] for k, t in D['types'][s_].items() if t in ACC_T[b]}) for b in BANDS}
PAIRS = {}
ASSIGN = {}
for sc in SCENS:
    for band in BANDS:
        areas = AREAS[sc, band]
        assign = np.full(NP, -1)
        for k, polys in areas.items():
            assign[inside(PX, PY, polys) & (assign < 0)] = sidx[k]
        ASSIGN[sc, band] = assign
        cands = np.array(sorted(sidx[k] for k in areas))
        nearest = cands[np.argmin(WALK_M[cands], axis=0)]
        has = assign >= 0; ai = np.where(has, assign, 0)
        wm = WALK_M[ai, np.arange(NP)]
        tmin = {m: TT[m][ai, np.arange(NP)] / 60 for m in TT}
        wb = PW[:, BCOL[band]] * has          # band-age residents per point (assigned only)
        thr = BUS_HEADLINE[band] * MILE
        beyond = wm > thr
        # ---- per block ----
        wp = PW[:, 0] * has                    # weight block means by residents
        tot = np.bincount(PB, wp, NB)
        blk = lambda v: np.bincount(PB, wp * np.nan_to_num(v, posinf=0), NB) / np.where(tot > 0, tot, 1)
        bwalk, bwmin, bbike, bdrive, bbeyond = blk(wm / MILE), blk(tmin['walk']), blk(tmin['bike']), blk(tmin['drive']), blk(beyond)
        # majority school per block and nearest school per block (by mean walking distance over the block)
        key = PB * NS + ai
        votes = np.bincount(key[has], wp[has], NB * NS).reshape(NB, NS)
        bschool = np.where(votes.sum(1) > 0, votes.argmax(1), -1)
        bw_all = np.zeros((len(cands), NB))
        for ci, c in enumerate(cands): bw_all[ci] = np.bincount(PB, PW[:, 0] * WALK_M[c], NB) / np.maximum(np.bincount(PB, PW[:, 0], NB), 1e-9)
        bnear = cands[bw_all.argmin(0)]; bnear_mi = bw_all.min(0) / MILE
        bband = np.bincount(PB, wb, NB)
        for b in np.nonzero(bschool >= 0)[0]:
            block_rows.append([BG[b], sc, band, SK[bschool[b]], round(bband[b], 1), round(bwalk[b], 2), round(bwmin[b], 1),
                               round(bbike[b], 1), round(bdrive[b], 1), round(bbeyond[b], 2), SK[bnear[b]], round(bnear_mi[b], 2)])
        # ---- per school ----
        for k in sorted(areas):
            i = sidx[k]; sel = assign == i; w = wb[sel]
            if not sel.any() or w.sum() <= 0: continue
            o = np.argsort(wm[sel]); cw = np.cumsum(w[o]); med = wm[sel][o][np.searchsorted(cw, cw[-1] / 2)]
            row = dict(scenario=sc, band=band, school=k, residents=round(w.sum()), mean_walk_mi=round(np.average(wm[sel], weights=w) / MILE, 2),
                       median_walk_mi=round(med / MILE, 2))
            for mi in BUS_MI[band]:
                bey = w[wm[sel] > mi * MILE].sum()
                row[f'beyond_{mi:g}mi_share'] = round(bey / w.sum(), 3); row[f'beyond_{mi:g}mi'] = round(bey)
                row[f'beyond_{mi:g}mi_walkmi'] = round(float((w * wm[sel])[wm[sel] > mi * MILE].sum()) / MILE)   # their walking miles, summed
            for m in TT:
                row[f'{m}_min_mean'] = round(np.average(np.nan_to_num(tmin[m][sel], posinf=999), weights=w), 1)
                row[f'{m}_15min_share'] = round(w[tmin[m][sel] <= 15].sum() / w.sum(), 3)
            row['nearest_is_assigned_share'] = round(w[nearest[sel] == i].sum() / w.sum(), 3)
            for m in TT:   # residents per travel-time bin, ';'-separated
                h = np.bincount(np.searchsorted(HIST_MIN, np.nan_to_num(tmin[m][sel], posinf=999), 'right'), w, len(HIST_MIN) + 1)
                row[f'{m}_hist'] = ';'.join(str(int(round(x))) for x in h)
            # bus-eligible residents (beyond the band's bus distance) by walking miles, for the bus ride time histogram
            eb = w * (wm[sel] > thr)
            row['beyond_mi_hist'] = ';'.join(f'{x:.1f}' for x in np.bincount(np.searchsorted(BH_MI, wm[sel] / MILE, 'right'), eb, len(BH_MI) + 1))
            school_rows.append(row)
            # ---- this area's residents travelling to each other school in the region that could take these grades
            # (for custom closures: moved students still live in their old school's area) ----
            ws = w.sum()
            def stats(j):
                wmj = WALK_M[j, sel]; tj = {m: np.nan_to_num(TT[m][j, sel] / 60, posinf=999) for m in TT}
                return [round(ws), round(w[wmj > thr].sum() / ws, 3), round(np.average(wmj, weights=w) / MILE, 2),
                        *[round(np.average(tj[m], weights=w), 1) for m in TT], *[round(w[tj[m] <= 15].sum() / ws, 3) for m in TT],
                        round(w[nearest[sel] == j].sum() / ws, 3),
                        *[[int(round(x)) for x in np.bincount(np.searchsorted(HIST_MIN, tj[m], 'right'), w, len(HIST_MIN) + 1)] for m in TT],
                        round(float((w * wmj)[wmj > thr].sum()) / MILE),
                        [round(float(x), 1) for x in np.bincount(np.searchsorted(BH_MI, wmj / MILE, 'right'), w * (wmj > thr), len(BH_MI) + 1)]]
            for r in TAKERS[band]:
                if r != k and D['region_of'].get(r) == D['region_of'].get(k):
                    PAIRS.setdefault(sc, {}).setdefault(k, {}).setdefault(band, {})[r] = stats(sidx[r])
        # ---- district ----
        d = dict(residents=round(wb.sum()), mean_walk_mi=round(np.average(wm[has], weights=wb[has]) / MILE, 2),
                 nearest_is_assigned_share=round(wb[(nearest == assign)].sum() / wb.sum(), 3))
        for mi in BUS_MI[band]: d[f'beyond_{mi:g}mi'] = round(wb[wm > mi * MILE].sum()); d[f'beyond_{mi:g}mi_share'] = round(wb[wm > mi * MILE].sum() / wb.sum(), 3)
        for mi in BUS_MI[band]: d[f'beyond_{mi:g}mi_walkmi'] = round(float((wb * wm)[wm > mi * MILE].sum()) / MILE)
        for m in TT: d[f'{m}_15min_share'] = round(wb[tmin[m] <= 15].sum() / wb.sum(), 3)
        district.setdefault(sc, {})[band] = d
    log(f'{sc}: ' + '; '.join(f"{b} beyond {BUS_HEADLINE[b]:g} mi {district[sc][b][f'beyond_{BUS_HEADLINE[b]:g}mi']:,} of {district[sc][b]['residents']:,}" for b in BANDS))

# changes vs Status Quo
for sc in ['A', 'B']:
    for band in BANDS:
        d, q = district[sc][band], district['SQ'][band]
        d['vs_SQ'] = {k: round(d[k] - q[k], 3) for k in d if isinstance(d[k], (int, float)) and k in q}

with open(os.path.join(OUT, 'block-access.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['GEOID', 'scenario', 'band', 'school', 'band_age_residents', 'walk_mi', 'walk_min', 'bike_min', 'drive_min',
                'beyond_bus_distance_share', 'nearest_school', 'nearest_walk_mi'])
    w.writerows(block_rows)
cols = list(dict.fromkeys(k for r in school_rows for k in r))
with open(os.path.join(OUT, 'school-access.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, cols); w.writeheader(); w.writerows(school_rows)
# area -> other school travel, same layout as the explorer's per-area arrays plus their walking miles beyond bus distance
json.dump(dict(layout='residents, beyond share, mean walk mi, mean walk/bike/drive min, within 15 min walk/bike/drive, '
                      'nearest share, walk/bike/drive histogram, walking miles beyond bus distance, '
                      'bus-eligible residents by walking miles (bins edged at bh_mi)', bh_mi=BH_MI, pairs=PAIRS),
          open(os.path.join(OUT, 'school-pairs.json'), 'w', encoding='utf-8'), separators=(',', ':'))
json.dump(dict(method=__doc__.split('Outputs')[0].strip(), built=time.strftime('%Y-%m-%d'), walk_mph=WALK_MPH, bike_mph=BIKE_MPH,
               drive_factor_vs_osrm=round(DRIVE_FACTOR, 3), hist_min=HIST_MIN, bh_mi=BH_MI, bus_headline_miles=BUS_HEADLINE, grid_m=GRID_M, district=district),
          open(os.path.join(OUT, 'district-access.json'), 'w', encoding='utf-8'), indent=1)
# block x school matrix, resident-weighted mean minutes per block (for custom scenarios)
wsum = np.bincount(PB, PW[:, 0], NB)
mat = {m: np.stack([np.bincount(PB, PW[:, 0] * np.nan_to_num(TT[m][i] / 60, posinf=999), NB) / np.maximum(wsum, 1e-9) for i in range(NS)]).astype(np.float32) for m in TT}
np.savez_compressed(os.path.join(OUT, 'block-school-matrix.npz'), geoid=np.array(BG), school=np.array(SK), weights=BW.astype(np.float32), **{f'{m}_min': v for m, v in mat.items()})
log(f'wrote {len(block_rows):,} block rows, {len(school_rows)} school rows -> {os.path.relpath(OUT, ROOT)}')

# ---------- trip corridors: where each school's trips would run, by bike and by car ----------
# Each resident point's band-age residents follow the shortest-path tree (bike: the low-stress route; drive: the
# fastest) to their assigned school; summing them along the tree gives how many of the school's residents would use
# each street segment. Kept: segments carrying at least CORR_MIN of the school's residents, as polylines by share
# level, plus the named streets carrying the most. For each school a scenario closes, the same for its Status Quo area's
# residents going to their new schools.
CORR_MIN, CORR_LEVELS = 0.03, [0.03, 0.1, 0.25, 0.5]
TB = {'ES': ['k5'], 'K8': ['k5', '68'], 'MS': ['68'], 'HS': ['912']}
STREET_CLASS = {'trunk': 'A', 'trunk_link': 'A', 'primary': 'A', 'primary_link': 'A', 'secondary': 'A', 'secondary_link': 'A', 'tertiary': 'C', 'tertiary_link': 'C'}
LON_ = np.array([S['nodes'][k][0] for k in ids]); LAT_ = np.array([S['nodes'][k][1] for k in ids])
WAYNAME = [t.get('name', '') for t in WTAGS]
def dp(xy, tol):
    """Douglas-Peucker on an (n, 2) metre array; returns kept indices"""
    keep = np.zeros(len(xy), bool); keep[[0, -1]] = True; st = [(0, len(xy) - 1)]
    while st:
        a, b = st.pop()
        if b <= a + 1: continue
        p, q = xy[a], xy[b]; d = q - p; n = math.hypot(*d) or 1e-9
        e_ = xy[a + 1:b] - p; dist = np.abs(d[0] * e_[:, 1] - d[1] * e_[:, 0]) / n
        i = int(dist.argmax())
        if dist[i] > tol: keep[a + 1 + i] = True; st += [(a, a + 1 + i), (a + 1 + i, b)]
    return np.nonzero(keep)[0]
def enc(nodes):
    xy = np.c_[NX[nodes], NY[nodes]]; kp = nodes[dp(xy, 6.0)]
    la, lo = np.round(LAT_[kp] * 1e5).astype(int), np.round(LON_[kp] * 1e5).astype(int)
    out = [int(la[0]), int(lo[0])]
    for i in range(1, len(kp)): out += [int(la[i] - la[i - 1]), int(lo[i] - lo[i - 1])]
    return out
# arterial hazards on bike and walk corridors: where a route crosses a major arterial (trunk, primary, secondary) and
# stretches that run along one (for bikes, unless on a path or in a protected, separated or buffered bike lane)
HZ_ART = {'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link'}
SEG_ART = np.isin(HW[R], list(HZ_ART))
NODE_ART = np.zeros(NN, bool); NODE_ART[U[SEG_ART]] = True; NODE_ART[V[SEG_ART]] = True
NODE_ART_NAME = np.full(NN, '', dtype=object)
for sg in np.nonzero(SEG_ART)[0]:
    nm = WAYNAME[R[sg]] or HW[R[sg]]
    NODE_ART_NAME[U[sg]] = NODE_ART_NAME[U[sg]] or nm; NODE_ART_NAME[V[sg]] = NODE_ART_NAME[V[sg]] or nm
# a bike route on an arterial is not a hazard where it rides a path, a protected / separated lane or a buffered lane;
# standard and advisory bike lanes, shared-lane markings and enhanced shared roadways still are
PROTECTED = np.isin(seg_fac, ['TRL', 'PBL', 'SIR', 'BBL', 'BBBL', 'SBBL'])
HZ_MIN_RUN = 40.0   # metres along an arterial before it counts
def hazards(m, pred, K, sh, kept):
    _, sg = edge_lookup(m, K, pred[K])
    ok = sg >= 0
    along = np.zeros(NN, bool)
    a = ok & SEG_ART[np.where(ok, sg, 0)]
    if m == 'bike': a &= ~PROTECTED[np.where(ok, sg, 0)]
    along[K[a]] = True
    seg_of = np.full(NN, -1); seg_of[K] = np.where(ok, sg, -1)
    on_art = np.zeros(NN, bool); on_art[K[ok & SEG_ART[np.where(ok, sg, 0)]]] = True   # on the arterial at all (protected or not)
    nonart_child = np.zeros(NN, bool); nonart_child[pred[K[~on_art[K]]]] = True
    art_child = np.zeros(NN, bool); art_child[pred[K[along[K]]]] = True
    out = []
    # crossings: the route goes through an arterial intersection on side streets (in and out not along the arterial)
    xs = sorted(K[NODE_ART[K] & ~on_art[K] & nonart_child[K]], key=lambda p: -sh[p])
    keep = []   # one point per crossing: merge points within 40 m on the same arterial (divided roads, wide intersections)
    for p in xs:
        if any(NODE_ART_NAME[q] == NODE_ART_NAME[p] and math.hypot(NX[p] - NX[q], NY[p] - NY[q]) < 40 for q in keep): continue
        keep.append(p)
        out.append(['x', round(float(LAT_[p]), 5), round(float(LON_[p]), 5), round(float(sh[p]), 3), NODE_ART_NAME[p], 0])
    # stretches along an arterial
    for n in K[along[K] & ~art_child[K]]:
        seq, length, cur = [n], 0.0, n
        while along[cur] and kept[cur]:
            length += L[seg_of[cur]] if seg_of[cur] >= 0 else 0; cur = pred[cur]; seq.append(cur)
            if cur < 0: break
        if length < HZ_MIN_RUN: continue
        mid = seq[len(seq) // 2]; nm = WAYNAME[R[seg_of[n]]] if seg_of[n] >= 0 else ''
        out.append(['f', round(float(LAT_[mid]), 5), round(float(LON_[mid]), 5), round(float(sh[seq[-2]]), 3), nm, int(round(length))])
    return out
HZN = None
def corridors(m, si, cols):
    global HZN
    """cols: list of (source point indices, weights). Returns per column {w, L: [[level, path]], st: [[name, share]]}"""
    pred = PRED[m][si].astype(np.int64); has = pred >= 0
    depth = tree_sum(pred, np.ones(NN))
    C = len(cols); F = np.zeros((NN, C))
    for c, (pts, w) in enumerate(cols): np.add.at(F[:, c], PNODE[m][pts], w)
    srcd = max((depth[PNODE[m][pts]].max() for pts, _ in cols if len(pts)), default=0)
    nodes = np.nonzero(has & (depth <= srcd))[0]
    nodes = nodes[np.argsort(-depth[nodes], kind='stable')]
    dv = depth[nodes]; cut = np.r_[0, np.nonzero(dv[1:] != dv[:-1])[0] + 1, len(nodes)]
    for a, b in zip(cut[:-1], cut[1:]):
        idx = nodes[a:b]; np.add.at(F, pred[idx], F[idx])
    if m in ('bike', 'walk'):   # hazards met on each node's route: arterial stretches and arterial crossings
        _, sga = edge_lookup(m, np.arange(NN), np.maximum(pred, 0))
        okk = (pred >= 0) & (sga >= 0); sgs = np.where(okk, sga, 0)
        anyart = okk & SEG_ART[sgs]
        al = anyart & (~PROTECTED[sgs] if m == 'bike' else True)
        ind = (al | (NODE_ART & ~anyart & (pred >= 0))).astype(float)
        HZN = tree_sum(pred, ind)
    out = []
    for c, (pts, w) in enumerate(cols):
        W = float(np.sum(w))
        if W <= 0: out.append(None); continue
        sh = F[:, c] / W
        kept = has & (sh >= CORR_MIN)
        K = np.nonzero(kept)[0]
        lvl = np.searchsorted(CORR_LEVELS, sh, 'right') - 1
        nchild = np.bincount(pred[K], minlength=NN)
        child_of = np.full(NN, -1); child_of[pred[K]] = K   # (only meaningful where nchild == 1)
        starts = [n for n in K if nchild[n] != 1 or lvl[child_of[n]] != lvl[n]]
        lines = []
        for n in starts:
            seq = [n]; cur = n
            while True:
                p = pred[cur]; seq.append(p)
                if not kept[p] or nchild[p] != 1 or lvl[p] != lvl[n]: break
                cur = p
            lines.append([int(lvl[n]), enc(np.array(seq))])
        _, seg = edge_lookup(m, K, pred[K])
        names = {}   # name -> [max share, metres by street class (A arterial, C collector, L local), metres by bike facility]
        for n, sg in zip(K, seg):
            if sg < 0: continue
            nm = WAYNAME[R[sg]]
            if not nm: continue
            e = names.setdefault(nm, [0.0, {}, {}])
            e[0] = max(e[0], sh[n])
            cl = STREET_CLASS.get(HW[R[sg]], 'L'); e[1][cl] = e[1].get(cl, 0) + L[sg]
            e[2][seg_fac[sg]] = e[2].get(seg_fac[sg], 0) + L[sg]
        top = lambda d: max(d, key=d.get) if d else ''
        st = [[nm, round(v[0], 3), top(v[1]), top(v[2]) if m == 'bike' else ''] for nm, v in sorted(names.items(), key=lambda kv: -kv[1][0]) if v[0] >= 0.05][:14]
        res = dict(w=round(W), L=lines, st=st)
        if m in ('bike', 'walk'):
            res['H'] = hazards(m, pred, K, sh, kept)
            res['hx'] = round(float(np.sum(w[HZN[PNODE[m][pts]] > 0]) / W), 3)
        out.append(res)
    return out
CORR = {'levels': CORR_LEVELS, 'min_share': CORR_MIN, 'S': {}, 'F': {}}
for m in ('bike', 'drive', 'walk'):
    CORR['S'][m] = {sc: {} for sc in SCENS}; CORR['F'][m] = {sc: {} for sc in SCENS[1:]}
    for k in SK:
        i = sidx[k]; cols, tags = [], []
        prev = None
        for sc in SCENS:
            t = D['types'].get(sc, {}).get(k)
            if not t or D['detail'].get(sc, {}).get(k, {}).get('closed'): continue
            sel = np.zeros(NP); 
            for b in TB.get(t, []): sel += PW[:, BCOL[b]] * (ASSIGN[sc, b] == i)
            pts = np.nonzero(sel > 0)[0]
            if not len(pts): continue
            if prev is not None and sc != 'SQ' and len(prev) == len(sel) and np.allclose(prev, sel): continue   # same as Status Quo
            if sc == 'SQ': prev = sel
            cols.append((pts, sel[pts])); tags.append(('S', sc, k))
        # Status Quo areas of schools a scenario closes, going to this school
        for sc in SCENS[1:]:
            for c_ in SK:
                if not D['detail'].get(sc, {}).get(c_, {}).get('closed'): continue
                sel = np.zeros(NP)
                for b in TB.get(D['types']['SQ'].get(c_), []): sel += PW[:, BCOL[b]] * (ASSIGN['SQ', b] == sidx[c_]) * (ASSIGN[sc, b] == i)
                pts = np.nonzero(sel > 0)[0]
                if len(pts) and sel[pts].sum() >= 5: cols.append((pts, sel[pts])); tags.append(('F', sc, c_))
        if not cols: continue
        for (kind, sc, key), res in zip(tags, corridors(m, i, cols)):
            if not res: continue
            if kind == 'S': CORR['S'][m][sc][key] = res
            else: CORR['F'][m][sc].setdefault(key, []).append(dict(to=k, **res))
    log(f'corridors {m}: ' + ', '.join(f'{sc} {len(CORR["S"][m][sc])} schools' for sc in SCENS))
CORR['hazards'] = ('Bike and walk corridors: x = the route crosses a major arterial (trunk, primary or secondary road) at an intersection, '
                   f'f = it runs along one for at least {HZ_MIN_RUN:g} m (bikes: unless on a path or in a protected, separated or buffered bike lane); '
                   "with the share of the area's residents whose route passes there; hx = share of the area's residents whose route "
                   "has at least one. Signals and crosswalks are not known.")
CORR['method'] = ('Shortest-path trees from every resident point to its assigned school; bike routes minimise travel time x street stress '
                  '(PBOT bicycle network facility, else OpenStreetMap tags; arterial class, speed, lanes) with a climbing penalty from '
                  'ground elevation; drive routes minimise free-flow time. Residents = 2020 Census residents of the grades\' ages, '
                  'not PPS students; everyone is assumed to make the trip by that mode.')
json.dump(CORR, open(os.path.join(OUT, 'corridors.json'), 'w', encoding='utf-8'), separators=(',', ':'))
log(f'corridors.json {os.path.getsize(os.path.join(OUT, "corridors.json")) / 1e6:.1f} MB')
