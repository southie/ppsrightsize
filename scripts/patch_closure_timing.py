"""Closure timing in the reconstruction of Scenarios A and B: Sellwood (middle school) and Marysville close in 2028-29,
not 2027-28. PPS's move rules (source/pps-powerbi, scenarios table) move their students in 2028; every other closure
is in 2027.
  2027-28: Sellwood and Marysville keep their Status Quo enrollment; the schools that take their students give them
  back for that year: Arleta all of Marysville; Hosford and Brentwood (Lane) Sellwood's, split by PPS's shares of
  Sellwood's neighborhood students (A: Hosford 49.8%, B: 33.9%; the rest to Brentwood).
The PPS model results (scripts/build_pps_model.py) already follow PPS's years. Data changed once (the reconstruction's
series are embedded; a rerun finds them already open in 2027-28 and changes nothing).
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
yi = D['years'].index('2027-28')
HOSFORD = {'A': 0.498127340823, 'B': 0.33855799373}   # PPS: share of Sellwood's neighborhood students to Hosford
changed = []
for sc in ('A', 'B'):
    S = D['series'][sc]; Q = D['series']['SQ']
    if S['Sellwood'][yi] is None:
        v = Q['Sellwood'][yi]; S['Sellwood'][yi] = v
        S['Hosford'][yi] = round(S['Hosford'][yi] - v * HOSFORD[sc], 1); S['Lane'][yi] = round(S['Lane'][yi] - v * (1 - HOSFORD[sc]), 1)
        changed.append(f'{sc}: Sellwood {v} open in 2027-28')
    if S['Marysville'][yi] is None:
        v = Q['Marysville'][yi]; S['Marysville'][yi] = v; S['Arleta'][yi] = round(S['Arleta'][yi] - v, 1)
        changed.append(f'{sc}: Marysville {v} open in 2027-28')
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched;', '; '.join(changed) or 'already open in 2027-28')
