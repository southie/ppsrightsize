"""Embed staffing inputs into rightsizing-scenario-explorer.html as D.staff:
  * PPS 2026-27 school staffing formula (Proposed Budget Vol. 1, pp. 206-210)
  * each school's 2025-26 grade mix (ODE fall membership) and Title I status (pps-data roster)
"""
import csv, json, os, re, shutil, sys
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
ODE = os.path.join(ROOT, 'pps-data', 'data', 'raw', 'fall_membership_2025_26.xlsx')
ROSTER = os.path.join(ROOT, 'pps-data', 'data', 'pps_schools.csv')
OUT = os.path.join(ROOT, 'source', 'staffing', 'staffing-inputs.json')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
keys = list(D['region_of'])

def norm(s):
    s = s.lower().replace('é', 'e').replace('á', 'a').replace('.', '').replace('-', ' ').replace('/', ' ')
    for w in ('elementary school', 'middle school', 'high school', 'k 8 school', 'school', 'elementary'):
        s = s.replace(w, '')
    return ' '.join(s.split())
ALIAS = {'MLK Jr': 'dr martin luther king jr', 'Boise-Eliot/Humboldt': 'boise eliot', 'Ida B Wells-Barnett': 'ida b wells barnett',
         'McDaniel': 'leodis v mcdaniel', 'Roseway Heights': 'roseway heights', 'Lane': 'lane', 'Lee': 'lee', 'Gray': 'gray',
         'Harrison Park': 'harrison park', 'Beverly Cleary': 'beverly cleary', 'César Chávez': 'cesar chavez'}

# ---- ODE grade counts ----
ws = openpyxl.load_workbook(ODE, read_only=True)['School 20252026']
rows = list(ws.iter_rows(values_only=True)); hdr = rows[0]
gcols = [hdr.index(h) for h in hdr if h and re.match(r'2025-26 (Kindergarten|Grade )', h)]
ode = {}
for r in rows[1:]:
    if r[0] and 'Portland SD' in str(r[0]) and r[2] and r[2] != 'Portland SD 1J':
        ode[norm(r[2])] = dict(name=r[2].strip(), grades=[int(r[c] or 0) for c in gcols])

# ---- Title I ----
title = {norm(r['school_name']): r['is_title_i'] == 'True' for r in csv.DictReader(open(ROSTER, encoding='utf-8'))}

schools, missing = {}, []
for k in keys:
    n = ALIAS.get(k, norm(k))
    o = ode.get(n) or next((v for kk, v in ode.items() if kk.startswith(n) or n.startswith(kk)), None)
    t = title.get(n, next((v for kk, v in title.items() if kk.startswith(n) or n.startswith(kk)), None))
    if not o: missing.append(k)
    schools[k] = dict(ode_name=o['name'] if o else None, grades_2526=o['grades'] if o else None, title1=bool(t))
print('no ODE grade counts:', missing)
print('Title I schools:', sorted(k for k, v in schools.items() if v['title1']))

FORMULA = dict(
    source='PPS 2026-27 Proposed Budget, Volume 1, School Staffing (pp. 206-210); allocations are preliminary per PPS',
    # K-5 homeroom maximums by grade K..5 (budget "Target Class Size")
    caps_budget={'title1': [28, 30, 30, 30, 33, 33], 'other': [29, 31, 32, 33, 34, 34]},
    caps_contract={'title1': [24, 26, 26, 26, 28, 28], 'other': [24, 26, 26, 26, 28, 28]},
    ms_ratio=23.5, ms_base_title1=1.0, hs_ratio=25.0, counselor_ratio=350,
)
out = dict(formula=FORMULA, schools=schools)
json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

shutil.copy(PAGE, os.path.join(ROOT, 'source', 'rightsizing-scenario-explorer.backup-before-staffing.html'))
D['staff'] = out
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
open(PAGE, 'w', encoding='utf-8').write(html)
print('D.staff embedded;', len(schools), 'schools')
