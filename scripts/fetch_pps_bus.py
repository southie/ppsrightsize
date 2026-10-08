"""Crawl PPS General Transportation (GT) bus schedules and parse every route PDF.

Source: https://sites.google.com/pps.net/gt-bus-schedule/  (public Google Site, PPS Transportation Services)
  index page -> one sub-page per school -> embedded Google Drive folder(s) -> one PDF per route
  (e.g. 217BMT-A_Effective_082626.pdf = route 217, Beaumont, morning, effective 08/26/26)

Polite: ~1 request/second, retries with backoff, everything cached under source/pps-bus/ so reruns only fetch new files.

Outputs (source/pps-bus/):
  pdf/<file name>.pdf        raw route PDFs
  crawl.json                 pages, folders and files found
  pps-bus-routes.json        one record per route: school page, code, period, effective date, anchor, ordered stops
  pps-bus-stops.csv          one row per stop
Usage: python scripts/fetch_pps_bus.py [--limit N] [--parse-only]   (N = only the first N school pages, for testing)
"""
import csv, html as H, json, os, re, sys, time, urllib.request, urllib.error
import pymupdf
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'source', 'pps-bus'); PDF = os.path.join(OUT, 'pdf')
os.makedirs(PDF, exist_ok=True)
BASE = 'https://sites.google.com/pps.net/gt-bus-schedule'
UA = 'Mozilla/5.0 (pps-rightsizing-analysis; low-volume research crawler)'
MIN_INTERVAL = 1.0
LIMIT = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
PARSE_ONLY = '--parse-only' in sys.argv   # reuse crawl.json and the downloaded PDFs

