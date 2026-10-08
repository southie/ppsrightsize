"""Private-school enrollment trend near PPS from the NCES Private School Universe Survey (PSS).

Schools: Oregon private schools inside the PPS district or within MAX_OUT_MI miles of its edge (the same
rule as the explorer's private-school layer), from the PSS public-use files in source/nces-pss
(2015-16, 2017-18, 2019-20, 2021-22, 2023-24). Enrollment is NUMSTUDS (K-12 plus ungraded; PSS does not
count pre-K-only programs). Schools are followed across years by PPIN.

Writes private-school-enrollment-pss.csv (one row per school, enrollment by survey year) and prints a summary.
"""
import csv, glob, io, json, math, os, re, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSS = os.path.join(ROOT, 'source', 'nces-pss')
BOUNDS = os.path.join(ROOT, 'source', 'pps-data', 'data', 'raw', 'pps_boundaries_high.geojson')
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
OUT = os.path.join(ROOT, 'private-school-enrollment-pss.csv')
MAX_OUT_MI = 2.0
WAVES = [('1516', '2015-16'), ('1718', '2017-18'), ('1920', '2019-20'), ('2122', '2021-22'), ('2324', '2023-24')]

# ---------- PPS district geometry ----------
polys, segs = [], []
for f in json.load(open(BOUNDS, encoding='utf-8'))['features']:
    g = f['geometry']
    for p in ([g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']):
        polys.append(p)
        for ring in p: segs += list(zip(ring, ring[1:]))

def in_district(lat, lng):
    for p in polys:
        c = False
        for ring in p:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1: c = not c
        if c: return True
    return False

def miles_to_edge(lat, lng):
    kx, ky = math.cos(math.radians(lat)) * 69.17, 69.0
    best = math.inf
    for (x1, y1), (x2, y2) in segs:
        ax, ay, bx, by = (x1 - lng) * kx, (y1 - lat) * ky, (x2 - lng) * kx, (y2 - lat) * ky
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, -(ax * dx + ay * dy) / ((dx * dx + dy * dy) or 1)))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best

# ---------- PSS waves ----------
schools = {}   # ppin -> {name, city, zip, lat, lng, inside, enroll: {year: n}}
for code, year in WAVES:
    zf = zipfile.ZipFile(os.path.join(PSS, f'pss{code}_pu_csv.zip'))
    name = next(n for n in zf.namelist() if n.lower().endswith('.csv'))
    rows = csv.DictReader(io.TextIOWrapper(zf.open(name), encoding='latin-1'))
    n_or = 0
    for r in rows:
        r = {k.upper(): v for k, v in r.items()}
        if r['PSTABB'] != 'OR': continue
        n_or += 1
        lat = float(r.get(f'LATITUDE{code[2:]}') or 0); lng = float(r.get(f'LONGITUDE{code[2:]}') or 0)
        if not lat: continue
        inside = in_district(lat, lng)
        if not inside and miles_to_edge(lat, lng) > MAX_OUT_MI: continue
        s = schools.setdefault(r['PPIN'], {'enroll': {}})
        s.update(name=r['PINST'].strip(), city=r['PCITY'].strip().title(), zip=r['PZIP'][:5], lat=lat, lng=lng, inside=inside)
        s['enroll'][year] = int(float(r['NUMSTUDS'] or 0))
    print(f'{year}: {n_or} Oregon private schools in the file, {sum(year in s["enroll"] for s in schools.values())} near PPS')

Y = [y for _, y in WAVES]
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['ppin', 'name', 'city', 'zip', 'inside_pps', *[f'enroll_{y}' for y in Y]])
    for ppin, s in sorted(schools.items(), key=lambda kv: kv[1]['name']):
        w.writerow([ppin, s['name'], s['city'], s['zip'], s['inside'], *[s['enroll'].get(y, '') for y in Y]])
print(f'wrote {os.path.basename(OUT)}: {len(schools)} schools')

# ---------- summary ----------
def tot(sel, y): return sum(s['enroll'][y] for s in sel if y in s['enroll'])
allp = list(schools.values())
print('\nAll schools reporting in each survey year (schools come and go):')
for y in Y:
    rep = [s for s in allp if y in s['enroll']]
    print(f'  {y}: {len(rep):3d} schools, {tot(rep, y):6,} students')
for label, sel in [('Every year 2015-16 to 2023-24', [s for s in allp if all(y in s['enroll'] for y in Y)]),
                   ('Every year 2019-20 to 2023-24', [s for s in allp if all(y in s['enroll'] for y in Y[2:])])]:
    yrs = Y if label.startswith('Every year 2015') else Y[2:]
    print(f'\nSame schools, {label}: {len(sel)} schools')
    for scope, sub in [('all', sel), ('inside PPS', [s for s in sel if s['inside']])]:
        vals = [tot(sub, y) for y in yrs]
        print(f'  {scope:10s} ' + '  '.join(f'{y} {v:6,}' for y, v in zip(yrs, vals)) + f'   change {vals[-1] - vals[0]:+,} ({(vals[-1] / vals[0] - 1) * 100:+.1f}%)')
sel = [s for s in allp if '2019-20' in s['enroll'] and '2023-24' in s['enroll'] and s['enroll']['2019-20'] >= 50]
ch = sorted(sel, key=lambda s: s['enroll']['2023-24'] - s['enroll']['2019-20'])
fmt = lambda s: f"{s['name'][:44]:44s} {s['city'][:12]:12s} {s['enroll']['2019-20']:5d} -> {s['enroll']['2023-24']:5d} ({s['enroll']['2023-24'] - s['enroll']['2019-20']:+d})"
print('\nLargest declines 2019-20 -> 2023-24 (schools with 50+ students in 2019-20):'); [print('  ' + fmt(s)) for s in ch[:8]]
print('Largest gains:'); [print('  ' + fmt(s)) for s in ch[::-1][:8]]
steady = [s for s in sel if abs(s['enroll']['2023-24'] / s['enroll']['2019-20'] - 1) <= .10]
print(f'\n{len(steady)} of {len(sel)} such schools are within +/-10% of their 2019-20 enrollment')
new = [s for s in allp if '2023-24' in s['enroll'] and not any(y in s['enroll'] for y in Y[:3])]
gone = [s for s in allp if '2019-20' in s['enroll'] and not any(y in s['enroll'] for y in Y[3:])]
print(f'In 2023-24 but not 2015-16 to 2019-20: {len(new)} schools, {sum(s["enroll"]["2023-24"] for s in new):,} students')
print(f'In 2019-20 but not 2021-22 or 2023-24: {len(gone)} schools, {sum(s["enroll"]["2019-20"] for s in gone):,} students (closed, or did not respond)')

# ---------- coverage of the explorer's private schools ----------
m = re.search(r'const D = (\{.*?\});\r?\nconst esc', open(PAGE, encoding='utf-8').read(), re.S)
P = json.loads(m.group(1))['private']
def near(x):
    best = min(allp, key=lambda s: (s['lat'] - x['lat']) ** 2 + ((s['lng'] - x['lng']) * .7) ** 2)
    d = math.hypot((best['lat'] - x['lat']) * 69, (best['lng'] - x['lng']) * 48.4)
    return best if d < .15 else None
hits = [x for x in P if not x.get('preKOnly') and near(x)]
print(f"\nExplorer private schools found in PSS (within 0.15 mi): {sum(1 for x in P if near(x))} of {len(P)}")
