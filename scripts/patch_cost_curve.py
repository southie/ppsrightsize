"""Staffing cost per student by school size: a card after "Small schools and staffing cost over time" with one chart per
school type (K-5, K-8, middle, high). Each chart plots the staffing formula's cost per student (salary + benefits,
2026-27 dollars, the year and class sizes set in Staffing impact) for a school of that type across enrollments from
about 20% below the smallest current school to 20% above the largest (the type's average grade mix; solid non-Title I,
dashed Title I where it differs), marks the sustainability threshold and its cost per student, and plots each current school
at its Status Quo enrollment and formula cost per student. Code added once.
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

if 'function renderCostCurve' not in html:
    rep("""    <div class="tablewrap" id="trend"></div>
  </section>""", """    <div class="tablewrap" id="trend"></div>
  </section>

  <section class="card">
    <h2>The sustainability threshold impact on cost per student by school size</h2>
    <p class="sub">PPS's staffing formula cost per student (salary + benefits, 2026-27 dollars; year and class sizes as set in Staffing impact) for a school of each type at each enrollment, with that type's average grade mix: solid line non-Title I, dashed Title I where it differs. Steps are where the formula adds a homeroom, an assistant principal or a support position. The shaded line marks the sustainability threshold. Dots are current schools at their Status Quo enrollment (hover for the school); ringed dots are schools closing in the scenario being viewed (in Scenario A or B when viewing Status Quo). Base formula staffing only: Title I, equity, SIA, Measure 98 and grant positions are not included, so PPS's published dollars per student run higher.</p>
    <div id="costcurve" class="ccgrid"></div>
  </section>""")
    rep(".hstable { min-width: 640px; }", ".hstable { min-width: 640px; }\n.ccgrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 12px 20px; } .ccgrid h4 { margin: 4px 0 2px; font-size: 14px; }")
    rep("function renderAll() {", r"""// ---------- staffing cost per student by school size ----------
