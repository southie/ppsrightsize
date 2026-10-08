// ---------- staffing estimate: PPS 2026-27 school staffing formula (Proposed Budget Vol. 1, pp. 206-210) ----------
const SF = D.staff.formula;
const STAFF_YEARS = D.years.filter(y => y >= D.impl_year);
let staffYear = D.impl_year, capPreset = 'budget';
let caps = JSON.parse(JSON.stringify(SF.caps_budget));
const staffOpen = new Set();
const ceil02 = x => Math.ceil(x * 5 - 1e-9) / 5;
const nearest = (x, s) => Math.round(x / s) * s;
const GRADE_LABELS = ['K', '1', '2', '3', '4', '5'];
// average K-5 share of enrollment among K-8 schools (fallback when a school has no grade counts)
const K8_AVG_FRAC = (() => {
  const v = Object.entries(D.staff.schools).filter(([k, s]) => D.types.SQ[k] === 'K8' && s.grades_2526)
    .map(([, s]) => s.grades_2526.slice(0, 6).reduce((a, b) => a + b, 0) / s.grades_2526.slice(0, 9).reduce((a, b) => a + b, 0));
  return v.reduce((a, b) => a + b, 0) / v.length;
})();
function k5Shares(k) {
  const g = D.staff.schools[k]?.grades_2526, k5 = g ? g.slice(0, 6) : null, t = k5 ? k5.reduce((a, b) => a + b, 0) : 0;
  return t > 0 ? k5.map(v => v / t) : [1, 1, 1, 1, 1, 1].map(v => v / 6);
}
function k8Frac(k) {
  const g = D.staff.schools[k]?.grades_2526;
  if (!g) return K8_AVG_FRAC;
  const a = g.slice(0, 6).reduce((x, y) => x + y, 0), b = g.slice(6, 9).reduce((x, y) => x + y, 0);
  return a + b > 0 ? a / (a + b) : K8_AVG_FRAC;
}
const HS_BANDS = [   // [min enrollment, vice principals, athletic director, librarian, social worker, HS support]
  [1600, 3, 1, 1, 1, 2.5], [1400, 2, 1, 1, 1, 2.5], [1200, 2, 1, 1, 1, 2.25], [700, 2, 1, 1, 1, 2.0], [600, 1, 1, 1, 1, 2.0], [100, 1, 1, 1, 1, 1.5], [0, 0, 0, 0, 0, 0]];
// formula FTE (licensed equivalents) for one school in one scenario/year; null when closed
function schoolFTE(k, sc, yi, enrollOverride, typeOverride) {
  const t = typeOverride || D.types[sc][k], E = enrollOverride ?? D.series[sc][k][yi];
  if (E == null || !t) return null;
  const T1 = !!D.staff.schools[k]?.title1;
  const r = { principal: 0, ap: 0, office: 0, homeroom: 0, specialists: 0, support: 0, t68: 0, t912: 0, enroll: E, type: t, title1: T1, homeroomsByGrade: null };
  let k5 = 0, m68 = 0;
  // K-8 split uses the same district K-5 share as the enrollment model, so Status Quo and scenarios stay consistent
  const f = D.k5_share[D.years[yi]] ?? K8_AVG_FRAC;
  if (t === 'ES') k5 = E; else if (t === 'K8') { k5 = E * f; m68 = E - k5; } else if (t === 'MS') m68 = E;
  if (k5 > 0) {
    const cap = caps[T1 ? 'title1' : 'other'];
    r.homeroomsByGrade = k5Shares(k).map((s, i) => { const n = k5 * s; return n >= 0.5 ? Math.ceil(n / cap[i] - 1e-9) : 0; });
    const H = r.homeroomsByGrade.reduce((a, b) => a + b, 0);
    r.homeroom = H;
    // PE 90 min/wk, music and visual art 45 min/wk each (6 homerooms/day); library 45 min/wk (5/day); 0.2 FTE steps
    r.specialists = ceil02(H * 2 / 30) + 2 * ceil02(H / 30) + ceil02(H / 25);
  }
  if (t === 'ES' || t === 'K8') {
    r.principal = 1; r.ap = (t === 'ES' ? (E >= 550 || (T1 && E >= 500)) : E >= 400) ? 1 : 0;
    r.office = E >= 600 ? 1 : 0.75; r.support = 1 + nearest(E / SF.counselor_ratio, 0.2);   // discretionary + counselors
  }
  if (t === 'MS') { r.principal = 1; r.ap = 1; r.office = 0.75; r.specialists += 0.5; r.support = nearest(E / SF.counselor_ratio, 0.2); }
  if (m68 > 0) r.t68 = m68 / SF.ms_ratio + (t === 'MS' && T1 ? SF.ms_base_title1 : 0);
  if (t === 'HS') {
    const b = HS_BANDS.find(x => E >= x[0]);
    r.principal = 1; r.ap = b[1]; r.office = b[2] + b[5]; r.specialists = b[3];
    r.support = b[4] + nearest(E / SF.counselor_ratio, 0.5);
    const base = E < 800 ? 4 : E > 1000 ? 1 : 4 - 3 * (E - 800) / 200;
    r.t912 = E / SF.hs_ratio + base;
  }
  r.total = r.principal + r.ap + r.office + r.homeroom + r.specialists + r.support + r.t68 + r.t912;
  return r;
}
const STAFF_COLS = [
  ['principal', 'Principals'], ['ap', 'Assistant / vice principals'], ['office', 'Office & admin support'],
  ['homeroom', 'K-5 homeroom teachers'], ['specialists', 'PE, arts & library'], ['support', 'Counselors, social workers & discretionary'],
  ['t68', '6-8 teachers'], ['t912', '9-12 teachers'], ['total', 'Total FTE']];
