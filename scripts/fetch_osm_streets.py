"""OpenStreetMap streets, paths and trails covering the PPS attendance areas (plus a buffer), from the Overpass API,
saved to source/osm/streets.json for scripts/build_block_access.py.

One query per tile (the area split into a 2 x 2 grid) so no single request is huge; each tile is cached, so a rerun
only fetches what is missing. Ways keep only the tags the walk / bike / drive rules need.
"""
import glob, json, os, sys, time
import requests
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'source', 'pps-explorer-boundaries')
OUT_DIR = os.path.join(ROOT, 'source', 'osm'); os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, 'streets.json')
SERVERS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
UA = 'pps-rightsizing-analysis/1.0 (personal research, low volume)'
BUFFER = 0.03   # degrees (~2.5-3 km) beyond the attendance areas, so routes can leave and re-enter the district
KEEP = {'highway', 'oneway', 'junction', 'maxspeed', 'access', 'foot', 'bicycle', 'motor_vehicle', 'motorcar', 'vehicle',
        'service', 'oneway:bicycle', 'cycleway', 'sidewalk', 'area', 'name'}

def polys_of(g):
    return [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
pts = [p for f in glob.glob(os.path.join(SRC, '*_*.geojson')) if not f.endswith(('_schools.geojson', '_changed.geojson'))
       for ft in json.load(open(f, encoding='utf-8'))['features'] for poly in polys_of(ft['geometry']) for p in poly[0]]
W, S = min(p[0] for p in pts) - BUFFER, min(p[1] for p in pts) - BUFFER
E, N = max(p[0] for p in pts) + BUFFER, max(p[1] for p in pts) + BUFFER
print(f'bbox S {S:.4f} W {W:.4f} N {N:.4f} E {E:.4f}')

def fetch(s, w, n, e, tries=4):
    q = f'[out:json][timeout:900];way["highway"]({s},{w},{n},{e});out body;>;out skel qt;'
    delay = 10
    for i in range(tries):
        url = SERVERS[i % len(SERVERS)]
        try:
            r = requests.post(url, data={'data': q}, headers={'User-Agent': UA}, timeout=1200)
            if r.status_code == 200: return r.json()
            print(f'    HTTP {r.status_code} from {url}; waiting {delay}s')
        except Exception as ex:
            print(f'    {type(ex).__name__}: {ex}; waiting {delay}s')
        time.sleep(delay); delay = min(delay * 2, 300)
    return None

nodes, ways = {}, {}
def tile(s, w, n, e, name, depth=0):
    """fetch one tile (cached); if Overpass keeps failing, split it into 2 x 2 smaller tiles"""
    cache = os.path.join(OUT_DIR, f'tile_{name}.json')
    if os.path.exists(cache): return [json.load(open(cache, encoding='utf-8'))]
    print(f'tile {name}: fetching'); t0 = time.time()
    d = fetch(s, w, n, e)
    if d is None:
        if depth >= 2: sys.exit(f'Overpass failed for tile {name}')
        print(f'  splitting tile {name}')
        ms, mw = (s + n) / 2, (w + e) / 2
        return [x for i, (a, b) in enumerate([(s, ms), (ms, n)]) for j, (c, dd) in enumerate([(w, mw), (mw, e)])
                for x in tile(a, c, b, dd, f'{name}{i}{j}', depth + 1)]
    json.dump(d, open(cache, 'w', encoding='utf-8'))
    print(f'  {len(d["elements"]):,} elements in {time.time() - t0:.0f}s')
    time.sleep(5)
    return [d]
NT = 2
for i in range(NT):
    for j in range(NT):
        for d in tile(S + (N - S) * i / NT, W + (E - W) * j / NT, S + (N - S) * (i + 1) / NT, W + (E - W) * (j + 1) / NT, f'{i}{j}'):
            for el in d['elements']:
                if el['type'] == 'node': nodes[el['id']] = (round(el['lon'], 7), round(el['lat'], 7))
                elif el['type'] == 'way': ways[el['id']] = dict(nodes=el['nodes'], tags={k: v for k, v in el.get('tags', {}).items() if k in KEEP})
json.dump(dict(bbox=[W, S, E, N], fetched=time.strftime('%Y-%m-%d'), nodes={str(k): v for k, v in nodes.items()},
               ways=[dict(id=k, **v) for k, v in ways.items()]), open(OUT, 'w', encoding='utf-8'), separators=(',', ':'))
for f in glob.glob(os.path.join(OUT_DIR, 'tile_*.json')): os.remove(f)
print(f'{len(ways):,} ways, {len(nodes):,} nodes -> {os.path.relpath(OUT, ROOT)} ({os.path.getsize(OUT) / 1e6:.0f} MB)')
