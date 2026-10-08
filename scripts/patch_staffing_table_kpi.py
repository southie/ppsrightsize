"""Show staffing positions and dollars in the published-measures table (region, district and school rows) and as a KPI card."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function staffCell(' in html: sys.exit('already patched')
def rep(a, b, count=1):
    global html
    assert html.count(a) == count, (html.count(a), a[:100])
    html = html.replace(a, b)

# ---- cell + KPI helpers (live next to the other cost cells) ----
rep("function schoolRows(rn) {",
r"""// staffing (PPS school staffing formula, salary + benefits): uses the year and class sizes chosen in the Staffing section
function staffDelta(keys) {
  const yi = D.years.indexOf(staffYear), sq = staffAgg(keys, 'SQ', yi), cur = staffAgg(keys, scen, yi);
  const adminFTE = a => a.principal + a.ap + a.office;
  const adminUSD = a => (a.principal + a.ap) * SC.administrator + a.office * 2 * SC.classified;
  return { sq, cur, fte: cur.total - sq.total, usd: staffCost(cur) - staffCost(sq), aFte: adminFTE(cur) - adminFTE(sq), aUsd: adminUSD(cur) - adminUSD(sq),
           teach: (cur.homeroom + cur.t68 + cur.t912) - (sq.homeroom + sq.t68 + sq.t912) };
}
const sgn = (v, d = 1) => (Math.abs(v) < 0.05 ? '0' : (v > 0 ? '+' : '&minus;') + Math.abs(v).toFixed(d));
function staffCell(keys) {
  const s = staffDelta(keys);
  if (keys.length === 1) {
    const a = schoolFTE(keys[0], 'SQ', D.years.indexOf(staffYear)), b = schoolFTE(keys[0], scen, D.years.indexOf(staffYear));
    if (!a) return '<td class="cost muted">&mdash;</td>';
    if (scen === 'SQ') return `<td class="cost"><span class="rm">Positions</span>${a.total.toFixed(1)} FTE<br><span class="rm">Per year</span>${staffUSD(staffCost(a))}</td>`;
    if (Math.abs(s.fte) < 0.05) return '<td class="cost muted">no change</td>';
    return `<td class="cost">${b ? '' : '<span class="ca">closes</span><br>'}<span class="rm">Positions</span><b>${sgn(s.fte)}</b> FTE<br><span class="rm">Per year</span><b>${staffUSD(s.usd)}</b>` +
      (Math.abs(s.aFte) >= 0.05 ? `<br><span class="muted" style="font-size:11px">admin ${sgn(s.aFte)} FTE</span>` : '') + '</td>';
  }
  if (scen === 'SQ') return `<td class="cost"><span class="muted" style="font-size:11px">Status Quo, ${staffYear}</span><br><span class="rm">Positions</span><b>${s.sq.total.toFixed(0)}</b> FTE<br><span class="rm">Per year</span><b>${staffUSD(staffCost(s.sq))}</b></td>`;
  return `<td class="cost"><span class="rm">Positions</span><b>${sgn(s.fte)}</b> FTE <span class="muted">of ${s.sq.total.toFixed(0)}</span><br>` +
    `<span class="rm">Per year</span><b>${staffUSD(s.usd)}</b> <span class="muted">of ${staffUSD(staffCost(s.sq))}</span><br>` +
    `<span class="muted" style="font-size:11px">admin ${sgn(s.aFte)} FTE (${staffUSD(s.aUsd)}) &middot; teachers ${sgn(s.teach)} &middot; ${staffYear}</span></td>`;
}
function staffKPI() {
  const s = staffDelta(D.schools.map(x => x.key));
  if (scen === 'SQ') return `<div class="kpi"><div class="v">${staffUSD(staffCost(s.sq))}</div><div class="l">School staffing per year under PPS's formula, ${staffYear} (salary + benefits, 2026-27 $)</div>` +
    `<div class="s"><b>${s.sq.total.toFixed(0)}</b> formula FTE at these schools</div></div>`;
  const yi = D.years.indexOf(staffYear), d = c => (s.sq[c] - s.cur[c]);
  return `<div class="kpi"><div class="v">${staffUSD(-s.usd).replace('&minus;', '')}<span class="d" style="color:var(--text-muted)">per year</span></div>` +
    `<div class="l">School staffing no longer needed under PPS's formula, ${staffYear} vs Status Quo (salary + benefits, 2026-27 $)</div>` +
    `<div class="s"><b>${(-s.fte).toFixed(0)}</b> FTE: ${d('principal').toFixed(0)} principals, ${d('ap').toFixed(0)} asst/vice principals, ${d('office').toFixed(1)} office, ${d('homeroom').toFixed(0)} K-5 homerooms, ${(d('specialists') + d('support')).toFixed(1)} specialists &amp; support${Math.abs(d('t68') + d('t912')) >= 0.05 ? `, ${(d('t68') + d('t912')).toFixed(1)} 6-12 teachers` : ''} &middot; admin ${staffUSD(-s.aUsd).replace('&minus;', '')}</div></div>`;
}
function schoolRows(rn) {""")

# ---- KPI card ----
rep("  }).join('') + extraKPIs();", "  }).join('') + extraKPIs() + staffKPI();")

# ---- table header + cells ----
rep("<th>Building costs avoided by closures<br><span style=\"font-weight:400\">(2026 $; must-fix = deferred maintenance + seismic retrofit; school rows show each building)</span></th>",
    "<th>Building costs avoided by closures<br><span style=\"font-weight:400\">(2026 $; must-fix = deferred maintenance + seismic retrofit; school rows show each building)</span></th>"
    "<th>School staffing no longer needed<br><span style=\"font-weight:400\">(PPS staffing formula; FTE and salary + benefits per year, 2026-27 $; year and class sizes set in Staffing impact)</span></th>")
rep("    h += costCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));",
    "    h += costCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));\n"
    "    h += staffCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));")
rep("'<td class=\"reach muted\">&mdash;</td>' + costCell([n]) + landCell([n])", "'<td class=\"reach muted\">&mdash;</td>' + costCell([n]) + staffCell([n]) + landCell([n])")
rep("reachCell([n]) + costCell([n]) + landCell([n]) + '<td></td></tr>';", "reachCell([n]) + costCell([n]) + staffCell([n]) + landCell([n]) + '<td></td></tr>';")

# ---- staffing controls refresh the card and the table too ----
blk_a = html.index('// ---------- staffing estimate'); blk_b = html.index('function renderAll()')
blk = html[blk_a:blk_b]
n = blk.count('renderStaffing(); };') + blk.count('renderStaffing(); });')
blk = (blk.replace("staffYear = e.target.value; renderStaffing(); };", "staffYear = e.target.value; staffChanged(); };")
          .replace("caps = JSON.parse(JSON.stringify(capPreset === 'budget' ? SF.caps_budget : SF.caps_contract)); renderStaffing(); };",
                   "caps = JSON.parse(JSON.stringify(capPreset === 'budget' ? SF.caps_budget : SF.caps_contract)); staffChanged(); };")
          .replace("capPreset = 'custom'; renderStaffing();", "capPreset = 'custom'; staffChanged();"))
blk = blk.replace("function renderStaffing() {", "function staffChanged() { renderKPIs(); renderEndpoints(); renderStaffing(); }\nfunction renderStaffing() {")
assert blk.count('staffChanged();') == 3, blk.count('staffChanged();')
html = html[:blk_a] + blk + html[blk_b:]
open(PAGE, 'w', encoding='utf-8').write(html)
open(os.path.join(ROOT, 'scripts', 'staffing.js'), 'w', encoding='utf-8').write(blk)
print('patched')