function renderCostCurve() {
  const host = document.getElementById('costcurve'); if (!host) return;
  const yi = D.years.indexOf(staffYear), keys = Object.keys(D.region_of);
  const TYPES = [['ES', 'K-5 schools'], ['K8', 'K-8 schools'], ['MS', 'Middle schools (6-8)'], ['HS', 'High schools (9-12)']];
  // generic schools for the curve: an even grade mix (no grade counts), non-Title I and Title I
  for (const t1 of [false, true]) D.staff.schools[`__cc_${t1 ? 't1' : 'nt'}`] = { title1: t1 };
  const per = (k, E, t) => { const r = schoolFTE(k, 'SQ', yi, E, t); return r && E > 0 ? staffCost(r) / E : null; };
  const usd = v => '$' + Math.round(v).toLocaleString();
  host.innerHTML = TYPES.map(([t, title]) => {
    const pts = keys.filter(k => D.types.SQ[k] === t && D.series.SQ[k]?.[yi] > 0).map(k => ({ k, E: D.series.SQ[k][yi], c: per(k, D.series.SQ[k][yi], t), t1: !!D.staff.schools[k]?.title1 }));
    if (!pts.length) return '';
    // the curve's school has this type's average grade mix (an even mix would add a homeroom in every grade at once)
    const gs = pts.map(p => D.staff.schools[p.k]?.grades_2526).filter(Boolean);
    const avgG = gs.length ? gs[0].map((_, i) => gs.reduce((a, g) => a + (g[i] || 0), 0) / gs.length) : null;
    for (const c of ['__cc_nt', '__cc_t1']) D.staff.schools[c].grades_2526 = avgG;
    const thr = D.thresholds[t], eMin = Math.min(...pts.map(p => p.E)), eMax = Math.max(...pts.map(p => p.E));
    const lo = Math.max(20, Math.floor(Math.min(eMin * 0.8, thr * 0.8) / 10) * 10), hi = Math.ceil(Math.max(eMax * 1.2, thr * 1.2) / 10) * 10;
    const step = Math.max(1, Math.round((hi - lo) / 240));
    const xs = []; for (let E = lo; E <= hi; E += step) xs.push(E);
    const cNT = xs.map(E => per('__cc_nt', E, t)), cT1 = xs.map(E => per('__cc_t1', E, t));
    const same = cNT.every((v, i) => Math.abs(v - cT1[i]) < 1);
    const all = [...cNT, ...(same ? [] : cT1), ...pts.map(p => p.c)].filter(v => v != null);
    const yLo = Math.floor(Math.min(...all) / 1000) * 1000, yHi = Math.ceil(Math.max(...all) / 1000) * 1000;
    const W = 360, H = 220, L = 54, R = 10, T = 12, B = 30;
    const x = E => L + (W - L - R) * (E - lo) / (hi - lo), y = v => T + (H - T - B) * (1 - (v - yLo) / ((yHi - yLo) || 1));
    let g = '';
    const ys = (yHi - yLo) / 1000 > 8 ? 2000 : 1000;
    for (let v = yLo; v <= yHi; v += ys) g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 5}" y="${y(v) + 4}" text-anchor="end" font-size="10" fill="var(--text-muted)">$${(v / 1000).toFixed(0)}k</text>`;
    const xstep = (hi - lo) > 1200 ? 400 : (hi - lo) > 500 ? 200 : 100;
    for (let E = Math.ceil(lo / xstep) * xstep; E <= hi; E += xstep) g += `<text x="${x(E)}" y="${H - B + 14}" text-anchor="middle" font-size="10" fill="var(--text-muted)">${E}</text>`;
    g += `<text x="${L + (W - L - R) / 2}" y="${H - 3}" text-anchor="middle" font-size="10" fill="var(--text-muted)">students</text>`;
    // threshold highlight
    const cThr = per('__cc_nt', thr, t);
    g += `<rect x="${x(thr) - 3}" y="${T}" width="6" height="${H - T - B}" fill="var(--change)" opacity=".18"/><line x1="${x(thr)}" x2="${x(thr)}" y1="${T}" y2="${H - B}" stroke="var(--change)" stroke-width="1.5"/>` +
      `<circle cx="${x(thr)}" cy="${y(cThr)}" r="4.5" fill="var(--change)" stroke="#fff" stroke-width="1.2"><title>${esc(`Threshold ${thr} students: ${usd(cThr)} per student (formula, non-Title I)`)}</title></circle>` +
      `<text x="${x(thr) + (x(thr) > W - 120 ? -6 : 6)}" y="${T + 11}" font-size="10.5" font-weight="600" text-anchor="${x(thr) > W - 120 ? 'end' : 'start'}" fill="var(--change)">threshold ${thr}: ${usd(cThr)}</text>`;
    // curves (stepped where the formula adds staff)
    const path = cs => xs.map((E, i) => `${i ? 'L' : 'M'}${x(E).toFixed(1)},${y(cs[i]).toFixed(1)}`).join('');
    g += `<path d="${path(cNT)}" fill="none" stroke="var(--text-secondary)" stroke-width="1.8"/>`;
    if (!same) g += `<path d="${path(cT1)}" fill="none" stroke="var(--text-secondary)" stroke-width="1.4" stroke-dasharray="4 3"/>`;
    // current schools
    // schools closing: in the scenario being viewed, or (under Status Quo) in Scenario A or B
    const closesIn = k => (scen === 'SQ' ? ['A', 'B'] : [scen]).filter(s => D.detail[s]?.[k]?.closed);
    for (const p of pts) {
      const cl = closesIn(p.k);
      g += `<circle cx="${x(p.E)}" cy="${y(p.c)}" r="${cl.length ? 4.2 : 3.6}" fill="${p.E >= thr ? 'var(--up)' : 'var(--down)'}" stroke="${cl.length ? 'var(--text-primary)' : '#fff'}" stroke-width="${cl.length ? 2 : 1}" opacity=".95">` +
        `<title>${esc(`${short(byKey[p.k].name)}${p.t1 ? ' (Title I)' : ''}: ${Math.round(p.E)} students, ${usd(p.c)} per student (formula, Status Quo ${staffYear})${cl.length ? `; closes in ${cl.map(s => LABEL[s]).join(' and ')}` : ''}`)}</title></circle>`;
    }
    const below = pts.filter(p => p.E < thr).length, nClose = pts.filter(p => closesIn(p.k).length).length;
    return `<div><h4>${title}</h4><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${title}: staffing cost per student by enrollment" style="width:100%;display:block">${g}</svg>` +
      `<p class="muted" style="font-size:11.5px;margin:2px 0 0">${pts.length} schools, ${Math.round(eMin)}&ndash;${Math.round(eMax)} students (${staffYear}); ${below} below the threshold (red dots); ${nClose} closing in ${scen === 'SQ' ? 'Scenario A or B' : esc(LABEL[scen])} (ringed). Formula cost at the threshold: ${usd(cThr)} per student${same ? '' : `, ${usd(per('__cc_t1', thr, t))} if Title I`}.</p></div>`;
  }).join('');
}
function renderAll() {""")
    rep("renderEndpoints(); renderTrend();", "renderEndpoints(); renderTrend(); renderCostCurve();")
    rep("function staffChanged() { renderKPIs(); renderEndpoints(); renderStaffing(); }", "function staffChanged() { renderKPIs(); renderEndpoints(); renderStaffing(); renderTrend(); renderCostCurve(); }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
