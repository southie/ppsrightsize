"""School report: the "Getting to school" panel title without the year (it shows the year just after the scenario
applies; the year is in the report's year selector). Code changed once."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
a = "<h3>Getting to school, ${rpYear}${sc === 'SQ' ? '' : `: ${esc(LABEL[sc])} and Status Quo`}</h3>"
b = "<h3>Getting to school${sc === 'SQ' ? '' : `: ${esc(LABEL[sc])} and Status Quo`}</h3>"
if a in html:
    assert html.count(a) == 1
    html = html.replace(a, b)
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
