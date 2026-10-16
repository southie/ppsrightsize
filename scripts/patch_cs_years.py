"""Class sizes and teacher loads by grade: years follow the scenarios' timeline, as the General Fund chart does
(scripts/patch_gf_years.py).
  - Year dropdown: 2025-26 (actual), 2027-28 (first changes), 2028-29 (scenarios take effect).
  - Default year 2028-29 (FULL_YEAR); the remembered year uses a new key so the earlier default does not stick.
  - A note when a year before 2028-29 is chosen: before any change, or only the first changes (Sellwood and Marysville
    close in 2028-29). Schools close in the table from the year their enrollment ends (already per year).
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

if 'csTimelineNote' not in html:
    rep("""<div class="controls"><label>School year <select id="cs-year"></select></label></div>""",
        """<div class="controls"><label>School year <select id="cs-year"></select></label></div>
    <p class="muted" id="cs-note" style="font-size:12.5px;margin:0 0 6px"></p>""")
    rep("""let csYear = D.impl_year;
try { const y = localStorage.getItem('rsCsYear'); if (D.years.includes(y)) csYear = y; } catch (e) {}""",
        """let csYear = FULL_YEAR;   // patch_cs_years: the first year every change is in place
try { const y = localStorage.getItem('rsCsYear2'); if (D.years.includes(y)) csYear = y; } catch (e) {}""")
    rep("""    sel.innerHTML = D.years.map(y => `<option value="${y}">${y}${y === D.years[0] ? ' (actual)' : y === D.impl_year ? ' (scenarios take effect)' : ''}</option>`).join('');
    sel.onchange = () => { csYear = sel.value; try { localStorage.setItem('rsCsYear', csYear); } catch (e) {} renderClassSizes(); renderKPIs(); };""",
        """    sel.innerHTML = D.years.map(y => `<option value="${y}">${y}${y === D.years[0] ? ' (actual)' : y === D.impl_year ? ' (first changes)' : y === FULL_YEAR ? ' (scenarios take effect)' : ''}</option>`).join('');
    sel.onchange = () => { csYear = sel.value; try { localStorage.setItem('rsCsYear2', csYear); } catch (e) {} renderClassSizes(); renderKPIs(); };""")
    rep("""  sel.value = csYear;
  const yi = D.years.indexOf(csYear), sc = scen,""", """  sel.value = csYear; csTimelineNote();
  const yi = D.years.indexOf(csYear), sc = scen,""")
    rep("""function renderClassSizes() {""", """// note on the scenarios' timeline for the chosen year (scripts/patch_cs_years.py)
function csTimelineNote() {
  const el = document.getElementById('cs-note'); if (!el) return;
  const yi = D.years.indexOf(csYear), i0 = D.years.indexOf(D.impl_year), i1 = D.years.indexOf(FULL_YEAR);
  el.textContent = yi < i0 ? `${csYear} is before any scenario change. The scenarios start in ${D.impl_year} and are complete in ${FULL_YEAR}, when Sellwood and Marysville close; choose ${FULL_YEAR} to see their full effect.`
    : yi < i1 ? `${csYear} shows the first changes only: Sellwood and Marysville stay open until ${FULL_YEAR}, when the scenarios are complete.` : '';
}
function renderClassSizes() {""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
