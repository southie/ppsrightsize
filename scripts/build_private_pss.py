"""Private schools for rightsizing-scenario-explorer.html from the NCES Private School Universe Survey (PSS).

  python scripts/build_private_pss.py          build source/nces-pss/private-schools-pss.json
  python scripts/fetch_osrm_matrix.py          driving distances for the list (cached; only new pairs are fetched)
  python scripts/build_private_pss.py --embed  put the list and its driving matrix into the page (D.private, D.drive.pv)

Schools: Oregon schools in the 2023-24, 2021-22 or 2019-20 PSS (each from its most recent survey), inside the PPS
district or within MAX_OUT_MI miles of its edge (pps-data high-school boundaries). Schools last seen in
2017-18 or earlier are left out as likely closed. Listings at the same location with overlapping names
(the same school reported twice) are merged. PSS covers kindergarten through grade 12, so pre-K-only
programs are not included and enrollment is K-12.
"""
import csv, io, json, math, os, re, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSS = os.path.join(ROOT, 'source', 'nces-pss')
OUT = os.path.join(PSS, 'private-schools-pss.json')
BOUNDS = os.path.join(ROOT, 'source', 'pps-data', 'data', 'raw', 'pps_boundaries_high.geojson')
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
MATRIX = os.path.join(ROOT, 'source', 'osrm', 'osrm-matrix.json')
MAX_OUT_MI = 2.0
WAVES = [('2324', '2023-24'), ('2122', '2021-22'), ('1920', '2019-20')]   # newest first
NEWLINE = '\r\n'   # the page is kept with CRLF line endings

# ---------- PSS codes (2021-22 and 2023-24 codebooks) ----------
def grade_label(code):   # LOGR/HIGR: 1 ungraded, 2 PK, 3 K, 4 transitional K, 5 transitional 1st, 6-17 grades 1-12
    c = int(code)
    return None if c == 1 else 'PK' if c == 2 else 'K' if c in (3, 4, 5) else str(c - 5)

def grades_served(lo, hi):
    a, b = grade_label(lo), grade_label(hi)
    if a is None or b is None: return 'K-12 (ungraded)'
    if a == b: return a
    if a == 'PK': return 'PK, ' + ('K' if b == 'K' else f'K-{b}')
    return f'{a}-{b}'

ORIENT = {1: 'Catholic', 2: 'African Methodist Episcopal', 3: 'Amish', 4: 'Assembly of God', 5: 'Baptist', 6: 'Brethren',
          7: 'Calvinist', 8: 'Christian (General)', 9: 'Church of Christ', 10: 'Church of God', 11: 'Church of God in Christ',
          12: 'Church of the Nazarene', 13: 'Disciples of Christ', 14: 'Episcopal', 15: 'Friends', 16: 'Greek Orthodox',
          17: 'Islamic', 18: 'Jewish', 19: 'Latter Day Saints', 20: 'Lutheran', 21: 'Lutheran', 22: 'Lutheran', 23: 'Lutheran',
          24: 'Mennonite', 25: 'Methodist', 26: 'Pentecostal', 27: 'Presbyterian', 28: 'Seventh-Day Adventist', 29: 'Other religious'}

def kind(typology, orient):   # -> (genus, character) in the page's existing style
    t, o = int(typology), int(orient)
    if t == 9: return 'Special Education School', 'Private, Special Education'
    if o == 30: return 'Private School', 'Private, special program emphasis' if t == 8 else 'Private'
    label = ORIENT.get(o, 'Other religious')
    genus = {'Catholic': 'Catholic School', 'Jewish': 'Jewish School', 'Islamic': 'Islamic School', 'Episcopal': 'Episcopal School'}.get(label, 'Christian School')
    return genus, f'Private, {label}'

