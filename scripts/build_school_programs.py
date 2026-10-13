"""School programs and designations for the school report header:
  - type, programs (immersion language, focus), ODE support status (CSI / TSI) and Title I, and the 2024-25 share of
    students qualifying for free meals by Direct Certification (DC), from PPS's 2026-27 Proposed Budget, Volume 2, school
    summary table (pp. 10-11, "2026-27 School Type (Programs), ODE status, and Title I")
  - enrollment by program (neighborhood / each immersion program), 2025-26, and centrally allocated special education
    FTE (licensed and classified, 2026-27 budget), from each school's report in the same volume
  - SUN Community School sites (Multnomah County SUN Community School Contact List, August 2026; PPS sites are those
    with a pps.net principal)
Title I rule (Volume 2 p. 9): elementary, middle and K-8 schools with at least 33% of students qualifying for free meals
by Direct Certification; high schools at 46.9% ("high poverty"); recently exited schools are "bridged" for a year.
Output: source/pps-programs/school-programs.json
"""
import json, os, re, sys, unicodedata
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOL2 = os.path.join(ROOT, 'archive', 'budget', '2026-27ProposedBudget-Volume2.pdf')
SUN = os.path.join(ROOT, 'source', 'sun', 'sun-contact-list.pdf')
OUT = os.path.join(ROOT, 'source', 'pps-programs'); os.makedirs(OUT, exist_ok=True)
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', open(PAGE, encoding='utf-8').read(), re.S).group(1))
def n(s): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
ALIAS = {n('Brentwood'): 'Lane', n('Lane'): 'Lane', n('Martin Luther King Jr'): 'MLK Jr', n('King'): 'MLK Jr', n('Ida B Wells'): 'Ida B Wells-Barnett',
         n('Ida B. Wells-Barnett'): 'Ida B Wells-Barnett', n('Bridger'): 'Bridger Creative Science', n('Sunnyside'): 'Sunnyside Environmental',
         n('Boise-Eliot'): 'Boise-Eliot/Humboldt', n('Leodis V. McDaniel'): 'McDaniel', n('Harriet Tubman'): 'Harriet Tubman', n('Tubman'): 'Harriet Tubman',
         n('Cesar Chavez'): 'César Chávez', n('Dr. Martin Luther King, Jr'): 'MLK Jr', n('Robert Gray'): 'Gray', n('Bridger Creative'): 'Bridger Creative Science', n('Martin Luther'): 'MLK Jr', n('Sunrise'): 'Lee', n('Mt. Tabor'): 'Mt Tabor', n('Mount Tabor'): 'Mt Tabor'}
KEYS = {n(k): k for k in D['region_of']}
for s in D['schools']: KEYS.setdefault(n(s['name']), s['key'])
def key_of(name):
    c = n(re.sub(r'\b(Elementary|Middle|High|School|K-8|K8|PK-8)\b', '', name))
    return ALIAS.get(c) or KEYS.get(c)

doc = pymupdf.open(VOL2)
# ---------- summary table ----------
TYPE = re.compile(r'^(K-5|K-8|6-8|9-12|K-12|PK-5|PK-8|2-8|1-8)\b')
summary = {}
for pg in (9, 10):
    lines = [l.strip() for l in doc[pg].get_text().split('\n') if l.strip()]
    i = 0
    while i < len(lines):
        l = lines[i]
        if TYPE.match(l) and i >= 2:
            # walk back to the school name: the nearest line that is not a number, %, $ or a header
            j = i - 1; nums = []
            while j >= 0 and re.fullmatch(r'[\d.,$%]+', lines[j]): nums.append(lines[j]); j -= 1
            name = lines[j]
            k = key_of(name)
            dc = next((float(x[:-1]) for x in nums if x.endswith('%')), None)   # the last % before the type: DC%
            m = re.match(r'^(\S+)\s*(\(([^)]*)\))?\s*(CSI|TSI)?\s*(Title I)?\s*$', l)
            if m and k:
                summary[k] = dict(name=name, type=m.group(1), programs=m.group(3) or '', ode=m.group(4) or '', title1=bool(m.group(5)), dc_2425=dc)
        i += 1
print(f'summary table: {len(summary)} schools matched')

