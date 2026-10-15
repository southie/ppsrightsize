"""Enrollment uncertainty method note: how PSU's affordable-housing students fit its forecast. PSU adds them to the schools
serving each development (2026-27 forecast, section 4.1-4.2, step 3), then reconciles every school to a district total
from its population model (births, deaths, migration x capture x grade progression), which has no housing input, by
adjusting other schools' capture rates and grade progression ratios. Checked: PSU's school totals (this page's schools
plus ACCESS, Benson, MLC, da Vinci and charter/other programs) sum exactly to its district total every year 2025-26 to
2035-36 while the housing students grow from 234 to about 736. So they are moved within the district, not added to it;
which schools give them up is not published. Text added once.
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

if 'housing-redistributed' not in html:
    rep("""students PSU expects from new affordable housing (${D.mc.params.housing.join(', ')} students in ${D.mc.out_years.join(', ')}) are held fixed.""",
        """students PSU expects from new affordable housing (${D.mc.params.housing.join(', ')} students in ${D.mc.out_years.join(', ')}) are held fixed. <span class="housing-redistributed">These housing students are moved within the district, not added to it: PSU adds them to the schools serving each development, then reconciles every school to its district total (from births, deaths, migration, kindergarten capture and grade progression, with no housing input) by lowering other schools' capture rates and grade progression ratios. PSU's school forecasts sum exactly to its district total every year through 2035-36; which schools give the students up is not published (PSU enrollment forecast 2026-27, sections 4.1-4.2).</span>""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
