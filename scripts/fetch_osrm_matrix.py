"""Precompute driving distance/time between every PPS school and (a) every other PPS school and
(b) every private school that serves grade 1+ (not preschool/kindergarten only).

Uses the public OSRM demo server (router.project-osrm.org) table service, politely:
  * one request per source school per destination batch (<= 90 destinations)
  * at least MIN_INTERVAL seconds between requests
  * exponential backoff on HTTP 429/5xx or network errors, honoring Retry-After
  * every result is cached immediately, so the run can be stopped and resumed

Cache: source/osrm/osrm-drive-cache.json  {"lon,lat;lon,lat": [miles, minutes] | null}
Matrix: source/osrm/osrm-matrix.json      (schools, private schools and the two matrices)
"""
import json, os, re, sys, time, urllib.request, urllib.error
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
PRIV = os.path.join(ROOT, 'source', 'nces-pss', 'private-schools-pss.json')   # from scripts/build_private_pss.py
CACHE = os.path.join(ROOT, 'source', 'osrm', 'osrm-drive-cache.json')
OUT = os.path.join(ROOT, 'source', 'osrm', 'osrm-matrix.json')
OSRM = 'https://router.project-osrm.org/table/v1/driving/'
UA = 'pps-rightsizing-analysis/1.0 (personal research, low volume)'
MIN_INTERVAL, BATCH, MAX_TRIES = 1.2, 90, 6

html = open(PAGE, encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
pps = [dict(key=s['key'], name=s['name'], lat=s['lat'], lng=s['lng']) for s in D['schools']]

def grades(t):
    g = set()
    for part in (t or '').split(','):
        part = part.strip()
        if not part: continue
        a, _, b = part.partition('-'); v = lambda x: -1 if x == 'PK' else 0 if x == 'K' else int(re.sub(r'\D', '', x))   # '12 (ungraded)' -> 12
        lo = v(a.strip()); hi = v(b.strip()) if b else lo; g.update(range(lo, hi + 1))
    return g
priv_all = json.load(open(PRIV, encoding='utf-8'))['schools']
priv = [dict(name=x['name'], lat=x['lat'], lng=x['lng']) for x in priv_all if any(k >= 1 for k in grades(x['grades_served']))]

cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
key = lambda a, b: f"{a['lng']:.6f},{a['lat']:.6f};{b['lng']:.6f},{b['lat']:.6f}"
last = [0.0]; n_req = [0]

def save():
    tmp = CACHE + '.tmp'
    with open(tmp, 'w') as f: json.dump(cache, f)
    for attempt in range(10):   # OneDrive can briefly lock the cache while syncing it
        try: os.replace(tmp, CACHE); return
        except PermissionError: time.sleep(0.5 * (attempt + 1))
    os.replace(tmp, CACHE)

def request(src, dsts):
    coords = ';'.join(f"{p['lng']:.6f},{p['lat']:.6f}" for p in [src] + dsts)
    url = f"{OSRM}{coords}?sources=0&annotations=distance,duration"
    delay = 5
    for attempt in range(1, MAX_TRIES + 1):
        wait = MIN_INTERVAL - (time.time() - last[0])
        if wait > 0: time.sleep(wait)
        last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                js = json.load(r)
            n_req[0] += 1
            if js.get('code') != 'Ok': raise RuntimeError(js.get('code'))
            return js
        except urllib.error.HTTPError as e:
            ra = e.headers.get('Retry-After')
            pause = int(ra) if ra and ra.isdigit() else delay
            print(f'    HTTP {e.code}; waiting {pause}s (attempt {attempt}/{MAX_TRIES})')
            time.sleep(pause); delay = min(delay * 2, 120)
        except Exception as e:
            print(f'    {type(e).__name__}: {e}; waiting {delay}s (attempt {attempt}/{MAX_TRIES})')
            time.sleep(delay); delay = min(delay * 2, 120)
    raise SystemExit('OSRM not responding; cache saved, rerun to resume')

def fill(src, dsts, label):
    todo = [d for d in dsts if key(src, d) not in cache]
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        js = request(src, chunk)
        for j, d in enumerate(chunk, start=1):
            dist, dur = js['distances'][0][j], js['durations'][0][j]
            cache[key(src, d)] = None if dist is None else [round(dist / 1609.344, 2), round(dur / 60, 1)]
        save()
    return len(todo)

t0 = time.time()
print(f'{len(pps)} PPS schools, {len(priv)} private schools (grade 1+); cache has {len(cache)} pairs')
for i, s in enumerate(pps, 1):
    a = fill(s, [o for o in pps if o is not s], 'pps')
    b = fill(s, priv, 'private')
    print(f'[{i:2d}/{len(pps)}] {s["key"]:26s} new pairs: {a:3d} PPS, {b:3d} private | requests so far {n_req[0]} | {time.time() - t0:5.0f}s')

pp = [[cache.get(key(a, b)) if a is not b else [0, 0] for b in pps] for a in pps]
pv = [[cache.get(key(a, b)) for b in priv] for a in pps]
json.dump(dict(source='OSRM public demo server, table service (driving, free-flow), fetched ' + time.strftime('%Y-%m-%d'),
               units=['miles', 'minutes'], pps=pps, private=priv, pps_to_pps=pp, pps_to_private=pv),
          open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
missing = sum(v is None for r in pp for v in r) + sum(v is None for r in pv for v in r)
print(f'done: {n_req[0]} requests in {time.time() - t0:.0f}s; matrix {len(pps)}x{len(pps)} + {len(pps)}x{len(priv)}; unroutable pairs: {missing}')
