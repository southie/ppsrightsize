"""Itemize an estimated annual operating cost (custodial, utilities, grounds, maintenance) for each closed building.
Shown as an expense attached to closed buildings, not as savings.

Rate: General Fund 'Operation and Maintenance of Plant Services' (function 2540), 2026-27 proposed $72,437,027
(PPS 2026-27 Proposed Budget, Vol. 1, p. 101) / ~9.0 million sq ft of district building area (budget p. 48; 2021 LRFP Vol. 1 p. 28).
"""
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function opexOf(' in html: sys.exit('already patched')

OM, SQFT = 72437027, 9_000_000
OPEX = dict(rate=round(OM / SQFT, 2), om_budget=OM, district_sqft=SQFT,
            source='PPS 2026-27 Proposed Budget Vol. 1: General Fund Operation and Maintenance of Plant (p. 101) / about 9 million sq ft of district buildings (p. 48)')
i = html.index('const D = ') + len('const D = ')
D, end = json.JSONDecoder().raw_decode(html[i:])
D['opex'] = OPEX
html = html[:i] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[i + end:]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# helpers
rep("const pctOf = (d, base) =>",
"""// estimated annual operating cost of a building (custodial, utilities, grounds, maintenance), 2026-27 $
const opexOf = k => (D.costs?.[k]?.sf || 0) * D.opex.rate;
const usdM1 = v => '$' + (v / 1e6).toFixed(1) + 'M';
function closedOpex(keys) { const det = D.detail[scen] || {}; const c = keys.filter(k => det[k]?.closed && D.costs?.[k]?.sf); return { n: c.length, usd: c.reduce((a, k) => a + opexOf(k), 0), sf: c.reduce((a, k) => a + D.costs[k].sf, 0) }; }
const pctOf = (d, base) =>""")

# school rows: closed building carries its operating cost line
rep("""    return `<td class="cost" title="${esc(tip)}">${closed ? '<span class="ca">avoided</span><br>' : ''}<span class="rm">Must-fix</span>${c.mf == null ? '&mdash;' : usdM(c.mf)}<br><span class="rm">Modernize</span>${c.mod == null ? '&mdash;' : usdM(c.mod)}</td>`;""",
"""    return `<td class="cost" title="${esc(tip)}">${closed ? '<span class="ca">avoided</span><br>' : ''}<span class="rm">Must-fix</span>${c.mf == null ? '&mdash;' : usdM(c.mf)}<br><span class="rm">Modernize</span>${c.mod == null ? '&mdash;' : usdM(c.mod)}` +
      (closed && c.sf ? `<br><span class="rm">Operating</span>${usdM1(opexOf(keys[0]))}/yr <span class="muted" style="font-size:11px">est.</span>` : '') + '</td>';""")
# region / district rows: operating cost of the closed buildings
rep("""  return `<td class="cost">${line('Must-fix', a.mf, t.mf)}<br>${line('Modernize', a.mod, t.mod)}<br><span class="muted" style="font-size:11px">${a.n ? `${a.n} building${a.n === 1 ? '' : 's'} closed` : 'none closed'}; totals are Status Quo</span></td>`;""",
"""  const o = closedOpex(keys);
  return `<td class="cost">${line('Must-fix', a.mf, t.mf)}<br>${line('Modernize', a.mod, t.mod)}` +
    (o.n ? `<br><span class="rm">Operating</span>${usdM1(o.usd)}/yr <span class="muted" style="font-size:11px">est., closed buildings</span>` : '') +
    `<br><span class="muted" style="font-size:11px">${a.n ? `${a.n} building${a.n === 1 ? '' : 's'} closed` : 'none closed'}; totals are Status Quo</span></td>`;""")
# column header note
rep("(2026 $; must-fix = deferred maintenance + seismic retrofit; school rows show each building)</span></th>",
    "(2026 $; must-fix = deferred maintenance + seismic retrofit; operating = estimated annual custodial, utilities and maintenance cost of closed buildings; school rows show each building)</span></th>")
# building cost KPI card: itemized operating expense of the closed buildings
rep("""        `<div class="s">Full modernization avoided: <b>${usdM(a.mod)}</b> (${pctOf(-a.mod, t.mod)} of ${usdM(t.mod)})${a.n ? ` &middot; ${a.n} building${a.n === 1 ? '' : 's'}` : ''}</div></div>`)""",
"""        `<div class="s">Full modernization avoided: <b>${usdM(a.mod)}</b> (${pctOf(-a.mod, t.mod)} of ${usdM(t.mod)})${a.n ? ` &middot; ${a.n} building${a.n === 1 ? '' : 's'}` : ''}</div>` +
        ((o) => o.n ? `<div class="s">Operating cost of the closed buildings (est.): <b>${usdM1(o.usd)}</b> a year (${Math.round(o.sf).toLocaleString()} sq ft at $${D.opex.rate.toFixed(2)}/sq ft)</div>` : '')(closedOpex(D.schools.map(s => s.key))) + '</div>')""")
# method note
rep("  'Student-group rates below zero in the roster are CRDC suppression codes",
    "  'Building operating cost (estimate): PPS budgets $72.4M in 2026-27 for operation and maintenance of plant (custodial, utilities, grounds, maintenance and repair; General Fund, Proposed Budget Vol. 1 p. 101) across about 9 million sq ft of district buildings (p. 48), about $' + D.opex.rate.toFixed(2) + ' per sq ft per year. Closed buildings show that rate times their floor area as an annual expense attached to the building; it is an average, not a building-specific figure, and is not counted as savings.',\n"
    "  'Student-group rates below zero in the roster are CRDC suppression codes")
open(PAGE, 'w', encoding='utf-8').write(html)
print('patched; rate', OPEX['rate'])
