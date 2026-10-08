"""rightsizing-scenario-explorer.html: in the over-capacity list, highlight the years a school is over its
2021 functional capacity under the selected scenario but not under Status Quo. Safe to rerun: the code is
only added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function overYears' not in html:
    rep("#overlist table { min-width: 640px; }",
        "#overlist .newyr { font-weight: 600; background: color-mix(in srgb, var(--over) 38%, transparent); border-radius: 4px; padding: 0 4px; }\n"
        "#overlist table { min-width: 640px; }")
    rep("  const TL = { ES: 'K-5', K8: 'K-8', MS: '6-8', HS: '9-12' };",
"""  const TL = { ES: 'K-5', K8: 'K-8', MS: '6-8', HS: '9-12' };
  // years over capacity; under a scenario, years that are not over under Status Quo are highlighted
  function overYears(r) {
    const idx = r.yrs.map(y => Y.indexOf(y));
    if (scen === 'SQ') return r.yrs.length === Y.length ? 'every year' : esc(r.yrs.join(', '));
    const sq = D.series.SQ[r.n] || [], sqOver = i => sq[i] != null && sq[i] > r.c;
    const nNew = idx.filter(i => !sqOver(i)).length;
    if (!nNew && r.yrs.length === Y.length) return 'every year';
    return idx.map(i => sqOver(i) ? esc(Y[i]) : `<span class="newyr" title="Not over capacity under Status Quo">${esc(Y[i])}</span>`).join(', ') +
      (nNew ? ` <span class="muted">(${nNew} new vs Status Quo)</span>` : '');
  }""")
    rep("<th>Years over capacity</th></tr></thead><tbody>`",
        "<th>Years over capacity${scen === 'SQ' ? '' : ' <span style=\"font-weight:400\">(<span class=\"newyr\">highlighted</span> = not over in Status Quo)</span>'}</th></tr></thead><tbody>`")
    rep("<td>${r.yrs.length === Y.length ? 'every year' : esc(r.yrs.join(', '))}</td></tr>`",
        "<td>${overYears(r)}</td></tr>`")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
