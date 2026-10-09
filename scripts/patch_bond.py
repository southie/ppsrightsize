"""Bond capital in the building, staffing and land costs table: a "Bond capital" column with dollars paid out of
dollars allocated, for the bond projects PPS's bond reports assign to one school (modernizations, design, a school's
own projects); region and district rows sum those, and the district row's hover lists the district-wide pools that
cannot be split by school. School rows also list the scheduled bond work (scope, status, completion date) from the bond
program schedule. Data: source/pps-bond/bond-projects.json (scripts/build_bond_projects.py). Runs after
patch_building_table. Data refreshed on rerun; code added once. (The school report's building costs panel shows the
same data; see scripts/school_report.js.)
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
B = json.load(open(os.path.join(ROOT, 'source', 'pps-bond', 'bond-projects.json'), encoding='utf-8'))
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['bond'] = {k: B[k] for k in ('source', 'as_of', 'schedule_as_of', 'financials_url', 'schedule_url', 'pools', 'totals')}
D['bond']['schools'] = {k: dict(dollars=[{f: d[f] for f in ('bond', 'project', 'budget', 'paid', 'encumbered')} for d in v.get('dollars', [])],
                                work=[{f: w[f] for f in ('scope', 'status', 'finish', 'construction')} for w in v.get('work', [])])
                        for k, v in B['schools'].items()}
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function bondCell' not in html:
    rep("function renderBuildings() {", r"""// ---------- bond capital (D.bond, PPS bond program reports; scripts/build_bond_projects.py) ----------
const bondUSD = v => Math.abs(v) >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : Math.abs(v) >= 1e7 ? `$${Math.round(v / 1e6)}M` : `$${(v / 1e6).toFixed(1)}M`;
const bondMon = d => { const [y, m] = d.split('-'); return `${'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ')[+m - 1]} ${y}`; };
// school-specific bond dollars (all four bonds) for a set of schools
function bondSum(keys) {
  const o = { budget: 0, paid: 0, n: 0, list: [] };
  for (const k of keys) for (const d of D.bond?.schools?.[k]?.dollars || []) { o.budget += d.budget; o.paid += d.paid; o.n++; o.list.push([k, d]); }
  return o;
}
// scheduled bond work at a school: scope, status, completion
function bondWork(k, html = true) {
  return (D.bond?.schools?.[k]?.work || []).map(w => {
    const when = w.status === 'complete' ? `complete ${bondMon(w.finish)}` : `${w.status}; ${w.construction ? `construction ${bondMon(w.construction[0])} to ${bondMon(w.construction[1])}, ` : ''}completes ${bondMon(w.finish)}`;
    return html ? `<span class="bw"><b>${esc(w.scope)}</b>: ${esc(when)}</span>` : `${w.scope}: ${when}`;
  });
}
function bondCell(keys, closedHere) {
  const s = bondSum(keys), work = keys.length === 1 ? bondWork(keys[0]) : [];
  const dist = keys.length > 1 && keys.length === Object.keys(D.region_of).length;
  const pools = dist ? Object.entries(D.bond?.pools || {}).flatMap(([b, ps]) => ps.filter(p => p.budget >= 1e6).map(p => `${b} ${p.project}: ${bondUSD(p.paid)} paid of ${bondUSD(p.budget)}`)) : [];
  const tip = [s.list.map(([k, d]) => `${keys.length > 1 ? short(byKey[k].name) + ', ' : ''}${d.bond} ${d.project}: ${bondUSD(d.paid)} paid of ${bondUSD(d.budget)}`).join('\n'),
    pools.length ? 'District-wide, not assignable to schools:\n' + pools.join('\n') : ''].filter(Boolean).join('\n\n');
  const nWork = keys.length > 1 ? keys.filter(k => (D.bond?.schools?.[k]?.work || []).some(w => w.status !== 'complete')).length : 0;
  if (!s.n && !work.length && !nWork) return '<td class="muted">&mdash;</td>';
  return `<td class="bondc"${tip ? ` title="${esc(tip)}"` : ''}>` +
    (s.n ? `<span class="main">${bondUSD(s.paid)}</span><span class="muted" style="display:block;font-size:11px">paid of ${bondUSD(s.budget)} allocated</span>` : '') +
    (nWork ? `<span class="muted" style="display:block;font-size:11px">${nWork} school${nWork === 1 ? '' : 's'} with bond work under way or planned</span>` : '') +
    (dist ? `<span class="muted" style="display:block;font-size:11px">plus district-wide pools (hover)</span>` : '') +
    (work.length ? `<span class="bwl">${work.join('')}</span>` : '') +
    (closedHere && work.length && (D.bond.schools[keys[0]].work || []).some(w => w.status !== 'complete') ? '<span class="ca" style="display:block">planned work at a closing school</span>' : '') + '</td>';
}
function renderBuildings() {""")
    rep("""    `<th>Buildings<br><span style="font-weight:400">${isSQ ? 'with cost data' : 'closed'}</span></th>` +""",
        """    `<th>Buildings<br><span style="font-weight:400">${isSQ ? 'with cost data' : 'closed'}</span></th>` +
    `<th>Bond capital<br><span style="font-weight:400">school-specific projects: paid of allocated, as of ${bondMon(D.bond.as_of)}; scheduled work</span></th>` +""")
    rep("""of ${keys.length}</span>`}</td>` + staffCell(keys) + landCell(keys) + '</tr>';""",
        """of ${keys.length}</span>`}</td>` + bondCell(keys) + staffCell(keys) + landCell(keys) + '</tr>';""")
    rep("""'<span class="muted">&mdash;</span>'}</td><td></td>` + staffCell([k]) + landCell([k]) + '</tr>';""",
        """'<span class="muted">&mdash;</span>'}</td><td></td>` + bondCell([k], closed) + staffCell([k]) + landCell([k]) + '</tr>';""")
    rep("""Click a region to see its schools.</p>""",
        """<b>Bond capital</b> is money from PPS's 2012, 2017, 2020 and 2025 bonds that PPS's bond reports assign to one school (mostly high school modernizations), paid out of allocated (<a href="${D.bond.financials_url}" target="_blank" rel="noopener">bond financials</a>); district-wide pools for roofs, seismic, accessibility, mechanical systems and technology are not reported by school (hover the district row). School rows list scheduled bond work from the <a href="${D.bond.schedule_url}" target="_blank" rel="noopener">bond schedule</a>. Click a region to see its schools.</p>""".replace('${D.bond.financials_url}', B['financials_url']).replace('${D.bond.schedule_url}', B['schedule_url']))
    rep(".bltable { min-width: 980px; }",
        ".bltable { min-width: 1120px; } .bltable td.bondc { text-align: left; max-width: 260px; } .bltable .bwl { display: block; margin-top: 3px; } .bltable .bw { display: block; font-size: 11px; line-height: 1.35; color: var(--text-secondary); white-space: normal; }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
