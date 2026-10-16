"""Closures: net change in General Fund staffing per student moved (actual-budget estimate) follows the scenarios'
timeline, as the General Fund chart does (scripts/patch_gf_years.py).
  - Only schools closed by the chosen year count (Sellwood and Marysville from 2028-29); in 2027-28 a note lists the
    closures still to come.
  - With a year before the scenarios start (2026-27), the chart shows 2028-29, the first year every closure is in place.
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

if 'gfPending' not in html:
    rep("""ys = D.years.indexOf(gfYear) >= D.years.indexOf(D.impl_year) ? D.years.indexOf(gfYear) : D.years.indexOf(D.impl_year), yr = D.years[ys];""",
        """ys = D.years.indexOf(gfYear) >= D.years.indexOf(D.impl_year) ? D.years.indexOf(gfYear) : D.years.indexOf(FULL_YEAR), yr = D.years[ys];
  const gfPending = [];   // closures not yet in effect in the chosen year (patch_gfclose_years)""")
    rep("""    if (!D.detail[base]?.[k]?.closed) continue;
    const c = gfCloseNet(k, base, ys); if (c) out.push(c);""",
        """    if (!D.detail[base]?.[k]?.closed) continue;
    if (D.series[base]?.[k]?.[ys] != null) { gfPending.push(k); continue; }   // closes in a later year
    const c = gfCloseNet(k, base, ys); if (c) out.push(c);""")
    rep("""  sub.innerHTML = `${esc(LABEL[base])}, ${yr}${D.years.indexOf(gfYear) < D.years.indexOf(D.impl_year) ? ` (closures take effect in ${D.impl_year}, so that year is shown)` : ''}: """,
        """  sub.innerHTML = `${esc(LABEL[base])}, ${yr}${D.years.indexOf(gfYear) < D.years.indexOf(D.impl_year) ? ` (the scenarios are complete in ${FULL_YEAR}, so that year is shown)` : ''}${gfPending.length ? ` (${gfPending.map(k => esc(short(byKey[k]?.name || k))).join(' and ')} ${gfPending.length === 1 ? 'closes' : 'close'} in ${closeYear(gfPending[0], base) || FULL_YEAR}, so ${gfPending.length === 1 ? 'is' : 'are'} not counted in ${yr})` : ''}: """)
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
