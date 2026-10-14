"""Enrollment uncertainty section: the school table is sorted by school name (it was most at risk first). The default
view still lists only the schools whose outcome is uncertain (5% to 95% chance below the threshold); "Show all
schools" lists every school. Code changed once.
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

if 'mc-sort-name' not in html:
    rep("""  rows.sort((a, b) => key(b) - key(a) || short(byKey[a.k]?.name || a.k).localeCompare(short(byKey[b.k]?.name || b.k)));""",
        """  rows.sort((a, b) => short(byKey[a.k]?.name || a.k).localeCompare(short(byKey[b.k]?.name || b.k)));   // mc-sort-name: by school name""")
    rep("""const show = mcAll ? rows : rows.filter(r => (r.p[sc] ?? 0) >= 0.05 && (r.p[sc] ?? 0) <= 0.95).slice(0, 25);""",
        """const show = mcAll ? rows : rows.filter(r => (r.p[sc] ?? 0) >= 0.05 && (r.p[sc] ?? 0) <= 0.95);""")
    rep("""'Schools whose outcome is uncertain (5% to 95% in the scenario being viewed), most at risk first.'""",
        """'Schools whose outcome is uncertain (5% to 95% in the scenario being viewed), by name.'""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
