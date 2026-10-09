"""Actual school staffing from PPS's 2026-27 Proposed Budget, Volume 2 (Individual School Reports): each school's
school-allocated FTE by position for 2021-22 to 2025-26 (actual) and 2026-27 (budget), read by position on the page
(the PDF's text order scrambles the table). Kept: teachers, administrators (principals and assistant principals,
"Admin."), clerical, and the school total (school-allocated, not centrally allocated custodial / nutrition / special
education). 1.00 FTE = 40 hours a week in these reports.
Schools are matched to the explorer's keys; program schools the explorer does not model (ACCESS, Alliance, Benson,
da Vinci, Metropolitan Learning Center, ...) count in the district totals only.
Input: archive/budget/2026-27ProposedBudget-Volume2.pdf
Output: source/staffing/school-staff-budget.json
"""
import json, os, re, sys, unicodedata
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, 'archive', 'budget', '2026-27ProposedBudget-Volume2.pdf')
OUT = os.path.join(ROOT, 'source', 'staffing', 'school-staff-budget.json')
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
YRS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26', '2026-27']
ROWS = {'Teachers': 'teachers', 'Clerical': 'clerical', 'Admin.': 'admin'}

d = pymupdf.open(PDF)
schools = {}
for i, p in enumerate(d):
    W = p.get_text('words')
    staff = [w for w in W if w[4] == 'Staff']
    if not staff: continue
    sy = staff[0][1]
    hdr = sorted([w for w in W if w[4] in YRS and abs(w[1] - (sy - 6)) < 8], key=lambda w: w[0])
    if len(hdr) != 6: continue
    hx = [w[2] for w in hdr]   # numbers are right-aligned under the year headers
    def vals(y):
        v = [None] * 6
        for w in W:
            if abs(w[1] - y) < 2.5 and re.fullmatch(r'\d+\.\d\d', w[4]) and w[0] > 190:
                j = min(range(6), key=lambda j: abs(w[2] - hx[j]))
                if abs(w[2] - hx[j]) < 15: v[j] = float(w[4])
        return v
    end = min([w[1] for w in W if w[4] == 'Grand' and w[1] > sy] or [9e9])
    rec = {}
    for lab, key in ROWS.items():
        c = sorted([w for w in W if w[4] == lab and sy < w[1] < end], key=lambda w: w[1])
        if c: rec[key] = vals(c[0][1])   # first occurrence: the FTE-by-position table
    st = sorted([w for w in W if w[4] == 'Total' and w[0] < 125 and sy < w[1] < end
                 and any(x[4] == 'School' and abs(x[1] - w[1]) < 2 and x[0] < w[0] for x in W)], key=lambda w: w[1])
    if st: rec['school_total'] = vals(st[0][1])
    title = ' '.join(w[4] for w in sorted([w for w in W if w[1] < 60 and w[0] < 200], key=lambda w: (round(w[1]), w[0])))
    schools[title] = dict(page=i + 1, **rec)
print(f'{len(schools)} school reports')

# ---- match to the explorer's schools ----
html = open(PAGE, encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
def n(s): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
ALIAS = {'MLK Jr': 'MARTIN LUTHER KING JR', 'Ida B Wells-Barnett': 'IDA B. WELLS-BARNETT', 'McDaniel': 'MCDANIEL', 'Bridger Creative Science': 'BRIDGER CREATIVE'}
TN = {n(t): t for t in schools}
match = {}
for k in D['region_of']:
    c = n(ALIAS.get(k, k))
    t = TN.get(c) or next((t for nt, t in TN.items() if c and (nt.startswith(c) or c.startswith(nt))), None)
    if t: match[k] = t
missing = [k for k in D['region_of'] if k not in match]
unused = sorted(set(schools) - set(match.values()))
print('matched', len(match), '| explorer schools without a report:', missing, '| reports not on the explorer:', unused)

def total(keys, f, j): return round(sum((schools[t].get(f) or [0] * 6)[j] or 0 for t in keys), 1)
J = dict(source='PPS 2026-27 Proposed Budget, Volume 2, Individual School Reports (school-allocated FTE by position; 1.00 FTE = 40 hours a week)',
         years=YRS, actual_years=YRS[:5], budget_year=YRS[5],
         district={f: [total(schools, f, j) for j in range(6)] for f in ('teachers', 'admin', 'clerical', 'school_total')},
         reports=len(schools), not_on_explorer=unused,
         schools={k: {f: schools[t].get(f) for f in ('teachers', 'admin', 'clerical', 'school_total')} | dict(report=t, page=schools[t]['page']) for k, t in match.items()})
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(J, open(OUT, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
for f, v in J['district'].items(): print(f, dict(zip(YRS, v)))
