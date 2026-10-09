"""PPS capital bond work by school, from the bond program's own reports (ppsbondhub.com):
  financials  "Bond Financials as of 07.01.26": each bond's projects with budget, outstanding encumbrance, amount paid
              to date and remaining balance (2012, 2017, 2020 and 2025 bonds)
  schedule    "PPS Summary Schedule 2026.09.02" (data date 06-Jul-26): each project's phases (design, permitting,
              construction, close-out) with start and finish dates; "A" marks an actual date
A project is assigned to a school only where the report names one school (modernizations, design, a school's field or
seismic work). District-wide pools (Health & Safety, Infrastructure, Technology, Curriculum, the 2025 Elementary &
Middle Schools and Priority Scope funds, administration, contingency) cannot be split by school; they are kept as
district totals. Scheduled work names the school and scope but carries no dollars.
Raw files (downloaded if missing): archive/bond/
Output: source/pps-bond/bond-projects.json
"""
import json, os, re, sys, urllib.request
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'archive', 'bond'); os.makedirs(RAW, exist_ok=True)
OUT = os.path.join(ROOT, 'source', 'pps-bond'); os.makedirs(OUT, exist_ok=True)
FIN_URL = 'https://ppsbondhub.com/wp-content/uploads/2026/09/Bond-Financials-as-of-07.01.26.pdf'
SCH_URL = 'https://ppsbondhub.com/wp-content/uploads/2026/09/PPS-Summary-Schedule-2026.09.02.pdf'
def get(url):
    f = os.path.join(RAW, os.path.basename(url))
    if not os.path.exists(f):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (pps-rightsizing-analysis)'})
        open(f, 'wb').write(urllib.request.urlopen(req, timeout=60).read())
    return f

# ---------- financials ----------
money = lambda s: float(s.replace('$', '').replace(',', ''))
FIN = {}
for page in pymupdf.open(get(FIN_URL)):
    t = page.get_text(); m = re.search(r'(\d{4}) Program Financial Status', t)
    if not m: continue
    bond = m.group(1); lines = [l.strip() for l in t.split('\n') if l.strip()]
    rows, i = [], 0
    while i < len(lines):
        l = lines[i]
        mm = re.match(r'^(.*?)\s*((?:-?\$[\d,]+\s*){4,5})$', l)   # "Name $a $b $c $d" on one line
        if mm and mm.group(1):
            name, nums = mm.group(1), re.findall(r'-?\$[\d,]+', mm.group(2)); i += 1
        elif not l.startswith(('$', '-$')) and i + 4 < len(lines) and all(re.fullmatch(r'-?\$[\d,]+', x) for x in lines[i + 1:i + 5]):
            name, nums = l, lines[i + 1:i + 5]; i += 5
            if i < len(lines) and re.fullmatch(r'-?\$[\d,]+', lines[i]): nums.append(lines[i]); i += 1
        else:
            i += 1; continue
        v = [money(x) for x in nums]
        budget, enc, paid, rem = (v[0], v[1], v[2], v[3]) if len(v) == 4 else (v[0] + v[1], v[2], v[3], v[4])
        rows.append(dict(project=name, budget=budget, encumbered=enc, paid=paid, remaining=rem))
    FIN[bond] = rows
    print(bond, len(rows), 'rows:', ', '.join(r['project'] for r in rows))

# project -> explorer school key (only projects that name one school)
PROJECT_SCHOOL = {
    ('2012', 'Franklin HS Mod'): 'Franklin', ('2012', 'Grant HS Mod'): 'Grant', ('2012', 'Roosevelt HS Mod'): 'Roosevelt',
    ('2012', 'Faubion Replace'): 'Faubion', ('2012', 'Grant Upper Field'): 'Grant', ('2012', 'RHS Phase IV'): 'Roosevelt',
    ('2017', 'Lincoln HS Repl'): 'Lincoln', ('2017', 'Kellogg MS Replace'): 'Kellogg', ('2017', 'McDaniel Mod'): 'McDaniel',
    ('2020', 'Jefferson HS Mod'): 'Jefferson', ('2020', 'Jefferson Add Ons'): 'Jefferson', ('2020', 'Cleveland HS – Design'): 'Cleveland',
    ('2020', 'Cleveland Swing Site'): 'Cleveland', ('2020', 'Wells HS – Design'): 'Ida B Wells-Barnett', ('2020', 'Roosevelt PhV – Design'): 'Roosevelt',
    ('2025', 'Jefferson HS Modernization'): 'Jefferson', ('2025', 'Cleveland HS Modernization'): 'Cleveland',
    ('2025', 'Ida B Wells HS Modernization'): 'Ida B Wells-Barnett'}
NOT_ON_PAGE = {'Benson', 'Benson HS Mod', 'Benson Add Ons', 'Benson Swings', 'Benson 2020 Funds', 'MPG Building', 'CEE'}

# ---------- schedule ----------
DATE = r'\d{2}-[A-Z][a-z]{2}-\d{2}'
def parse_date(s):
    m = re.match(r'(\d{2})-([A-Z][a-z]{2})-(\d{2})', s); mon = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split().index(m.group(2)) + 1
    return f'20{m.group(3)}-{mon:02d}-{m.group(1)}'
