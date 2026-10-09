"""Data for the school report's getting-to-school panel: D.commute.R, the travel of each area a scenario takes away
from a school (closures, and grade bands a school stops serving) to the schools its blocks are newly assigned to
(source/block-access/closure-access.json, scripts/build_closure_access.py). The panel itself is in
scripts/school_report.js; run this, then scripts/patch_school_report.py. Data refreshed on rerun.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['commute']['R'] = json.load(open(os.path.join(ROOT, 'source', 'block-access', 'closure-access.json'), encoding='utf-8'))
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('embedded D.commute.R')
