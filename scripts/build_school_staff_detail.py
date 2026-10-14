"""Full staffing detail for each school from PPS's 2026-27 Proposed Budget, Volume 2 (Individual School Reports), for the
school report's "Beyond the formula" panel: 2021-22 to 2025-26 actual and 2026-27 budget (1.00 FTE = 40 hours a week).
  School-allocated FTE by position: licensed (teachers, counseling, library/media, instructional specialists / coaches /
  interventionists, other), classified (clerical, educational assistants / paraeducators, library, other), administrators,
  school total.
  Centrally Allocated School Resources (CASR): licensed (special education, ESL, other) and classified (special
  education, ESL, nutrition services, custodial, other), CASR total, grand total, students per FTE.
  School-allocated FTE by funding source: licensed (General Fund, Gen Fund Equity, Gen Fund K-5 Arts, Foundation,
  Title I, SIA/M98, other), classified (General Fund, Equity, Foundation, Title I, SIA/M98, other), administrators
  (General Fund, Equity, Title I, other).
The PDF's text order scrambles the tables, so rows are read by position: each row label (a fixed set, in a fixed
order) is located on the page and its values are the numbers level with the label's middle, under each year's column.
Checks: positions add up to the school total, CASR rows to the CASR total, funding rows to the school total.
Input: archive/budget/2026-27ProposedBudget-Volume2.pdf    Output: source/staffing/school-staff-detail.json
"""
import json, os, re, sys, unicodedata
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, 'archive', 'budget', '2026-27ProposedBudget-Volume2.pdf')
OUT = os.path.join(ROOT, 'source', 'staffing', 'school-staff-detail.json')
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
YRS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26', '2026-27']
FIRST = {'Teachers', 'Counseling', 'Library/Media', 'Instructional', 'Other', 'Clerical', 'Ed.', 'Special', 'ESL', 'Nutrition', 'Custodial', 'Gen', 'Foundation', 'Title', 'SIA/M98'}
CONT = {'Services', 'Spec/', 'Intervention', 'Paraeducator', 'Education'}
POS = ['lic_teachers', 'lic_counseling', 'lic_library', 'lic_coach', 'lic_other', 'cls_clerical', 'cls_ea', 'cls_library', 'cls_other']
CASR = ['casr_lic_sped', 'casr_lic_esl', 'casr_lic_other', 'casr_cls_sped', 'casr_cls_esl', 'casr_cls_nutrition', 'casr_cls_custodial', 'casr_cls_other']
FUND = ['f_lic_gf', 'f_lic_equity', 'f_lic_arts', 'f_lic_foundation', 'f_lic_title1', 'f_lic_sia', 'f_lic_other',
        'f_cls_gf', 'f_cls_equity', 'f_cls_foundation', 'f_cls_title1', 'f_cls_sia', 'f_cls_other',
        'f_adm_gf', 'f_adm_equity', 'f_adm_title1', 'f_adm_other']

