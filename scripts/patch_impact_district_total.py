"""Scenario impact by region table: the district row shows its total students in 2031-32 (the table's year) under the
name, with the change from Status Quo under a scenario. The total is this page's projection summed over the schools on
the page (D.series, all scenarios' enrollment model, including the modified enrollment model when it is on). Code
added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
a = """      : esc(rn)}</td>`;"""
b = """      : `${esc(rn)}${(() => {   // total students, 2031-32 (scripts/patch_impact_district_total.py)
        const yi = D.years.indexOf('2031-32'), tot = s => Object.keys(D.region_of).reduce((t, k) => t + (D.series[s]?.[k]?.[yi] || 0), 0);
        const c = tot(scen), q = tot('SQ'), d = Math.round(c - q);
        return `<span style="display:block;color:var(--text-muted);font-size:11.5px;font-weight:400" title="${esc(`Students in 2031-32 at the ${Object.keys(D.region_of).length} schools on this page, ${LABEL[scen]}${scen === 'SQ' ? '' : `; Status Quo ${Math.round(q).toLocaleString()}`}. Scenarios move students between schools, so the total matches Status Quo (to within rounding). Program schools not on this page are not counted.`)}">${Math.round(c).toLocaleString()} students (2031-32)${scen !== 'SQ' && Math.abs(d) >= 5 ? ` <span class="delta ${d > 0 ? 'up' : 'down'}" style="display:inline">${d > 0 ? '+' : '&minus;'}${Math.abs(d).toLocaleString()} vs SQ</span>` : ''}</span>`;
      })()}`}</td>`;"""
if 'patch_impact_district_total' not in html:
    assert html.count(a) == 1, html.count(a)
    html = html.replace(a, b)
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
