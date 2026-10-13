"""Trip corridors on the school report map: D.corr from source/block-access/corridors.json
(scripts/build_block_access.py): for each school and scenario, the street segments that would carry at least 3% of its
attendance area's school-age residents by bike (lowest-stress route) and by car (fastest route), by share level, and
the named streets carrying the most; for each closed school, its Status Quo area's corridors to its new schools.
The map layer and its note are in scripts/school_report.js (rpCorrLayer). Data refreshed on rerun.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
C = json.load(open(os.path.join(ROOT, 'source', 'block-access', 'corridors.json'), encoding='utf-8'))
# street names shortened the way Portland signs them (Southeast Division Street -> SE Division St)
AB = [('Southeast ', 'SE '), ('Southwest ', 'SW '), ('Northeast ', 'NE '), ('Northwest ', 'NW '), ('North ', 'N '), ('South ', 'S '),
      (' Avenue', ' Ave'), (' Street', ' St'), (' Boulevard', ' Blvd'), (' Road', ' Rd'), (' Drive', ' Dr'), (' Place', ' Pl'),
      (' Court', ' Ct'), (' Highway', ' Hwy'), (' Parkway', ' Pkwy'), (' Lane', ' Ln'), (' Terrace', ' Ter'), (' Frontage Rd', ' frontage')]
def short_name(n):
    for a, b in AB: n = n.replace(a, b) if not a.endswith(' ') else (b + n[len(a):] if n.startswith(a) else n)
    return n
for part in ('S', 'F'):
    for m_, bysc in C[part].items():
        for sc, bys in bysc.items():
            for k, v in bys.items():
                for r in (v if isinstance(v, list) else [v]):
                    for x in r['st']: x[0] = short_name(x[0])
                    for h in r.get('H', []): h[4] = short_name(h[4]) if h[4] and '_' not in h[4] else 'a highway ramp' if '_' in (h[4] or '') else h[4]
D['corr'] = {k: C[k] for k in ('levels', 'min_share', 'S', 'F', 'method', 'hazards')}
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print(f"D.corr {len(json.dumps(D['corr'], separators=(',', ':'))) / 1e6:.2f} MB; page {os.path.getsize(PAGE) / 1e6:.2f} MB")
