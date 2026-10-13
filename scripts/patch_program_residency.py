"""WITHDRAWN (now data only): where each school's program students live (D.progres). It used to send a closing school's
immersion students who live in its neighborhood to the neighborhood school; immersion students now all follow their
program to the consolidated immersion school. Original description:
Where a closing school's immersion students go, by where they live: part of the "Modified enrollment model" switch.
PPS's scenarios send a closing school's immersion (DLI) program to a new site and its neighborhood students to a
neighborhood receiver; the model sent all of the school's immersion share (D.dli) to the new site. PPS's October 2025
enrollment by neighborhood (source/pps-programs/enroll-by-neighborhood.json, scripts/build_enroll_by_neighborhood.py)
says how many of each immersion program's students live in the school's own neighborhood. With the switch on, those
students go to the closing school's neighborhood receiver(s) instead, and the rest follow the program to its new site.
Affects Beach and James John (Spanish, to Cesar Chavez; their neighborhoods to Chief Joseph and Sitton) and, in
Scenario A, Rose City Park (Vietnamese, to Vestal; neighborhood to Scott). Focus schools that close without their
focus moving (Buckman, arts) already send their students to the neighborhood receivers, so they are unchanged.
The same split drives custom scenarios that keep such a school open (the students returned from each receiver) and the
closures' staffing figures. Data: D.progres {school: {imm: [program, share living in the school's neighborhood,
program students, school total], nb: whole school's share}}. Runs after patch_k8_shares / patch_boundary_adjust.
Data refreshed on rerun; code added once.
"""
import json, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
R = json.load(open(os.path.join(ROOT, 'source', 'pps-programs', 'enroll-by-neighborhood.json'), encoding='utf-8'))['schools']
n = lambda s: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
RN = {n(k): k for k in R}
P = {}
for k in D['region_of']:
    r = R.get(RN.get(n(k)))
    if not r: continue
    e = {'nb': r['Total']['nbhd_share']} if r.get('Total') else {}
    imm = [(p, v) for p, v in r.items() if 'Immersion' in p and v['total']]
    if len(imm) == 1:
        p, v = imm[0]; e['imm'] = [p.replace(' Immersion', ''), v['nbhd_share'], v['total'], r['Total']['total']]
    P[k] = e
D['progres'] = P
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
print(len(P), 'schools;', sum('imm' in v for v in P.values()), 'with one immersion program')

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# Withdrawn: closing schools' immersion students all go to their consolidated immersion school (the model's own
# split), so the page code this script used to add (the move, the receivers' weights, the switch text) was removed;
# only the data (D.progres) is kept.
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
