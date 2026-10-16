"""School reports show when a school closes: the first year, from the year the scenarios take effect, with no students in
that scenario (Sellwood and Marysville close in 2028-29, the other closures in 2027-28; custom scenarios by their own
enrollment). closeYear(k, sc).
  - Header tag "Closes in 2028-29"; the scenario's enrollment box shows the year's enrollment while the school is still
    open ("closed" only from its closing year); the "This school" box badge; the student-flow, building-cost and staff
    notes ("closes in Scenario A in 2028-29").
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

if 'function closeYear' not in html:
    rep("""function renderReport() {""", """// the year a school closes in a scenario: the first year from the scenarios' start with no students (scripts/patch_close_year.py)
function closeYear(k, sc) {
  const s = D.series[sc]?.[k]; if (!s) return null;
  for (let i = D.years.indexOf(D.impl_year); i < s.length; i++) if (s[i] == null) return D.years[i];
  return null;
}
const closeIn = (k, sc) => { const y = closeYear(k, sc); return y ? ` in ${y}` : ''; };
function renderReport() {""")
    rep("""  const tag = { closes: 'Closes', receives:""", """  const tag = { closes: `Closes${closeIn(k, sc)}`, receives:""")
    rep("""${d1.closed ? 'closed' : e1 == null ? '&mdash;' : Math.round(e1)}${d1.closed ? '' : rpMark(k, sc)}""",
        """${e1 == null ? (d1.closed ? 'closed' : '&mdash;') : Math.round(e1)}${e1 == null ? '' : rpMark(k, sc)}""")
    rep("""'<span class="rpbadge rem">closes</span>'""", """`<span class="rpbadge rem">closes${closeIn(k, sc)}</span>`""")
    rep("""${d1.closed ? `${nm} closes in ${esc(LABEL[base])}`""", """${d1.closed ? `${nm} closes in ${esc(LABEL[base])}${closeIn(k, sc)}`""")
    rep("""<span class="stag closes">closes in ${esc(LABEL[sc])}</span>""", """<span class="stag closes">closes in ${esc(LABEL[sc])}${closeIn(k, sc)}</span>""", 2)
    rep("""<b>${esc(LABEL[sc])}: ${esc(rpName(k))} closes.</b>""", """<b>${esc(LABEL[sc])}: ${esc(rpName(k))} closes${closeIn(k, sc)}.</b>""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