last = [0.0]
def get(url, binary=False, tries=5):
    delay = 5
    for attempt in range(1, tries + 1):
        wait = MIN_INTERVAL - (time.time() - last[0])
        if wait > 0: time.sleep(wait)
        last[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                b = r.read()
                return b if binary else b.decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            ra = e.headers.get('Retry-After'); pause = int(ra) if ra and ra.isdigit() else delay
            print(f'    HTTP {e.code} {url[:80]}; waiting {pause}s ({attempt}/{tries})')
            time.sleep(pause); delay = min(delay * 2, 120)
        except Exception as e:
            print(f'    {type(e).__name__}: {e}; waiting {delay}s ({attempt}/{tries})')
            time.sleep(delay); delay = min(delay * 2, 120)
    print(f'    giving up on {url}')
    return None

if PARSE_ONLY:
    crawl = json.load(open(os.path.join(OUT, 'crawl.json'), encoding='utf-8'))
    for c in crawl:
        for f in c['files']:
            if f['name'].lower().endswith('.pdf'): f['local'] = 'pdf/' + re.sub(r'[^\w.\-]+', '_', f['name'])
else:
    # ---------- crawl ----------
    index = get(BASE + '/?authuser=0')
    pages = sorted(set(re.findall(r'href="(/pps\.net/gt-bus-schedule/[^"#?]+)"', index)))
    pages = [p for p in pages if p.rstrip('/') != '/pps.net/gt-bus-schedule/GT-Bus-Schedules']
    if LIMIT: pages = pages[:LIMIT]
    print(f'{len(pages)} school pages')

    def list_folder(fid, depth=0):
        """files in an embedded Drive folder (recursing into subfolders)"""
        t = get(f'https://drive.google.com/embeddedfolderview?id={fid}#list') or ''
        out = []
        for url, name in re.findall(r'<a href="(https://[^"]+)"[^>]*>.*?<div class="flip-entry-title">(.*?)</div>', t, re.S):
            name = H.unescape(name).strip()
            m = re.search(r'/file/d/([\w-]+)', url)
            if m: out.append(dict(id=m.group(1), name=name, folder=fid)); continue
            m = re.search(r'/folders/([\w-]+)', url)
            if m and depth < 3: out += list_folder(m.group(1), depth + 1)
        return out

    crawl = []
    for p in pages:
        slug = p.rstrip('/').split('/')[-1]
        t = get('https://sites.google.com' + p) or ''
        title = H.unescape((re.search(r'<title>(.*?)</title>', t, re.S) or [None, slug])[1]).strip()
        fids = list(dict.fromkeys(re.findall(r'embeddedfolderview\?id=([\w-]+)', t)))
        files = [f for fid in fids for f in list_folder(fid)]
        crawl.append(dict(page=slug, title=title, url='https://sites.google.com' + p, folders=fids, files=files))
        print(f'  {slug:28s} folders {len(fids)}  files {len(files)}')
    json.dump(crawl, open(os.path.join(OUT, 'crawl.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

    # ---------- download ----------
    n_new = 0
    for c in crawl:
        for f in c['files']:
            if not f['name'].lower().endswith('.pdf'): continue
            dst = os.path.join(PDF, re.sub(r'[^\w.\-]+', '_', f['name']))
            f['local'] = os.path.relpath(dst, OUT).replace('\\', '/')
            if os.path.exists(dst) and os.path.getsize(dst) > 0: continue
            b = get(f'https://drive.google.com/uc?export=download&id={f["id"]}', binary=True)
            if b and b[:4] == b'%PDF':
                open(dst, 'wb').write(b); n_new += 1
            else:
                print(f'    not a PDF: {f["name"]}')
    print(f'downloaded {n_new} new PDFs')

# ---------- parse ----------
TIME = re.compile(r'^\d{1,2}:\d{2}\s*[ap]m$', re.I)
CODE = re.compile(r'^(\d{2,4})([A-Z0-9]{2,4})-([A-Z])\b')
KIND = {'START', 'STOP', 'END', 'DEST'}   # stop types in the 'Bus Stop Locations' layout (GARAGE = depot, skipped)
class Scanned(Exception): pass
def parse(path):
    lines = [l.strip() for pg in pymupdf.open(path) for l in pg.get_text().split('\n') if l.strip()]
    if not lines: raise Scanned('scanned image, no text layer')
    if any(l.startswith('Bus Stop Locations For') for l in lines): return parse_locations(lines, path)
    head = next((l for l in lines if l.startswith('Route:')), '')
    m = re.match(r'Route:\s*(\S+)(?:\s+(\d{1,2}/\d{1,2}/\d{2}))?', head)
    anchor = next((l.split(':', 1)[1].strip() for l in lines if l.startswith('Anchor Name:')), None)
    stops, i = [], 0
    while i < len(lines):
        if TIME.match(lines[i]) and i + 2 < len(lines) and CODE.match(lines[i + 2]):
            loc, order = lines[i + 1], None
            if i + 3 < len(lines) and re.fullmatch(r'\(\d+\)', lines[i + 3]): order = int(lines[i + 3][1:-1])
            side = (re.search(r'\[([NSEW]{1,2})\]\s*$', loc) or [None, None])[1]
            clean = re.sub(r'\s*\[[NSEW]{1,2}\]\s*$', '', loc)
            stops.append(dict(time=lines[i].lower(), location=clean, side=side, order=order,
                              loading_zone=bool(re.search(r'LOAD(ING)? ZONE', clean.upper())) or (anchor is not None and clean.upper() == anchor.upper())))
            i += 3; continue
        i += 1
    return record(m.group(1) if m else None, m.group(2) if m and m.group(2) else None, anchor, stops, 'SNOW' in head.upper(), path)

def record(code, eff, anchor, stops, snow_hdr, path):
    cm = CODE.match(code or '')
    period = {'A': 'morning', 'P': 'afternoon', 'X': 'extended day'}.get(cm.group(3)) if cm else None
    if not period:   # other letters (e.g. 114SAB-Q): AM / PM from the file name, else the first stop time
        fn = os.path.basename(path).upper()
        period = 'afternoon' if re.search(r'(^|[-_])PM([-_]|$)', fn) else 'morning' if re.search(r'(^|[-_])AM([-_]|$)', fn) else \
                 ('afternoon' if stops and stops[0]['time'].endswith('pm') else 'morning' if stops else None)
    if eff:
        mo, d, y = eff.split('/'); eff = f'{int(mo):02d}/{int(d):02d}/{y}'
    return dict(route=code, number=cm.group(1) if cm else None, school_code=cm.group(2) if cm else None, snow_header=snow_hdr,
                period=period, effective=eff, anchor=anchor, stops=stops, n_stops=sum(1 for s in stops if not s['loading_zone']))

def parse_locations(lines, path):
    """'Bus Stop Locations For 146LNC-A 10/14/26' layout: time, location, START/STOP/END/DEST/GARAGE, riders."""
    hm = re.search(r'Bus Stop Locations For\s+(\S+)\s+(\d{1,2}/\d{1,2}/\d{2})', next(l for l in lines if l.startswith('Bus Stop Locations For')))
    stops, anchor = [], None
    for i in range(len(lines) - 2):
        if TIME.match(lines[i]) and lines[i + 2] in KIND:
            loc = lines[i + 1]
            side = (re.search(r'\[([NSEW]{1,2})\]\s*$', loc) or [None, None])[1]
            clean = re.sub(r'\s*\[[NSEW]{1,2}\]\s*$', '', loc)
            if lines[i + 2] == 'DEST': anchor = clean
            stops.append(dict(time=lines[i].lower(), location=clean, side=side, order=len(stops) + 1, loading_zone=lines[i + 2] == 'DEST'))
    return record(hm.group(1) if hm else None, hm.group(2) if hm else None, anchor, stops, False, path)

routes, problems, scanned = [], [], []
for c in crawl:
    for f in c['files']:
        if 'local' not in f or not os.path.exists(os.path.join(OUT, f['local'])): continue
        try:
            r = parse(os.path.join(OUT, f['local']))
        except Scanned:
            scanned.append(f['name']); continue
        except Exception as e:
            problems.append(f'{f["name"]}: {e}'); continue
        if not r['route'] or not r['stops']: problems.append(f'{f["name"]}: no route/stops parsed')
        r.update(page=c['page'], page_title=c['title'], file=f['name'], drive_id=f['id'], snow='SNOW' in f['name'].upper())
        routes.append(r)
# effective date: header, else file name (…Effective_082626 / Effective-090121 / Effective090121)
for r in routes:
    if not r['effective']:
        fm = re.search(r'Effective[-_]?(\d{2})(\d{2})(\d{2})', r['file'], re.I)
        if fm: r['effective'] = f'{fm.group(1)}/{fm.group(2)}/{fm.group(3)}'
    mm, dd, yy = (r['effective'] or '//').split('/') if r['effective'] else (None, None, None)
    r['effective_date'] = f'20{yy}-{mm}-{dd}' if yy else None
    r['snow'] = r['snow'] or r.pop('snow_header', False)
# the same file can sit on several school pages (shared folders): keep one record, list the pages
merged = {}
for r in routes:
    k = r['drive_id']
    if k in merged: merged[k]['pages'] = sorted(set(merged[k]['pages'] + [r['page']]))
    else: r['pages'] = [r.pop('page')]; merged[k] = r
routes = list(merged.values())
for r in routes: r.pop('page', None)
# current = latest effective version of each route (snow kept separate); outdated = effective before this school year
SCHOOL_YEAR_START = '2026-07-01'
latest = {}
for r in routes:
    k = (r['route'], r['snow'])
    if r['effective_date'] and (k not in latest or r['effective_date'] > latest[k]): latest[k] = r['effective_date']
for r in routes:
    r['outdated'] = bool(r['effective_date'] and r['effective_date'] < SCHOOL_YEAR_START)
    r['current'] = (not r['outdated']) and r['effective_date'] == latest.get((r['route'], r['snow']))
routes.sort(key=lambda r: (r['school_code'] or '', r['number'] or '', r['period'] or '', r['snow'], r['effective_date'] or ''))
json.dump(dict(source=BASE, fetched=time.strftime('%Y-%m-%d'), routes=routes), open(os.path.join(OUT, 'pps-bus-routes.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
with open(os.path.join(OUT, 'pps-bus-stops.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['pages', 'route', 'school_code', 'period', 'effective_date', 'current', 'outdated', 'snow', 'stop_order', 'time', 'location', 'side', 'loading_zone', 'anchor', 'file'])
    for r in routes:
        for s in r['stops']:
            w.writerow([';'.join(r['pages']), r['route'], r['school_code'], r['period'], r['effective_date'], r['current'], r['outdated'], r['snow'], s['order'], s['time'], s['location'], s['side'], s['loading_zone'], r['anchor'], r['file']])
cur = [r for r in routes if r['current']]
print(f'parsed {len(routes)} route files ({len(cur)} current, {sum(r["outdated"] for r in routes)} outdated, {sum(r["snow"] for r in routes)} snow); '
      f'{sum(len(r["stops"]) for r in routes)} stop rows; current routes serve {len({r["school_code"] for r in cur})} school codes; problems: {len(problems)}')
for p in problems[:20]: print('  ', p)
if scanned: print(f'{len(set(scanned))} scanned PDFs with no text layer (not parsed): ' + ', '.join(sorted(set(scanned))))
