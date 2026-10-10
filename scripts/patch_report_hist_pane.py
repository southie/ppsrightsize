"""The getting-to-school detail pane (cmPaneHtml) can show a row whose figures are already computed: a pane row may
carry c (this scenario) and q (Status Quo, or null), a scenario label, year and grade-band label, as the school
report's getting-to-school rows do (their closing-area rows are not a set of schools cmAgg can recompute). Rows from
the getting-to-school table are unchanged. Code changed once.
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

if 's.scLabel ||' not in html:
    rep("  const c = cmAgg(scen, s.keys, cmBand), isSQ = scen === 'SQ', q = isSQ ? null : cmAgg('SQ', s.keys, cmBand), m = s.m;",
        "  // a row may carry its own figures (school report): c, q (null = no comparison), scLabel, year, bandLabel\n"
        "  const c = s.c || cmAgg(scen, s.keys, cmBand), isSQ = s.c ? !s.q : scen === 'SQ', q = s.c ? s.q : isSQ ? null : cmAgg('SQ', s.keys, cmBand), m = s.m;\n"
        "  const scL = s.scLabel || LABEL[scen], yr = s.year || cmYear;")
    rep("""<div class="muted">${LABEL[scen]}${isSQ ? '' : ' vs Status Quo'} &middot; ${band} &middot; ${cmYear}</div>""",
        """<div class="muted">${scL}${isSQ ? '' : ' vs Status Quo'} &middot; ${s.bandLabel || band} &middot; ${yr}</div>""")
    rep("""<span class="sw" style="background:var(--text-secondary);opacity:.85"></span>${LABEL[scen]}, within 15 min""",
        """<span class="sw" style="background:var(--text-secondary);opacity:.85"></span>${scL}, within 15 min""")
    rep("""<th>${isSQ ? 'Status Quo' : LABEL[scen]}</th>""", """<th>${isSQ ? 'Status Quo' : scL}</th>""")
    rep("""Students are ${cmYear} enrollment (${cmYear === D.years[0] ? 'actual' : 'projected'})""",
        """Students are ${yr} enrollment (${yr === D.years[0] ? 'actual' : 'projected'})""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
