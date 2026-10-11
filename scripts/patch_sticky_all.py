"""Every table keeps its header row(s) and first column visible while scrolling: each table sits in a scroll box
(.tablewrap, at most a screen tall below the scenario bar), its whole header sticks to the top of that box and its
first column sticks to the left. Tables not already in a box (the school report's) are wrapped after each render.
Extends patch_sticky_headers (which did this for the largest tables). Code added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function wrapTables' not in html:
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
/* every table: header row(s) and first column stay visible while its box scrolls */
.tablewrap { max-height: max(360px, calc(100vh - 120px)); overflow: auto; overscroll-behavior: auto; }
.tablewrap > table > thead { position: sticky; top: 0; z-index: 3; }
.tablewrap > table > thead th { background: var(--surface-1); box-shadow: inset 0 -1px 0 var(--line); }
.tablewrap > table > thead > tr:first-child > th:first-child,
.tablewrap > table > tbody > tr > td:first-child, .tablewrap > table > tbody > tr > th:first-child,
.tablewrap > table > tfoot > tr > td:first-child {
  position: sticky; left: 0; z-index: 2; background: var(--surface-1); box-shadow: inset -1px 0 0 var(--line), 8px 0 8px -8px rgba(0, 0, 0, .18);
}
.tablewrap > table > thead > tr:first-child > th:first-child { z-index: 4; }
.tablewrap > table > tbody > tr.srow > td:first-child { background: var(--surface-2); }
.tablewrap > table > tbody > tr > td[colspan]:first-child { position: static; box-shadow: none; }""")
    rep("function renderAll() {", r"""// put any table that is not in a scroll box into one (school report tables), so its header and first column stick
function wrapTables(root = document) {
  root.querySelectorAll('main table').forEach(t => {
    if (t.closest('.tablewrap') || t.closest('.leaflet-container') || t.closest('.dock')) return;
    const w = document.createElement('div'); w.className = 'tablewrap'; t.parentNode.insertBefore(w, t); w.appendChild(t);
  });
}
renderReport = (f => function (...a) { const r = f.apply(this, a); if (typeof document.querySelectorAll === 'function') wrapTables(); return r; })(renderReport);
function renderAll() {""")
    rep("renderVirtual(); renderBusMap(); }", "renderVirtual(); renderBusMap(); if (typeof document.querySelectorAll === 'function') wrapTables(); }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
