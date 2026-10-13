"""Ground elevation for the bike routing's hill penalty: Mapzen/Tilezen "terrarium" elevation tiles (AWS Open Data,
s3://elevation-tiles-prod; in the US from USGS 3DEP / NED) at zoom 13 (about 13 m per pixel at Portland's latitude),
covering the street network's bounding box (source/osm/streets.json). Elevation (m) = R*256 + G + B/256 - 32768.
Output: source/elevation/z13_<x>_<y>.png and source/elevation/index.json
"""
import json, math, os, sys, time
import requests
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'source', 'elevation'); os.makedirs(OUT, exist_ok=True)
Z = 13
W, S, E, N = json.load(open(os.path.join(ROOT, 'source', 'osm', 'streets.json'), encoding='utf-8'))['bbox']
def tx(lon): return int((lon + 180) / 360 * 2 ** Z)
def ty(lat): r = math.radians(lat); return int((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2 ** Z)
xs, ys = range(tx(W), tx(E) + 1), range(ty(N), ty(S) + 1)
n = 0
for x in xs:
    for y in ys:
        p = os.path.join(OUT, f'z{Z}_{x}_{y}.png')
        if os.path.exists(p): continue
        r = requests.get(f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png', timeout=60)
        r.raise_for_status(); open(p, 'wb').write(r.content); n += 1
json.dump(dict(z=Z, x=[xs[0], xs[-1]], y=[ys[0], ys[-1]], source='https://registry.opendata.aws/terrain-tiles/ (terrarium)',
               fetched=time.strftime('%Y-%m-%d')), open(os.path.join(OUT, 'index.json'), 'w'))
print(f'{len(xs) * len(ys)} tiles ({n} fetched)')