NAME_FIXES = {'ALL SAINTS CHOOL': 'ALL SAINTS SCHOOL', 'THE MONTESORRI HOUSE OF ST JOHNS': 'THE MONTESSORI HOUSE OF ST JOHNS',   # typos in the PSS file
              'OUR LADY OF THE LAKE CARTHOLIC SCHOOL': 'OUR LADY OF THE LAKE CATHOLIC SCHOOL',
              'CHRISTA MCAULIFFE ACADEMY - SCHOOL OF ARTS/SCES': 'CHRISTA MCAULIFFE ACADEMY - SCHOOL OF ARTS AND SCIENCES'}
ACRONYMS = {'OIC', 'PSU', 'NAYA', 'II', 'III', 'IV'}
SMALL = {'of', 'and', 'the', 'for', 'at', 'in'}

def cap(w):
    if w.upper() in ACRONYMS: return w.upper()
    w = re.sub(r"(^|[-/(])([a-z])", lambda m: m.group(1) + m.group(2).upper(), w.lower())
    w = re.sub(r"^Mc([a-z])", lambda m: 'Mc' + m.group(1).upper(), w)
    return re.sub(r"^([LD])'([a-z])", lambda m: m.group(1) + "'" + m.group(2).upper(), w)   # L'Etoile

def title(s):
    words = NAME_FIXES.get(s, s).split()
    return ' '.join(cap(w) if i == 0 or w.lower() not in SMALL else w.lower() for i, w in enumerate(words))

# ---------- PPS geometry ----------
feats = json.load(open(BOUNDS, encoding='utf-8'))['features']
segs = [seg for f in feats for p in ([f['geometry']['coordinates']] if f['geometry']['type'] == 'Polygon' else f['geometry']['coordinates'])
        for ring in p for seg in zip(ring, ring[1:])]
REGION = {'Cleveland': 'Cleveland / Franklin', 'Franklin': 'Cleveland / Franklin', 'Grant': 'Grant / McDaniel', 'McDaniel': 'Grant / McDaniel',
          'Jefferson': 'Jefferson / Roosevelt', 'Roosevelt': 'Jefferson / Roosevelt', 'Ida B. Wells': 'Ida B. Wells / Lincoln', 'Lincoln': 'Ida B. Wells / Lincoln'}

def contains(g, lat, lng):
    for p in ([g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']):
        c = False
        for ring in p:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1: c = not c
        if c: return True
    return False

def hs_area(lat, lng):
    names = [f['properties']['school_name'] for f in feats if contains(f['geometry'], lat, lng)]
    if len(names) > 1 and 'Jefferson' in names:   # 2024-25 Jefferson shared zones overlap a neighboring area
        names = ['Jefferson'] + [n for n in names if n != 'Jefferson']
    return ' / '.join(names) or None

def miles_to_edge(lat, lng):
    kx, ky = math.cos(math.radians(lat)) * 69.17, 69.0
    best = math.inf
    for (x1, y1), (x2, y2) in segs:
        ax, ay, bx, by = (x1 - lng) * kx, (y1 - lat) * ky, (x2 - lng) * kx, (y2 - lat) * ky
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, -(ax * dx + ay * dy) / ((dx * dx + dy * dy) or 1)))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best

def miles(a, b):
    return math.hypot((a['lat'] - b['lat']) * 69.0, (a['lng'] - b['lng']) * math.cos(math.radians(a['lat'])) * 69.17)

