"""Getting to school (walk, bike and drive times, bus distance): no year dropdown; the section shows the year after the
scenarios are fully in place (FULL_YEAR, 2028-29). The remembered year and the link's year are no longer used.
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

if 'patch_cm_full_year' not in html:
    rep("""<label>Grades <select id="cm-band"></select></label><label>Year <select id="cm-year"></select></label></div>""",
        """<label>Grades <select id="cm-band"></select></label></div>""")
    rep("""let cmYear = '2031-32';""", """let cmYear = FULL_YEAR;   // after the scenarios are fully in place; no year choice (patch_cm_full_year)""")
    rep("""try { const y = localStorage.getItem('rsCmYear'); if (CM_YEARS.includes(y)) cmYear = y; } catch (e) {}\n""", "")
    rep("""  const ysel = document.getElementById('cm-year');
  if (!ysel.options.length) {""", """  const ysel = document.getElementById('cm-year');
  if (ysel && !ysel.options.length) {""")
    rep("""  ysel.value = cmYear;\n  const sel = document.getElementById('cm-band');""", """  if (ysel) ysel.value = cmYear;\n  const sel = document.getElementById('cm-band');""")
    rep("""  if (D.years.includes(q.get('cmy'))) cmYear = q.get('cmy');""", """  // the link's year (cmy) is no longer used: the section shows FULL_YEAR""")
    rep("""  if (key === 'commute') { p.set('cmy', cmYear); p.set('cmb', cmBand);""", """  if (key === 'commute') { p.set('cmb', cmBand);""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
