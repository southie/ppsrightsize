"""Building costs in their own table: the "Building costs avoided by closures" column moves out of the Scenario impact
by region table into a "Building costs by region" card right below it. Region rows (and the district) expand to their
schools: must-fix (deferred maintenance + seismic retrofit) and full modernization, Status Quo totals or the share a
scenario's closures avoid, the estimated operating cost of the closed buildings, and buildings closed; school rows
show each building, its status, 2021 FCI and size. School staffing (PPS formula) and assessor land value move to the
same table (card renamed "Building, staffing and land costs by region"). The must-fix, staffing and land value summary
cards link to the new table. Rows are alphabetical and keep their height across scenarios (stableLayout). Runs after
patch_stable_rows. Code added once.
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

if 'function renderBuildings' not in html:
    # ---- out of the region table ----
    rep("""<th>Building costs avoided by closures<br><span style="font-weight:400">(2026 $; must-fix = deferred maintenance + seismic retrofit; operating = estimated annual custodial, utilities and maintenance cost of closed buildings; school rows show each building)</span></th>""", "")
    rep("""`<td class="muted">${s0.fc ? `building of ${s0.fc.toLocaleString()} seats` : '&mdash;'}</td>` + costCell([n]) + staffCell([n])""",
        """`<td class="muted">${s0.fc ? `building of ${s0.fc.toLocaleString()} seats` : '&mdash;'}</td>` + staffCell([n])""")
    rep("""'<span class="muted">no data</span>'}</td>` + costCell([n]) + staffCell([n])""", """'<span class="muted">no data</span>'}</td>` + staffCell([n])""")
    rep("""    h += costCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));\n""", "")
    rep("function endpointCols() { return ['region', ...MEAS.map(m => m.key), 'util', 'cost', 'staff', 'land', 'change']; }",
        "function endpointCols() { return ['region', ...MEAS.map(m => m.key), 'util', 'staff', 'land', 'change']; }")
    # the must-fix card goes to the new table
    rep("""  if (target === 'classsize') {""", """  if (target === 'cost') {
    const t = document.getElementById('bldcosts'); if (!t) return;
    t.scrollIntoView({ behavior: 'smooth', block: 'start' }); flash([t]); return;
  }
  if (target === 'classsize') {""")
    rep("t === 'classsize' ? 'Show class sizes and teacher loads by grade' :", "t === 'classsize' ? 'Show class sizes and teacher loads by grade' : t === 'cost' ? 'Show building costs by region' :")
    # ---- the new card ----
    rep("""    <div class="tablewrap" id="endpoints"></div>
  </section>""", """    <div class="tablewrap" id="endpoints"></div>
  </section>

  <section class="card">
    <h2>Building costs by region</h2>
    <p class="sub">Capital needs of PPS's buildings (2026 dollars) from the 2021 Long-Range Facility Plan: <b>must-fix</b> = deferred maintenance + seismic retrofit; <b>modernize</b> = full modernization. Under Status Quo every building stays open; under a scenario, the costs of the buildings it closes are avoided (shown against the Status Quo total). Operating cost is the estimated annual custodial, utilities and maintenance cost of the closed buildings (square feet &times; PPS's rate). Click a region to see its buildings.</p>
    <div class="controls tabletools"><button id="bc-expand">Expand all regions</button></div>
    <div class="tablewrap" id="bldcosts"></div>
  </section>""")
    rep("function renderAll() {", r"""// ---------- building costs by region (D.costs, D.opex; moved out of the region table) ----------
const bcOpen = new Set();
function renderBuildings() {
  const host = document.getElementById('bldcosts'); if (!host) return;
  const isSQ = scen === 'SQ', C = D.costs || {}, det = D.detail[scen] || {};
  const keysOf = rn => Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn);
  const amt = (v, tot) => isSQ ? `<span class="main">${usdM(v)}</span>`
    : `<span class="main">${usdM(v)}</span><span class="muted" style="display:block;font-size:11px">of ${usdM(tot)} &middot; ${pctOf(-v, tot)}</span>`;
  let h = `<table class="bltable"><thead><tr><th>Region</th><th>Must-fix<br><span style="font-weight:400">${isSQ ? 'all buildings' : 'avoided by closures'} (deferred maintenance + seismic)</span></th>` +
    `<th>Full modernization<br><span style="font-weight:400">${isSQ ? 'all buildings' : 'avoided by closures'}</span></th><th>Operating cost<br><span style="font-weight:400">${isSQ ? 'all buildings, a year (est.)' : 'of closed buildings, a year (est.)'}</span></th>` +
    `<th>Buildings<br><span style="font-weight:400">${isSQ ? 'with cost data' : 'closed'}</span></th></tr></thead><tbody>`;
  for (const rn of [...D.region_order, 'District']) {
    const keys = keysOf(rn), a = avoidedCosts(keys), t = totalCosts(keys), o = closedOpex(keys), isReg = rn !== 'District', open = bcOpen.has(rn);
    const allOpex = keys.reduce((s, k) => s + opexOf(k), 0), withData = keys.filter(k => C[k] && (C[k].mf != null || C[k].mod != null)).length;
    h += `<tr class="${isReg ? '' : 'dist'}"><td>${isReg ? `<button class="xbtn bc-x" data-r="${esc(rn)}" aria-expanded="${open}"><span class="car">&#9656;</span><span>${esc(rn)}</span></button>` : esc(rn)}</td>` +
      `<td>${amt(isSQ ? t.mf : a.mf, t.mf)}</td><td>${amt(isSQ ? t.mod : a.mod, t.mod)}</td>` +
      `<td><span class="main">${usdM1(isSQ ? allOpex : o.usd)}</span>${isSQ ? '' : `<span class="muted" style="display:block;font-size:11px">${Math.round(o.sf).toLocaleString()} sq ft</span>`}</td>` +
      `<td><span class="main">${isSQ ? withData : a.n}</span>${isSQ ? '' : `<span class="muted" style="display:block;font-size:11px">of ${keys.length}</span>`}</td></tr>`;
    if (!isReg || !open) continue;
    for (const k of [...keys].sort(byStatusName)) {
      const c = C[k], closed = det[k]?.closed, sch = byKey[k];
      const tag = isSQ ? '' : `<span class="stag ${closed ? 'closes' : 'none'}">${closed ? 'Closes' : 'Open'}</span> `;
      const tip = c ? `Deferred maintenance ${c.dm == null ? 'n/a' : usdM(c.dm)} + seismic retrofit ${c.se == null ? 'n/a' : usdM(c.se)}${c.urm ? ` (URM part ${usdM(c.urm)})` : ''}` : '';
      const cell = v => v == null ? '<td class="muted">&mdash;</td>' : `<td title="${esc(tip)}"><span class="main" style="${closed || isSQ ? '' : 'color:var(--text-muted)'}">${usdM(v)}</span>${closed ? '<span class="ca" style="display:block">avoided</span>' : ''}</td>`;
      h += `<tr class="srow${closed ? ' closed' : ''}"><td><span class="nm">${esc(short(sch ? sch.name : k))}</span><span class="ty">${TYPE_LABEL[D.types.SQ[k]] || ''}</span>` +
        `<span class="muted" style="display:block;font-size:11px">${tag}${c?.fci != null ? `2021 FCI ${c.fci}` : ''}${c?.sf ? `${c?.fci != null ? ' &middot; ' : ''}${c.sf.toLocaleString()} sq ft` : ''}</span></td>` +
        (c ? cell(c.mf) + cell(c.mod) : '<td class="muted">&mdash;</td><td class="muted">&mdash;</td>') +
        `<td>${c?.sf ? `<span class="main" style="${closed || isSQ ? '' : 'color:var(--text-muted)'}">${usdM1(opexOf(k))}</span>${closed ? '<span class="ca" style="display:block">saved</span>' : ''}` : '<span class="muted">&mdash;</span>'}</td><td></td></tr>`;
    }
  }
  host.innerHTML = h + '</tbody></table>';
  host.querySelectorAll('.bc-x').forEach(b => b.onclick = () => { const r = b.dataset.r; bcOpen.has(r) ? bcOpen.delete(r) : bcOpen.add(r); renderBuildings(); });
  const ex = document.getElementById('bc-expand');
  if (ex) { ex.textContent = bcOpen.size === D.region_order.length ? 'Collapse all regions' : 'Expand all regions';
    ex.onclick = () => { if (bcOpen.size === D.region_order.length) bcOpen.clear(); else D.region_order.forEach(r => bcOpen.add(r)); renderBuildings(); }; }
}
renderBuildings = stableLayout(renderBuildings, 'bldcosts');
function renderAll() {""")
    rep("renderEndpoints(); renderCommute();", "renderEndpoints(); renderBuildings(); renderCommute();")
    rep(".hstable { min-width: 640px; }", ".hstable { min-width: 640px; }\n.bltable { min-width: 620px; } .bltable td, .bltable th { text-align: right; } .bltable td:first-child, .bltable th:first-child { text-align: left; }")
if 'bl-staff' not in html:
    # ---- staffing and land value move to the same table ----
    rep("""<th>School staffing no longer needed<br><span style="font-weight:400">(PPS staffing formula; FTE and salary + benefits per year, 2026-27 $; year and class sizes set in Staffing impact)</span></th>""", "")
    rep("""<th>Land value (assessor)<br><span style="font-weight:400">(Multnomah County real market value, 2025 roll; land, and land + buildings)</span></th>""", "")
    assert html.count(" + staffCell([n]) + landCell([n])") == 2
    html = html.replace(" + staffCell([n]) + landCell([n])", "")
    rep("""    h += staffCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));
    h += landCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));\n""", "")
    rep("function endpointCols() { return ['region', ...MEAS.map(m => m.key), 'util', 'staff', 'land', 'change']; }",
        "function endpointCols() { return ['region', ...MEAS.map(m => m.key), 'util', 'change']; }")
    rep("  if (target === 'cost') {", "  if (target === 'cost' || target === 'staff' || target === 'land') {")
    rep("t === 'cost' ? 'Show building costs by region' :", "t === 'cost' || t === 'staff' || t === 'land' ? 'Show building, staffing and land costs by region' :")
    rep("<h2>Building costs by region</h2>", "<h2>Building, staffing and land costs by region</h2>")
    rep("""Click a region to see its buildings.</p>""",
        """<b>Staffing</b> is school positions under PPS's staffing formula (licensed-equivalent FTE and salary + benefits, 2026-27 dollars; the year and class sizes are set in Staffing impact): Status Quo totals, or the change under a scenario. <b>Land value</b> is the Multnomah County assessor's real market value (2025 roll): all sites under Status Quo, or the sites a scenario closes. Click a region to see its schools.</p>""")
    rep("""`<th>Buildings<br><span style="font-weight:400">${isSQ ? 'with cost data' : 'closed'}</span></th></tr></thead><tbody>`;""",
        """`<th>Buildings<br><span style="font-weight:400">${isSQ ? 'with cost data' : 'closed'}</span></th>` +
    `<th class="bl-staff">School staffing<br><span style="font-weight:400">${isSQ ? 'positions and cost a year' : 'positions no longer needed'} (${staffYear})</span></th>` +
    `<th>Land value (assessor)<br><span style="font-weight:400">${isSQ ? 'all sites' : 'sites closed'}; land, and land + buildings</span></th></tr></thead><tbody>`;""")
    rep("""      `<td><span class="main">${isSQ ? withData : a.n}</span>${isSQ ? '' : `<span class="muted" style="display:block;font-size:11px">of ${keys.length}</span>`}</td></tr>`;""",
        """      `<td><span class="main">${isSQ ? withData : a.n}</span>${isSQ ? '' : `<span class="muted" style="display:block;font-size:11px">of ${keys.length}</span>`}</td>` + staffCell(keys) + landCell(keys) + '</tr>';""")
    rep("""'<span class="muted">&mdash;</span>'}</td><td></td></tr>`;""", """'<span class="muted">&mdash;</span>'}</td><td></td>` + staffCell([k]) + landCell([k]) + '</tr>';""")
    rep("<h2>Scenario impact by region: enrollment, buildings, staffing and costs</h2>", "<h2>Scenario impact by region: enrollment and buildings</h2>")
    rep("The remaining columns are this analysis's estimates: building utilization, building costs (capital, plus the operating cost of closed buildings), school staffing under PPS's staffing formula, and assessor land value.",
        "Building utilization is this analysis's estimate; building costs, school staffing and land value are in the next table.")
    rep(".bltable { min-width: 620px; } .bltable td, .bltable th { text-align: right; }", ".bltable { min-width: 980px; } .bltable td, .bltable th { text-align: right; } .bltable td.cost { text-align: left; }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