def embed():
    html = open(PAGE, encoding='utf-8').read()
    m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
    D = json.loads(m.group(1))
    P = json.load(open(OUT, encoding='utf-8'))['schools']
    M = json.load(open(MATRIX, encoding='utf-8'))
    assert [s['key'] for s in M['pps']] == [s['key'] for s in D['schools']], 'school order differs; rerun fetch_osrm_matrix.py'
    col = {(p['name'], round(p['lat'], 5), round(p['lng'], 5)): j for j, p in enumerate(M['private'])}
    pmap = [col.get((x['name'], round(x['lat'], 5), round(x['lng'], 5))) for x in P]
    routed = sum(c is not None for c in pmap)
    print(f'{routed} of {len(P)} private schools have driving routes (pre-K/K-only schools are not routed by design)')
    D['private'] = P
    D['drive'] = dict(source=M['source'], units=M['units'], pp=M['pps_to_pps'],
                      pv=[[row[c] if c is not None else None for c in pmap] for row in M['pps_to_private']])
    html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
    # method note and popup wording (once)
    old_note = re.search(r"'Private schools: a public private-school directory search[^)]*\)\. ", html)
    if old_note:
        html = html[:old_note.start()] + ("'Private schools: the NCES Private School Universe Survey (PSS), the most recent response from each school in 2023-24, 2021-22 or 2019-20 "
            "(schools last reported in 2017-18 or earlier are left out as likely closed); Oregon schools inside the district or within " + f"{MAX_OUT_MI:g}" +
            " miles of it. The PSS covers kindergarten through grade 12, so student counts are K-12 and pre-K-only programs are not included; "
            "schools that answered neither recent survey are missing. ") + html[old_note.end():]
    a2 = "Students: ${x.students != null ? x.students.toLocaleString() : 'n/a'}"
    if html.count(a2) == 1:
        html = html.replace(a2, a2 + "${x.pss_year ? ` (K-12, ${x.pss_year} survey)` : ''}")
    open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
    print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')

if '--embed' in sys.argv[1:]:
    embed(); sys.exit()

# ---------- build ----------
latest, seen_older = {}, {}
for code, year in WAVES:
    zf = zipfile.ZipFile(os.path.join(PSS, f'pss{code}_pu_csv.zip'))
    for r in csv.DictReader(io.TextIOWrapper(zf.open(next(n for n in zf.namelist() if n.lower().endswith('.csv'))), encoding='latin-1')):
        r = {k.upper(): v for k, v in r.items()}
        if r['PSTABB'] != 'OR' or r['PPIN'] in latest: continue
        yy = code[2:]
        lat, lng = float(r[f'LATITUDE{yy}']), float(r[f'LONGITUDE{yy}'])
        area = hs_area(lat, lng)
        if not area and miles_to_edge(lat, lng) > MAX_OUT_MI: continue
        genus, character = kind(r['TYPOLOGY'], r['ORIENT'])
        ratio = float(r['STTCH_RT'] or 0)
        latest[r['PPIN']] = dict(name=title(r['PINST'].strip()), lat=lat, lng=lng, city=f"{r['PCITY'].strip().title()}, OR",
                                 genus=genus, character=character, grades_served=grades_served(r[f'LOGR20{yy}'], r[f'HIGR20{yy}']),
                                 students=int(float(r['NUMSTUDS'] or 0)), ratio=round(ratio) if ratio else None,
                                 pps_hs_area=area, pps_region=REGION.get(area), pss_ppin=r['PPIN'], pss_year=year)

# merge duplicate listings: same place (< 0.05 mi) and a shared name word
schools = sorted(latest.values(), key=lambda s: (s['pss_year'], s['students']), reverse=True)
kept = []
for s in schools:
    words = set(re.findall(r'[a-z]{4,}', s['name'].lower())) - {'school', 'schools', 'academy', 'christian', 'catholic', 'portland', 'montessori'}
    dup = next((k for k in kept if miles(k, s) < .05 and words & set(re.findall(r'[a-z]{4,}', k['name'].lower()))), None)
    if dup: print(f"  merged duplicate listing: {s['name']} ({s['pss_year']}, {s['students']}) into {dup['name']} ({dup['pss_year']}, {dup['students']})")
    else: kept.append(s)
kept.sort(key=lambda s: s['name'])
json.dump({'source': 'NCES Private School Universe Survey public-use files, 2023-24, 2021-22 and 2019-20 (most recent per school)',
           'rule': f'Oregon, inside the PPS district or within {MAX_OUT_MI:g} miles of it', 'schools': kept},
          open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
by_year = {y: sum(s['pss_year'] == y for s in kept) for _, y in WAVES}
print(f'wrote {os.path.relpath(OUT, ROOT)}: {len(kept)} schools ({by_year}); {sum(1 for s in kept if s["pps_hs_area"])} inside PPS')
