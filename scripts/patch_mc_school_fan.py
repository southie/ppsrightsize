"""Enrollment uncertainty section: click a school's projected-students range to open its fan chart, 2025-26 to 2035-36:
actual enrollment (PSU-reported history), the page's projection for the scenario being viewed and for Status Quo, the
simulated median and 50% / 90% ranges, and the school's size threshold, with a row of yearly figures and the chance of
being below the threshold. Each school's simulated path is rebuilt from the stored district draws for every year (as
the table's range is); with school-level error, the error follows a random walk with PSU's typical school miss at each
horizon (mean one), the same for the table and the chart. Replaces mcSchoolEnroll (patch_mc_school_enroll.py) with a
path-based version. Needs D.mc.house_all / hband_all / school_sd_all. Code added once.
"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

NEW = r'''// each school's simulated enrollment path, every year (scripts/patch_mc_school_fan.py; replaces patch_mc_school_enroll's single-year version)
const mcPathCache = {};
let mcRatioCache = null;
function mcRatios() {   // per year, per district draw: each band's change net of affordable-housing students
  if (mcRatioCache) return mcRatioCache;
  const M = D.mc, bands = M.variants.district.bands;
  return mcRatioCache = M.years.map((_, fi) => { const md = M.medium_bands[fi], hb = M.hband_all[fi];
    return bands.map(b => { const s = b[fi], r = (i, h) => (s[i] - h) / (md[i] - h); return { k5: r(1, hb[0]), m68: r(2, hb[1]), h912: r(3, hb[2]) }; }); });
}
function mcSchoolPath(k, sc) {   // [year][draw] simulated enrollment (null after the school closes)
  const ck = [k, sc, mcVar, adjOn].join('|'); if (mcPathCache[ck]) return mcPathCache[ck];
  const M = D.mc, R = mcRatios(), impl = D.years.indexOf(D.impl_year), ki = M.schools.indexOf(k), n = R[0].length;
  let st = (ki + 1) * 2654435761 >>> 0;
  const u = () => { st = (st + 0x6D2B79F5) >>> 0; let x = st; x = Math.imul(x ^ (x >>> 15), x | 1); x ^= x + Math.imul(x ^ (x >>> 7), x | 61); return (((x ^ (x >>> 14)) >>> 0) + 0.5) / 4294967297; };
  const nrm = () => Math.sqrt(-2 * Math.log(u())) * Math.cos(2 * Math.PI * u());
  const z = new Float64Array(n);   // school error, a random walk in log enrollment (same draws in every scenario)
  const out = D.years.map((y, yi) => {
    const sd = M.school_sd_all[yi] || 0, sdp = yi > 1 ? M.school_sd_all[yi - 1] : 0;
    if (mcVar === 'school' && yi) { const step = Math.sqrt(Math.max(0, sd * sd - sdp * sdp)); for (let i = 0; i < n; i++) z[i] += step * nrm(); }
    const v = D.series[sc]?.[k]?.[yi]; if (v == null) return null;
    const t = (yi < impl ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k], f = k5Of(k, y) ?? 0.66, h = Math.min(v, M.house_all[sc]?.[k]?.[yi] || 0);
    return R[yi].map((r, i) => { const m = t === 'ES' ? r.k5 : t === 'MS' ? r.m68 : t === 'HS' ? r.h912 : f * r.k5 + (1 - f) * r.m68;
      return (v - h) * m * (mcVar === 'school' ? Math.exp(z[i] - sd * sd / 2) : 1) + h; });
  });
  return mcPathCache[ck] = out;
}
const mcDW = () => { const [lo, hi] = mcCap || [-1, 9]; return D.mc.variants.district.cap.map(c => c >= lo - 1e-9 && c <= hi + 1e-9 ? 1 : 0); };
const mcThr = (k, sc, yi) => D.thresholds[(yi < D.years.indexOf(D.impl_year) ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k]] ?? 0;
function mcSchoolEnroll(sc) {
  const yi = D.years.indexOf(mcYear), wd = mcDW(), out = {};
  D.mc.schools.forEach(k => { const p = mcSchoolPath(k, sc)[yi]; if (!p) { out[k] = null; return; }
    const [p5, p50, p95] = mcQ(p, wd, [0.05, 0.5, 0.95]); out[k] = { page: D.series[sc][k][yi], p5, p50, p95, pb: mcProb(p, wd, x => x < mcThr(k, sc, yi) - 1e-9) }; });
  return out;
}
function mcSchoolFan(k, sc) {
  document.getElementById('mcpop')?.remove();
  const wd = mcDW(), P = mcSchoolPath(k, sc), nm = short(byKey[k]?.name || k), lab = sc === 'SQ' ? 'Status Quo' : LABEL[sc];
  const Q = P.map(p => p ? mcQ(p, wd, [0.05, 0.25, 0.5, 0.75, 0.95]) : null), pb = P.map((p, yi) => p ? mcProb(p, wd, x => x < mcThr(k, sc, yi) - 1e-9) : null);
  const hist = Object.entries(D.fcacc?.sch?.[k]?.a || {}).map(([y, v]) => [+y.slice(0, 4), v]).filter(([f]) => f >= 2016 && f <= 2025);
  const page = D.years.map((y, yi) => [2025 + yi, D.series[sc]?.[k]?.[yi]]), sq = D.years.map((y, yi) => [2025 + yi, D.series.SQ?.[k]?.[yi]]);
  const F = D.years.map((_, yi) => 2025 + yi), x0 = 2016, x1 = 2035, W = 680, H = 280, L = 52, R = 14, T = 14, B = 28;
  const thr = F.map((f, yi) => mcThr(k, sc, yi));
  const vals = [...hist.map(h => h[1]), ...Q.flatMap(q => q ? [q[0], q[4]] : []), ...page.map(p => p[1]), ...sq.map(p => p[1]), ...thr].filter(v => v != null && isFinite(v));
  const ylo = Math.max(0, Math.min(...vals) * 0.9), yhi = Math.max(...vals) * 1.06;
  const x = f => L + (W - L - R) * (f - x0) / (x1 - x0), y = v => T + (H - T - B) * (1 - (v - ylo) / ((yhi - ylo) || 1));
  let s = '';
  const step = (yhi - ylo) > 1500 ? 500 : (yhi - ylo) > 600 ? 200 : (yhi - ylo) > 250 ? 50 : 25;
  for (let v = Math.ceil(ylo / step) * step; v <= yhi; v += step) s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" font-size="10.5" fill="var(--text-muted)">${v.toLocaleString()}</text>`;
  for (let f = x0; f <= x1; f += 2) s += `<text x="${x(f)}" y="${H - B + 15}" text-anchor="middle" font-size="10" fill="var(--text-muted)">${f}</text>`;
  s += `<line x1="${x(2025.5)}" x2="${x(2025.5)}" y1="${T}" y2="${H - B}" stroke="var(--line)" stroke-dasharray="3 3"/>`;
  const seg = (fs, fn) => { const out = []; let cur = []; fs.forEach((f, i) => { const v = fn(i); if (v == null) { if (cur.length) out.push(cur); cur = []; } else cur.push([f, v]); }); if (cur.length) out.push(cur); return out; };
  // threshold
  s += seg(F, i => thr[i]).map(p => `<polyline points="${p.map(q => `${x(q[0])},${y(q[1])}`).join(' ')}" fill="none" stroke="var(--down)" stroke-width="1.6" stroke-dasharray="6 4"><title>Size threshold</title></polyline>`).join('');
  // ranges
  for (const [a, b, op] of [[0, 4, 0.14], [1, 3, 0.26]]) for (const p of seg(F, i => Q[i] ? 1 : null)) {
    const idx = p.map(q => q[0] - 2025);
    s += `<polygon points="${idx.map(i => `${x(F[i])},${y(Q[i][b])}`).join(' ')} ${idx.map(i => `${x(F[i])},${y(Q[i][a])}`).reverse().join(' ')}" fill="var(--change)" opacity="${op}"/>`;
  }
  s += seg(F, i => Q[i]?.[2]).map(p => `<polyline points="${p.map(q => `${x(q[0])},${y(q[1])}`).join(' ')}" fill="none" stroke="var(--change)" stroke-width="2"/>`).join('');
  if (sc !== 'SQ') s += seg(F, i => sq[i][1]).map(p => `<polyline points="${p.map(q => `${x(q[0])},${y(q[1])}`).join(' ')}" fill="none" stroke="var(--text-muted)" stroke-width="1.4" stroke-dasharray="4 3"><title>Status Quo (page)</title></polyline>`).join('');
  s += seg(F, i => page[i][1]).map(p => `<polyline points="${p.map(q => `${x(q[0])},${y(q[1])}`).join(' ')}" fill="none" stroke="var(--text-primary)" stroke-width="1.8"><title>${esc(lab)} (page, PSU medium)</title></polyline>`).join('');
  if (hist.length) s += `<polyline points="${hist.map(h => `${x(h[0])},${y(h[1])}`).join(' ')}" fill="none" stroke="var(--text-primary)" stroke-width="2.6"/>` + hist.map(h => `<circle cx="${x(h[0])}" cy="${y(h[1])}" r="2.6" fill="var(--text-primary)"><title>Fall ${h[0]}: ${h[1].toLocaleString()} actual</title></circle>`).join('');
  F.forEach((f, i) => { if (Q[i]) s += `<rect x="${x(f) - 9}" y="${T}" width="18" height="${H - T - B}" fill="transparent"><title>${D.years[i]}: median ${Math.round(Q[i][2]).toLocaleString()}; 50% range ${Math.round(Q[i][1]).toLocaleString()}-${Math.round(Q[i][3]).toLocaleString()}; 90% range ${Math.round(Q[i][0]).toLocaleString()}-${Math.round(Q[i][4]).toLocaleString()}; page ${Math.round(page[i][1]).toLocaleString()}; threshold ${thr[i]}; chance below ${Math.round(100 * pb[i])}%</title></rect>`; });
  const closeYr = D.years.find((y, yi) => yi > 0 && D.series[sc]?.[k]?.[yi] == null && D.series[sc]?.[k]?.[yi - 1] != null);
  const tbl = `<div class="tablewrap" style="margin-top:6px"><table style="min-width:0;font-size:12px"><thead><tr><th style="text-align:left">Year</th>${D.years.map(y => `<th style="text-align:right">${y.slice(2)}</th>`).join('')}</tr></thead><tbody>` +
    `<tr><td style="text-align:left">Page</td>${page.map(p => `<td style="text-align:right">${p[1] == null ? '&mdash;' : Math.round(p[1])}</td>`).join('')}</tr>` +
    `<tr><td style="text-align:left">Median</td>${Q.map(q => `<td style="text-align:right">${q ? Math.round(q[2]) : '&mdash;'}</td>`).join('')}</tr>` +
    `<tr><td style="text-align:left">90% range</td>${Q.map(q => `<td style="text-align:right;white-space:nowrap" class="muted">${q ? `${Math.round(q[0])}&ndash;${Math.round(q[4])}` : '&mdash;'}</td>`).join('')}</tr>` +
    `<tr><td style="text-align:left">Below threshold</td>${pb.map(p => `<td style="text-align:right">${p == null ? '&mdash;' : Math.round(100 * p) + '%'}</td>`).join('')}</tr></tbody></table></div>`;
  const pop = document.createElement('div'); pop.id = 'mcpop';
  pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-modal', 'true'); pop.setAttribute('aria-label', `${nm}: projected students`);
  pop.style.cssText = 'position:fixed;inset:0;z-index:3000;background:rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;padding:16px';
  pop.innerHTML = `<div style="background:var(--surface-1);color:var(--text-primary);border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.3);max-width:760px;width:100%;max-height:92vh;overflow:auto;padding:14px 16px">` +
    `<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px"><h3 style="margin:0;font-size:16px">${esc(nm)}: projected students, ${esc(lab)}</h3><button type="button" id="mcpop-x" aria-label="Close" style="font:inherit;font-size:18px;border:0;background:none;cursor:pointer;color:var(--text-secondary)">&times;</button></div>` +
    `<p class="sub" style="margin:4px 0 8px">${TYPE_LABEL[(D.types[sc] || {})[k] || D.types.SQ[k]] || ''}${closeYr ? ` &middot; closes in ${esc(lab)} from ${closeYr}` : ''} &middot; ${mcVar === 'school' ? 'district uncertainty plus the school’s own forecast error' : 'district uncertainty (kindergarten capture and grade progression)'}${mcCap && (mcCap[0] > D.mc.params.capture.tri.a + 1e-6 || mcCap[1] < D.mc.params.capture.tri.b - 1e-6) ? `, long-run capture ${mcCap[0].toFixed(3)}&ndash;${mcCap[1].toFixed(3)}` : ''}</p>` +
    `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto" role="img" aria-label="Projected students by year">${s}</svg>` +
    `<div class="rplegend"><span><i class="k" style="border-top:2.6px solid var(--text-primary);width:18px"></i>actual</span><span><i class="k" style="border-top:1.8px solid var(--text-primary);width:18px"></i>${esc(lab)} (page)</span>${sc !== 'SQ' ? '<span><i class="k" style="border-top:1.6px dashed var(--text-muted);width:18px"></i>Status Quo (page)</span>' : ''}` +
    `<span><i class="k" style="height:10px;width:16px;background:var(--change);opacity:.35"></i>simulated 50% / 90%</span><span><i class="k" style="border-top:2px solid var(--change);width:18px"></i>simulated median</span><span><i class="k" style="border-top:1.6px dashed var(--down);width:18px"></i>size threshold</span></div>` + tbl + `</div>`;
  document.body.appendChild(pop);
  const close = () => { pop.remove(); document.removeEventListener('keydown', esc_); };
  const esc_ = e => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', esc_);
  pop.onclick = e => { if (e.target === pop) close(); };
  document.getElementById('mcpop-x').onclick = close; document.getElementById('mcpop-x').focus();
}
function renderMCSchools(w, sc) {'''

if 'mcSchoolFan' not in html:
    m = re.search(r"// each school's simulated enrollment in the year and scenario being viewed \(scripts/patch_mc_school_enroll\.py\)\n.*?\nfunction renderMCSchools\(w, sc\) \{", html, re.S)
    assert m, 'mcSchoolEnroll block'
    html = html[:m.start()] + NEW + html[m.end():]
    # clickable range cell
    rep("""return e ? `<td style="text-align:right;white-space:nowrap"><b>""",
        """return e ? `<td class="mc-en" data-k="${esc(r.k)}" tabindex="0" role="button" title="Show this school's projected students by year" style="text-align:right;white-space:nowrap;cursor:pointer"><b>""")
    rep("""  const b = document.getElementById('mc-allsch'); if (b) {""",
        """  host.querySelectorAll('.mc-en').forEach(td => { const open = () => mcSchoolFan(td.dataset.k, sc); td.onclick = open; td.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } }; });
  const b = document.getElementById('mc-allsch'); if (b) {""")
    rep(""".linkbtn { margin-left: 10px;""", """td.mc-en:hover b, td.mc-en:focus-visible b { text-decoration: underline; color: var(--change); } td.mc-en:focus-visible { outline: 2px solid var(--change); outline-offset: -2px; }
.linkbtn { margin-left: 10px;""")
    rep("""`</tbody></table><p class="sub" style="margin:6px 0 0">Projected students: the simulated median and middle 90% for the scenario being viewed, and the page's value (PSU medium forecast);""",
        """`</tbody></table><p class="sub" style="margin:6px 0 0">Projected students: the simulated median and middle 90% for the scenario being viewed, and the page's value (PSU medium forecast); click a range for the school's chart by year;""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
