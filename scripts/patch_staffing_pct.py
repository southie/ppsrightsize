"""Add % change vs Status Quo to the staffing column (measures table) and the staffing KPI card."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
a = html.index('function staffDelta(keys) {')
b = html.index('function schoolRows(rn) {')
NEW = r"""function staffDelta(keys) {
  const yi = D.years.indexOf(staffYear), sq = staffAgg(keys, 'SQ', yi), cur = staffAgg(keys, scen, yi);
  const adminFTE = a => a.principal + a.ap + a.office;
  const adminUSD = a => (a.principal + a.ap) * SC.administrator + a.office * 2 * SC.classified;
  const sqUsd = staffCost(sq), sqAF = adminFTE(sq), sqAU = adminUSD(sq);
  const r = { sq, cur, fte: cur.total - sq.total, usd: staffCost(cur) - sqUsd, aFte: adminFTE(cur) - sqAF, aUsd: adminUSD(cur) - sqAU,
              base: { fte: sq.total, usd: sqUsd, aFte: sqAF, aUsd: sqAU, tFte: sq.total - sqAF, tUsd: sqUsd - sqAU } };
  r.tFte = r.fte - r.aFte; r.tUsd = r.usd - r.aUsd;   // teachers and direct support = everything except administration
  return r;
}
const sgn = (v, d = 1) => (Math.abs(v) < 0.05 ? '0' : (v > 0 ? '+' : '&minus;') + Math.abs(v).toFixed(d));
const pcS = (d, base) => base ? ` <span class="pcs">(${pctOf(d, base)})</span>` : '';
function staffCell(keys) {
  const s = staffDelta(keys);
  if (keys.length === 1) {
    const a = schoolFTE(keys[0], 'SQ', D.years.indexOf(staffYear)), b = schoolFTE(keys[0], scen, D.years.indexOf(staffYear));
    if (!a) return '<td class="cost muted">&mdash;</td>';
    if (scen === 'SQ') return `<td class="cost"><span class="rm">Positions</span>${a.total.toFixed(1)} FTE<br><span class="rm">Per year</span>${staffUSD(staffCost(a))}</td>`;
    if (Math.abs(s.fte) < 0.05) return '<td class="cost muted">no change</td>';
    return `<td class="cost">${b ? '' : '<span class="ca">closes</span><br>'}<span class="rm">Positions</span><b>${sgn(s.fte)}</b> FTE${pcS(s.fte, s.base.fte)}<br>` +
      `<span class="rm">Per year</span><b>${staffUSD(s.usd)}</b>${pcS(s.usd, s.base.usd)}` +
      (Math.abs(s.aFte) >= 0.05 ? `<br><span class="muted" style="font-size:11px">admin ${sgn(s.aFte)} FTE${pcS(s.aFte, s.base.aFte)}</span>` : '') + '</td>';
  }
  if (scen === 'SQ') return `<td class="cost"><span class="muted" style="font-size:11px">Status Quo, ${staffYear}</span><br><span class="rm">Positions</span><b>${s.sq.total.toFixed(0)}</b> FTE<br><span class="rm">Per year</span><b>${staffUSD(staffCost(s.sq))}</b>` +
    `<br><span class="muted" style="font-size:11px">admin ${s.base.aFte.toFixed(1)} FTE (${Math.round(100 * s.base.aFte / s.base.fte)}%) &middot; teachers &amp; direct support ${s.base.tFte.toFixed(1)}</span></td>`;
  return `<td class="cost"><span class="rm">Positions</span><b>${sgn(s.fte)}</b> FTE${pcS(s.fte, s.base.fte)} <span class="muted">of ${s.sq.total.toFixed(0)}</span><br>` +
    `<span class="rm">Per year</span><b>${staffUSD(s.usd)}</b>${pcS(s.usd, s.base.usd)} <span class="muted">of ${staffUSD(s.base.usd)}</span><br>` +
    `<span class="muted" style="font-size:11px">admin ${sgn(s.aFte)} FTE${pcS(s.aFte, s.base.aFte)} &middot; teachers &amp; direct support ${sgn(s.tFte)}${pcS(s.tFte, s.base.tFte)} &middot; ${staffYear}</span></td>`;
}
function staffKPI() {
  const s = staffDelta(D.schools.map(x => x.key));
  // two-way split: administration (principals, assistant/vice principals, office) vs teachers and direct student support
  const pos = v => staffUSD(Math.abs(v)).replace('&minus;', '');
  if (scen === 'SQ') {
    const sh = v => `${Math.round(100 * v / s.base.fte)}% of positions`;
    return `<div class="kpi"><div class="v">${staffUSD(s.base.usd)}</div><div class="l">School staffing per year under PPS's formula, ${staffYear} (salary + benefits, 2026-27 $)</div>` +
      `<div class="s">Administration: <b>${s.base.aFte.toFixed(1)}</b> FTE &middot; <b>${pos(s.base.aUsd)}</b> <span class="pcs">(${sh(s.base.aFte)})</span><br>` +
      `Teachers &amp; direct support: <b>${s.base.tFte.toFixed(1)}</b> FTE &middot; <b>${pos(s.base.tUsd)}</b> <span class="pcs">(${sh(s.base.tFte)})</span></div></div>`;
  }
  const line = (label, fte, usd, bF, bU) => `${label}: <b>${Math.abs(fte).toFixed(1)}</b> FTE${pcS(fte, bF)} &middot; <b>${pos(usd)}</b>${pcS(usd, bU)}`;
  return `<div class="kpi"><div class="v">${pos(s.usd)}<span class="d" style="color:var(--text-muted)">${pctOf(s.usd, s.base.usd)} vs SQ</span></div>` +
    `<div class="l">School staffing no longer needed per year under PPS's formula, ${staffYear} vs Status Quo (salary + benefits, 2026-27 $): <b>${Math.abs(s.fte).toFixed(1)}</b> FTE${pcS(s.fte, s.base.fte)}</div>` +
    `<div class="s">${line('Administration', s.aFte, s.aUsd, s.base.aFte, s.base.aUsd)}<br>${line('Teachers &amp; direct support', s.tFte, s.tUsd, s.base.tFte, s.base.tUsd)}</div></div>`;
}
"""
html = html[:a] + NEW + html[b:]
css_a = 'ul.notes { color: var(--text-secondary); font-size: 13px; padding-left: 20px; }'
assert html.count(css_a) == 1
html = html.replace(css_a, css_a + '\n.pcs { color: var(--text-muted); font-weight: 400; white-space: nowrap; }')
open(PAGE, 'w', encoding='utf-8').write(html)
print('patched')