d = pymupdf.open(PDF)
schools, problems = {}, []
for i, p in enumerate(d):
    W = p.get_text('words')
    staff = [w for w in W if w[4] == 'Staff' and w[0] < 110]
    if len(staff) < 2: continue
    sy, fy = sorted(w[1] for w in staff)[:2]          # "Staff Type Position" and "Staff Type Funding Source" headers
    hdr = sorted([w for w in W if w[4] in YRS and abs(w[1] - (sy - 6)) < 8], key=lambda w: w[0])
    if len(hdr) != 6: continue
    hx = [w[2] for w in hdr]
    def vals(y, tol=2.6):
        v = [0.0] * 6
        for w in W:
            if abs(w[1] - y) < tol and re.fullmatch(r'\d+\.\d\d', w[4]) and w[0] > 190:
                j = min(range(6), key=lambda j: abs(w[2] - hx[j]))
                if abs(w[2] - hx[j]) < 15: v[j] = float(w[4])
        return v
    # label lines in the row-label column
    lines = {}
    for w in W:
        if 134 < w[0] < 190 and w[1] > sy: lines.setdefault(round(w[1], 1), []).append(w)
    ls = sorted((y, sorted(ws, key=lambda w: w[0])) for y, ws in lines.items())
    anchors = []   # (y centre, first word, line text)
    j = 0
    while j < len(ls):
        y, ws = ls[j]
        if ws[0][4] in FIRST and ws[0][0] < 145:
            y2 = y
            while j + 1 < len(ls) and ls[j + 1][0] - y2 < 10.5 and ls[j + 1][1][0][4] in CONT: j += 1; y2 = ls[j][0]
            anchors.append(((y + y2) / 2, ws[0][4], ' '.join(w[4] for w in ws)))
        j += 1
    left = lambda t: sorted([w for w in W if w[4] == t and w[0] < 125], key=lambda w: w[1])
    st = [w for w in left('Total') if any(x[4] == 'School' and abs(x[1] - w[1]) < 2 and x[0] < w[0] for x in W)]
    if len(st) < 2: continue
    st1, st2 = st[0][1], st[-1][1]
    adm = [w for w in left('Admin.') if sy < w[1] < st1]
    casrT = [w for w in left('CASR') if st1 < w[1] < fy and any(x[4] == 'Total' and abs(x[1] - w[1]) < 2 for x in W)]
    grand = [w for w in left('Grand') if st1 < w[1] < fy]
    rec = {}
    pos = [a for a in anchors if a[0] < st1]; cas = [a for a in anchors if st1 < a[0] < (casrT[0][1] if casrT else fy)]; fun = [a for a in anchors if fy < a[0] < st2]
    for names, got in ((POS, pos), (CASR, cas), (FUND, fun)):
        if len(got) != len(names): problems.append((i + 1, names[0], len(got), len(names))); continue
        for nm, a in zip(names, got): rec[nm] = vals(a[0])
    if adm: rec['admin'] = vals(adm[0][1])
    rec['school_total'] = vals(st1); rec['school_total_funding'] = vals(st2)
    if casrT: rec['casr_total'] = vals(casrT[0][1])
    if grand: rec['grand_total'] = vals(grand[0][1])
    ov = [w for w in W if w[4] == 'Overall' and w[0] < 100]
    if ov:
        rr = [None] * 6
        for w in W:
            if abs(w[1] - ov[0][1]) < 3 and re.fullmatch(r'[\d.]+:1', w[4]):
                jj = min(range(6), key=lambda j: abs(w[2] - hx[j])); rr[jj] = float(w[4][:-2])
        rec['students_per_fte'] = rr
    title = ' '.join(w[4] for w in sorted([w for w in W if w[1] < 60 and w[0] < 200], key=lambda w: (round(w[1]), w[0])))
    schools[title] = dict(page=i + 1, **rec)
print(f'{len(schools)} school reports; label-count problems: {problems[:6]}')

# ---- checks ----
bad = []
for t, r in schools.items():
    for j in range(6):
        pos = sum(r.get(k, [0] * 6)[j] for k in POS) + r.get('admin', [0] * 6)[j]
        cas = sum(r.get(k, [0] * 6)[j] for k in CASR); fun = sum(r.get(k, [0] * 6)[j] for k in FUND)
        for lab, a, b in (('positions', pos, r['school_total'][j]), ('casr', cas, r.get('casr_total', [0] * 6)[j]), ('funding', fun, r['school_total'][j])):
            if abs(a - b) > 0.06: bad.append((t, YRS[j], lab, round(a, 2), b))
print('sum checks failing:', len(bad), bad[:8])

# ---- match to the explorer's schools (as build_school_staff.py) ----
html = open(PAGE, encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
def n(s): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
ALIAS = {'MLK Jr': 'MARTIN LUTHER KING JR', 'Ida B Wells-Barnett': 'IDA B. WELLS-BARNETT', 'McDaniel': 'MCDANIEL', 'Bridger Creative Science': 'BRIDGER CREATIVE'}
TN = {n(t): t for t in schools}
match = {}
for k in D['region_of']:
    c = n(ALIAS.get(k, k)); t = TN.get(c) or next((t for nt, t in TN.items() if c and (nt.startswith(c) or c.startswith(nt))), None)
    if t: match[k] = t
print('matched', len(match), 'of', len(D['region_of']), '| missing:', [k for k in D['region_of'] if k not in match])
r2 = lambda v: [round(x, 2) for x in v] if isinstance(v, list) and v and isinstance(v[0], float) else v
J = dict(source='PPS 2026-27 Proposed Budget, Volume 2, Individual School Reports (1.00 FTE = 40 hours a week; CASR = centrally allocated school resources)',
         years=YRS, fields=dict(positions=POS + ['admin', 'school_total'], casr=CASR + ['casr_total', 'grand_total', 'students_per_fte'], funding=FUND),
         schools={k: {f: r2(v) for f, v in schools[t].items()} | dict(report=t) for k, t in match.items()})
json.dump(J, open(OUT, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
print('wrote', os.path.relpath(OUT, ROOT))
