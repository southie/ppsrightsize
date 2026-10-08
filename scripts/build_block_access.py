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
                      one-way streets respected unless bikes are exempt, BIKE_MPH, flat (hills ignored)
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
MODES = {
    'walk': graph(RL[R, 0], RL[R, 0], ones * WALK_MPH * MPH),
    'bike': graph(RL[R, 1], RL[R, 2], ones * BIKE_MPH * MPH),
    'drive': graph(RL[R, 3], RL[R, 4], seg_mph * MPH),
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
TT = {}   # mode -> (NS, NP) float32 seconds
SS = {}   # mode -> (NS, NS) seconds school -> school
for m, G in MODES.items():
    cand, tree = TREES[m]
    pd_, pi = tree.query(np.c_[PXm, PYm]); pnode = cand[pi]
    sd_, si = tree.query(np.c_[SXm, SYm]); snode = cand[si]
    Gt = G.T.tocsr()
    out = np.empty((NS, NP), np.float32); ss = np.empty((NS, NS))
    for b0 in range(0, NS, 8):
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
for sc in SCENS:
    for band in BANDS:
        areas = AREAS[sc, band]
        assign = np.full(NP, -1)
        for k, polys in areas.items():
            assign[inside(PX, PY, polys) & (assign < 0)] = sidx[k]
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
            school_rows.append(row)
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
json.dump(dict(method=__doc__.split('Outputs')[0].strip(), built=time.strftime('%Y-%m-%d'), walk_mph=WALK_MPH, bike_mph=BIKE_MPH,
               drive_factor_vs_osrm=round(DRIVE_FACTOR, 3), hist_min=HIST_MIN, bus_headline_miles=BUS_HEADLINE, grid_m=GRID_M, district=district),
          open(os.path.join(OUT, 'district-access.json'), 'w', encoding='utf-8'), indent=1)
# block x school matrix, resident-weighted mean minutes per block (for custom scenarios)
wsum = np.bincount(PB, PW[:, 0], NB)
mat = {m: np.stack([np.bincount(PB, PW[:, 0] * np.nan_to_num(TT[m][i] / 60, posinf=999), NB) / np.maximum(wsum, 1e-9) for i in range(NS)]).astype(np.float32) for m in TT}
np.savez_compressed(os.path.join(OUT, 'block-school-matrix.npz'), geoid=np.array(BG), school=np.array(SK), weights=BW.astype(np.float32), **{f'{m}_min': v for m, v in mat.items()})
log(f'wrote {len(block_rows):,} block rows, {len(school_rows)} school rows -> {os.path.relpath(OUT, ROOT)}')