const SC = D.staff.costs;
function staffCost(a) {
  return (a.principal + a.ap) * SC.administrator + a.office * 2 * SC.classified
    + (a.homeroom + a.specialists + a.support + a.t68 + a.t912) * SC.licensed;
}
const staffUSD = v => (v < 0 ? '&minus;' : '') + '$' + (Math.abs(v) / 1e6).toFixed(1) + 'M';
function staffAgg(keys, sc, yi) {
  const a = Object.fromEntries(STAFF_COLS.map(([c]) => [c, 0])); a.closed = 0; a.open = 0;
  for (const k of keys) { const r = schoolFTE(k, sc, yi); if (!r) { a.closed++; continue; } a.open++; for (const [c] of STAFF_COLS) a[c] += r[c]; }
  return a;
}
const fte1 = v => (Math.abs(v) < 0.05 ? '0' : (v > 0 ? '+' : '&minus;') + Math.abs(v).toFixed(Math.abs(v) >= 100 ? 0 : 1));
function staffChanged() { renderKPIs(); renderEndpoints(); renderStaffing(); }
function renderStaffing() {
  const host = document.getElementById('staffing'); if (!host) return;
  const yi = D.years.indexOf(staffYear), isSQ = scen === 'SQ';
  const rows = [...D.region_order, 'District'];
  const keysOf = rn => Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn);
  // controls
  const capRow = which => `<tr><th>${which === 'title1' ? 'Title I schools' : 'Other schools'}</th>${caps[which].map((v, i) => `<td><input type="number" min="10" max="40" step="1" value="${v}" data-w="${which}" data-g="${i}" aria-label="${which} grade ${GRADE_LABELS[i]} maximum"></td>`).join('')}</tr>`;
  let h = `<div class="controls staffctl">
      <label>School year <select id="st-year">${STAFF_YEARS.map(y => `<option ${y === staffYear ? 'selected' : ''}>${y}</option>`).join('')}</select></label>
      <label>K-5 class-size maximums <select id="st-preset">
        <option value="budget" ${capPreset === 'budget' ? 'selected' : ''}>PPS 2026-27 budget (grade 1: 31, Title I 30)</option>
        <option value="contract" ${capPreset === 'contract' ? 'selected' : ''}>Teachers' contract overload thresholds (24/26/28)</option>
        <option value="custom" ${capPreset === 'custom' ? 'selected' : ''}>Custom (edit below)</option></select></label>
      <button id="st-capbtn" type="button">${document.getElementById('st-capgrid')?.dataset.open === '1' ? 'Hide' : 'Edit'} maximums</button></div>
    <div id="st-capgrid" class="capgrid" data-open="${document.getElementById('st-capgrid')?.dataset.open || '0'}" ${document.getElementById('st-capgrid')?.dataset.open === '1' ? '' : 'hidden'}>
      <table><thead><tr><th>Students per homeroom, at most</th>${GRADE_LABELS.map(g => `<th>${g === 'K' ? 'K' : 'Grade ' + g}</th>`).join('')}</tr></thead><tbody>${capRow('title1')}${capRow('other')}</tbody></table></div>`;
  // table
  h += `<div class="tablewrap"><table class="stafftable"><thead><tr><th>Region</th><th>Buildings closed</th>${STAFF_COLS.map(([, l]) => `<th>${l}</th>`).join('')}<th>Annual cost (2026-27 $)</th></tr></thead><tbody>`;
  for (const rn of rows) {
    const keys = keysOf(rn), sq = staffAgg(keys, 'SQ', yi), cur = staffAgg(keys, scen, yi), isReg = rn !== 'District', open = staffOpen.has(rn);
    h += `<tr class="${isReg ? '' : 'dist'}"><td>${isReg ? `<button class="xbtn st-x" data-r="${esc(rn)}" aria-expanded="${open}"><span class="car">&#9656;</span><span>${esc(rn)}</span></button>` : esc(rn)}</td><td>${isSQ ? 0 : cur.closed}</td>`;
    for (const [c] of STAFF_COLS) {
      const d = cur[c] - sq[c];
      h += isSQ ? `<td>${sq[c].toFixed(c === 'principal' || c === 'ap' ? 0 : 1)}</td>`
        : `<td><span class="main">${fte1(d)}</span><span class="muted" style="display:block;font-size:11px">of ${sq[c].toFixed(c === 'principal' || c === 'ap' ? 0 : 1)}</span></td>`;
    }
    const cs = staffCost(sq), cc = staffCost(cur);
    h += isSQ ? `<td>${staffUSD(cs)}</td>` : `<td><span class="main">${staffUSD(cc - cs)}</span><span class="muted" style="display:block;font-size:11px">of ${staffUSD(cs)}</span></td>`;
    h += '</tr>';
    if (isReg && open) {
      for (const k of keys.sort(byStatusName)) {
        const a = schoolFTE(k, 'SQ', yi), b = schoolFTE(k, scen, yi);
        h += `<tr class="srow${b ? '' : ' closed'}"><td><span class="nm">${esc(short(byKey[k].name))}</span><span class="ty">${TYPE_LABEL[(b || a).type]}${a.title1 ? ' &middot; Title I' : ''}</span>` +
          `<span class="muted" style="display:block;font-size:11px">${Math.round(a.enroll)}${isSQ ? '' : ` &rarr; ${b ? Math.round(b.enroll) : 'closed'}`} students${a.homeroomsByGrade && !isSQ && b?.homeroomsByGrade ? ` &middot; homerooms ${a.homeroom} &rarr; ${b.homeroom}` : a.homeroomsByGrade ? ` &middot; ${a.homeroom} homerooms` : ''}</span></td>` +
          `<td>${b ? '' : '<span class="stag closes">Closes</span>'}</td>` +
          STAFF_COLS.map(([c]) => isSQ ? `<td>${a[c].toFixed(c === 'principal' || c === 'ap' ? 0 : 1)}</td>` : `<td>${fte1((b ? b[c] : 0) - a[c])}</td>`).join('') +
          (isSQ ? `<td>${staffUSD(staffCost(a))}</td>` : `<td>${staffUSD((b ? staffCost(b) : 0) - staffCost(a))}</td>`) + '</tr>';
      }
    }
  }
  h += '</tbody></table></div>';
  const dist = staffAgg(keysOf('District'), scen, yi), dsq = staffAgg(keysOf('District'), 'SQ', yi);
  const admin = (dsq.principal + dsq.ap + dsq.office) - (dist.principal + dist.ap + dist.office);
  const teach = (dsq.homeroom + dsq.t68 + dsq.t912) - (dist.homeroom + dist.t68 + dist.t912);
  document.getElementById('staffsum').innerHTML = isSQ
    ? `Status Quo in ${staffYear}: the formula allocates <b>${dsq.total.toFixed(0)}</b> licensed-equivalent FTE to these ${dsq.open} schools. Pick Scenario A, B or Custom to see positions no longer needed.`
    : `${LABEL[scen]} in ${staffYear}, compared with Status Quo the same year: about <b>${staffUSD(staffCost(dsq) - staffCost(dist)).replace('&minus;', '')}</b> a year in formula staffing (2026-27 dollars, salary plus benefits), from about <b>${(dsq.total - dist.total).toFixed(0)}</b> fewer formula positions (licensed-equivalent FTE): <b>${(dsq.principal - dist.principal).toFixed(0)}</b> principals, <b>${(dsq.ap - dist.ap).toFixed(0)}</b> assistant/vice principals and <b>${(dsq.office - dist.office).toFixed(1)}</b> office FTE (administration ${admin.toFixed(1)} in all), and <b>${teach.toFixed(1)}</b> classroom teachers, of which <b>${(dsq.homeroom - dist.homeroom).toFixed(0)}</b> are K-5 homerooms freed when students fill open seats at receiving schools.`;
  host.innerHTML = h;
  // wiring
  document.getElementById('st-year').onchange = e => { staffYear = e.target.value; staffChanged(); };
  document.getElementById('st-preset').onchange = e => { capPreset = e.target.value; if (capPreset !== 'custom') caps = JSON.parse(JSON.stringify(capPreset === 'budget' ? SF.caps_budget : SF.caps_contract)); staffChanged(); };
  document.getElementById('st-capbtn').onclick = () => { const g = document.getElementById('st-capgrid'); g.dataset.open = g.dataset.open === '1' ? '0' : '1'; renderStaffing(); };
  host.querySelectorAll('.capgrid input').forEach(inp => inp.onchange = () => {
    const v = Math.max(10, Math.min(40, Math.round(+inp.value || 0))); caps[inp.dataset.w][+inp.dataset.g] = v; capPreset = 'custom'; staffChanged();
  });
  host.querySelectorAll('.st-x').forEach(b => b.onclick = () => { const r = b.dataset.r; staffOpen.has(r) ? staffOpen.delete(r) : staffOpen.add(r); renderStaffing(); });
}

