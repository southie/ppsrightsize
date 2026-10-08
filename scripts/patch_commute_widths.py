"""Getting-to-school table: narrower first four data columns (students, beyond bus distance, bus student-miles, bus
cost) so more of the table fits in view; their headers and notes wrap instead of widening the column. Full-width
message cells (closed and program-school rows) are left alone. Safe to rerun: added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if '/* getting to school: narrower first four data columns' in html: sys.exit('already patched')
a = ".commutetable td, .commutetable th { white-space: nowrap; } .commutetable td .main { font-size: 14px; font-weight: 600; }"
assert html.count(a) == 1
html = html.replace(a, a + """
/* getting to school: narrower first four data columns (headers and notes wrap) */
.commutetable thead th:nth-child(n+2):nth-child(-n+5) { white-space: normal; width: 108px; min-width: 96px; max-width: 112px; }
.commutetable tbody td:nth-child(n+2):nth-child(-n+5):not([colspan]) { width: 108px; max-width: 112px; }
.commutetable td .cmprog { white-space: normal; line-height: 1.3; }""", 1)
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
