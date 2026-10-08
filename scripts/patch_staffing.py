"""Add the staffing-impact section (scripts/staffing.js) to rightsizing-scenario-explorer.html."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function renderStaffing' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

rep("""  <section class="card">
    <h2>Projected enrollment by school, 2025-26 to 2035-36</h2>""",
"""  <section class="card">
    <h2>Staffing impact: positions no longer needed</h2>
    <p class="sub">Applies PPS's 2026-27 school staffing formula (Adopted Budget, Volume 1, pp. 232-238) to every school's projected enrollment under the selected scenario and under Status Quo in the same year; the difference is positions the formula no longer funds. K-5 homerooms are counted grade by grade from each school's 2025-26 grade mix, so they capture students filling open seats at receiving schools. Counts are licensed-equivalent FTE (an administrative assistant counts as half). Positions funded by equity, Title I, special education, multilingual, Measure 98 and grants, which largely follow students, are excluded. Whether reductions become layoffs, reassignments or attrition is PPS's decision.</p>
    <p class="sub" id="staffsum"></p>
    <div id="staffing"></div>
  </section>

  <section class="card">
    <h2>Projected enrollment by school, 2025-26 to 2035-36</h2>""")
rep("function renderAll() { renderKPIs(); renderCustomPanel(); renderMap(); renderEndpoints(); renderLines(); }",
    open(os.path.join(ROOT, 'scripts', 'staffing.js'), encoding='utf-8').read() +
    "\nfunction renderAll() { renderKPIs(); renderCustomPanel(); renderMap(); renderEndpoints(); renderStaffing(); renderLines(); }")
rep(".hide-rec .rec { display: none; }",
""".hide-rec .rec { display: none; }
.staffctl { flex-wrap: wrap; } .staffctl select { max-width: 100%; }
.capgrid { margin: 0 0 12px; overflow-x: auto; } .capgrid table { min-width: 0; width: auto; }
.capgrid th, .capgrid td { padding: 4px 8px; text-align: center; } .capgrid th:first-child { text-align: left; }
.capgrid input { width: 56px; font: inherit; font-size: 13px; padding: 3px 6px; border-radius: 6px; border: 1px solid var(--line); background: var(--surface-1); color: var(--text-primary); text-align: right; }
.stafftable td, .stafftable th { white-space: nowrap; } .stafftable td .main { font-size: 14px; font-weight: 600; }""")
open(PAGE, 'w', encoding='utf-8').write(html)
print('patched')