work, PHASE = [], re.compile(r'^(DESIGN|PERMITTING|CONSTRUCTION|CLOSE-OUT|A/E PROCUREMENT|DIRECT SELECT|LAND USE PERMIT|BUILDING PERMITS|DEMO|PROJECT REDESIGN|P&R NEGOTIATIONS|PROGRAMMING)')
SECTION = {'PORTLAND PS BOND PROGRAM', 'ATHLETIC FACILITIES', 'ALL SEISMIC 2025 BOND'}
SUB = re.compile(r'^(PHASE \w+|HUB FIELD|UPPER FIELD)')   # sub-projects under the project heading above them
for page in pymupdf.open(get(SCH_URL)):
    lines = [l.strip() for l in page.get_text().split('\n') if l.strip()]
    i, proj, sub = 0, None, None
    while i < len(lines):
        l = lines[i]
        # headings: capitals with at least four letters (durations and quarter labels are not), repeated in the text
        if re.fullmatch(r"[A-Z0-9][A-Z0-9 &/\-\.\(\)']+", l) and len(re.findall('[A-Z]', l)) >= 4 and not PHASE.match(l) \
                and l not in SECTION and not l.startswith(('PORTLAND', 'CLOSE-OUT &')):
            if SUB.match(l):
                if not (sub and (l.startswith(sub[:10]) or sub.startswith(l[:10]))): sub = l
                elif len(l) > len(sub): sub = l
            elif proj and (l.startswith(proj[:12]) or proj.startswith(l[:12])):
                if len(l) > len(proj): proj = l   # the longest spelling of a repeated heading
            else:
                proj, sub = l, None
            i += 1; continue
        if PHASE.match(l) and i + 3 < len(lines) and re.match(DATE, lines[i + 2]):
            st, fi, used = lines[i + 2], lines[i + 3], 4
            if not re.match(DATE, fi):   # start and finish on one line: the next line is already the next activity
                m2 = re.findall(DATE + r'\*?(?: A)?', st)
                if len(m2) >= 2: st, fi = m2[0], m2[1]
                used = 3
            work.append(dict(proj=proj, sub=sub, activity=l, start=parse_date(st), finish=parse_date(fi),
                             start_actual=' A' in st, finish_actual=' A' in fi))
            i += used; continue
        i += 1
print(len(work), 'scheduled activities')

D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', open(os.path.join(ROOT, 'rightsizing-scenario-explorer.html'), encoding='utf-8').read(), re.S).group(1))
KEYS = list(D['region_of'])
NAME_ALIAS = {'IDA B WELLS': 'Ida B Wells-Barnett', 'WELLS': 'Ida B Wells-Barnett', 'BEVERLY CLEARY': 'Beverly Cleary', 'MLK': 'MLK Jr'}
def schools_in(text):
    t = text.upper(); hits = [v for k, v in NAME_ALIAS.items() if re.search(r'\b' + re.escape(k) + r'\b', t)]
    for k in sorted(KEYS, key=len, reverse=True):
        if re.search(r'\b' + re.escape(k.upper()) + r'\b', t) and k not in hits and not any(k in h for h in hits): hits.append(k)
    return hits
# group activities into projects (school, scope = the project heading, plus the sub-project if any)
proj = {}
for w in work:
    if not w['proj']: continue
    title = w['proj'] + (f" / {w['sub']}" if w['sub'] else '')
    for k in schools_in(w['proj']):
        proj.setdefault((k, title), []).append(w)
def status(acts):
    if all(a['finish_actual'] for a in acts): return 'complete'
    if any(a['start_actual'] and a['activity'].startswith(('CONSTRUCTION', 'DEMO')) for a in acts): return 'in construction'
    if any(a['start_actual'] for a in acts): return 'in design or permitting'
    return 'planned'
schools = {}
for (k, title), acts in proj.items():
    cons = [a for a in acts if a['activity'].startswith(('CONSTRUCTION', 'DEMO'))]
    scope = re.sub(r'\s*\(COMPLETE\)', '', title).title()
    for a_, b_ in (('Hs', 'HS'), ('Ms', 'MS'), ('Cee', 'CEE'), ('B- ', 'B, '), ('And', 'and'), ('Phase 1a', 'Phase 1A'), ('Phase 1b', 'Phase 1B')): scope = scope.replace(a_, b_)
    schools.setdefault(k, {}).setdefault('work', []).append(dict(
        scope=scope, status=status(acts), finish=max(a['finish'] for a in acts),
        construction=[min(a['start'] for a in cons), max(a['finish'] for a in cons)] if cons else None,
        phases=[[a['activity'].title(), a['start'], a['finish'], a['finish_actual']] for a in acts]))
for bond, rows in FIN.items():
    for r in rows:
        k = PROJECT_SCHOOL.get((bond, r['project']))
        if k: schools.setdefault(k, {}).setdefault('dollars', []).append(dict(bond=bond, **r))
pools = {bond: [r for r in rows if (bond, r['project']) not in PROJECT_SCHOOL and r['project'] not in NOT_ON_PAGE and 'Total' not in r['project']] for bond, rows in FIN.items()}
totals = {bond: next((r for r in rows if 'Total' in r['project']), None) for bond, rows in FIN.items()}
J = dict(source='PPS bond program reports, ppsbondhub.com: Bond Financials as of 07.01.26; PPS Summary Schedule (data date 06-Jul-26, run 02-Sep-26)',
         as_of='2026-07-01', schedule_as_of='2026-07-06', financials_url=FIN_URL, schedule_url=SCH_URL,
         schools=schools, pools=pools, totals=totals, note=__doc__.split('Raw files')[0].strip())
json.dump(J, open(os.path.join(OUT, 'bond-projects.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
for k, v in sorted(schools.items()):
    print(k, '| $', [(d['bond'], d['project'], round(d['budget'] / 1e6, 1), round(d['paid'] / 1e6, 1)) for d in v.get('dollars', [])],
          '| work', [(w['scope'], w['status'], w['finish']) for w in v.get('work', [])])
print('pools:', {b: [(p['project'], round(p['budget'] / 1e6)) for p in v] for b, v in pools.items()})
