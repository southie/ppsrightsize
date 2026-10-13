"""General Fund staffing cost per student by school against the sustainability threshold, above the threshold impact
chart: one bar per school (2026-27 budget: salaries and payroll costs of school-allocated staff paid from the General
Fund, estimated by its share of the school's FTE, D.staff_actual, over projected 2026-27 enrollment), grouped by school
type and sorted from furthest below to furthest above the target. Reference lines per group: the target (the General
Fund cost per student of a school at the threshold size, from a fit of that type's schools: cost per student = a + b /
enrollment, i.e. a fixed cost spread over the students plus a cost per student), the group average and the district
average (both enrollment-weighted). Schools closing in the scenario being viewed (or in A or B under Status Quo) are
outlined. Code added once.
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

if 'function renderGFPer' not in html:
    rep("""  <section class="card">
    <h2>The sustainability threshold impact on cost per student by school size</h2>""",
        """  <section class="card">
    <h2>General Fund cost per student by school, against the sustainability threshold</h2>
    <p class="sub" id="gfpersub"></p>
    <div class="controls"><label>Show <select id="gf-mode"><option value="pp">Per student</option><option value="sub">Net total subsidy</option></select></label><label>Enrollment year <select id="gf-year"></select></label></div>
    <div class="gfperwrap" id="gfper"></div>
    <h3 class="cshead" id="gfclosehead"><span id="gfcloseheadtxt">Closures: net change in General Fund staffing</span></h3>
    <p class="sub" id="gfclosesub"></p>
    <div class="controls"><label>Show <select id="gf-mode2"><option value="pp">Per student moved</option><option value="sub">Net total</option></select></label><label>Enrollment year <select id="gf-year2"></select></label></div>
    <div class="gfperwrap" id="gfclose"></div>
  </section>

  <section class="card">
    <h2>The sustainability threshold impact on cost per student by school size</h2>""")
    rep("function renderCostCurve() {", r"""// ---------- General Fund cost per student vs the sustainability threshold (scripts/patch_gf_per_student.py) ----------
