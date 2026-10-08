"""Assessor real market value (land and improvements) for each PPS school site, from Multnomah County's
public tax-lot service (Taxlots_Orion_Public; 2025 assessment roll).

A site is every tax lot owned by the district within RADIUS_M of the school's location; each lot counts toward
its nearest school only (by lot centroid). Lots owned by others are left out even under a school point (Rosa Parks
shares a campus lot with the New Columbia Youth Center). West Sylvan is in Washington County, outside this service. Public school property is tax-exempt, so
assessed value is 0, but the assessor still records real market value (RMV).

Writes source/assessor/pps-school-taxlots-2025.csv (one row per lot) and pps-school-land-2025.csv (per school).
"""
import csv, json, math, os, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
OUT = os.path.join(ROOT, 'source', 'assessor')
URL = 'https://www3.multco.us/gisagspublic/rest/services/DART/Taxlots_Orion_Public/MapServer/0/query'
RADIUS_M = 200
FIELDS = 'PROPID,MAPTAXLOT,NAME,SITUSADDR,SIZEACRES,ZONING,EXEMPTION,PROPCLASS,ROLLYEAR,ROLLLAND,ROLLIMP,xCentroid,yCentroid'
PPS = re.compile(r'(SCHOOL DIST(RICT)?|PORTLAND PUBLIC SCHOOL).*?(NO\.?|#)\s*1J?\b(?!\d)')   # district 1(J), not 10, 3, 40 ...

D = json.loads(re.search(r'const D = (\{.*?\});\r?\nconst esc', open(PAGE, encoding='utf-8').read(), re.S).group(1))

def query(lng, lat, distance=None):
    p = {'geometry': f'{lng},{lat}', 'geometryType': 'esriGeometryPoint', 'inSR': 4326, 'spatialRel': 'esriSpatialRelIntersects',
         'outFields': FIELDS, 'returnGeometry': 'true', 'outSR': 4326, 'f': 'json'}
    if distance: p.update(distance=distance, units='esriSRUnit_Meter')
    for attempt in range(5):
        try:
            d = json.load(urllib.request.urlopen(URL + '?' + urllib.parse.urlencode(p), timeout=60))
            if 'error' in d: raise RuntimeError(d['error'])
            out = []
            for f in d.get('features', []):
                pts = [p for ring in f['geometry']['rings'] for p in ring]
                out.append(dict(f['attributes'], lng=sum(p[0] for p in pts) / len(pts), lat=sum(p[1] for p in pts) / len(pts)))
            return out
        except Exception as e:
            print(f'  retry {attempt + 1}: {e}'); time.sleep(2 * (attempt + 1))
    raise SystemExit('county service unavailable')

def miles(a, s):
    return math.hypot((a['lat'] - s['lat']) * 69.0, (a['lng'] - s['lng']) * math.cos(math.radians(s['lat'])) * 69.17)

lots, under_pt, foreign = {}, {}, []   # PROPID -> lot; school -> PROPID under its point
for s in D['schools']:
    for a in query(s['lng'], s['lat']):
        if PPS.search(a['NAME'] or ''): under_pt[s['key']] = a['PROPID']
        else: foreign.append((s['key'], a['NAME']))
    for a in query(s['lng'], s['lat'], RADIUS_M):
        if PPS.search(a['NAME'] or ''): lots.setdefault(a['PROPID'], dict(a, cands=set()))['cands'].add(s['key'])
    time.sleep(0.2)
SK = {s['key']: s for s in D['schools']}
site = {k: [] for k in SK}
for pid, a in lots.items():
    owner = next((k for k, p in under_pt.items() if p == pid), None)   # a lot under a school point stays with it
    k = owner or min(a['cands'], key=lambda c: miles(a, SK[c]))
    a['under'] = owner == k
    site[k].append(a)

with open(os.path.join(OUT, 'pps-school-taxlots-2025.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['school_key', 'propid', 'maptaxlot', 'owner', 'situs', 'acres', 'zoning', 'exemption', 'propclass', 'roll_year', 'rmv_land', 'rmv_improvements', 'under_school_point'])
    for k, ls in site.items():
        for a in ls:
            w.writerow([k, a['PROPID'], a['MAPTAXLOT'], a['NAME'], a['SITUSADDR'], a['SIZEACRES'], a['ZONING'], (a['EXEMPTION'] or '').strip(), a['PROPCLASS'],
                        a['ROLLYEAR'], a['ROLLLAND'], a['ROLLIMP'], a['under']])
with open(os.path.join(OUT, 'pps-school-land-2025.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['school_key', 'lots', 'acres', 'rmv_land', 'rmv_improvements', 'rmv_total', 'zoning', 'owner_under_point'])
    for k, ls in site.items():
        land = sum(a['ROLLLAND'] or 0 for a in ls); imp = sum(a['ROLLIMP'] or 0 for a in ls)
        under = next((a for a in ls if a['under']), None) or max(ls, key=lambda a: a['SIZEACRES'] or 0, default=None)
        w.writerow([k, len(ls), round(sum(a['SIZEACRES'] or 0 for a in ls), 2), land, imp, land + imp, (under or {}).get('ZONING', ''), (under or {}).get('NAME', '')])
n = sum(len(v) for v in site.values())
print(f'{len(D["schools"])} schools, {n} tax lots; schools with no lot: {[k for k, v in site.items() if not v]}')
print('lot under the school point owned by someone else (left out):', foreign)
print(f"district total RMV: land ${sum(a['ROLLLAND'] or 0 for v in site.values() for a in v)/1e6:,.0f}M, improvements ${sum(a['ROLLIMP'] or 0 for v in site.values() for a in v)/1e6:,.0f}M")
