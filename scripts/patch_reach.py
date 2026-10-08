"""Share of each school's attendance-area residents living within its 15-minute walk / bike / drive area,
per scenario, added to the endpoints table in rightsizing-scenario-explorer.html (one column, one line per mode).

Attendance areas: source/pps-explorer-boundaries (K-5 for elementary and K-8 schools, 6-8 for middle,
9-12 for high). Travel-time areas: D.iso (15-minute isochrones). Residents: 2020 Census block population
(source/census-blocks, from scripts/fetch_census_blocks.py), spread evenly over a GRID_M grid of points in
each block, so water, parks, islands and industrial land carry no weight. Safe to rerun: data is
refreshed, code added once.
"""
import glob, json, math, os, re, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
SRC = os.path.join(ROOT, 'source', 'pps-explorer-boundaries')
BLOCKS = os.path.join(ROOT, 'source', 'census-blocks', 'blocks_2020.geojson')
GRID_M = 40
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
CHECK = '--check' in sys.argv[1:]
html_now = open(PAGE, encoding='utf-8').read()
if 'function renderCommute' in html_now:
    sys.exit('superseded: the 15-minute column was replaced by the Getting to school table (scripts/patch_commute.py)')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))

# ---------- geometry ----------
LAT0 = 45.53
KX, KY = math.cos(math.radians(LAT0)) * 111320.0, 110540.0   # metres per degree

