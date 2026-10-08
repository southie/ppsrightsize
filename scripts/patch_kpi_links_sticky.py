"""Summary cards link to their detail (column in the measures table, or the over-capacity list),
and the first column of the measures and staffing tables stays visible when scrolling right."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function goTo(' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# wire the cards each time they render
rep("  }).join('') + extraKPIs() + staffKPI();", "  }).join('') + extraKPIs() + staffKPI();\n  wireKPIs();")

# navigation helpers (function declarations are hoisted, so renderKPIs can call them)
rep("function extraKPIs() {",
r"""// ---------- summary cards link to their detail ----------
// cards render in this order: the four PPS district measures, then extraKPIs() (over capacity, 15-minute access,
// building costs, land value), then staffKPI(); keep this list in step if cards are added or reordered
const KPI_TARGETS = ['closures', 'schools_above', 'students_above', 'change', 'overcap', 'reach', 'cost', 'land', 'staff'];
// columns of the measures table, in header order (see renderEndpoints)
function endpointCols() { return ['region', ...MEAS.map(m => m.key), 'util', 'reach', 'cost', 'staff', 'land', 'change']; }
function flash(els) {
  els.forEach(e => { e.classList.remove('flash'); void e.offsetWidth; e.classList.add('flash'); });
  setTimeout(() => els.forEach(e => e.classList.remove('flash')), 2700);
}
function goTo(target) {
  if (target === 'overcap') {
    const d = document.getElementById('overwrap'); if (!d) return;
    d.open = true; d.scrollIntoView({ behavior: 'smooth', block: 'start' }); flash([d]); return;
  }
  const tbl = document.querySelector('#endpoints table'), wrap = document.getElementById('endpoints');
  const idx = endpointCols().indexOf(target);
  if (!tbl || idx < 0) return;
  tbl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  const head = tbl.tHead.rows[0], th = head.cells[idx], pinned = head.cells[0].offsetWidth;
  wrap.scrollTo({ left: Math.max(0, th.offsetLeft - pinned - 24), behavior: 'smooth' });
  flash([...tbl.rows].map(r => r.cells[idx]).filter(Boolean));
}
function wireKPIs() {
  document.querySelectorAll('#kpis .kpi').forEach((k, i) => {
    const t = KPI_TARGETS[i]; if (!t) return;
    k.classList.add('go'); k.tabIndex = 0; k.setAttribute('role', 'link');
    k.title = t === 'overcap' ? 'Show the schools over capacity' : 'Show this in the table by region';
    k.onclick = () => goTo(t);
    k.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goTo(t); } };
  });
}
function extraKPIs() {""")

# styles: clickable cards, highlight, pinned first column
rep(".kpi { background: var(--surface-1); border-radius: 12px; padding: 12px 14px; }",
""".kpi { background: var(--surface-1); border-radius: 12px; padding: 12px 14px; }
.kpi.go { cursor: pointer; transition: box-shadow .15s; }
.kpi.go:hover, .kpi.go:focus-visible { box-shadow: 0 0 0 2px var(--change); outline: none; }
.flash { animation: flashcol 2.6s ease-out; }
@keyframes flashcol { 0%, 45% { background-color: rgba(250, 178, 25, .32); } 100% { background-color: inherit; } }
#endpoints table, #overwrap { scroll-margin-top: 72px; }
/* keep the Region / school column visible when the wide tables scroll sideways */
#endpoints table th:first-child, #endpoints table td:first-child,
.stafftable th:first-child, .stafftable td:first-child {
  position: sticky; left: 0; z-index: 2; background: var(--surface-1);
  box-shadow: inset -1px 0 0 var(--line), 8px 0 8px -8px rgba(0, 0, 0, .25);
}
#endpoints table tr.srow td:first-child, .stafftable tr.srow td:first-child { background: var(--surface-2); }""")
open(PAGE, 'w', encoding='utf-8').write(html)
print('patched')
