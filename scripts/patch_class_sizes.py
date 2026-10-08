"""Class sizes and teacher loads by grade, in the projected-enrollment section: for a chosen school year and the
selected scenario, each region (expandable to schools) shows students per grade, K-5 homerooms and class sizes at the
budget's maximum class sizes, and grade 6-8 / 9-12 teacher loads at the budget's staffing ratios; cells above the PAT
contract's overload-pay thresholds are highlighted.

Sources: 2026-27 Adopted Budget, Vol. 1, School Staffing (pp. 232-238): K-5 maximum class sizes (Title I / other),
6-8 at 23.5 students per FTE (+1.0 base in Title I middle schools) on a "5 of 7" schedule (7 periods, 5 taught),
9-12 at 25 per FTE plus a base (4 FTE under 800 students, 1 FTE over 1,000). PAT-PPS Agreement 2023-2026,
Article 8.3.3.2: overload thresholds K 24, grades 1-3 26, grades 4-5 28 students per class; middle school educators
150 and high school educators 160 students a day. Grade mix: each school's 2025-26 enrollment by grade.
Safe to rerun: added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function renderClassSizes' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# ---- markup ----
rep("""    <div class="panels" id="panels"></div>
  </section>""", """    <div class="panels" id="panels"></div>
    <h3 class="cshead">Class sizes and teacher loads by grade</h3>
    <p class="sub">Students per grade in the selected scenario and school year (this page's projection, split by each school's 2025-26 grade mix), at the <b>largest class sizes and staffing ratios PPS's 2026-27 budget allows</b>: K-5 homerooms at the maximum class size (Title I or other schools); grades 6-8 at 23.5 students per teacher (plus 1.0 in Title I middle schools) on a 5-of-7 schedule; grades 9-12 at 25 per teacher plus a base. <span class="csover-key">Highlighted</span> cells are above the PAT contract's overload-pay thresholds (2023-2026 agreement, Article 8.3.3.2): K over 24 students in a class, grades 1-3 over 26, grades 4-5 over 28; teachers over 150 students a day in grades 6-8 and over 160 in 9-12. Click a region to see its schools; hover a cell for details.</p>
    <div class="controls"><label>School year <select id="cs-year"></select></label></div>
    <div class="tablewrap" id="classsize"></div>
  </section>""")

# ---- code ----
rep("function renderAll() {", r"""// ---------- class sizes and teacher loads by grade ----------
// PAT-PPS Agreement 2023-2026, Art. 8.3.3.2: overload-pay thresholds (students per class K-5; students a day 6-8, 9-12)
const PAT_K5 = [24, 26, 26, 26, 28, 28], PAT_MS = 150, PAT_HS = 160;
const CS_DAY = 7, CS_TAUGHT = 5;   // budget: 5-of-7 schedule for grades 6-8 (assumed for 9-12 too): a teacher's load = students x 7 / teachers
const CS_GRADES = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
let csYear = D.impl_year;
try { const y = localStorage.getItem('rsCsYear'); if (D.years.includes(y)) csYear = y; } catch (e) {}
const csOpen = new Set();
// one school in one scenario and year, at the budget's largest class sizes and staffing ratios
function classSizes(k, sc, yi) {
  const t = D.types[sc]?.[k] || D.types.SQ[k], E = D.series[sc]?.[k]?.[yi];
  if (!E || !t) return null;
  const T1 = !!D.staff.schools[k]?.title1, f = D.k5_share[D.years[yi]] ?? K8_AVG_FRAC;
  const g = D.staff.schools[k]?.grades_2526 || [];
  const mix = (lo, hi) => { const s = CS_GRADES.slice(lo, hi + 1).map((_, i) => g[lo + i] || 0), tot = s.reduce((a, b) => a + b, 0);
    return tot ? s.map(x => x / tot) : s.map(() => 1 / s.length); };
  const k5 = t === 'ES' ? E : t === 'K8' ? E * f : 0, m68 = t === 'MS' ? E : t === 'K8' ? E * (1 - f) : 0, hs = t === 'HS' ? E : 0;
  const cap = SF.caps_budget[T1 ? 'title1' : 'other'];
  const grades = Array(13).fill(null);
  if (k5) k5Shares(k).forEach((s, i) => {
    const n = Math.round(k5 * s), h = n ? Math.ceil(n / cap[i] - 1e-9) : 0;
    if (!n) { grades[i] = { n: 0 }; return; }
    const lo = Math.floor(n / h), hi = Math.ceil(n / h), nHi = n - lo * h, thr = PAT_K5[i];
    const overCls = lo > thr ? h : hi > thr ? nHi : 0, overStu = lo > thr ? n - thr * h : hi > thr ? nHi * (hi - thr) : 0;
    grades[i] = { n, h, avg: n / h, max: hi, cap: cap[i], thr, overCls, overStu };
  });
  if (m68) mix(6, 8).forEach((s, i) => { grades[6 + i] = { n: Math.round(m68 * s) }; });
  if (hs) mix(9, 12).forEach((s, i) => { grades[9 + i] = { n: Math.round(hs * s) }; });
  const fte68 = m68 ? m68 / SF.ms_ratio + (t === 'MS' && T1 ? SF.ms_base_title1 : 0) : 0;
  const fte912 = hs ? hs / SF.hs_ratio + (hs < 800 ? 4 : hs > 1000 ? 1 : 4 - 3 * (hs - 800) / 200) : 0;
  return { t, T1, E, grades, m68, fte68, load68: fte68 ? m68 * CS_DAY / fte68 : null, hs, fte912, load912: fte912 ? hs * CS_DAY / fte912 : null };
}
function renderClassSizes() {
  const host = document.getElementById('classsize'); if (!host) return;
  const sel = document.getElementById('cs-year');
  if (!sel.options.length) {
    sel.innerHTML = D.years.map(y => `<option value="${y}">${y}${y === D.years[0] ? ' (actual)' : y === D.impl_year ? ' (scenarios take effect)' : ''}</option>`).join('');
    sel.onchange = () => { csYear = sel.value; try { localStorage.setItem('rsCsYear', csYear); } catch (e) {} renderClassSizes(); };
  }
  sel.value = csYear;
  const yi = D.years.indexOf(csYear), sc = scen, keysOf = rn => Object.keys(D.region_of).filter(k => D.region_of[k] === rn).sort(byStatusName);
  const n0 = v => Math.round(v).toLocaleString();
  const k5Cell = (gr, tip) => !gr || !gr.n ? '<td class="muted">&mdash;</td>'
    : `<td class="${gr.overCls ? 'csover' : ''}" title="${esc(tip)}"><span class="main">${gr.avg.toFixed(1)}</span><span class="cssub">${n0(gr.n)} in ${gr.h}${gr.overCls ? ` &middot; ${gr.overCls} over` : ''}</span></td>`;
  const loadCell = (load, fte, n, thr, tip) => load == null ? '<td class="muted">&mdash;</td>'
    : `<td class="${load > thr ? 'csover' : ''}" title="${esc(tip)}"><span class="main">${Math.round(load)}</span><span class="cssub">${fte.toFixed(1)} teachers &middot; class ~${Math.round(load / CS_TAUGHT)}</span></td>`;
  const nCell = n => n ? `<td>${n0(n)}</td>` : '<td class="muted">&mdash;</td>';
  let h = `<table class="cstable"><thead><tr><th>Region</th><th>Students</th>` +
    CS_GRADES.slice(0, 6).map((g, i) => `<th>${g === 'K' ? 'K' : 'Grade ' + g}<br><span style="font-weight:400">class size (over ${PAT_K5[i]})</span></th>`).join('') +
    CS_GRADES.slice(6, 9).map(g => `<th>Grade ${g}<br><span style="font-weight:400">students</span></th>`).join('') +
    `<th>6-8 teacher load<br><span style="font-weight:400">students a day (over ${PAT_MS})</span></th>` +
    CS_GRADES.slice(9).map(g => `<th>Grade ${g}<br><span style="font-weight:400">students</span></th>`).join('') +
    `<th>9-12 teacher load<br><span style="font-weight:400">students a day (over ${PAT_HS})</span></th></tr></thead><tbody>`;
  const sumRows = list => {   // region or district totals from school results
    const o = { E: 0, grades: Array(13).fill(null).map(() => ({ n: 0, h: 0, overCls: 0, overStu: 0 })), m68: 0, fte68: 0, hs: 0, fte912: 0, ms: 0, msOver: 0, hsN: 0, hsOver: 0 };
    for (const r of list) {
      o.E += r.E;
      r.grades.forEach((gr, i) => { if (!gr) return; const a = o.grades[i]; a.n += gr.n || 0; a.h += gr.h || 0; a.overCls += gr.overCls || 0; a.overStu += gr.overStu || 0; });
      if (r.fte68) { o.m68 += r.m68; o.fte68 += r.fte68; o.ms++; if (r.load68 > PAT_MS) o.msOver++; }
      if (r.fte912) { o.hs += r.hs; o.fte912 += r.fte912; o.hsN++; if (r.load912 > PAT_HS) o.hsOver++; }
    }
    return o;
  };
  const sumCells = o => `<td><span class="main">${n0(o.E)}</span></td>` +
    o.grades.slice(0, 6).map((a, i) => !a.n ? '<td class="muted">&mdash;</td>'
      : `<td class="${a.overCls ? 'csover' : ''}" title="${esc(`${n0(a.n)} students in ${a.h} homerooms; ${a.overCls} homeroom${a.overCls === 1 ? '' : 's'} over the PAT threshold of ${PAT_K5[i]} (${n0(a.overStu)} students over)`)}"><span class="main">${(a.n / a.h).toFixed(1)}</span><span class="cssub">${n0(a.n)} in ${a.h}${a.overCls ? ` &middot; ${a.overCls} over` : ''}</span></td>`).join('') +
    o.grades.slice(6, 9).map(a => nCell(a.n)).join('') +
    (o.fte68 ? `<td class="${o.msOver ? 'csover' : ''}" title="${esc(`${o.ms} school${o.ms === 1 ? '' : 's'} with grades 6-8; ${o.msOver} over ${PAT_MS} students a day per teacher`)}"><span class="main">${Math.round(o.m68 * CS_DAY / o.fte68)}</span><span class="cssub">${o.msOver} of ${o.ms} schools over</span></td>` : '<td class="muted">&mdash;</td>') +
    o.grades.slice(9).map(a => nCell(a.n)).join('') +
    (o.fte912 ? `<td class="${o.hsOver ? 'csover' : ''}" title="${esc(`${o.hsN} high school${o.hsN === 1 ? '' : 's'}; ${o.hsOver} over ${PAT_HS} students a day per teacher`)}"><span class="main">${Math.round(o.hs * CS_DAY / o.fte912)}</span><span class="cssub">${o.hsOver} of ${o.hsN} schools over</span></td>` : '<td class="muted">&mdash;</td>');
  const all = [];
  for (const rn of D.region_order) {
    const keys = keysOf(rn), res = keys.map(k => [k, classSizes(k, sc, yi)]), open = csOpen.has(rn);
    const ok = res.filter(([, r]) => r).map(([, r]) => r); all.push(...ok);
    h += `<tr><td><button class="xbtn cs-x" data-r="${esc(rn)}" aria-expanded="${open}"><span class="car">&#9656;</span><span>${esc(rn)}</span></button></td>${sumCells(sumRows(ok))}</tr>`;
    if (!open) continue;
    for (const [k, r] of res) {
      const nm = `<span class="nm">${esc(short(byKey[k].name))}</span><span class="ty">${TYPE_LABEL[r ? r.t : D.types.SQ[k]] || ''}${r?.T1 ? ' &middot; Title I' : ''}</span>`;
      if (!r) { h += `<tr class="srow closed"><td>${nm}</td><td colspan="18" style="text-align:left"><span class="stag closes">Closes</span> <span class="muted">no students in ${csYear}</span></td></tr>`; continue; }
      h += `<tr class="srow"><td>${nm}</td><td>${n0(r.E)}</td>` +
        r.grades.slice(0, 6).map((gr, i) => k5Cell(gr, gr && gr.n ? `${gr.n} students in ${gr.h} homeroom${gr.h === 1 ? '' : 's'} at the budget maximum of ${gr.cap}; largest class ${gr.max}; PAT overload threshold ${gr.thr}` + (gr.overCls ? `; ${gr.overCls} class${gr.overCls === 1 ? '' : 'es'} over (${gr.overStu} students over)` : '') : '')).join('') +
        r.grades.slice(6, 9).map(gr => nCell(gr?.n)).join('') +
        loadCell(r.load68, r.fte68, r.m68, PAT_MS, `${Math.round(r.m68)} students in grades 6-8; ${r.fte68.toFixed(1)} teachers at 23.5 students each${r.t === 'MS' && r.T1 ? ' plus 1.0 (Title I)' : ''}; ${CS_DAY} periods a day, ${CS_TAUGHT} taught: about ${Math.round(r.load68 || 0)} students a day per teacher, classes of about ${Math.round((r.load68 || 0) / CS_TAUGHT)}; PAT threshold ${PAT_MS}`) +
        r.grades.slice(9).map(gr => nCell(gr?.n)).join('') +
        loadCell(r.load912, r.fte912, r.hs, PAT_HS, `${Math.round(r.hs)} students; ${r.fte912.toFixed(1)} teachers at 25 students each plus a base; assuming ${CS_DAY} periods a day, ${CS_TAUGHT} taught: about ${Math.round(r.load912 || 0)} students a day per teacher; PAT threshold ${PAT_HS}`) + '</tr>';
    }
  }
  h += `<tr class="dist"><td>District</td>${sumCells(sumRows(all))}</tr>`;
  host.innerHTML = h + '</tbody></table>';
  host.querySelectorAll('.cs-x').forEach(b => b.onclick = () => { const r = b.dataset.r; csOpen.has(r) ? csOpen.delete(r) : csOpen.add(r); renderClassSizes(); });
}
function renderAll() {""")
rep("function renderAll() { renderKPIs(); renderCustomPanel(); renderMap(); renderEndpoints(); renderCommute(); renderStaffing(); renderLines(); }",
    "function renderAll() { renderKPIs(); renderCustomPanel(); renderMap(); renderEndpoints(); renderCommute(); renderStaffing(); renderLines(); renderClassSizes(); }")

# ---- styles: highlight, pinned first column and header, like the other large tables ----
rep("""#overlist table th:first-child, #overlist table td:first-child {
  position: sticky; left: 0;""", """#overlist table th:first-child, #overlist table td:first-child,
.cstable th:first-child, .cstable td:first-child {
  position: sticky; left: 0;""")
rep("#endpoints, #commute, #overlist, .tablewrap:has(> .stafftable) {", "#endpoints, #commute, #overlist, #classsize, .tablewrap:has(> .stafftable) {")
rep("#endpoints thead th, .commutetable thead th, .stafftable thead th, #overlist thead th {", "#endpoints thead th, .commutetable thead th, .stafftable thead th, #overlist thead th, .cstable thead th {")
rep("#endpoints thead th:first-child, .commutetable thead th:first-child, .stafftable thead th:first-child, #overlist thead th:first-child {",
    "#endpoints thead th:first-child, .commutetable thead th:first-child, .stafftable thead th:first-child, #overlist thead th:first-child, .cstable thead th:first-child {")
rep("#endpoints table tr.srow td:first-child, .stafftable tr.srow td:first-child, .commutetable tr.srow td:first-child { background: var(--surface-2); }",
    "#endpoints table tr.srow td:first-child, .stafftable tr.srow td:first-child, .commutetable tr.srow td:first-child, .cstable tr.srow td:first-child { background: var(--surface-2); }\n"
    ".cshead { margin: 22px 0 4px; font-size: 16px; }\n"
    ".cstable td, .cstable th { white-space: nowrap; } .cstable td .main { font-size: 14px; font-weight: 600; display: block; }\n"
    ".cstable .cssub { display: block; font-size: 11px; color: var(--text-muted); }\n"
    ".cstable td.csover, .csover-key { background: color-mix(in srgb, var(--over) 38%, transparent); } .cstable td.csover .cssub { color: var(--text-primary); }\n"
    ".csover-key { padding: 0 4px; border-radius: 3px; }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
