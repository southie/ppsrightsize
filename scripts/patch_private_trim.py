"""Drop private schools well outside PPS from rightsizing-scenario-explorer.html: more than
MAX_OUT_MI from the district edge (pps-data high-school boundaries), or in Washington.
Keeps D.private and the PPS-to-private driving matrix (D.drive.pv) aligned. Safe to rerun.
"""
import json, math, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
BOUNDS = os.path.join(ROOT, 'source', 'pps-data', 'data', 'raw', 'pps_boundaries_high.geojson')
MAX_OUT_MI = 2.0
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
html = open(PAGE, encoding='utf-8').read()

segs = []
for f in json.load(open(BOUNDS, encoding='utf-8'))['features']:
    g = f['geometry']
    for ring in (g['coordinates'] if g['type'] == 'Polygon' else [r for p in g['coordinates'] for r in p]):
        segs += list(zip(ring, ring[1:]))

def miles_to_edge(lat, lng):
    kx, ky = math.cos(math.radians(lat)) * 69.17, 69.0   # local equirectangular miles
    best = math.inf
    for (x1, y1), (x2, y2) in segs:
        ax, ay, bx, by = (x1 - lng) * kx, (y1 - lat) * ky, (x2 - lng) * kx, (y2 - lat) * ky
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, -(ax * dx + ay * dy) / ((dx * dx + dy * dy) or 1)))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best

m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
keep = [i for i, x in enumerate(D['private'])
        if x.get('pps_hs_area') or (miles_to_edge(x['lat'], x['lng']) <= MAX_OUT_MI and not (x.get('city') or '').endswith(', WA'))]
dropped = [x['name'] for i, x in enumerate(D['private']) if i not in set(keep)]
D['private'] = [D['private'][i] for i in keep]
D['drive']['pv'] = [[row[i] for i in keep] for row in D['drive']['pv']]
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
print(f'kept {len(keep)} private schools, dropped {len(dropped)}')

# the whole earlier note (including any repeated "the N more ... leaving N;" sentences) or the current one
old = re.search(r"\(private-schools-2026-10-7\.json(, 187 schools;( the \d+ more [^;]*;)*|; limited to schools[^;]*;( the \d+ more [^;]*;)*)", html)
new = (f"(private-schools-2026-10-7.json; limited to schools inside the district or within {MAX_OUT_MI:g} miles of it, "
       f"not in Washington: {len(D['private'])} schools;")
if old and old.group(0) != new:
    html = html[:old.start()] + new + html[old.end():]

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
