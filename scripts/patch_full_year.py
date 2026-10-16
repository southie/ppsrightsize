"""First full year for measurements: 2028-29, the first year every change is in effect (Sellwood and Marysville close in
2028-29, a year after the others). The scenarios still take effect in 2027-28 (D.impl_year) for enrollment.
  - FULL_YEAR constant.
  - Default staffing year (staffing, class-size and PAT cards, students-who-change-schools estimate) and General Fund
    chart year: 2028-29 (both can still be set to any year).
  - Yellow-bus cost card: measured in 2028-29 ("first full year").
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

if 'FULL_YEAR' not in html:
    rep("const SCENS = ['SQ', 'A', 'B'];", "const SCENS = ['SQ', 'A', 'B'];\nconst FULL_YEAR = '2028-29';   // first year every change is in effect (Sellwood and Marysville close in 2028-29); patch_full_year")
    rep("let staffYear = D.impl_year", "let staffYear = FULL_YEAR")
    rep("let gfYear = D.impl_year", "let gfYear = FULL_YEAR")
    rep("cmAtYear(D.impl_year, busScen)", "cmAtYear(FULL_YEAR, busScen)")
    rep("cmAtYear(D.impl_year, () => cmAgg(", "cmAtYear(FULL_YEAR, () => cmAgg(", 2)
    rep("cmYear !== D.impl_year", "cmYear !== FULL_YEAR")
    rep("${D.impl_year}, the first year (est.;", "${FULL_YEAR}, the first full year (est.;")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
