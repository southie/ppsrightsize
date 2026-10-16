"""General Fund cost per student by school: years follow the scenarios' timeline.
  - Year dropdown: 2026-27 (budget year), 2027-28 (first changes), 2028-29 (scenarios take effect: every change in place,
    Sellwood and Marysville close then).
  - A school counts as closed in the chosen year only from the year it closes (its scenario enrollment ends), so
    Sellwood and Marysville are open in 2027-28.
  - Default year 2028-29 (FULL_YEAR); the remembered year uses a new key so the earlier default does not stick.
  - With 2026-27 chosen, a note that the scenarios start in 2027-28 and are complete in 2028-29.
Code changed once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b, n=1):
    global html
    assert html.count(a) == n, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'gfTimelineNote' not in html:
    rep("""${y === '2026-27' ? ' (budget year)' : y === D.impl_year ? ' (scenarios take effect)' : ''}</option>`).join('');""",
        """${y === '2026-27' ? ' (budget year)' : y === D.impl_year ? ' (first changes)' : y === FULL_YEAR ? ' (scenarios take effect)' : ''}</option>`).join('');""")
    rep("""const ys = D.years.indexOf(gfYear), sc = scen, cl = D.detail[sc]?.[k]?.closed || (sc === 'C' && !D.series.C?.[k]?.[ys]);   // a custom scenario's own closures""",
        """const ys = D.years.indexOf(gfYear), sc = scen, cl = sc !== 'SQ' && D.series[sc]?.[k]?.[ys] == null;   // closed in that year (Sellwood and Marysville from 2028-29; custom scenarios' own closures)""")
    rep("localStorage.getItem('rsGfYear')", "localStorage.getItem('rsGfYear2')")
    rep("localStorage.setItem('rsGfYear', gfYear)", "localStorage.setItem('rsGfYear2', gfYear)")
    rep("""function renderAll() {""", """// General Fund chart: when the budget year is shown, say that the scenarios are not yet in place (scripts/patch_gf_years.py)
{ const _rg = renderGFPer; renderGFPer = function () { _rg(); gfTimelineNote(); }; }
function gfTimelineNote() {
  const sub = document.getElementById('gfpersub'); if (!sub || gfYear !== '2026-27') return;
  sub.innerHTML = `<span class="muted" style="display:block;border-left:3px solid var(--line);padding:2px 8px;margin-bottom:6px">${'2026-27'} is the budget year, before any scenario change. The scenarios start in ${D.impl_year} and are complete in ${FULL_YEAR}, when Sellwood and Marysville close; choose ${FULL_YEAR} to see their full effect.</span>` + sub.innerHTML;
}
function renderAll() {""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