// the year the lower bars estimate (2026-27 = the budget year itself), and what the bars measure
let gfYear = D.impl_year, gfMode = 'pp';
try { const v = localStorage.getItem('rsGfYear'); if (D.years.includes(v)) gfYear = v; gfMode = localStorage.getItem('rsGfMode') === 'sub' ? 'sub' : 'pp'; } catch (e) {}
const gfUsd = v => '$' + Math.round(v).toLocaleString();
const gfM = v => (v < 0 ? '&minus;' : '') + '$' + (Math.abs(v) / 1e6).toFixed(Math.abs(v) >= 1e7 ? 1 : 2) + 'M';
// a school's 2026-27 General Fund staffing (budget school report: school-allocated salaries and payroll costs, General
// Fund share by its share of the school's FTE)
function gfOf(k) {
  const SA = D.staff_actual, i = (SA?.years || []).indexOf('2026-27'), s = SA?.schools?.[k];
  if (!s?.salaries || i < 0 || s.salaries[i] == null || !s.alloc_fte?.[i]) return null;
  return (s.salaries[i] + (s.payroll?.[i] || 0)) * s.gf_fte[i] / s.alloc_fte[i];
}
function gfPerData() {
  const yi = D.years.indexOf('2026-27'); if (yi < 0) return null;
  const rows = [];
  for (const k of Object.keys(D.region_of)) {
    const t = D.types.SQ[k], e = D.series.SQ[k]?.[yi], gf = gfOf(k);
    if (gf == null || !e || !t) continue;
    const row = { k, t, e, gf, c: gf / e };
    // in the chosen year: the actual 2026-27 General Fund staffing scaled by the formula's change from Status Quo
    // 2026-27 to the scenario (or Status Quo) in that year, over the enrollment then
    if ((scen !== 'SQ' || gfYear !== '2026-27') && typeof schoolFTE === 'function') {
      const ys = D.years.indexOf(gfYear), sc = scen, cl = D.detail[sc === 'C' ? custom.base : sc]?.[k]?.closed || (sc === 'C' && !D.series.C?.[k]?.[ys]);
      if (cl) row.closed = true;
      else {
        const f0 = schoolFTE(k, 'SQ', yi), f1 = schoolFTE(k, sc, ys), e1 = D.series[sc]?.[k]?.[ys];
        if (f0 && f1 && e1) { row.gf1 = gf * staffCost(f1) / staffCost(f0); row.e1 = e1; row.c1 = row.gf1 / e1; }
      }
    }
    rows.push(row);
  }
  return rows;
}
function renderGFPer() {
  const host = document.getElementById('gfper'); if (!host) return;
  // the two charts share one year and one view; their two sets of controls stay in step
  for (const id of ['gf-year', 'gf-year2']) {
    const ysel = document.getElementById(id); if (!ysel) continue;
    if (!ysel.options.length) ysel.innerHTML = D.years.filter(y => y >= '2026-27').map(y => `<option value="${y}">${y}${y === '2026-27' ? ' (budget year)' : y === D.impl_year ? ' (scenarios take effect)' : ''}</option>`).join('');
    ysel.value = gfYear;
    ysel.onchange = () => { gfYear = ysel.value; try { localStorage.setItem('rsGfYear', gfYear); } catch (e) {} renderGFPer(); };
  }
  for (const id of ['gf-mode', 'gf-mode2']) {
    const msel = document.getElementById(id); if (!msel) continue;
    msel.value = gfMode;
    msel.onchange = () => { gfMode = msel.value; try { localStorage.setItem('rsGfMode', gfMode); } catch (e) {} renderGFPer(); };
  }
  const rows = gfPerData(); if (!rows?.length) { host.innerHTML = '<p class="muted">No budget data.</p>'; return; }
  const usd = gfUsd, SUB = gfMode === 'sub';
  const TYPES = [['ES', 'K-5'], ['K8', 'K-8'], ['MS', 'Middle (6-8)'], ['HS', 'High (9-12)']];
  const dist = rows.reduce((a, r) => a + r.gf, 0) / rows.reduce((a, r) => a + r.e, 0);
  const closesIn = k => (scen === 'SQ' ? ['A', 'B'] : [scen === 'C' ? custom.base : scen]).filter(s => D.detail[s]?.[k]?.closed);
  const groups = TYPES.map(([t, lab]) => {
    const g = rows.filter(r => r.t === t); if (!g.length) return null;
    const avg = g.reduce((a, r) => a + r.gf, 0) / g.reduce((a, r) => a + r.e, 0);
    // target: cost per student = a + b / enrollment, least squares over the type's schools, at the threshold size
    const thr = D.thresholds[t], n = g.length, xs = g.map(r => 1 / r.e), ys = g.map(r => r.c);
    const mx = xs.reduce((a, v) => a + v, 0) / n, my = ys.reduce((a, v) => a + v, 0) / n;
    const sxx = xs.reduce((a, v) => a + (v - mx) ** 2, 0), b = n > 2 && sxx > 0 ? xs.reduce((a, v, j) => a + (v - mx) * (ys[j] - my), 0) / sxx : 0;
    const fitOK = b > 0, a = my - b * mx, target = fitOK ? a + b / thr : avg;
    return { t, lab, g, avg, thr, target, a, b, fitOK };
  }).filter(Boolean);
  // what a bar measures, from zero = the current district-wide average: per student, or the school's total subsidy
  // (General Fund staffing above what its students would get at the district-average rate)
  const Z = dist;
  const v0 = r => SUB ? (r.c - Z) * r.e : r.c - Z, v1 = r => r.c1 == null ? null : SUB ? (r.c1 - Z) * r.e1 : r.c1 - Z;
  const fmt = v => SUB ? (v > 0 ? '+' : '') + gfM(v) : usd(v + Z), fmtTick = v => SUB ? (v > 0 ? '+' : v < 0 ? '&minus;' : '') + '$' + (Math.abs(v) / 1e6).toFixed(1) + 'M' : (v > 0 ? '+' : v < 0 ? '&minus;' : '') + '$' + Math.abs(v).toLocaleString();
  const SC = scen !== 'SQ' || gfYear !== '2026-27', W = 900, Lm = 210, R = 20, BH = SC ? 24 : 15, GH = 40, GAP = 14, T = 8, AX = 30;
  const vals = [0, ...groups.flatMap(G => [...G.g.flatMap(r => [v0(r), ...(v1(r) != null ? [v1(r)] : [])]), ...(SUB ? [] : [G.avg - Z, G.target - Z])])];
  const span = Math.max(...vals) - Math.min(...vals);
  const step = SUB ? (span > 6e6 ? 1e6 : span > 2.4e6 ? 5e5 : 2.5e5) : span > 6000 ? 1000 : 500;
  const xlo = Math.floor((Math.min(...vals) - span * 0.08) / step) * step, xhi = Math.ceil((Math.max(...vals) + span * 0.1) / step) * step;
  const x = v => Lm + (W - Lm - R) * (v - xlo) / (xhi - xlo);
  const H = T + groups.reduce((a, G) => a + GH + G.g.length * BH + GAP, 0) + AX;
  let s = '', y0 = T;
  const plotTop = T, plotBot = H - AX;
  for (let v = xlo; v <= xhi + 1e-9; v += step) s += `<line x1="${x(v)}" x2="${x(v)}" y1="${plotTop}" y2="${plotBot}" stroke="var(--line)"/>` +
    `<text x="${x(v)}" y="${plotBot + 14}" text-anchor="middle" font-size="10.5" fill="var(--text-muted)">${fmtTick(v)}</text>`;
  s += `<text x="${(Lm + W - R) / 2}" y="${plotBot + 27}" text-anchor="middle" font-size="10.5" fill="var(--text-muted)">${SUB ? `General Fund staffing above (right) or below (left) what the school's students would get at the district average (${usd(Z)} per student), a year` : `General Fund staffing per student above (right) or below (left) the district average (${usd(Z)})`}</text>`;
  for (const G of groups) {
    G.g.sort((p, q) => SUB ? v0(q) - v0(p) : q.c - p.c);
    const top = y0 + GH, bot = top + G.g.length * BH;
    const gSub = G.g.reduce((a, r) => a + v0(r), 0);
    s += `<rect x="0" y="${y0 + 2}" width="${W}" height="${GH - 6}" fill="var(--surface-2, rgba(0,0,0,.035))"/>` +
      `<text x="8" y="${y0 + 18}" font-size="13" font-weight="700" fill="var(--text-primary)">${G.lab} (${G.g.length} schools)</text>` +
      (SUB ? `<text x="8" y="${y0 + 32}" font-size="10.5" fill="var(--text-muted)">together ${gSub >= 0 ? gfM(gSub) + ' above' : gfM(-gSub) + ' below'} the district-average rate, 2026-27</text>`
        : `<text x="8" y="${y0 + 32}" font-size="10.5"><tspan fill="var(--change)" font-weight="700">target ${usd(G.target)}</tspan><tspan fill="var(--text-muted)"> per student at the ${G.thr}-student threshold &middot; group average ${usd(G.avg)}</tspan></text>`);
    G.g.forEach((r, j) => {
      const yy = top + j * BH, cl = closesIn(r.k), d = r.c - G.target, val = v0(r), nm = short(byKey[r.k]?.name || r.k);
      const left = Math.min(x(val), x(0)), w = Math.max(0.5, Math.abs(x(val) - x(0))), bh = SC ? 10 : BH - 4;
      const col = SUB ? (val > 0 ? 'var(--down)' : 'var(--up)') : (d <= 0 ? 'var(--up)' : 'var(--down)');
      s += `<text x="${Lm - 8}" y="${yy + BH / 2 + 3.5}" text-anchor="end" font-size="11" fill="${cl.length ? 'var(--text-primary)' : 'var(--text-secondary)'}" font-weight="${cl.length ? 700 : 400}">${esc(nm)}${cl.length ? ' &#9679;' : ''}</text>` +
        `<rect x="${left}" y="${yy + 2}" width="${w}" height="${bh}" fill="${col}" opacity=".82" stroke="${cl.length ? 'var(--text-primary)' : 'none'}" stroke-width="${cl.length ? 1.6 : 0}">` +
        `<title>${esc(`${nm}: ${usd(r.c)} per student (${usd(r.gf)} General Fund staffing, ${Math.round(r.e)} students, 2026-27); ${r.c >= Z ? usd(r.c - Z) + ' above' : usd(Z - r.c) + ' below'} the district average per student, ${(r.c - Z) * r.e >= 0 ? gfM((r.c - Z) * r.e).replace('&minus;', '-') + ' a year above' : gfM((Z - r.c) * r.e).replace('&minus;', '-') + ' a year below'} the district-average rate in total; ${d <= 0 ? usd(-d) + ' below' : usd(d) + ' above'} the ${G.lab} target (${usd(G.target)} at the ${G.thr}-student threshold)${cl.length ? `; closes in ${cl.map(z => LABEL[z]).join(' and ')}` : ''}`)}</title></rect>` +
        `<text x="${val > 0 ? x(val) + 4 : x(val) - 4}" y="${yy + 2 + bh / 2 + 3.5}" text-anchor="${val > 0 ? 'start' : 'end'}" font-size="9.5" fill="var(--text-muted)">${fmt(val)}</text>`;
      if (SC) {   // in the chosen year (after the scenario), under the current bar
        const y2 = yy + 2 + bh + 1;
        if (r.closed) s += `<text x="${x(0) + 4}" y="${y2 + 8}" font-size="9.5" font-style="italic" fill="var(--text-muted)">closes in ${esc(LABEL[scen])}</text>`;
        else if (r.c1 != null) {
          const val1 = v1(r), d1 = r.c1 - G.target, l1 = Math.min(x(val1), x(0)), w1 = Math.max(0.5, Math.abs(x(val1) - x(0)));
          const col1 = SUB ? (val1 > 0 ? 'var(--down)' : 'var(--up)') : (d1 <= 0 ? 'var(--up)' : 'var(--down)');
          s += `<rect x="${l1}" y="${y2}" width="${w1}" height="8" fill="${col1}" opacity=".38" stroke="${col1}" stroke-width="1">` +
            `<title>${esc(`${nm}, ${LABEL[scen]} ${gfYear} (est.): ${usd(r.c1)} per student (${usd(r.gf1)} General Fund staffing, ${Math.round(r.e1)} students); ${(r.c1 - Z) * r.e1 >= 0 ? gfM((r.c1 - Z) * r.e1) + ' a year above' : gfM((Z - r.c1) * r.e1) + ' a year below'} the district-average rate; ${r.c1 < r.c ? usd(r.c - r.c1) + ' less' : usd(r.c1 - r.c) + ' more'} per student than in 2026-27`.replace(/&minus;/g, '-'))}</title></rect>` +
            `<text x="${val1 > 0 ? x(val1) + 4 : x(val1) - 4}" y="${y2 + 7.5}" text-anchor="${val1 > 0 ? 'start' : 'end'}" font-size="9" fill="var(--text-muted)">${fmt(val1)}</text>`;
        }
      }
    });
    // reference lines down the group: district average (0); per student also the target and the group average
    s += `<line x1="${x(0)}" x2="${x(0)}" y1="${top - 2}" y2="${bot + 2}" stroke="#6d28d9" stroke-width="2.4"><title>${esc(`District average: ${usd(Z)} General Fund staffing per student (2026-27, enrollment-weighted, all ${rows.length} schools)`)}</title></line>`;
    if (!SUB) s += `<line x1="${x(G.target - Z)}" x2="${x(G.target - Z)}" y1="${top - 2}" y2="${bot + 2}" stroke="var(--change)" stroke-width="2.4"><title>${esc(`${G.lab} target: ${usd(G.target)} per student, the General Fund cost per student of a school at the ${G.thr}-student threshold${G.fitOK ? ` (fit to ${G.lab} schools: ${usd(G.a)} + ${usd(G.b)} / enrollment)` : ' (no size trend in the data: group average used)'}`)}</title></line>` +
      `<line x1="${x(G.avg - Z)}" x2="${x(G.avg - Z)}" y1="${top - 2}" y2="${bot + 2}" stroke="var(--text-primary)" stroke-width="1.6" stroke-dasharray="6 4"><title>${esc(`${G.lab} average: ${usd(G.avg)} per student (enrollment-weighted), ${G.avg >= G.target ? usd(G.avg - G.target) + ' above' : usd(G.target - G.avg) + ' below'} the target`)}</title></line>`;
    y0 = bot + GAP;
  }
  host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px;height:auto" role="img" aria-label="General Fund staffing by school against the district average, grouped by school type">${s}</svg>` +
    `<div class="rplegend" style="margin-top:2px"><span><i class="k" style="border-top:2.5px solid #6d28d9;width:18px"></i>0 = district average (${usd(Z)} per student)</span>` +
    (SUB ? '' : `<span><i class="k" style="border-top:2.5px solid var(--change);width:18px"></i>target: a school at the threshold size</span><span><i class="k" style="border-top:2px dashed var(--text-primary);width:18px"></i>group average</span>`) +
    `<span>&#9679; bold name, outlined bar: closes</span>${SC ? `<span><i class="k" style="height:8px;width:14px;border:1px solid var(--down);background:color-mix(in srgb, var(--down) 38%, transparent);vertical-align:-1px"></i>lower bar: ${esc(LABEL[scen])}, ${gfYear} (est.)</span>` : ''}</div>`;
  const over = groups.reduce((a, G) => a + G.g.filter(r => r.c > G.target).length, 0);
  document.getElementById('gfpersub').innerHTML = (SUB
    ? `<b>Net total subsidy</b>: each bar is how many General Fund staffing dollars a year a school gets above (right) or below (left) what its students would get at the <b style="color:#6d28d9">current district-wide average</b> (${usd(dist)} per student, the zero line): its cost per student less the average, times its enrollment. <span style="color:var(--down);font-weight:600">Red</span>: above the average rate (subsidized by the rest of the district); <span style="color:var(--up);font-weight:600">green</span>: below it. Schools run from most subsidized to least. `
    : `Each bar is a school's 2026-27 General Fund staffing cost per student above (right) or below (left) the <b style="color:#6d28d9">current district-wide average</b> (the zero line, ${usd(dist)}, enrollment-weighted across all schools); bars are red where the school is above its group's target and green at or below it (${over} of ${rows.length} above), and schools run from most above the target to least. ` +
      `<b style="color:var(--change)">Target</b> (solid blue; value in each group's heading): the General Fund cost per student of a school at the sustainability threshold size for its type, from a fit of that type's schools (a fixed cost spread over the students plus a cost per student). <b>Group average</b> (dashed) is enrollment-weighted. `) +
    `The cost: the salaries and payroll costs of each school's school-allocated staff paid from the General Fund (estimated by the General Fund's share of the school's positions; PPS 2026-27 Proposed Budget, Volume 2, school reports), over projected 2026-27 enrollment. Outlined bars and bold names: schools closing in ${scen === 'SQ' ? 'Scenario A or B' : esc(LABEL[scen === 'C' ? custom.base : scen])}. ` +
    (SC ? `Under each school, the lighter bar estimates the same measure ${scen === 'SQ' ? 'under Status Quo' : `after ${esc(LABEL[scen])}`} in ${gfYear}: its 2026-27 General Fund staffing scaled by how much PPS's staffing formula changes for it between Status Quo 2026-27 and ${scen === 'SQ' ? 'Status Quo' : 'the scenario'} in that year, over its projected enrollment then${scen === 'SQ' ? '' : '; schools that close have none'}. ` : 'Pick a later year or a scenario to add bars estimating each school then. ') +
    'Hover a bar or line for its figures. Centrally allocated staff (special education, ESL, custodial, nutrition) and non-staff costs are not included.';
  renderGFClose(rows);
}
// closures in the scenario: the General Fund staffing saved at each closed school against the staff its receiving schools
// add for its students, in the chosen year
function renderGFClose(rows) {
  const host = document.getElementById('gfclose'), sub = document.getElementById('gfclosesub'); if (!host) return;
  const base = scen === 'C' ? custom.base : scen;
  if (base === 'SQ') { host.innerHTML = ''; sub.innerHTML = 'Pick Scenario A or B (or a custom scenario) at the top to see the net effect of each closure.'; return; }
  const y0 = D.years.indexOf('2026-27'), ys = D.years.indexOf(gfYear) >= D.years.indexOf(D.impl_year) ? D.years.indexOf(gfYear) : D.years.indexOf(D.impl_year), yr = D.years[ys];
  const by = Object.fromEntries((rows || []).map(r => [r.k, r]));
  const ratio = k => { const g = gfOf(k), f = schoolFTE(k, 'SQ', y0); return g != null && f ? g / staffCost(f) : 1; };   // actual General Fund over formula, 2026-27
  const out = [];
  for (const k of Object.keys(D.region_of)) {
    if (!D.detail[base]?.[k]?.closed) continue;
    const fk0 = schoolFTE(k, 'SQ', y0), fk = schoolFTE(k, 'SQ', ys), g = gfOf(k); if (!fk || !fk0 || g == null) continue;
    const saved = g * staffCost(fk) / staffCost(fk0), n = D.series.SQ[k][ys] || 0;
    let added = 0; const to = [];
    for (const { to: t, w } of reopenWeights(k, base, ys)) {
      const ser = (D.series[base] || {})[t]; if (!ser || ser[ys] == null || !w) continue;
      const sent = w * n, withS = schoolFTE(t, base, ys), keep = ser[ys]; ser[ys] = Math.max(0, keep - sent);
      let without; try { without = schoolFTE(t, base, ys); } finally { ser[ys] = keep; }
      const a = (staffCost(withS) - (without ? staffCost(without) : 0)) * ratio(t);
      added += a; to.push([t, Math.round(sent), a]);
    }
    out.push({ k, saved, added, net: added - saved, n, to });
  }
  if (!out.length) { host.innerHTML = '<p class="muted">No closures with budget data in this scenario.</p>'; sub.innerHTML = ''; return; }
  // per student moved, or totals a year (the view chosen above)
  const PS = gfMode !== 'sub';
  const hd = document.getElementById('gfcloseheadtxt');
  if (hd) hd.textContent = PS ? 'Closures: net change in General Fund staffing per student moved' : 'Closures: net change in General Fund staffing, total a year';
  const S = r => PS ? 1 / Math.max(1, r.n) : 1;
  const money = v => PS ? (v < 0 ? '&minus;' : '') + gfUsd(Math.abs(v)) : gfM(v);
  out.forEach(r => { r.vs = r.saved * S(r); r.va = r.added * S(r); r.vn = r.net * S(r); });
  out.sort((a, b) => a.vn - b.vn);
  const tot = out.reduce((a, r) => ({ saved: a.saved + r.saved, added: a.added + r.added, net: a.net + r.net, n: a.n + r.n }), { saved: 0, added: 0, net: 0, n: 0 });
  const W = 900, Lm = 210, R = 20, BH = 30, T = 6, AX = 30, TOT = 40;
  const lo = Math.min(-Math.max(...out.map(r => r.vs)), ...out.map(r => r.vn)), hi = Math.max(...out.map(r => r.va), ...out.map(r => r.vn), 0);
  const span = hi - lo, step = PS ? (span > 24000 ? 5000 : span > 10000 ? 2000 : 1000) : span > 6e6 ? 1e6 : span > 2.4e6 ? 5e5 : 2.5e5;
  const xlo = Math.floor((lo - span * 0.12) / step) * step, xhi = Math.ceil((hi + span * 0.12) / step) * step;
  const x = v => Lm + (W - Lm - R) * (v - xlo) / (xhi - xlo);
  const H = T + out.length * BH + TOT + AX;
  let s = '';
  for (let v = xlo; v <= xhi + 1e-9; v += step) s += `<line x1="${x(v)}" x2="${x(v)}" y1="${T}" y2="${H - AX}" stroke="var(--line)"/><text x="${x(v)}" y="${H - AX + 14}" text-anchor="middle" font-size="10.5" fill="var(--text-muted)">${v > 0 ? '+' : v < 0 ? '&minus;' : ''}$${PS ? Math.abs(v).toLocaleString() : (Math.abs(v) / 1e6).toFixed(1) + 'M'}</text>`;
  s += `<text x="${(Lm + W - R) / 2}" y="${H - 3}" text-anchor="middle" font-size="10.5" fill="var(--text-muted)">General Fund staffing ${PS ? 'per student moved' : 'in total'}, a year, ${yr}: saved (left) and added at receiving schools (right)</text>`;
  const row = (r, yy, bold) => {
    const nm = r.k ? short(byKey[r.k]?.name || r.k) : 'All closures';
    let g = `<text x="${Lm - 8}" y="${yy + 12}" text-anchor="end" font-size="11.5" font-weight="${bold ? 700 : 600}" fill="var(--text-primary)">${esc(nm)}</text>` +
      `<text x="${Lm - 8}" y="${yy + 24}" text-anchor="end" font-size="9.5" fill="var(--text-muted)">${Math.round(r.n).toLocaleString()} students &middot; ${PS ? `net ${gfM(r.net)} in total` : `net ${(r.net < 0 ? '&minus;' : '') + gfUsd(Math.abs(r.net) / Math.max(1, r.n))} each`}</text>`;
    const tip = r.k ? `${nm} closes (${LABEL[base]}, ${yr}): ${gfM(r.saved).replace('&minus;', '-')} of General Fund staffing saved; ${gfM(r.added).replace('&minus;', '-')} added at ${r.to.map(([t, n_, a]) => `${short(byKey[t]?.name || t)} (${n_} students, ${gfM(a).replace('&minus;', '-')})`).join(', ')}; net ${r.net < 0 ? gfM(-r.net).replace('&minus;', '-') + ' a year saved' : gfM(r.net).replace('&minus;', '-') + ' a year more'}` : `All ${out.length} closures: net ${r.net < 0 ? gfM(-r.net) + ' a year saved' : gfM(r.net) + ' a year more'}`;
    g += `<rect x="${x(-r.vs)}" y="${yy + 3}" width="${Math.max(0.5, x(0) - x(-r.vs))}" height="8" fill="var(--up)" opacity=".8"><title>${esc(tip)}</title></rect>` +
      `<rect x="${x(0)}" y="${yy + 3}" width="${Math.max(0.5, x(r.va) - x(0))}" height="8" fill="var(--down)" opacity=".7"><title>${esc(tip)}</title></rect>` +
      `<rect x="${Math.min(x(r.vn), x(0))}" y="${yy + 14}" width="${Math.max(1, Math.abs(x(r.vn) - x(0)))}" height="9" fill="var(--text-primary)" opacity=".85"><title>${esc(tip)}</title></rect>` +
      `<text x="${x(-r.vs) - 4}" y="${yy + 10.5}" text-anchor="end" font-size="9" fill="var(--text-muted)">${money(-r.vs)}</text>` +
      `<text x="${x(r.va) + 4}" y="${yy + 10.5}" font-size="9" fill="var(--text-muted)">+${money(r.va)}</text>` +
      `<text x="${r.vn < 0 ? x(r.vn) - 4 : x(r.vn) + 4}" y="${yy + 21.5}" text-anchor="${r.vn < 0 ? 'end' : 'start'}" font-size="9.5" font-weight="700" fill="var(--text-primary)">net ${r.vn > 0 ? '+' : ''}${money(r.vn)}${PS ? ' per student moved' : ' a year'}</text>`;
    return g;
  };
  out.forEach((r, j) => { s += row(r, T + j * BH); });
  const ty = T + out.length * BH + 6;
  // the total is far larger than any one closure, so it is written out rather than drawn on the same scale
  s += `<line x1="8" x2="${W - R}" y1="${ty - 3}" y2="${ty - 3}" stroke="var(--text-muted)"/>` +
    `<text x="${Lm - 8}" y="${ty + 14}" text-anchor="end" font-size="11.5" font-weight="700" fill="var(--text-primary)">All ${out.length} closures</text>` +
    `<text x="${Lm + 4}" y="${ty + 14}" font-size="11.5" fill="var(--text-primary)"><tspan fill="var(--up)" font-weight="700">${gfM(-tot.saved)} saved</tspan>, <tspan fill="var(--down)" font-weight="700">+${gfM(tot.added)} added</tspan>, <tspan font-weight="700">net ${tot.net > 0 ? '+' : ''}${gfM(tot.net)} a year</tspan> (${Math.round(tot.n).toLocaleString()} students moved, ${tot.net < 0 ? '&minus;' : '+'}${gfUsd(Math.abs(tot.net) / Math.max(1, tot.n))} each)</text>`;
  s += `<line x1="${x(0)}" x2="${x(0)}" y1="${T}" y2="${H - AX}" stroke="var(--text-primary)" stroke-width="1.4"/>`;
  host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px;height:auto" role="img" aria-label="Net General Fund staffing change of each closure">${s}</svg>` +
    `<div class="rplegend" style="margin-top:2px"><span><i class="k" style="height:8px;width:14px;border:0;background:var(--up);vertical-align:-1px"></i>saved at the closed school${PS ? ', per student moved' : ''}</span><span><i class="k" style="height:8px;width:14px;border:0;background:var(--down);opacity:.7;vertical-align:-1px"></i>added at the receiving schools${PS ? ', per student moved' : ''}</span><span><i class="k" style="height:9px;width:14px;border:0;background:var(--text-primary);vertical-align:-1px"></i>net change${PS ? ' per student moved' : ' a year'}</span></div>`;
  sub.innerHTML = `${esc(LABEL[base])}, ${yr}${D.years.indexOf(gfYear) < D.years.indexOf(D.impl_year) ? ` (closures take effect in ${D.impl_year}, so that year is shown)` : ''}: for each school the scenario closes, the General Fund staffing saved there (its actual 2026-27 General Fund staffing carried to ${yr} by PPS's staffing formula) against the staff its receiving schools add for its students (the formula's added positions for the students each receives, at that school's actual General Fund cost relative to the formula). ` +
    `${PS ? 'Shown per student moved (each closure\'s figures over its students); switch Show to Net total for dollars a year. ' : 'Shown in total dollars a year; switch Show to Per student for each closure over its students. '}Closures run from the largest net saving${PS ? ' per student moved' : ''}. All ${out.length}: <b>${tot.net < 0 ? gfM(-tot.net) + ' a year saved' : gfM(tot.net) + ' a year more'}</b> net (${gfM(tot.saved)} saved, ${gfM(tot.added)} added), about ${gfUsd(Math.abs(tot.net) / Math.max(1, tot.n))} per student moved. Staffing only: building operating costs, transportation and centrally allocated staff are not included. Hover a row for the receiving schools.`;
}
function renderCostCurve() {""")
    assert html.count("renderTrend(); renderCostCurve();") == 2   # renderAll and staffChanged
    html = html.replace("renderTrend(); renderCostCurve();", "renderTrend(); renderGFPer(); renderCostCurve();")
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
.gfperwrap { overflow-x: auto; } .gfperwrap svg { display: block; }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