# ---------- school reports: enrollment by program, central special education FTE ----------
YRS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26', '2026-27']
reports = {}
for i, p in enumerate(doc):
    W = p.get_text('words')
    staff = [w for w in W if w[4] == 'Staff']
    if not staff: continue
    sy = staff[0][1]
    hdr = sorted([w for w in W if w[4] in YRS and abs(w[1] - (sy - 6)) < 8], key=lambda w: w[0])
    if len(hdr) != 6: continue
    hx = [w[2] for w in hdr]
    def vals(y):
        v = [None] * 6
        for w in W:
            if abs(w[1] - y) < 2.5 and re.fullmatch(r'\d+\.\d\d', w[4]) and w[0] > 190:
                j = min(range(6), key=lambda j: abs(w[2] - hx[j]))
                if abs(w[2] - hx[j]) < 15: v[j] = float(w[4])
        return v
    sp = sorted([w for w in W if w[4] == 'Special' and w[0] < 190 and w[1] > sy and any(x[4] == 'Education' and abs(x[1] - w[1]) < 2 for x in W)], key=lambda w: w[1])
    sped = [vals(w[1]) for w in sp[:2]]   # licensed, then classified (centrally allocated)
    # enrollment by program: rows above the staffing table, values under the 2021-22 ... 2028-29 headers
    ey = [w for w in W if w[4] == '2021-22' and w[1] < sy - 20]
    progs = {}
    if ey:
        y0 = ey[0][1]; ehx = sorted([w for w in W if re.fullmatch(r'20\d\d-\d\d', w[4]) and abs(w[1] - y0) < 3], key=lambda w: w[0])
        ex = [w[2] for w in ehx]
        rows = {}
        for w in W:
            if y0 + 8 < w[1] < sy - 10 and w[0] < 190 and not re.fullmatch(r'[\d,]+', w[4]): rows.setdefault(round(w[1]), []).append(w)
        for y, ws in rows.items():
            label = ' '.join(x[4] for x in sorted(ws, key=lambda x: x[0]))
            vv = [None] * len(ex)
            for w in W:
                if abs(w[1] - y) < 2.5 and re.fullmatch(r'[\d,]+', w[4]) and w[0] > 190:
                    j = min(range(len(ex)), key=lambda j: abs(w[2] - ex[j]))
                    if abs(w[2] - ex[j]) < 15: vv[j] = int(w[4].replace(',', ''))
            if any(v is not None for v in vv) and label not in ('Actual', 'Projected'): progs[label] = dict(zip([w[4] for w in ehx], vv))
    tw = [w for w in W if w[1] < 60 and w[0] < 200]
    y_top = min((round(w[1]) for w in tw), default=0)
    title = ' '.join(w[4] for w in sorted([w for w in tw if round(w[1]) == y_top], key=lambda w: w[0]))   # the report's heading line
    k = key_of(title) or key_of(title.replace('DR. ', '').replace('MLK', 'MLK Jr'))
    if not k: print('  report not matched:', repr(title), 'page', i + 1)
    if k: reports[k] = dict(page=i + 1, sped_licensed=sped[0] if sped else None, sped_classified=sped[1] if len(sped) > 1 else None, programs=progs)
print(f'school reports: {len(reports)} matched')

# ---------- SUN Community Schools ----------
t = '\n'.join(p.get_text() for p in pymupdf.open(SUN))
lines = [l.strip() for l in t.split('\n')]
sun = {}
starts = [i for i in range(1, len(lines) - 2) if re.match(r'^(Portland|Gresham|Fairview|Troutdale|Wood Village),\s*O[Rr]', lines[i])]
for a, b in zip(starts, starts[1:] + [len(lines)]):
    name = lines[a - 2] if lines[a - 2] else lines[a - 3]
    block = '\n'.join(lines[a:b])
    if '@pps.net' in block.lower():
        k = key_of(name)
        sun[name] = k
print('SUN PPS sites:', len(sun), '| unmatched:', [x for x, k in sun.items() if not k])

out = {}
for k in D['region_of']:
    s, r = summary.get(k, {}), reports.get(k, {})
    out[k] = dict(type=s.get('type'), programs=s.get('programs', ''), ode=s.get('ode', ''), title1=s.get('title1'), dc_2425=s.get('dc_2425'),
                  sped_licensed=r.get('sped_licensed'), sped_classified=r.get('sped_classified'), enroll_by_program=r.get('programs', {}),
                  sun=k in sun.values(), budget_page=r.get('page'))
missing = [k for k in out if not summary.get(k)]
print('explorer schools without a summary-table row:', missing)
json.dump(dict(source=dict(budget='PPS 2026-27 Proposed Budget, Volume 2 (school summary pp. 10-11; individual school reports)',
                           sun='Multnomah County SUN Community School Contact List, August 2026'),
               title1_rule='Elementary, middle and K-8 schools with at least 33% of students qualifying for free meals by Direct Certification; high schools at 46.9%.',
               sun_sites=sorted(v for v in sun.values() if v), schools=out),
          open(os.path.join(OUT, 'school-programs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k in ['Rose City Park', 'Sitton', 'Arleta', 'Lent', 'Franklin', 'Harrison Park', 'Kelly']:
    print(k, json.dumps(out[k], ensure_ascii=False)[:400])
