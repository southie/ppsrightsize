"""Assessor land values (Multnomah County real market value, 2025 roll) for each school site, added to
rightsizing-scenario-explorer.html: a table column and a summary card. Status Quo shows all sites; a scenario
shows the land value of the sites it closes, as a share of all sites. Values are not escalated (land, not
construction). Input: source/assessor/pps-school-land-2025.csv from scripts/fetch_land_values.py.
Safe to rerun: data is refreshed, page code is only added once.
"""
import csv, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
LAND = os.path.join(ROOT, 'source', 'assessor', 'pps-school-land-2025.csv')
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['land'] = {r['school_key']: {'land': int(r['rmv_land']), 'imp': int(r['rmv_improvements']), 'acres': float(r['acres']), 'lots': int(r['lots']), 'zone': r['zoning']}
             for r in csv.DictReader(open(LAND, encoding='utf-8')) if int(r['lots'])}
print(f"land values for {len(D['land'])} of {len(D['schools'])} schools; total land ${sum(v['land'] for v in D['land'].values())/1e6:,.0f}M")
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\/') + html[m.end(1):]

def rep(a, b, n=1):
    global html
    assert html.count(a) == n, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function landCell' not in html:
    rep("function costCell(keys) {",
"""// assessor land value (D.land, Multnomah County RMV, 2025 roll): school rows show the site; region and district
// rows show all sites under Status Quo and, under a scenario, the sites it closes as a share of all sites
function landSum(keys) {
  const L = D.land || {};
  return keys.reduce((a, k) => L[k] ? { land: a.land + L[k].land, tot: a.tot + L[k].land + L[k].imp, n: a.n + 1 } : a, { land: 0, tot: 0, n: 0 });
}
function closedLand(keys) { const det = D.detail[scen] || {}; return landSum(keys.filter(k => det[k]?.closed)); }
const shareOf = (v, t) => t ? `${Math.round(100 * v / t)}% of all sites` : '';
function landCell(keys) {
  if (keys.length === 1) {
    const l = (D.land || {})[keys[0]], closed = (D.detail[scen] || {})[keys[0]]?.closed;
    if (!l) return '<td class="cost muted" title="Not in the Multnomah County tax-lot data (West Sylvan is in Washington County)">&mdash;</td>';
    return `<td class="cost" title="${esc(`${l.lots} tax lot${l.lots === 1 ? '' : 's'}, ${l.acres} acres, zoned ${l.zone || 'n/a'}`)}">${closed ? '<span class="ca">closes</span><br>' : ''}` +
      `<span class="rm">Land</span>${usdM(l.land)}<br><span class="rm">+ buildings</span>${usdM(l.land + l.imp)}</td>`;
  }
  const all = landSum(keys);
  if (scen === 'SQ') return `<td class="cost"><span class="muted" style="font-size:11px">All sites</span><br><span class="rm">Land</span><b>${usdM(all.land)}</b><br><span class="rm">+ buildings</span><b>${usdM(all.tot)}</b></td>`;
  const c = closedLand(keys);
  if (!c.n) return `<td class="cost muted">no sites closed<br><span style="font-size:11px">all sites: land ${usdM(all.land)}</span></td>`;
  return `<td class="cost"><span class="rm">Land</span><b>${usdM(c.land)}</b> <span class="muted">${shareOf(c.land, all.land)}</span><br>` +
    `<span class="rm">+ buildings</span><b>${usdM(c.tot)}</b> <span class="muted">${shareOf(c.tot, all.tot)}</span><br><span class="muted" style="font-size:11px">${c.n} closed site${c.n === 1 ? '' : 's'}</span></td>`;
}
function landKPI() {
  const keys = D.schools.map(s => s.key), all = landSum(keys), c = closedLand(keys);
  return scen === 'SQ'
    ? `<div class="kpi"><div class="v">${usdM(all.land)}</div><div class="l">Assessor land value, all school sites (Multnomah County, 2025 roll)</div>` +
      `<div class="s">Land + buildings: <b>${usdM(all.tot)}</b></div></div>`
    : `<div class="kpi"><div class="v">${usdM(c.land)}<span class="d" style="color:var(--text-muted)">${Math.round(100 * c.land / (all.land || 1))}% of all sites</span></div>` +
      `<div class="l">Assessor land value of closed sites, of ${usdM(all.land)} for all school sites (2025 roll)</div>` +
      `<div class="s">Land + buildings: <b>${usdM(c.tot)}</b> (${Math.round(100 * c.tot / (all.tot || 1))}% of ${usdM(all.tot)})${c.n ? ` &middot; ${c.n} site${c.n === 1 ? '' : 's'}` : ''}</div></div>`;
}
function costCell(keys) {""")
    rep("<th>Students who would change schools</th>",
        "<th>Land value (assessor)<br><span style=\"font-weight:400\">(Multnomah County real market value, 2025 roll; land, and land + buildings)</span></th><th>Students who would change schools</th>")
    rep("    h += costCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));",
        "    h += costCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));\n"
        "    h += landCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));")
    rep("costCell([n]) + '<td></td></tr>'", "costCell([n]) + landCell([n]) + '<td></td></tr>'", n=2)
    rep("totalCosts(D.schools.map(s => s.key)));", "totalCosts(D.schools.map(s => s.key))) + landKPI();")
    rep("  'Private schools:",
        "  'Land value: Multnomah County assessor real market value (RMV) from the 2025 assessment roll, via the county public tax-lot service. A school site is every district-owned tax lot within 200 m of the school, each lot counted for its nearest school. School property is tax-exempt, so its assessed value is zero, but the assessor still records market value; values for exempt property may not be kept as current as taxable property, so treat them as a rough guide, not an appraisal. Land value is the better guide to what a buyer would pay; building value reflects the existing structure, which may add little. A sale would be one-time revenue and is not added to avoided building costs. West Sylvan is in Washington County and has no value here; Rosa Parks owns condominium units on a shared campus, so it shows building value but no land. Built by scripts/fetch_land_values.py and scripts/patch_land.py.',\n  'Private schools:")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