def polys_of(g):
    return [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']

def inside(px, py, polys):
    """Even-odd point-in-polygon for arrays of points against a list of polygons (rings in lon/lat)."""
    hit = np.zeros(px.shape, bool)
    for poly in polys:
        for ring in poly:
            r = np.asarray(ring, float)
            x1, y1, x2, y2 = r[:-1, 0], r[:-1, 1], r[1:, 0], r[1:, 1]
            for a, b, c, d in zip(x1, y1, x2, y2):
                if b == d: continue
                cross = ((b > py) != (d > py)) & (px < (c - a) * (py - b) / (d - b) + a)
                hit ^= cross
    return hit

# one district-wide grid; each point carries the population of its census block spread over the block's points
ALL = [p for f in glob.glob(os.path.join(SRC, '*_*.geojson')) if not f.endswith(('_schools.geojson', '_changed.geojson'))
       for ft in json.load(open(f, encoding='utf-8'))['features'] for poly in polys_of(ft['geometry']) for p in poly[0]]
(X0, Y0), (X1, Y1) = np.min(ALL, 0), np.max(ALL, 0)
DX, DY = GRID_M / KX, GRID_M / KY
XS, YS = np.arange(X0 + DX / 2, X1, DX), np.arange(Y0 + DY / 2, Y1, DY)
GX, GY = np.meshgrid(XS, YS)
POP = np.zeros(GX.shape)
tiny = 0
for f in json.load(open(BLOCKS, encoding='utf-8'))['features']:
    pop = f['properties'].get('POP100') or 0
    if not pop or not f['geometry']: continue
    polys = polys_of(f['geometry'])
    r = np.array([p for poly in polys for p in poly[0]])
    (a, b), (c, d) = r.min(0), r.max(0)
    i0, i1 = np.searchsorted(YS, b), np.searchsorted(YS, d, 'right')
    j0, j1 = np.searchsorted(XS, a), np.searchsorted(XS, c, 'right')
    hit = None
    if i0 < i1 and j0 < j1:
        sub = (slice(i0, i1), slice(j0, j1))
        hit = inside(GX[sub], GY[sub], polys)
    if hit is not None and hit.any():
        POP[sub][hit] += pop / hit.sum()
    else:   # block smaller than a grid cell: its population goes to the nearest point
        cx, cy = r.mean(0); tiny += 1
        ii, jj = min(max(np.searchsorted(YS, cy), 0), len(YS) - 1), min(max(np.searchsorted(XS, cx), 0), len(XS) - 1)
        POP[ii, jj] += pop
print(f'grid {GX.size:,} points, population {POP.sum():,.0f} ({tiny} blocks smaller than a grid cell), {np.mean(POP > 0):.0%} of points populated')

def sample(polys):
    pts = np.array([p for poly in polys for ring in poly for p in ring], float)
    (a, b), (c, d) = pts.min(0), pts.max(0)
    sub = (slice(np.searchsorted(YS, b), np.searchsorted(YS, d, 'right')), slice(np.searchsorted(XS, a), np.searchsorted(XS, c, 'right')))
    gx, gy, w = GX[sub].ravel(), GY[sub].ravel(), POP[sub].ravel()
    lived = w > 0
    gx, gy, w = gx[lived], gy[lived], w[lived]
    keep = inside(gx, gy, polys)
    return gx[keep], gy[keep], w[keep]

# ---------- match boundary names to explorer schools ----------
STRIP = r"\b(elementary|middle|high|school|k-8|k8|k-5|academy|program|of|the)\b"
def norm(n):
    n = n.lower().replace('’', "'").replace('.', '')
    n = re.sub(STRIP, ' ', n)
    return re.sub(r'[^a-z0-9]+', ' ', n).strip()
ALIAS = {'brentwood': 'Lane', 'sunrise': 'Lee', 'martin luther king jr': 'MLK Jr', 'king': 'MLK Jr',
         'boise eliot humboldt': 'Boise-Eliot/Humboldt', 'boise eliot': 'Boise-Eliot/Humboldt',
         'wells barnett': 'Ida B Wells-Barnett'}
bykey = {}
for s in D['schools']:
    for n in {s['key'], s['name']}:
        bykey[norm(n)] = s['key']
def key_of(name):
    n = norm(name)
    return ALIAS.get(n) or bykey.get(n)

BAND = {'ES': 'k5', 'K8': 'k5', 'MS': '68', 'HS': '912'}
reach, unmatched = {}, set()
for sc in ['sq', 'a', 'b']:
    SC = sc.upper()
    areas = {}
    for band in ['k5', '68', '912']:
        for f in json.load(open(os.path.join(SRC, f'{sc}_{band}.geojson'), encoding='utf-8'))['features']:
            k = key_of(f['properties']['name'])
            if not k: unmatched.add(f['properties']['name']); continue
            areas.setdefault((k, band), []).extend(polys_of(f['geometry']))
    reach[SC] = {}
    for s in D['schools']:
        k = s['key']
        t = D['types'][SC].get(k) or D['types']['SQ'].get(k)
        if D['detail'][SC].get(k, {}).get('closed') or t not in BAND: continue
        polys = areas.get((k, BAND[t]))
        if not polys: continue
        gx, gy, w = sample(polys)
        if not len(gx) or w.sum() <= 0: continue
        row = {'n': int(round(w.sum()))}   # 2020 residents in the attendance area
        for mode in ['walk', 'bike', 'drive']:
            iso = D['iso'].get(k, {}).get(mode, {}).get('15')
            row[mode[0]] = round(100 * w[inside(gx, gy, polys_of(iso))].sum() / w.sum()) if iso else None
        reach[SC][k] = row
    missing = [s['key'] for s in D['schools'] if s['key'] not in reach[SC] and not D['detail'][SC].get(s['key'], {}).get('closed')]
    print(f"{SC}: {len(reach[SC])} schools with shares; open but no area: {', '.join(missing) or 'none'}")
if unmatched: print('boundary names not matched:', ', '.join(sorted(unmatched)))
if CHECK:   # compare with what the page has now; extra arguments are school keys to print
    for k in [x for x in sys.argv[1:] if not x.startswith('--')]:
        print(k, {SC: reach[SC].get(k) for SC in reach})
    old = D.get('reach', {})
    for SC in ['SQ', 'A']:
        diffs = sorted(((abs(r[m] - o[m]), k, m, o[m], r[m]) for k, r in reach[SC].items() if (o := old.get(SC, {}).get(k))
                        for m in 'wbd' if r[m] is not None and o.get(m) is not None and r[m] != o[m]), reverse=True)
        print(f'{SC}: {len(diffs)} values change; largest:', '; '.join(f'{k} {dict(w="walk", b="bike", d="drive")[m]} {a}%->{b}%' for _, k, m, a, b in diffs[:10]))
    sys.exit()

D['reach'] = reach
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function reachCell' not in html:
    rep("tr.srow td:first-child { padding-left: 26px; }",
        "tr.srow td:first-child { padding-left: 26px; }\n"
        "td.reach { white-space: nowrap; font-size: 12px; line-height: 1.35; text-align: left; } td.reach .rm { color: var(--text-muted); display: inline-block; width: 36px; text-align: left; }\n"
        "td.reach .rd { font-size: 11px; font-weight: 600; } td.reach .rd.up { color: var(--up); } td.reach .rd.down { color: var(--down); }")
    rep("function schoolRows(rn) {",
"""// share of attendance area within 15 min of the school (D.reach; custom scenarios use their starting scenario's
// boundaries). Roll-ups weight schools by projected 2031-32 enrollment in the scenario; under a scenario each line
// also shows the change from Status Quo in percentage points.
const REACH_MODES = [['w', 'Walk'], ['b', 'Bike'], ['d', 'Drive']];
function reachRoll(sc, keys) {
  const R = D.reach[sc === 'C' ? custom.base : sc] || {}, det = D.detail[sc] || {};
  const out = {};
  for (const [m] of REACH_MODES) {
    let num = 0, den = 0;
    for (const k of keys) {
      const r = R[k], d = det[k]; if (!r || r[m] == null || !d || d.closed) continue;
      const w = keys.length === 1 ? 1 : (d.e || 0);
      num += r[m] * w; den += w;
    }
    out[m] = den ? Math.round(num / den) : null;
  }
  return out;
}
function reachCell(keys) {
  const cur = reachRoll(scen, keys);
  if (REACH_MODES.every(([m]) => cur[m] == null)) return `<td class="reach muted"${keys.length === 1 ? ' title="No neighborhood attendance area in this scenario"' : ''}>&mdash;</td>`;
  const sq = scen === 'SQ' ? null : reachRoll('SQ', keys);
  return '<td class="reach">' + REACH_MODES.map(([m, l]) => {
    const v = cur[m], dv = sq && v != null && sq[m] != null ? v - sq[m] : 0;
    return `<span class="rm">${l}</span>${v == null ? '&mdash;' : v + '%'}` +
      (dv ? ` <span class="rd ${dv > 0 ? 'up' : 'down'}">${dv > 0 ? '+' : '&minus;'}${Math.abs(dv)}</span>` : '');
  }).join('<br>') + '</td>';
}
function schoolRows(rn) {""")
    # school rows: closed -> dash; open -> the school's shares (before the last, empty cell)
    rep("""`<td class="muted">${s0.fc ? `building of ${s0.fc.toLocaleString()} seats` : '&mdash;'}</td><td></td></tr>`;""",
        """`<td class="muted">${s0.fc ? `building of ${s0.fc.toLocaleString()} seats` : '&mdash;'}</td>` + '<td class="reach muted">&mdash;</td><td></td></tr>';""")
    rep("""over capacity' : ''}</span>` : '<span class="muted">no data</span>'}</td><td></td></tr>`;""",
        """over capacity' : ''}</span>` : '<span class="muted">no data</span>'}</td>` + reachCell([n]) + '<td></td></tr>';""")
    # header and region / district rows
    rep("""(2031-32 enrollment &divide; 2021 functional capacity)</span></th><th>Students who would change schools</th>""",
        """(2031-32 enrollment &divide; 2021 functional capacity)</span></th><th>Attendance-area residents within 15 min<br><span style="font-weight:400">(of their school, 2020 Census; roll-ups weighted by 2031-32 enrollment; change vs Status Quo in pts)</span></th><th>Students who would change schools</th>""")
    rep("""    h += `<td>${rn === 'District' ? `<span class="main">${cur.change}%</span>`""",
        """    h += reachCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));
    h += `<td>${rn === 'District' ? `<span class="main">${cur.change}%</span>`""")
    # method note
    rep("  'Travel time:",
        "  'Residents within 15 min: for each open school, the share of the residents of its attendance area (K-5 for elementary and K-8 schools, 6-8 for middle, 9-12 for high, from the boundary layers) who live inside its 15-minute walk, bike or drive area. Residents are 2020 Census block populations spread over a " + str(GRID_M) + " m grid, so water, parks, islands and industrial land carry no weight. Region and district rows weight schools by their projected 2031-32 enrollment in the scenario. Under a scenario, each line also shows the change from Status Quo in percentage points (closed schools drop out). A custom scenario shows its starting scenario\\'s boundaries, so its shares are the starting scenario\\'s. Embedded by scripts/patch_reach.py.',\n  'Travel time:")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
