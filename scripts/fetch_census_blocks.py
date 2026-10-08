"""2020 Census blocks (geometry, POP100, HU100) covering the PPS attendance areas, from the Census
TIGERweb service, saved to source/census-blocks/blocks_2020.geojson for scripts/patch_reach.py."""
import glob, json, os, sys, time
import requests
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'source', 'pps-explorer-boundaries')
OUT = os.path.join(ROOT, 'source', 'census-blocks', 'blocks_2020.geojson')
URL = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/2/query'
PAGE = 2000

def coords(g):
    for poly in ([g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']):
        yield from poly[0]

pts = [p for f in glob.glob(os.path.join(SRC, '*_*.geojson')) if not f.endswith(('_schools.geojson', '_changed.geojson'))
       for ft in json.load(open(f, encoding='utf-8'))['features'] for p in coords(ft['geometry'])]
x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
print(f'bbox {x0:.4f},{y0:.4f},{x1:.4f},{y1:.4f}')

feats, offset = [], 0
while True:
    r = requests.post(URL, data={
        'geometry': f'{x0},{y0},{x1},{y1}', 'geometryType': 'esriGeometryEnvelope', 'inSR': 4326,
        'spatialRel': 'esriSpatialRelIntersects', 'outFields': 'GEOID,POP100,HU100,AREALAND', 'returnGeometry': 'true',
        'outSR': 4326, 'geometryPrecision': 5, 'orderByFields': 'OBJECTID', 'resultOffset': offset, 'resultRecordCount': PAGE,
        'f': 'geojson'}, timeout=120)
    r.raise_for_status()
    page = r.json().get('features', [])
    feats += page
    print(f'{len(feats)} blocks')
    if len(page) < PAGE: break
    offset += PAGE
    time.sleep(0.5)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({'type': 'FeatureCollection', 'features': feats}, open(OUT, 'w', encoding='utf-8'), separators=(',', ':'))
print(f'wrote {OUT} ({os.path.getsize(OUT) / 1e6:.1f} MB), population {sum(f["properties"]["POP100"] or 0 for f in feats):,}')
