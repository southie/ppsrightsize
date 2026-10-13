"""Travel-time histogram columns: center the column titles and the histograms under them, so each title lines up with
its chart. Getting-to-school table (walk, bike, drive, on the bus, walk to bus stop: columns 7-11) and the school
report's travel table (walk onward: columns 4+). CSS only; added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
a = """.commutetable td.cmh { padding-top: 6px; padding-bottom: 4px; } .commutetable td.cmh svg { display: block; margin-left: auto; overflow: visible; }"""
b = """.commutetable td.cmh { padding-top: 6px; padding-bottom: 4px; } .commutetable td.cmh svg { display: block; margin-left: auto; overflow: visible; }
/* histogram columns: titles and charts centered (scripts/patch_hist_center.py) */
.commutetable thead th:nth-child(n+7):nth-child(-n+11) { text-align: center; }
.commutetable td.cmh { text-align: center; } .commutetable td.cmh svg { margin-left: auto; margin-right: auto; }
.rptrav thead th:nth-child(n+4) { text-align: center; } .rptrav td.rph { text-align: center; } .rptrav td.rph svg { margin-left: auto; margin-right: auto; }"""
if 'patch_hist_center' not in html:
    assert html.count(a) == 1, html.count(a)
    html = html.replace(a, b)
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
