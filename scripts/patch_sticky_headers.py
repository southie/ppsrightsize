"""Keep the header row of the large tables (scenario impact, getting to school, staffing, over capacity) visible while
scrolling down. Each table's box scrolls both ways, at most a screen tall below the sticky scenario bar, so the header
row can stick to its top while the first column stays pinned on the left. Safe to rerun: added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if '/* large tables: header row stays visible' in html: sys.exit('already patched')
a = "#endpoints table tr.srow td:first-child, .stafftable tr.srow td:first-child, .commutetable tr.srow td:first-child { background: var(--surface-2); }"
assert html.count(a) == 1
html = html.replace(a, a + """
/* large tables: header row stays visible while scrolling down (the box scrolls both ways, under the scenario bar) */
#endpoints, #commute, #overlist, .tablewrap:has(> .stafftable) { max-height: max(360px, calc(100vh - 120px)); overflow: auto; overscroll-behavior: auto; }
#endpoints thead th, .commutetable thead th, .stafftable thead th, #overlist thead th {
  position: sticky; top: 0; z-index: 3; background: var(--surface-1); box-shadow: inset 0 -1px 0 var(--line);
}
#endpoints thead th:first-child, .commutetable thead th:first-child, .stafftable thead th:first-child, #overlist thead th:first-child {
  z-index: 4; box-shadow: inset -1px -1px 0 var(--line), 8px 0 8px -8px rgba(0, 0, 0, .25);
}
/* dimmed closed rows: keep the pinned cell's background solid so scrolled cells don't show through it */
tr.srow.closed td:first-child { opacity: 1; } tr.srow.closed td:first-child > * { opacity: .8; }""", 1)
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
