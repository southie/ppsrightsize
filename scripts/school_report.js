// ---------- school report: search above the map for a one-school summary (scripts/patch_school_report.py) ----------
// Compares the scenario being viewed with Status Quo. Pathways, boundaries and PPS's change list come from the
// scenario (a custom scenario uses its starting scenario's); enrollment, staffing and grades use this page's model.
const RP_BANDS = { ES: ['k5'], K8: ['k5', '68'], MS: ['68'], HS: ['912'] };
const RP_BL = { k5: 'K-5', '68': '6-8', '912': '9-12' };
const RP_TL = { ES: 'K-5', K8: 'K-8', MS: '6-8', HS: '9-12' };
let rpKey = null, rpYear = D.impl_year, rpMap = null, rpLayer = null, rpScroll = false;
try {
  rpKey = localStorage.getItem('rsReport');
  const y = localStorage.getItem('rsReportYear'); if (D.years.includes(y)) rpYear = y;
} catch (e) {}
// deep link: ?school=<name or key>&year=<school year>&scenario=SQ|A|B (a custom scenario keeps its own #custom=... link)
const rpFindKey = v => {
  v = (v || '').trim().toLowerCase(); if (!v) return null;
  const s = D.schools.find(x => x.key.toLowerCase() === v || x.name.toLowerCase() === v || rpTitle(x).toLowerCase() === v || short(x.name).toLowerCase() === v) ||
    D.schools.find(x => x.name.toLowerCase().includes(v) || short(x.name).toLowerCase().includes(v));
  return s ? s.key : null;
};
try {
  const q = new URLSearchParams(location.search), k = rpFindKey(q.get('school')), y = q.get('year'), sc = (q.get('scenario') || '').toUpperCase();
  if (k) { rpKey = k; rpScroll = true; }
  if (D.years.includes(y)) rpYear = y;
  // scenario= is only written while a published scenario is shown, so it wins over a #custom=... kept in the address
  if (['SQ', 'A', 'B'].includes(sc)) scen = sc;
} catch (e) {}
if (rpKey && !byKey[rpKey]) rpKey = null;
// first visit (nothing saved, no ?school= link): open on a high school, the first alphabetically
if (!rpKey) rpKey = D.schools.filter(s => D.types.SQ[s.key] === 'HS').map(s => s.key).sort((a, b) => short(byKey[a].name).localeCompare(short(byKey[b].name)))[0] || null;
// keep the address in step with the report so it can be shared
function rpSyncUrl() {
  try {
    const q = new URLSearchParams(location.search);
    if (rpKey) {
      q.set('school', rpTitle(byKey[rpKey])); q.set('year', rpYear);
      if (scen !== 'C') q.set('scenario', scen); else q.delete('scenario');
    } else ['school', 'year', 'scenario'].forEach(p => q.delete(p));
    const s = q.toString();
    history.replaceState(null, '', location.pathname + (s ? '?' + s : '') + location.hash);
  } catch (e) {}
}
// a school's name as a link to its own report (plain click swaps the report in place; the href also opens in a new tab)
function rpHref(k) {
  const q = new URLSearchParams(location.search);
  q.set('school', rpTitle(byKey[k])); q.set('year', rpYear);
  if (scen !== 'C') q.set('scenario', scen); else q.delete('scenario');
  return location.pathname + '?' + q.toString() + location.hash;
}
function rpLink(k, text) {
  text = esc(text ?? rpName(k));
  return !byKey[k] || k === rpKey ? text : `<a class="rplink" href="${esc(rpHref(k))}" data-k="${esc(k)}" title="Open the report for ${esc(rpTitle(byKey[k]))}">${text}</a>`;
}
function rpOpen(k) {
  rpKey = k;
  const box = document.getElementById('rpfind'); if (box) box.value = rpTitle(byKey[k]);
  try { localStorage.setItem('rsReport', rpKey); } catch (e) {}
  renderReport();
  document.getElementById('reportcard')?.scrollIntoView({ block: 'start' });
}
const rpBase = sc => sc === 'C' ? custom.base : sc;
const rpName = k => byKey[k] ? short(byKey[k].name) : k;
// full name with the page's renames (Lane -> Brentwood (Lane), Lee -> Sunrise (Lee))
function rpTitle(s) { const r = Object.entries(RENAMED).find(([a]) => s.name.startsWith(a + ' ')); return r ? r[1] + s.name.slice(r[0].length) : s.name; }
const rpPct = v => Math.round(100 * v) + '%';

// one flow column: key -> { sq, sc, notes }
function rpAdd(m, key, side, note) {
  if (!key) return;
  const e = m.get(key) || { sq: false, sc: false, notes: [] };
  e[side] = true;
  if (note && !e.notes.includes(note)) e.notes.push(note);
  m.set(key, e);
}
function rpFlow(k, sc) {
  const base = rpBase(sc), P0 = (D.feeders || {}).SQ || [], P1 = (D.feeders || {})[base] || P0;
  // inn: where students come from; next: the normal next school (or, if it closes, where its students go);
  // out: students relocated to another school at the same level, with the mechanism
  const inn = new Map(), next = new Map(), high = new Map(), out = new Map();
  for (const [P, side] of [[P0, 'sq'], [P1, 'sc']]) {
    for (const [es, ms, hs, prog, note] of P) {
      const pn = prog && prog !== 'neighborhood' ? prog + ' program' : '';
      const nt = side === 'sc' && note ? note : '';
      if (ms === k && es && es !== k) rpAdd(inn, es, side, [pn, nt].filter(Boolean).join('; '));
      if (hs === k && ms) rpAdd(inn, ms, side, '');
      if (es === k) {
        if (ms && ms !== k) rpAdd(next, ms, side, [pn, nt].filter(Boolean).join('; '));
        if (hs) rpAdd(high, hs, side, '');
      }
      if (ms === k && hs) rpAdd(high, hs, side, '');
    }
  }
  if (sc !== 'SQ') {
    const fl = D.flows[sc] || { receivers: [], moves: [] }, det = D.detail[sc] || {};
    for (const r of fl.receivers) {
      if (r.adj) continue;   // the modified enrollment model's own moves are listed below with their estimate
      const sh = r.share != null ? ` (${rpPct(r.share)})` : '';
      if (r.to_key === k) rpAdd(inn, r.from_key, 'sc', `${r.group}${sh}`);   // a closing origin already shows a "Closed" badge
      if (r.from_key === k) {
        if (det[k]?.closed) rpAdd(next, r.to_key, 'sc', `${r.group}${sh}`);
        else rpAdd(out, r.to_key, 'sc', `Receiving share: ${r.group}${sh}`);
      }
    }
    for (const mv of fl.moves || []) {
      if (mv.to_key === k && mv.from_key !== k) rpAdd(inn, mv.from_key, 'sc', mv.text);
      if (mv.from_key === k && mv.to_key !== k) rpAdd(out, mv.to_key, 'sc', `${mv.kind === 'grade' ? 'Grade change' : mv.kind === 'program' ? 'Program move' : 'Move'}: ${mv.text}`);
    }
    const as = adjScen(sc);
    if (as) for (const x of ADJ.moves[as] || []) {
      if (x.t === k) rpAdd(inn, x.f, 'sc', adjMoveTxt(x));
      if (x.f === k) rpAdd(out, x.t, 'sc', x.k8
        ? `Own grade mix: ${Math.abs(x.n)} ${x.n > 0 ? 'more' : 'fewer'} 6-8 students in 2031-32 than the district share sends (ODE grade counts; modified enrollment model)`
        : `About ${x.n} ${ADJ_BL[x.band]} students in 2031-32 (Census estimate of the boundary change; modified enrollment model)`);
    }
    for (const b of ['k5', '68', '912']) {
      const B = D.bounds[base.toLowerCase() + '_' + b]; if (!B || !B.ckeys) continue;
      B.ckeys.forEach(([f, t]) => {
        if (f === k && t) rpAdd(out, t, 'sc', `Boundary change: part of the ${RP_BL[b]} attendance area moves (PPS scenario boundary map)`);
        if (t === k && f) rpAdd(inn, f, 'sc', `Boundary change: part of its ${RP_BL[b]} attendance area joins (PPS scenario boundary map)`);
      });
    }
  }
  // a closing school sends all its students: its relocations belong with where its students go
  if (sc !== 'SQ' && (D.detail[sc] || {})[k]?.closed) {
    for (const [to, e] of out) for (const n of e.notes) rpAdd(next, to, 'sc', n);
    out.clear();
  }
  return { inn, next, high, out };
}
function rpBoxes(m, sc) {
  if (!m.size) return '<div class="rpbox none">none</div>';
  return [...m.entries()].sort((a, b) => (b[1].sc - a[1].sc) || rpName(a[0]).localeCompare(rpName(b[0]))).map(([key, e]) => {
    const cls = sc === 'SQ' ? '' : e.sc && !e.sq ? ' add' : e.sq && !e.sc ? ' rem' : '';
    const badge = (sc === 'SQ' ? '' : e.sc && !e.sq ? `<span class="rpbadge add">Changed in ${esc(LABEL[sc])}</span>` : e.sq && !e.sc ? '<span class="rpbadge rem">no longer</span>' : '') +
      (sc !== 'SQ' && (D.detail[sc] || {})[key]?.closed ? '<span class="rpbadge cl">Closed</span>' : '');
    const t = (D.types[sc] || {})[key] || D.types.SQ[key];
    return `<div class="rpbox${cls}"><b>${rpLink(key)}</b> <span class="n">${t ? RP_TL[t] : ''}</span>${badge}` +
      (e.notes.length ? `<span class="nt">${e.notes.map(esc).join('<br>')}</span>` : '') + '</div>';
  }).join('');
}
function rpChanges(k, sc) {
  const L0 = ((D.fchanges || {})[rpBase(sc)] || []).filter(c => c[0] === k || (c[4] || []).some(r => r[0] === k));
  if (!L0.length) return '';
  return `<h4>PPS's listed changes</h4><ul class="rplist">${L0.map(c => `<li>${esc(c[2])}${c[3] ? ` <span class="muted">(${esc(c[3])})</span>` : ''}</li>`).join('')}</ul>`;
}

// enrollment vs capacity, all projection years
// scenarios shown side by side in the plot and staffing table: Status Quo, A, B, and Custom when it is being viewed
const rpCols = sc => ['SQ', 'A', 'B', ...(sc === 'C' ? ['C'] : [])];
const RP_LINE = { SQ: 'lsq', A: 'la', B: 'lb', C: 'lc' };
// marker for figures the modified enrollment model (Census boundary changes, K-8 grade mix) changes in a scenario
const rpMark = (k, s) => s === 'SQ' || typeof adjMark !== 'function' ? '' : adjMark(k, s);
const rpMarkTxt = (k, s) => { const m = rpMark(k, s).match(/title="([^"]*)"/); return m ? m[1].replace(/&[a-z#0-9]+;/g, ' ') : ''; };
function rpPlot(k, sc) {
  const W = 620, H = 230, M = { l: 44, r: 12, t: 12, b: 26 }, Y = D.years;
  const cols = rpCols(sc), ser = Object.fromEntries(cols.map(s => [s, (D.series[s] || {})[k] || []]));
  const sq = ser.SQ, fc = byKey[k]?.fc;
  const t1 = (D.types[sc] || {})[k] || D.types.SQ[k], thr = D.thresholds[t1];
  const vals = [...cols.flatMap(s => ser[s]), fc, thr].filter(v => v != null);
  const ymax = Math.max(...vals) * 1.12 || 1;
  const x = i => M.l + (W - M.l - M.r) * i / (Y.length - 1), y = v => M.t + (H - M.t - M.b) * (1 - v / ymax);
  const line = (s, cls) => { let d = ''; s.forEach((v, i) => { if (v == null) return; d += (d && s[i - 1] != null ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1); }); return d ? `<path class="${cls}" d="${d}"/>` : ''; };
  const ticks = []; const step = ymax > 1500 ? 500 : ymax > 600 ? 200 : 100;
  for (let v = 0; v <= ymax; v += step) ticks.push(`<line class="grid" x1="${M.l}" x2="${W - M.r}" y1="${y(v)}" y2="${y(v)}"/><text class="ax" x="${M.l - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`);
  const xl = Y.map((yr, i) => i % 2 ? '' : `<text class="ax" x="${x(i)}" y="${H - 8}" text-anchor="middle">${yr}</text>`).join('');
  const imp = Y.indexOf(D.impl_year);
  const hline = (v, cls, lab) => v == null ? '' : `<line class="${cls}" x1="${M.l}" x2="${W - M.r}" y1="${y(v)}" y2="${y(v)}"/><text class="lab ${cls}" x="${W - M.r - 4}" y="${y(v) - 4}" text-anchor="end">${lab}</text>`;
  // the scenario being viewed is drawn last and thickest; Status Quo's line is shared until changes take effect
  const order = cols.filter(s => s !== sc).concat(cols.includes(sc) ? [sc] : []);
  const dots = s => ser[s].map((v, i) => v == null || (s !== 'SQ' && i < imp) ? '' :
    `<circle class="d ${RP_LINE[s]}${s === sc ? ' cur' : ''}" cx="${x(i)}" cy="${y(v)}" r="${s === sc ? 3 : 2.2}"><title>${esc(LABEL[s])}, ${Y[i]}: ${Math.round(v)}` +
    `${i >= imp && rpMarkTxt(k, s) ? ' ◆ modified enrollment model: ' + esc(rpMarkTxt(k, s)) : ''}</title></circle>`).join('');
  return `<svg class="rpplot" viewBox="0 0 ${W} ${H}" role="img" aria-label="Projected enrollment and capacity">${ticks.join('')}${xl}` +
    `<line class="impl" x1="${x(imp)}" x2="${x(imp)}" y1="${M.t}" y2="${H - M.b}"/>` +
    hline(fc, 'cap', `2021 capacity ${fc ? fc.toLocaleString() : ''}`) + hline(thr, 'thr', `size threshold ${thr}`) +
    order.map(s => line(s === 'SQ' ? ser[s] : ser[s].map((v, i) => i < imp - 1 ? null : v), RP_LINE[s] + (s === sc ? ' cur' : ''))).join('') +
    order.map(dots).join('') + '</svg>' +
    `<div class="rplegend">${cols.map(s => `<span${s === sc ? ' class="cur"' : ''}><i class="k ${RP_LINE[s]}"></i>${esc(LABEL[s])}${rpMark(k, s)}</span>`).join('')}` +
    `<span><i class="k cap"></i>2021 functional capacity</span><span><i class="k thr"></i>size threshold</span><span><i class="k impl"></i>changes take effect (${D.impl_year})</span></div>` +
    (cols.some(s => rpMark(k, s)) ? `<p class="muted rpnote">&#9670; marks a scenario whose figures for this school include the modified enrollment model (each K-8's own grade mix and Census estimates of boundary changes PPS's enrollment figures do not move); hover it for the moves. ${esc(ADJ_OFF)}</p>` : '');
}

// Southeast enrollment balancing, Phase 2 (fall 2023): the school's changes (D.segc, scripts/patch_segc.py)
function rpSegc(k) {
  const s = D.segc?.sch?.[k]; if (!s) return '';
  return `<div class="rppanel rpwide rpsegc"><h3>Southeast enrollment balancing: SEGC Phase 2 changes (fall 2023)</h3>` +
    `<ul>${s.p2.map(t => `<li>${esc(t)}</li>`).join('')}</ul>${s.p1 ? `<p class="muted rpnote">${esc(s.p1)}</p>` : ''}` +
    (typeof segcEst === 'function' && segcEst(k) ? `<p class="rpnote">${segcEst(k)}</p>` : '') +
    `<p class="muted rpnote">Adopted by the PPS Board in Resolution 6513 (May 2022) from the Southeast Guiding Coalition process. ${esc(D.segc.phase_in)} Student counts are those enrolled in 2021-22 in each area or program moved (PPS's school-by-school impact analysis). PSU's forecasts from 2023-24 on, and this page's projections, include these changes. Sources: ${D.segc.sources.map(x => `<a href="${esc(x[1])}">${esc(x[0])}</a>`).join('; ')}.</p></div>`;
}

// past PSU forecasts for this school against its actual enrollment (D.fcacc, scripts/patch_forecast_accuracy.py)
function rpFcAcc(k) {
  const F = D.fcacc, s = F?.sch?.[k];
  if (!s) return `<h4>How accurate have past forecasts been for this school?</h4><p class="muted rpnote">PSU's past forecasts do not include this school separately (a new school or one forecast with another).</p>`;
  const y0 = Math.min(...Object.keys(s.a).map(y => +y.slice(0, 4)), ...Object.keys(s.f).map(e => +e.slice(0, 4)));
  const Y = []; for (let i = y0; i <= +D.years[D.years.length - 1].slice(0, 4); i++) Y.push(`${i}-${String((i + 1) % 100).padStart(2, '0')}`);
  const W = 620, H = 230, M = { l: 44, r: 12, t: 12, b: 26 }, cur = F.eds[F.eds.length - 1];
  const vals = [...Object.values(s.a), ...Object.values(s.f).flat()].filter(v => v != null);
  const ymax = Math.max(...vals) * 1.1 || 1;
  const x = i => M.l + (W - M.l - M.r) * i / (Y.length - 1), y = v => M.t + (H - M.t - M.b) * (1 - v / ymax);
  const ticks = []; const step = ymax > 1500 ? 500 : ymax > 600 ? 200 : 100;
  for (let v = 0; v <= ymax; v += step) ticks.push(`<line class="grid" x1="${M.l}" x2="${W - M.r}" y1="${y(v)}" y2="${y(v)}"/><text class="ax" x="${M.l - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`);
  const xl = Y.map((yr, i) => i % 3 ? '' : `<text class="ax" x="${x(i)}" y="${H - 8}" text-anchor="middle">${yr}</text>`).join('');
  // each edition's line starts from the last actual it knew (the year before its first forecast year)
  const fl = e => {
    const i0 = Y.indexOf(e), prev = s.a[Y[i0 - 1]], pts = s.f[e].map((v, j) => [i0 + j, v]);
    if (prev != null) pts.unshift([i0 - 1, prev]);
    const cls = e === cur ? 'fa-cur' : F.post.includes(e) ? 'fa-post' : 'fa-pre';
    return `<path class="${cls}${s.bc.includes(e) ? ' fa-rs' : ''}" d="${pts.map(([i, v], j) => (j ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1)).join('')}"><title>${e} edition forecast: ${s.f[e].map((v, j) => `${Y[i0 + j]} ${v}`).join(', ')}${s.bc.includes(e) ? ' (counted differently: a later edition restated this school\'s enrollment)' : ''}</title></path>`;
  };
  const act = Object.entries(s.a).filter(([yr]) => Y.includes(yr)), ap = act.map(([yr, v]) => [Y.indexOf(yr), v]);
  const plot = `<svg class="rpplot" viewBox="0 0 ${W} ${H}" role="img" aria-label="Past forecasts and actual enrollment">${ticks.join('')}${xl}` +
    F.eds.filter(e => s.f[e]?.length && e !== cur).map(fl).join('') + (s.f[cur]?.length ? fl(cur) : '') +
    `<path class="fa-act" d="${ap.map(([i, v], j) => (j ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1)).join('')}"/>` +
    ap.map(([i, v]) => `<circle class="fa-act" cx="${x(i)}" cy="${y(v)}" r="2.6"><title>Actual, ${Y[i]}: ${v}</title></circle>`).join('') + '</svg>' +
    `<div class="rplegend"><span><i class="k fa-act"></i>Actual enrollment</span><span><i class="k fa-pre"></i>Pre-COVID editions (${F.pre[0]} to ${F.pre[F.pre.length - 1]})</span>` +
    `<span><i class="k fa-post"></i>Post-COVID editions (${F.post[0]} to ${F.post[F.post.length - 2]})</span><span><i class="k fa-cur"></i>${cur} edition (this page's Status Quo)</span></div>`;
  const cell = st => st ? `<td>${st[1].toFixed(1)}%</td><td>${st[2] > 0 ? '+' : st[2] < 0 ? '&minus;' : ''}${Math.abs(st[2]).toFixed(1)}%</td><td class="muted">${st[0]}</td>` : '<td class="muted">&mdash;</td><td class="muted">&mdash;</td><td class="muted"></td>';
  const typ = (era, h) => { const t = F.dist.typ[era]?.[h]; return t ? `${t[1].toFixed(1)}%` : '&mdash;'; };
  const rows = [1, 2, 3, 5].map(h => `<tr><td>${h} year${h === 1 ? '' : 's'} ahead</td>${cell(s.st.post?.[h])}${cell(s.st.pre?.[h])}<td class="muted">${typ('post', h)} / ${typ('pre', h)}</td></tr>`).join('');
  return `<h4>How accurate have past forecasts been for this school?</h4>${plot}` +
    `<table class="rptable"><thead><tr><th rowspan="2"></th><th colspan="3">Post-COVID editions</th><th colspan="3">Pre-COVID editions</th><th rowspan="2">Typical school<br><span style="font-weight:400">post / pre</span></th></tr>` +
    `<tr><th>average miss</th><th>lean</th><th>n</th><th>average miss</th><th>lean</th><th>n</th></tr></thead><tbody>${rows}</tbody></table>` +
    `<p class="muted rpnote">Each line is one PSU edition's medium forecast for this school, starting from the last enrollment it knew; hover a line for its numbers. Average miss is the typical size of the error, either way; lean is the average signed error (positive: forecasts were too high). Actuals are the enrollment PSU reported the following year. Post-COVID editions (2022-23 on) were made after the pandemic enrollment drop; the pre-COVID ones forecast into it.${s.bc.length ? ` Dashed: editions ${s.bc.join(', ')}, which a later edition counted differently (a program moved in or out), left out of the averages.` : ''} The typical school column is the average miss across all PPS schools.</p>`;
}

// grade-by-grade projection (this page's model: the school's grade mix progressed and scaled to its enrollment)
function rpGrades(k, sc) {
  const Y = D.years, G = CS_GRADES;
  // before the scenario takes effect the school keeps its Status Quo grade span
  const at = (s, yi) => { const r = classSizes(k, yi < D.years.indexOf(D.impl_year) ? 'SQ' : s, yi); return r ? r.grades.map(g => g?.n ?? null) : null; };
  const a = Y.map((_, yi) => at('SQ', yi)), b = sc === 'SQ' ? a : Y.map((_, yi) => at(sc, yi));
  const rows = G.map((g, i) => i).filter(i => a.some(r => r && r[i]) || b.some(r => r && r[i]));
  const IMP = D.years.indexOf(D.impl_year), cc = yi => yi === IMP ? ' cur' : '', ca = yi => yi === IMP ? ' class="cur"' : '';
  if (!rows.length) return '<p class="muted">No grade-level projection for this school.</p>';
  const cell = (yi, i) => {
    const v = b[yi] ? b[yi][i] : null, q = a[yi] ? a[yi][i] : null;
    if (!b[yi]) return `<td class="muted${cc(yi)}">closed</td>`;
    const dv = sc !== 'SQ' && q != null && Math.round(v ?? 0) !== Math.round(q);
    return `<td${ca(yi)}>${v == null ? '<span class="muted">&mdash;</span>' : Math.round(v)}${dv ? `<span class="sq">SQ ${Math.round(q)}</span>` : ''}</td>`;
  };
  const tot = yi => b[yi] ? `<td${ca(yi)}><b>${Math.round(b[yi].reduce((s, v) => s + (v || 0), 0))}</b></td>` : `<td class="muted${cc(yi)}">closed</td>`;
  return `<div class="tablewrap"><table class="rptable full"><thead><tr><th>Grade</th>${Y.map((y, yi) => `<th${ca(yi)}>${y}</th>`).join('')}</tr></thead><tbody>` +
    rows.map(i => `<tr><td>${G[i] === 'K' ? 'K' : 'Grade ' + G[i]}</td>${Y.map((_, yi) => cell(yi, i)).join('')}</tr>`).join('') +
    `<tr class="tot"><td>Total</td>${Y.map((_, yi) => tot(yi)).join('')}</tr></tbody></table></div>` +
    `<p class="muted rpnote">${sc === 'SQ' ? '' : `${esc(LABEL[sc])} figures, with Status Quo beneath where they differ. `}${esc(D.impl_year)} (highlighted) is the first year of the scenario. 2025-26 is the fall count by grade (ODE); later years move each grade up a year with the district forecast and scale to this page's projected enrollment.</p>`;
}

// staffing: budget formula FTE, and what it takes to stay under the PAT thresholds
function rpPat(k, sc, yi) {
  const r = classSizes(k, sc, yi); if (!r) return null;
  const o = { over: 0, h: 0, extraK5: 0, grades: [] };
  r.grades.slice(0, 6).forEach((g, i) => {
    if (!g || !g.h) return;
    const need = Math.ceil(g.n / g.thr - 1e-9);
    o.h += g.h; o.over += g.overCls; o.extraK5 += Math.max(0, need - g.h);
    o.grades.push({ g: CS_GRADES[i], n: g.n, h: g.h, max: g.max, thr: g.thr, over: g.overCls });
  });
  o.load68 = r.load68; o.extra68 = r.m68 ? Math.max(0, r.m68 * CS_DAY / PAT_MS - r.fte68) : 0;
  o.load912 = r.load912; o.extra912 = r.hs ? Math.max(0, r.hs * CS_DAY / PAT_HS - r.fte912) : 0;
  o.extra = o.extraK5 + o.extra68 + o.extra912;
  return o;
}
// actual staffing spending from PPS's budget school reports (D.staff_actual): salaries + associated payroll costs of the
// school-allocated funds, the General Fund share estimated by its share of the school-allocated FTE, against this page's
// formula for the same school (Status Quo)
function rpActualStaff(k) {
  const sa = D.staff_actual?.schools?.[k]; if (!sa?.salaries) return '';
  const Y = D.staff_actual.years, cols = [3, 4, 5], lab = ['actual', 'estimated', 'budget'];
  const usd = v => v == null ? '&mdash;' : '$' + (v / 1e6).toFixed(2) + 'M', per = v => v == null ? '&mdash;' : '$' + Math.round(v).toLocaleString();
  const all = i => sa.salaries[i] == null ? null : sa.salaries[i] + (sa.payroll?.[i] || 0);
  const gfShare = i => sa.alloc_fte?.[i] ? sa.gf_fte[i] / sa.alloc_fte[i] : null;
  const gf = i => all(i) != null && gfShare(i) != null ? all(i) * gfShare(i) : null;
  const yIdx = i => D.years.indexOf(Y[i]), enr = i => yIdx(i) >= 0 ? D.series.SQ[k]?.[yIdx(i)] : null;
  const form = i => { const yi = yIdx(i); if (yi < 0) return null; const r = schoolFTE(k, 'SQ', yi); return r ? staffCost(r) : null; };
  const row = (l, f, cls = '') => `<tr${cls ? ` class="${cls}"` : ''}><td>${l}</td>${cols.map(i => `<td>${f(i)}</td>`).join('')}</tr>`;
  return `<h4>Actual staffing spending compared (PPS budget school report)</h4><table class="rptable"><thead><tr><th></th>` +
    cols.map((i, j) => `<th>${Y[i]}<br><span style="font-weight:400">${lab[j]}</span></th>`).join('') + '</tr></thead><tbody>' +
    row('Staffing spending, all school funds (salaries + payroll costs)', i => usd(all(i)), 'tot') +
    row('&nbsp;&nbsp;General Fund share (est., by its share of FTE)', i => gf(i) == null ? '&mdash;' : `${usd(gf(i))} <span class="muted">(${Math.round(100 * gfShare(i))}%, ${sa.gf_fte[i]} of ${sa.alloc_fte[i]} FTE)</span>`) +
    row("This page's formula, Status Quo", i => usd(form(i))) +
    row('Students', i => enr(i) == null ? '&mdash;' : Math.round(enr(i)).toLocaleString()) +
    row('Per student: all school funds', i => enr(i) ? per(all(i) / enr(i)) : '&mdash;') +
    row('Per student: General Fund (est.)', i => enr(i) && gf(i) != null ? per(gf(i) / enr(i)) : '&mdash;') +
    row('Per student: formula', i => enr(i) && form(i) != null ? per(form(i) / enr(i)) : '&mdash;') +
    `</tbody></table><p class="muted rpnote">From PPS's 2026-27 Proposed Budget, Volume 2 (this school's report): salaries and associated payroll costs of the school-allocated funds (General Fund, Equity, Foundation, Title I and other grants; centrally allocated special education, ESL, nutrition and custodial staff are not included). The General Fund share is estimated from the share of the school's FTE that the General Fund pays for (Gen Fund, Equity and K-5 Arts rows). The formula is this page's estimate from PPS's staffing formula at average salaries; it leaves out Title I, SIA, Measure 98, grant and discretionary positions.</p>`;
}
function rpStaff(k, sc) {
  const yi = D.years.indexOf(rpYear), cols = rpCols(sc);
  const F = Object.fromEntries(cols.map(s => [s, (D.series[s] || {})[k] ? schoolFTE(k, s, yi) : null]));
  if (cols.every(s => !F[s])) return '<p class="muted">No staffing estimate for this school.</p>';
  const f = v => v == null ? '&mdash;' : (Math.round(v * 10) / 10).toFixed(1);
  const dl = (d, money) => Math.abs(d) < (money ? 5e4 : 0.05) ? '' : `<span class="sq">${money ? (d > 0 ? '+' : '') + staffUSD(d) : (d > 0 ? '+' : '&minus;') + Math.abs(d).toFixed(1)} vs SQ</span>`;
  // a scenario that closes this school: the net change for each staff type = this school's Status Quo positions lost
  // + the positions its students add at each destination (the destination's staffing with them minus without them)
  const dests = s => [...new Set((D.flows[s]?.receivers || []).filter(r => r.from_key === k && byKey[r.to_key]).map(r => r.to_key))];
  const fte = (t, s) => (D.series[s] || {})[t] ? schoolFTE(t, s, yi) : null;
  const sent = (s, t) => { const w = reopenWeights(k, s, yi).filter(x => x.to === t).reduce((a, x) => a + x.w, 0);
    return w * ((D.series.SQ[k] || [])[yi] || 0); };   // this school's Status Quo students that go to t
  const without = (t, s, n) => { const ser = (D.series[s] || {})[t]; if (!ser || ser[yi] == null) return null;
    const keep = ser[yi]; ser[yi] = Math.max(0, keep - n); try { return schoolFTE(t, s, yi); } finally { ser[yi] = keep; } };
  const destChange = (s, t, val) => { const a = fte(t, s); if (!a) return 0; const b = without(t, s, sent(s, t)); return val(a) - (b ? val(b) : 0); };
  const netOf = (s, val) => dests(s).reduce((a, t) => a + destChange(s, t, val), -val(F.SQ));
  // hover: this school's Status Quo positions and each destination's change for this row
  const netTip = (s, val, money) => {
    const fmt = v => money ? (Math.abs(v) < 5e4 ? '$0' : (v > 0 ? '+' : '') + staffUSD(v).replace(/&minus;/g, '-')) : (Math.abs(v) < 0.05 ? '0.0' : (v > 0 ? '+' : '-') + Math.abs(v).toFixed(1));
    const lines = dests(s).map(t => `${rpName(t)}: ${fmt(destChange(s, t, val))} for about ${Math.round(sent(s, t))} students from ${rpName(k)}`);
    return `${rpName(k)} closes in ${LABEL[s]}. Shown: its Status Quo ${money ? 'cost' : 'positions'} plus the net change, i.e. what its students still need at their new schools.\n` +
      `${rpName(k)}: ${fmt(-val(F.SQ))}\n` + lines.join('\n') + `\nNet: ${fmt(netOf(s, val))}\n(Each destination: its staffing with these students minus without them, so its own grade changes and other schools' students are left out.)`;
  };
  // the closed school's column: Status Quo + net change, with the change shown as "vs SQ"
  const netCell = (s, val, money) => { const n = netOf(s, val), v0 = val(F.SQ);
    return `<td class="rpnet${s === sc ? ' cur' : ''}" title="${esc(netTip(s, val, money))}"><span class="muted">closes</span><br>` +
      `${money ? staffUSD(v0 + n) : f(v0 + n)}${dl(n, money)}</td>`; };
  const cell = (s, c) => {
    const r = F[s];
    if (!r) return s !== 'SQ' && F.SQ ? netCell(s, x => x[c], false) : '<td class="muted">closed</td>';
    return `<td${s === sc ? ' class="cur"' : ''}>${f(r[c])}${s !== 'SQ' ? dl(r[c] - (F.SQ ? F.SQ[c] : 0)) : ''}</td>`;
  };
  const rows = STAFF_COLS.filter(([c]) => cols.some(s => F[s] && F[s][c])).map(([c, l]) =>
    `<tr${c === 'total' ? ' class="tot"' : ''}><td>${esc(l)}</td>${cols.map(s => cell(s, c)).join('')}</tr>`).join('');
  const cost = s => { const r = F[s];
    if (!r) return s !== 'SQ' && F.SQ ? netCell(s, staffCost, true) : '<td class="muted">closed</td>';
    const v = staffCost(r);
    return `<td${s === sc ? ' class="cur"' : ''}>${staffUSD(v)}${s !== 'SQ' ? dl(v - (F.SQ ? staffCost(F.SQ) : 0), true) : ''}</td>`; };
  const anyNet = cols.some(s => s !== 'SQ' && !F[s] && F.SQ);
  const P = Object.fromEntries(cols.map(s => [s, F[s] ? rpPat(k, s, yi) : null]));
  const pat = p => !p ? 'closed' : [p.h ? `${p.over} of ${p.h} K-5 classes over` : '', p.load68 ? `6-8 load ${Math.round(p.load68)} a day (limit ${PAT_MS})` : '',
    p.load912 ? `9-12 load ${Math.round(p.load912)} a day (limit ${PAT_HS})` : ''].filter(Boolean).join('; ') + `; <b>${p.extra.toFixed(1)}</b> more FTE to stay under`;
  const pg = P[sc] || P.SQ;
  const grade = !pg || !pg.grades.length ? '' : `<h4>K-5 classes, ${esc(LABEL[P[sc] ? sc : 'SQ'])}${rpMark(k, P[sc] ? sc : 'SQ')}</h4><table class="rptable sm"><thead><tr><th>Grade</th><th>Students</th><th>Homerooms</th><th>Largest class</th><th>PAT threshold</th><th>Over</th></tr></thead><tbody>` +
    pg.grades.map(g => `<tr><td>${g.g}</td><td>${g.n}</td><td>${g.h}</td><td>${g.max}</td><td>${g.thr}</td><td${g.over ? ' class="over"' : ''}>${g.over || ''}</td></tr>`).join('') + '</tbody></table>';
  return `<table class="rptable"><thead><tr><th>${rpYear}</th>${cols.map(s => `<th${s === sc ? ' class="cur"' : ''}>${esc(LABEL[s])}${rpMark(k, s)}</th>`).join('')}</tr></thead><tbody>${rows}` +
    `<tr><td>Staffing cost</td>${cols.map(cost).join('')}</tr></tbody></table>` + rpActualStaff(k) +
    `<h4>Under the PAT thresholds (K over 24, grades 1-3 over 26, 4-5 over 28; 6-8 over ${PAT_MS} and 9-12 over ${PAT_HS} students a day)</h4>` +
    cols.map(s => `<p class="rpline${s === sc ? ' cur' : ''}">${esc(LABEL[s])}${rpMark(k, s)}: ${pat(P[s])}</p>`).join('') + grade +
    `<p class="muted rpnote">Budget formula FTE: PPS 2026-27 adopted staffing formula at its largest class sizes. "More FTE to stay under" adds the homeroom teachers needed to keep every K-5 class at or under its PAT threshold, and the 6-8 and 9-12 teachers needed to keep daily student loads at or under ${PAT_MS} and ${PAT_HS}.` +
    (anyNet ? ' Where a scenario closes this school, its column shows, by staff type, this school\'s Status Quo positions plus the net change: its positions lost and the positions its students add at the schools they go to (each destination\'s staffing with them minus without them; hover for each school).' : '') +
    (cols.some(s => rpMark(k, s)) ? ' &#9670;: this scenario\'s enrollment for the school includes the modified enrollment model; hover it for the moves.' : '') + '</p>';
}
// costs and land
// ---------- getting to school ----------
// The school's students in the report year: students eligible for bus service and walk / bike / drive / bus time histograms
// (bars: the scenario; outline: Status Quo). For an area the scenario takes away from the school (a closure, or a K-8's
// 6-8 grades), its students by their newly assigned school (D.commute.R, scripts/build_closure_access.py), against
// those students' Status Quo trips to this school. Uses the getting-to-school table's helpers (cmAgg, cmHist).
function rpAggV(list) {   // list of [per-area array in the D.commute.X layout, students, yellow-bus grades?]
  const nb = D.commute.hist_min.length + 1;
  const o = { r: 0, beyond: 0, wmi: 0, wmin: 0, bmin: 0, dmin: 0, w15: 0, b15: 0, d15: 0, near: 0, bm: 0, be8: 0,
    bh: Array(D.commute.bh_mi.length + 1).fill(0), h: { walk: Array(nb).fill(0), bike: Array(nb).fill(0), drive: Array(nb).fill(0), stop: Array(nb).fill(0) },
    swn: 0, sws: 0 };
  for (const [v, r, bus, sw] of list) {   // sw: the area's walk to the bus stop (D.commute.SW; cmSw)
    if (!v || !v[0] || !r) continue;
    const x = r / v[0];   // students per census resident of the area
    o.r += r; o.beyond += r * v[1]; o.wmi += r * v[2]; o.wmin += r * v[3]; o.bmin += r * v[4]; o.dmin += r * v[5];
    o.w15 += r * v[6]; o.b15 += r * v[7]; o.d15 += r * v[8]; o.near += r * v[9];
    ['walk', 'bike', 'drive'].forEach((m, j) => v[10 + j].forEach((y, i) => { o.h[m][i] += y * x; }));
    if (bus && v[13] != null) { o.bm += v[13] * x; o.be8 += r * v[1]; (v[14] || []).forEach((y, i) => { o.bh[i] += y * x; }); }
    if (bus && sw && sw[0] && typeof cmSw === 'function') cmSw(o, sw, r * v[1]);
  }
  if (o.r) for (const f of ['wmi', 'wmin', 'bmin', 'dmin', 'w15', 'b15', 'd15', 'near']) o[f] /= o.r;
  // bus ride: walking miles x ride-to-walk ratio x minutes per bus-mile (as cmAgg)
  const K = (D.buscost?.ratio || 0) * (D.buscost?.min_per_mile || 0), E = D.commute.hist_min, BM = D.commute.bh_mi;
  o.h.bus = Array(E.length + 1).fill(0);
  o.bh.forEach((y, i) => {
    if (!y) return;
    const mi = i === 0 ? BM[0] / 2 : i < BM.length ? (BM[i - 1] + BM[i]) / 2 : BM[BM.length - 1] + 0.5;
    o.h.bus[E.filter(e => e <= mi * K).length] += y;
  });
  o.busmin = o.be8 ? o.bm * K / o.be8 : 0;
  o.swmin = o.swn ? o.sws / o.swn : 0;
  return o;
}
let RP_ROWS = [];   // the report's getting-to-school rows, for the detail pane (cmOpenPane)
function rpTravRow(label, c, q, hs, sc) {
  if (!c || !c.r) return '';
  const ri = RP_ROWS.push({ label: label.replace(/<[^>]+>/g, '').replace(/&rarr;/g, '\u2192').replace(/&amp;/g, '&').trim(), c, q: q || null,
    scLabel: sc ? LABEL[sc] : 'Status Quo', year: rpYear, bandLabel: hs ? 'grades 9-12' : 'grades K-8' }) - 1;
  const keep = cmBand; cmBand = hs ? '912' : 'all';
  try {
    const n0 = v => Math.round(v).toLocaleString();
    const dm = (a, b, u = '') => { if (b == null) return ''; const d = Math.round(a - b);
      return ` <span class="muted">(${d > 0 ? '+' : d < 0 ? '&minus;' : '&plusmn;'}${Math.abs(d).toLocaleString()}${u})</span>`; };
    const cell = (m, mean, qm) => {
      const h = cmHist(c, q, m).replace(/^<td[^>]*>/, '').replace(/<\/td>$/, '');
      const noBus = (m === 'bus' || m === 'stop') && (hs || !c.be8);
      return `<td class="rph${noBus ? '' : ' go'}"${noBus ? '' : ` data-rr="${ri}" data-m="${m}" tabindex="0" role="button" title="Show ${m} times in detail"`}>${noBus ? '' : `<span class="main">${Math.round(mean)} min</span>${q && !((m === 'bus' || m === 'stop') && !q.be8) ? dm(mean, qm) : ''}<br>`}${h}</td>`;
    };
    return `<tr><td>${label}</td><td><span class="main">${n0(c.r)}</span></td>` +
      `<td><span class="main">${n0(c.beyond)}</span> <span class="muted">${Math.round(100 * c.beyond / Math.max(1, c.r))}%</span>${q ? dm(c.beyond, q.beyond) : ''}</td>` +
      cell('walk', c.wmin, q?.wmin) + cell('bike', c.bmin, q?.bmin) + cell('drive', c.dmin, q?.dmin) + cell('bus', c.busmin, q?.busmin) + (D.commute.SW ? cell('stop', c.swmin, q?.swmin) : '') + '</tr>';
  } finally { cmBand = keep; }
}
function rpTravel(k, sc) {
  return cmAtYear(rpYear, () => {
    const base = rpBase(sc), d1 = (D.detail[sc] || {})[k] || {}, hs = D.types.SQ[k] === 'HS', nm = esc(rpName(k));
    const vec = (s, kk, b) => { const v = D.commute.S[s]?.[kk]?.[b]; return v ? [...v, D.buscost?.M?.[s]?.[kk]?.[b] ?? null, D.commute.BH?.[s]?.[kk]?.[b] || null] : null; };
    const swS = (s, kk, b) => D.commute.SW?.S?.[s]?.[kk]?.[b], swR = (kk, b, t) => D.commute.SW?.R?.[base]?.[kk]?.[b]?.[t];
    const NC = D.commute.SW ? 8 : 7;   // columns
    RP_ROWS = [];
    let h = `<style>.rptrav td.rph.go { cursor: pointer; } .rptrav td.rph.go:hover svg, .rptrav td.rph.go:focus-visible svg { outline: 2px solid var(--change); outline-offset: 2px; border-radius: 3px; } .rptrav td { vertical-align: top; } .rptrav td.rph { min-width: 128px; } .rptrav td.rph svg { display: block; margin-top: 2px; } .rptrav tr.rpsub td { background: var(--surface-2); font-size: 12px; color: var(--text-secondary); }</style>` +
      `<div class="tablewrap"><table class="rptable rptrav"><thead><tr><th></th><th>Students</th><th>Eligible for bus service</th><th>Walk</th><th>Bike</th><th>Drive</th><th>${D.commute.SW ? 'On the bus' : 'Bus'}${hs ? '' : ' (eligible K-8)'}</th>${D.commute.SW ? `<th>Walk to bus stop${hs ? '' : ' (eligible K-8)'}</th>` : ''}</tr></thead><tbody>`;
    if (!d1.closed) {
      const c = cmAgg(sc, [k], 'all'), q = sc === 'SQ' ? null : cmAgg('SQ', [k], 'all');
      if (c.r) h += rpTravRow(`${nm} students${sc === 'SQ' ? '' : `, ${esc(LABEL[sc])}`}`, c, q, hs, sc);
    }
    // areas the scenario takes away from this school, by the school each block is newly assigned to
    const R = base === 'SQ' ? null : D.commute.R?.[base]?.[k];
    let shown = false;
    if (R) for (const [b, to] of Object.entries(R)) {
      const n = cmStu('SQ', k, b), tot = Object.values(to).reduce((a, v) => a + v[0], 0);
      if (!n || !tot) continue;
      const bus = b !== '912', q = rpAggV([[vec('SQ', k, b), n, bus, swS('SQ', k, b)]]);
      h += `<tr class="rpsub"><td colspan="${NC}">${d1.closed ? `${nm} closes in ${esc(LABEL[base])}` : `${nm}'s ${RP_BL[b]} grades move in ${esc(LABEL[base])}`}: ` +
        `its ${RP_BL[b]} students' area by newly assigned school (Status Quo enrollment; outline and changes: their Status Quo trip to ${nm})</td></tr>`;
      h += rpTravRow(`All ${RP_BL[b]} students from ${nm}'s area`, rpAggV(Object.entries(to).map(([t, v]) => [v, n * v[0] / tot, bus, swR(k, b, t)])), q, !bus, base);
      for (const [t, v] of Object.entries(to).sort((x, y) => y[1][0] - x[1][0]))
        h += rpTravRow(`&rarr; ${rpLink(t, esc(rpName(t)))} <span class="muted">${Math.round(100 * v[0] / tot)}% of the area</span>`, rpAggV([[v, n * v[0] / tot, bus, swR(k, b, t)]]), q, !bus, base);
      shown = true;
    }
    if (d1.closed && !shown) h += `<tr><td colspan="${NC}" class="muted">${nm} closes in this custom scenario; see the getting-to-school table for its students' travel to their receiving schools.</td></tr>`;
    return h + `</tbody></table></div><p class="muted rpnote">Click a chart for the detailed graph and statistics. Bars: ${esc(LABEL[sc])}; outline: Status Quo. Shaded bars are trips of 15 minutes or less. Students eligible for bus service: K-5 more than 1 mile, 6-12 more than 1.5 miles of walking. ${D.commute.SW ? 'On the bus' : 'Bus'}: eligible K-8 students' time on the bus, stop to school (walking miles &times; ${(D.buscost?.ratio || 0).toFixed(1)} &times; ${(D.buscost?.min_per_mile || 0).toFixed(1)} min per bus-mile).${D.commute.SW ? ' Walk to bus stop: their walk from home to the nearest stop on their school&rsquo;s candidate bus routes; waiting at the stop is not included.' : ''} High school students get TriMet passes.</p>`;
  });
}
addEventListener('click', e => {
  const td = e.target.closest('.rptrav td.rph.go'); if (!td || e.target.closest('a')) return;
  const r = RP_ROWS[+td.dataset.rr]; if (r) cmOpenPane(r, td.dataset.m);
});
addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const td = e.target.closest?.('.rptrav td.rph.go'); if (!td) return;
  e.preventDefault(); const r = RP_ROWS[+td.dataset.rr]; if (r) cmOpenPane(r, td.dataset.m);
});
function rpCosts(k, sc) {
  const c = (D.costs || {})[k], l = (D.land || {})[k], closed = (D.detail[sc] || {})[k]?.closed, bd = D.bond?.schools?.[k];
  if (!c && !l && !bd) return '<p class="muted">No cost estimate for this school.</p>';
  const v = x => x == null ? '&mdash;' : usdM(x);
  // bond capital: projects PPS's bond reports assign to this school (paid of allocated) and scheduled bond work
  let bond = '';
  if (bd && typeof bondUSD === 'function') {
    const ds = bd.dollars || [], ws = bd.work || [], open = ws.filter(w => w.status !== 'complete');
    const tb = ds.reduce((a, d) => a + d.budget, 0), tp = ds.reduce((a, d) => a + d.paid, 0);
    bond = `<h4>Bond capital</h4>` + (ds.length ? `<table class="rptable"><tbody>` +
      `<tr class="tot"><td>School-specific bond projects</td><td>${bondUSD(tp)} paid of ${bondUSD(tb)}</td></tr>` +
      ds.map(d => `<tr><td>&nbsp;&nbsp;${esc(d.bond)} bond: ${esc(d.project)}</td><td>${bondUSD(d.paid)} of ${bondUSD(d.budget)}${d.encumbered >= 5e4 ? ` <span class="muted">(${bondUSD(d.encumbered)} committed)</span>` : ''}</td></tr>`).join('') +
      `</tbody></table>` : '') +
      (ws.length ? `<ul class="rplist">${ws.map(w => `<li><b>${esc(w.scope)}</b>: ${w.status === 'complete' ? `complete ${bondMon(w.finish)}` :
        `${esc(w.status)}${w.construction ? `; construction ${bondMon(w.construction[0])} to ${bondMon(w.construction[1])}` : ''}; completes ${bondMon(w.finish)}`}</li>`).join('')}</ul>` : '') +
      (closed && open.length ? `<p class="rpline"><span class="stag closes">closes in ${esc(LABEL[sc])}</span> bond work not yet complete here could be avoided or redirected</p>` : '') +
      `<p class="muted rpnote">PPS bond reports, as of ${bondMon(D.bond.as_of)} (dollars) and ${bondMon(D.bond.schedule_as_of)} (schedule). Roofs, seismic, accessibility and mechanical work paid from district-wide pools are not reported by school, so only school-specific projects carry dollars.</p>`;
  }
  return (closed ? `<p class="rpline"><span class="stag closes">closes in ${esc(LABEL[sc])}</span> these costs are avoided</p>` : '') +
    (c || l ? `<table class="rptable"><tbody>` +
    (c ? `<tr class="tot"><td>Outstanding repairs</td><td>${v(c.mf)}</td></tr><tr><td>&nbsp;&nbsp;Deferred maintenance (2021 FCI ${c.fci ?? 'n/a'})</td><td>${v(c.dm)}</td></tr>` +
      `<tr><td>&nbsp;&nbsp;Seismic retrofit${c.urm ? ` (URM part ${usdM(c.urm)})` : ''}</td><td>${v(c.se)}</td></tr>` +
      `<tr><td>Building area</td><td>${c.sf ? c.sf.toLocaleString() + ' sq ft' : '&mdash;'}</td></tr>` +
      `<tr><td class="muted">Replacement value, for reference (not a cost)</td><td class="muted">${v(c.mod)}</td></tr>` : '') +
    (l ? `<tr><td>Assessor land value (2025 roll)</td><td>${usdM(l.land)}</td></tr><tr><td>&nbsp;&nbsp;Land + buildings</td><td>${usdM(l.land + l.imp)}</td></tr>` : '') +
    `</tbody></table><p class="muted rpnote">2026 dollars. Outstanding repairs = deferred maintenance + remaining seismic retrofit (2021 Long-Range Facility Plan; bond work since 2021 is not subtracted). Replacement value is what a new building would cost, shown for reference only (see Method).</p>` : '') + bond;
}

// boundary map: Status Quo area outlined, scenario area filled, changing parts in gold
function rpDrawMap(k, sc) {
  const el = document.getElementById('rpmap'); if (!el) return '';
  if (!rpMap) {
    rpMap = L.map(el, { scrollWheelZoom: false, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(rpMap);
    rpLayer = L.layerGroup().addTo(rpMap);
    // maximize: the map's panel (map, controls and notes) fills the window; Esc or the button restores it
    const Max = L.Control.extend({ options: { position: 'topright' }, onAdd() {
      const a = L.DomUtil.create('a', 'leaflet-bar rpmaxbtn'); a.href = '#'; a.setAttribute('role', 'button');
      L.DomEvent.on(a, 'click', e => { L.DomEvent.preventDefault(e); L.DomEvent.stopPropagation(e); rpMaximize(!rpMax); });
      return a; } });
    new Max().addTo(rpMap);
    rpMaximize(rpMax, true);
  }
  if (!rpMap._loaded) rpMap.setView(ll(byKey[k]), 13);   // a view before adding layers (permanent labels need one)
  rpLayer.clearLayers();
  const base = rpBase(sc).toLowerCase(), t0 = D.types.SQ[k], t1 = (D.types[sc] || {})[k] || t0, closed = (D.detail[sc] || {})[k]?.closed;
  const bands = [...new Set([...(RP_BANDS[t0] || []), ...(RP_BANDS[t1] || [])])];
  const all = [], notes = []; let jn = false, lv = false;
  const draw = (g, style) => { const lyr = L.geoJSON(g, { interactive: false, style }).addTo(rpLayer); all.push(lyr.getBounds()); };
  for (const b of bands) {
    const S = D.bounds['sq_' + b], B = D.bounds[base + '_' + b];
    if (S && S.akeys) S.areas.forEach(([lab, g], i) => { if (S.akeys[i] === k) draw(g, { color: '#33312c', weight: 2, dashArray: '6 4', fill: false }); });
    if (sc !== 'SQ' && !closed && B && B.akeys) B.areas.forEach(([lab, g], i) => { if (B.akeys[i] === k) draw(g, { stroke: false, fillColor: css('--change'), fillOpacity: .22 }); });
    if (sc === 'SQ' && S && S.akeys) S.areas.forEach(([lab, g], i) => { if (S.akeys[i] === k) draw(g, { stroke: false, fillColor: css('--change'), fillOpacity: .18 }); });
    if (sc !== 'SQ' && B && B.ckeys) B.ckeys.forEach(([f, t], i) => {
      if (f !== k && t !== k) return;
      if (f === k) lv = true; else jn = true;
      draw(B.changed[i][2], { stroke: false, fillColor: f === k ? '#d6452c' : '#1f9d47', fillOpacity: .55 });
      notes.push(`${RP_BL[b]}: ${f === k ? `part moves to ${rpLink(t)}` : `part of ${rpLink(f)} joins`}`);
    });
  }
  const s = byKey[k];
  // the other schools involved: where a closing school's area goes (with residents of the grades' ages), and the
  // schools a boundary change takes area to or brings it from
  const rel = new Map();
  const addRel = (key, kind, note) => { if (!key || key === k || !byKey[key]) return; const r = rel.get(key) || { to: false, from: false, notes: [] };
    r[kind] = true; if (note && !r.notes.includes(note)) r.notes.push(note); rel.set(key, r); };
  if (sc !== 'SQ') {
    for (const b of bands) { const B = D.bounds[base + '_' + b]; if (B && B.ckeys) B.ckeys.forEach(([f, t]) => { if (f === k) addRel(t, 'to', `${RP_BL[b]}: takes part of this area`); if (t === k) addRel(f, 'from', `${RP_BL[b]}: gives part of its area to this school`); }); }
    const RR = D.commute?.R?.[rpBase(sc)]?.[k];
    if (RR) for (const [b, m] of Object.entries(RR)) for (const [to, v] of Object.entries(m)) addRel(to, 'to', `${RP_BL[b] || b}: about ${Math.round(v[0]).toLocaleString()} school-age residents of this area`);
  }
  for (const [key, r] of rel) {
    const p = ll(byKey[key]), to = r.to;
    L.circleMarker(p, { radius: 7, color: '#fff', weight: 2, fillColor: to ? '#1f9d47' : '#7c5cbf', fillOpacity: 1 })
      .bindTooltip(`<b>${esc(rpName(key))}</b>${closed ? ' (new school)' : to ? ' (gains area)' : ' (gives area)'}`, { direction: 'top', offset: [0, -6], className: 'rpmlabel' })   // hover only; the school itself is labelled
      .bindPopup(`<b>${esc(rpTitle(byKey[key]))}</b><br>${r.notes.map(esc).join('<br>')}<br><a href="${esc(rpHref(key))}" class="rplink" data-k="${esc(key)}">Open its report</a>`)
      .on('popupopen', e => { const a = e.popup.getElement()?.querySelector('a.rplink'); if (a) a.onclick = ev => { ev.preventDefault(); rpOpen(key); }; })
      .addTo(rpLayer);
    all.push(L.latLngBounds([p, p]));
  }
  const busNote = (rel.size ? `<div class="rplegend">${[...rel.values()].some(r => r.to) ? `<span><i class="k" style="width:10px;height:10px;border:0;border-radius:50%;background:#1f9d47;vertical-align:-1px"></i>${closed ? 'new school for this area' : 'school gaining part of this area'}</span>` : ''}` +
      `${[...rel.values()].some(r => r.from && !r.to) ? '<span><i class="k" style="width:10px;height:10px;border:0;border-radius:50%;background:#7c5cbf;vertical-align:-1px"></i>school giving area to this one</span>' : ''}<span class="muted">hover a marker for its name, click for details</span></div>` : '') +
    rpCorrLayer(k, sc, closed, all) + rpBusLayer(k, sc, bands, closed, all);
  L.circleMarker(ll(s), { radius: 7, color: '#fff', weight: 2, fillColor: closed ? css('--close') : css('--change'), fillOpacity: 1, interactive: false })
    .bindTooltip(`${esc(rpName(k))}${closed ? ` (closes in ${esc(LABEL[sc])})` : ''}`, { permanent: true, direction: 'top', offset: [0, -7], className: 'rpmlabel rpmself' }).addTo(rpLayer);
  setTimeout(() => {
    rpMap.invalidateSize();
    if (all.length) { const bb = all.reduce((a, b) => a.extend(b), L.latLngBounds(all[0].getSouthWest(), all[0].getNorthEast())); rpMap.fitBounds(bb, { padding: [12, 12] }); }
    else rpMap.setView(ll(s), 14);
  }, 50);
  return (all.length ? '' : '<p class="muted">No neighborhood attendance area for this school (focus option or program school).</p>') +
    `<div class="rplegend"><span><i class="k sqa"></i>Status Quo area</span>${sc !== 'SQ' && !closed ? `<span><i class="k sca"></i>${esc(LABEL[sc])} area</span>` : ''}${jn ? '<span><i class="k jn"></i>area joining this school</span>' : ''}${lv ? '<span><i class="k lv"></i>area leaving this school</span>' : ''}</div>` +
    (notes.length ? `<p class="muted rpnote">Joining and leaving areas are drawn on top of the other shading and overlap it: an area joining this school lies inside its ${esc(LABEL[sc])} area, and an area leaving it lies inside its Status Quo area (dashed outline).</p>` : '') +
    (notes.length ? `<ul class="rplist">${notes.map(n => `<li>${n}</li>`).join('')}</ul>` : '') + busNote;
}

// bus routes on the report map (D.busmap): PPS's current posted morning runs to this school, and this page's simulated
// candidate runs (scripts/build_bus_routes.py) for the scenario's base (Status Quo, A or B). For a school the scenario
// closes: the simulated runs that pick up in its Status Quo attendance area, to the schools its students go to.
// defaults: bike corridors and projected (simulated) bus routes on, current bus routes off (remembered as rsRpBus2)
let rpBus = { cur: false, sim: true, corr: 'bike' };
try { const v = JSON.parse(localStorage.getItem('rsRpBus2') || 'null'); if (v) rpBus = v; } catch (e) {}
function rpBusToggle(which, on) {
  rpBus[which] = on; try { localStorage.setItem('rsRpBus2', JSON.stringify(rpBus)); } catch (e) {}
  const n = document.getElementById('rpmapnote'); if (n && rpKey) n.innerHTML = rpDrawMap(rpKey, scen);
}
// programs and designations under the school's name (D.progs, scripts/patch_programs.py): immersion, Title I and ODE
// status, SUN Community School, special education staff; and what the scenario being viewed changes
function rpDesig(k, sc) {
  const P = D.progs?.sch?.[k]; if (!P) return '';
  const chip = (txt, tip, cls = '') => `<span class="rpchip${cls ? ' ' + cls : ''}"${tip ? ` title="${esc(tip)}"` : ''}>${txt}</span>`;
  const chips = [];
  const tot = P.total || D.series.SQ[k]?.[0];
  for (const [p, n] of Object.entries(P.dli || {})) chips.push(chip(`${esc(p.replace('Immersion', 'immersion (DLI)'))} <span class="muted">${n}${tot ? ` of ${tot}` : ''} students</span>`, `2025-26 enrollment in the program (PPS 2026-27 Proposed Budget, Vol. 2)`));
  if (P.programs && !/Immersion/.test(P.programs)) chips.push(chip(esc(P.programs), 'School program (PPS budget)'));
  chips.push(P.title1 ? chip('Title I', `Title I school in 2026-27; ${P.dc_2425 ?? '?'}% of students qualified for free meals by Direct Certification in 2024-25. ${D.progs.rule}`, 'on')
                      : chip(`Not Title I <span class="muted">(${P.dc_2425 ?? '?'}% DC)</span>`, `${P.dc_2425 ?? '?'}% of students qualified for free meals by Direct Certification in 2024-25. ${D.progs.rule}`));
  if (P.ode) chips.push(chip(P.ode, P.ode === 'CSI' ? 'ODE Comprehensive Support and Improvement school' : 'ODE Targeted Support and Improvement school', 'on'));
  chips.push(P.sun ? chip('SUN Community School', 'Multnomah County SUN Community School site (contact list, August 2026)', 'on') : chip('Not a SUN school', 'Not on the Multnomah County SUN Community School list (August 2026)'));
  if (P.sped && (P.sped[0] || P.sped[1])) chips.push(chip(`Special education staff <span class="muted">${P.sped[0] || 0} licensed, ${P.sped[1] || 0} classified FTE</span>`,
    'Special education staff allocated centrally to this school, 2026-27 budget (PPS 2026-27 Proposed Budget, Vol. 2). PPS does not publish which schools host special education focus classrooms.'));
  const base = rpBase(sc), ch = sc === 'SQ' ? null : (D.progs.chg[base] || {})[k] || [];
  const t1 = sc === 'SQ' ? null : D.progs.t1?.[base]?.[k];
  return `<div class="rpdesig">${chips.join('')}</div>` + (ch == null ? '' : `<div class="rpdesig chg"><b>${esc(LABEL[sc])}:</b> ` +
    (ch.length ? ch.map(t => chip(esc(t), '', /no longer|closes|need a new/.test(t) ? 'loss' : /Receives|qualify/.test(t) ? 'gain' : '')).join('') : '<span class="muted">no change to immersion programs, Title I (est.), SUN or special education</span>') +
    (t1 && !ch.some(t => t.startsWith('Title I')) ? `<span class="muted" title="${esc(`Estimated: this school's 2024-25 Direct Certification share mixed with that of the closing schools whose students it receives (${t1[2].map(x => `${x[0]} about ${x[1]} students at ${x[2]}%`).join(', ')}).`)}"> Title I unchanged (est. ${t1[0]}% DC)</span>` : '') +
    (sc === 'C' ? `<span class="muted"> (shown for ${esc(LABEL[base])}, the custom scenario's starting point)</span>` : '') + '</div>');
}

// maximized report map (kept across re-renders of the report)
let rpMax = false;
function rpMaximize(on, quiet) {
  rpMax = on;
  const el = document.getElementById('rpmap'), panel = el?.closest('.rppanel'); if (!panel || !rpMap) return;
  panel.classList.toggle('rpmax', on); document.body.classList.toggle('rpmax-open', on);
  const b = el.querySelector('.rpmaxbtn');
  if (b) { b.innerHTML = on ? '&#x2715;' : '&#x26F6;'; b.title = on ? 'Restore the map (Esc)' : 'Maximize the map'; b.setAttribute('aria-label', b.title); }
  if (!quiet) { const c = rpMap.getCenter(), z = rpMap.getZoom(); setTimeout(() => { rpMap.invalidateSize(); rpMap.setView(c, on ? z + 1 : Math.max(z - 1, 10)); }, 60); }
  else setTimeout(() => rpMap && rpMap.invalidateSize(), 60);
}
if (typeof addEventListener === 'function') addEventListener('keydown', e => { if (e.key === 'Escape' && rpMax) rpMaximize(false); });

// trip corridors (D.corr, scripts/build_block_access.py): the streets the school's trips would use if every school-age
// resident of its attendance area went by bike (lowest-stress route) or by car (fastest), line width by share
function rpCorrToggle(v) {
  rpBus.corr = v; try { localStorage.setItem('rsRpBus2', JSON.stringify(rpBus)); } catch (e) {}
  const n = document.getElementById('rpmapnote'); if (n && rpKey) n.innerHTML = rpDrawMap(rpKey, scen);
}
// arterial hazard marker (bike and walk corridors): x = crossing a major arterial, f = a stretch along one
const RP_HZ_SVG = '<svg width="18" height="16" viewBox="0 0 18 16"><path d="M9 1 L17 15 L1 15 Z" fill="#f2b705" stroke="#5a3d00" stroke-width="1.3" stroke-linejoin="round"/><path d="M9 5.5 V10" stroke="#3a2a00" stroke-width="1.8" stroke-linecap="round"/><circle cx="9" cy="12.6" r="1" fill="#3a2a00"/></svg>';
const rpHzIcon = () => L.divIcon({ className: 'hzicon', iconSize: [18, 16], iconAnchor: [9, 9], html: RP_HZ_SVG });
function rpHazardText(h, mode, who) {
  const pct = Math.round(100 * h[3]), nm = esc(h[4] || 'a major arterial');
  return h[0] === 'x' ? `Crosses ${nm} (major arterial): ${pct}% of ${who} ${mode === 'bike' ? 'ride' : 'walk'} through here`
    : `Runs along ${nm} (major arterial) for about ${Math.round(h[5]).toLocaleString()} m${mode === 'bike' ? ' without a protected or buffered bike lane' : ''}: up to ${pct}% of ${who}`;
}
function rpCorrLayer(k, sc, closed, all) {
  const C = D.corr; if (!C) return '';
  const mode = rpBus.corr || '', gsc = ['SQ', 'A', 'B'].includes(rpBase(sc)) ? rpBase(sc) : 'SQ', lab = gsc === 'SQ' ? 'Status Quo' : LABEL[gsc];
  const sel = `<div class="rpbusctl"><label>Trip corridors <select onchange="rpCorrToggle(this.value)">` +
    [['', 'Off'], ['walk', 'On foot (shortest walk)'], ['bike', 'By bike (lowest-stress route)'], ['drive', 'By car (fastest route)']].map(([v, l]) => `<option value="${v}"${v === mode ? ' selected' : ''}>${l}</option>`).join('') + '</select></label></div>';
  if (!mode) return sel;
  const dec = p => { const out = []; let a = p[0], b = p[1]; out.push([a / 1e5, b / 1e5]); for (let i = 2; i < p.length; i += 2) { a += p[i]; b += p[i + 1]; out.push([a / 1e5, b / 1e5]); } return out; };
  const W = [2, 3.5, 5.5, 8], col0 = { walk: '#2563eb', bike: '#15803d', drive: '#b45309' }[mode];
  const verb = { walk: 'would walk', bike: 'would ride', drive: 'would be driven' }[mode], how = { walk: 'on foot', bike: 'by bike', drive: 'by car' }[mode];
  const draw = (r, col, tip) => r.L.forEach(([lv, p]) => L.polyline(dec(p), { color: col, weight: W[lv], opacity: .7, lineCap: 'round', className: 'rproute' }).bindTooltip(tip(lv), { sticky: true }).addTo(rpLayer));
  const hz = (r, who) => (r.H || []).forEach(h => L.marker([h[1], h[2]], { icon: rpHzIcon(), keyboard: false, zIndexOffset: 500 }).bindTooltip(rpHazardText(h, mode, who)).addTo(rpLayer));
  const hzLine = r => { if (!r.H) return ''; const nx = r.H.filter(h => h[0] === 'x').length, nf = r.H.length - nx;
    return ` <span class="hztxt"><span class="hzsym">&#9888;</span> ${Math.round(100 * r.hx)}% of them would cross or run along a major arterial (${nx} crossing${nx === 1 ? '' : 's'}, ${nf} stretch${nf === 1 ? '' : 'es'} along one).</span>`; };
  const lvTxt = lv => ['3-10%', '10-25%', '25-50%', '50%+'][lv];
  // named streets by role: bikeways (with facility), arterials / collectors, then the busiest local streets
  const FACN = { NG: 'neighborhood greenway', TRL: 'path', PBL: 'protected bike lane', SIR: 'separated bike lane', BBL: 'buffered bike lane', BBBL: 'buffered bike lane',
    SBBL: 'buffered bike lane', BL: 'bike lane', ABL: 'advisory bike lane', ESR: 'enhanced shared roadway', SHARED: 'shared-lane markings' };
  const li = (a, n, f) => a.slice(0, n).map(x => `${esc(x[0])} ${Math.round(100 * x[1])}%${f ? f(x) : ''}`).join(', ');
  const streets = st => {
    if (!st.length) return 'no single named street carries 5% or more.';
    const out = [];
    if (mode === 'bike') {
      const bw = st.filter(x => x[3]), art = st.filter(x => !x[3] && x[2] !== 'L'), loc = st.filter(x => !x[3] && x[2] === 'L');
      if (bw.length) out.push(`<b>bikeways</b> ${li(bw, 5, x => ` (${FACN[x[3]] || x[3]})`)}`);
      if (art.length) out.push(`<b>arterials and collectors without a bike facility</b> ${li(art, 4)}`);
      if (loc.length) out.push(`<b>local streets</b> ${li(loc, 3)}`);
    } else {
      const art = st.filter(x => x[2] === 'A'), col = st.filter(x => x[2] === 'C'), loc = st.filter(x => x[2] === 'L');
      if (art.length) out.push(`<b>arterials</b> ${li(art, 5)}`);
      if (col.length) out.push(`<b>collectors</b> ${li(col, 4)}`);
      if (loc.length) out.push(`<b>local streets</b> ${li(loc, 3)}`);
    }
    return out.join('; ') + '.';
  };
  let txt = '';
  if (!closed) {
    const r = C.S[mode]?.[gsc]?.[k] || C.S[mode]?.SQ?.[k];
    if (!r) return sel + '<p class="muted rpnote">No corridor data for this school (no neighborhood attendance area).</p>';
    draw(r, col0, lv => `${lvTxt(lv)} of the area's ${Math.round(r.w).toLocaleString()} school-age residents ${verb} along here`);
    hz(r, "the area's school-age residents");
    txt = `<b>Streets used ${how}, ${esc(lab)}</b> (share of the area's ${Math.round(r.w).toLocaleString()} school-age residents whose route uses each): ${streets(r.st)}${hzLine(r)}`;
  } else {
    const F = C.F[mode]?.[gsc]?.[k] || [];
    F.forEach(r => { const col = `hsl(${rpHue(r.to)} 60% 38%)`;
      draw(r, col, lv => `${lvTxt(lv)} of this area's residents going to ${esc(rpName(r.to))} would use this street`);
      hz(r, `this area's residents going to ${esc(rpName(r.to))}`);
      r.L.forEach(([, p]) => all.push(L.polyline(dec(p)).getBounds())); });
    txt = F.length ? `<b>From this area to its new schools ${how}, ${esc(lab)}:</b> ` + F.sort((a, b) => b.w - a.w).map(r => `to ${rpLink(r.to)} (${Math.round(r.w)} residents): ${streets(r.st)}${hzLine(r)}`).join(' ') : 'No corridor data for this area.';
  }
  const hzKey = mode === 'drive' ? '' : `<span><svg width="14" height="12" viewBox="0 0 18 16" style="vertical-align:-1px;margin-right:4px"><path d="M9 1 L17 15 L1 15 Z" fill="#f2b705" stroke="#5a3d00" stroke-width="1.3"/></svg>crosses or runs along a major arterial</span>`;
  return sel + `<div class="rplegend">${[0, 1, 2, 3].map(lv => `<span><i class="k" style="border-top:${W[lv]}px solid ${closed ? '#6b7280' : col0};width:18px"></i>${lvTxt(lv)}</span>`).join('')}${hzKey}</div>` +
    `<p class="rpnote">${txt}</p><p class="muted rpnote">Trip corridors: where trips would concentrate if every school-age resident of the attendance area (2020 Census, not enrolled students) made the trip ${mode === 'bike' ? 'by bike, on the lowest-stress route (bike paths, protected lanes and neighborhood greenways preferred, busy arterials avoided, hills penalised)' : mode === 'walk' ? 'on foot, by the shortest walking route' : 'by car, on the fastest route (free-flow, no traffic)'}; line width is the share of those residents using the street. Modelled, not counts of actual trips.` +
    (mode === 'drive' ? '' : ` Hazard markers: where these routes cross a major arterial (state highways and primary or secondary arterials) or run along one for 40 m or more${mode === 'bike' ? ' outside a path or a protected, separated or buffered bike lane (standard and advisory bike lanes count as hazards)' : ''}. Traffic signals and crosswalks are not known, so a signalized crossing is still marked.`) +
    `${closed ? ' Closed school: corridors from its Status Quo area to the schools its students go to, colored by school.' : ''}</p>`;
}
// is [lat, lng] inside a GeoJSON Polygon / MultiPolygon (or a Feature of one)?
function rpInGeom(lat, lng, g) {
  if (!g) return false;
  if (g.type === 'Feature') return rpInGeom(lat, lng, g.geometry);
  if (g.type === 'FeatureCollection') return g.features.some(f => rpInGeom(lat, lng, f));
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];
  const inRing = r => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, yi] = r[i], [xj, yj] = r[j];
    if ((yi > lat) !== (yj > lat) && lng < (xj - xi) * (lat - yi) / (yj - yi) + xi) c = !c; } return c; };
  return polys.some(p => inRing(p[0]) && !p.slice(1).some(inRing));
}
const rpHue = k => { let h = 0; for (const c of k) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
function rpBusLayer(k, sc, bands, closed, all) {
  const BM = D.busmap; if (!BM) return '';
  const dec = p => { const out = []; let a = p[0], b = p[1]; out.push([a / 1e5, b / 1e5]); for (let i = 2; i < p.length; i += 2) { a += p[i]; b += p[i + 1]; out.push([a / 1e5, b / 1e5]); } return out; };
  const gsc = ['SQ', 'A', 'B'].includes(rpBase(sc)) ? rpBase(sc) : 'SQ', G = BM.generated[gsc] || {};
  const simLab = gsc === 'SQ' ? 'Status Quo' : LABEL[gsc];
  const line = (run, sll, style, tip) => {
    const pts = run.s.map(p => [p[0], p[1]]);
    const lyr = L.polyline(run.p ? dec(run.p) : [...pts, sll], { ...style, className: 'rproute' }).bindTooltip(tip, { sticky: true }).addTo(rpLayer);
    for (const p of pts) L.circleMarker(p, { radius: 2.4, stroke: false, fillColor: style.color, fillOpacity: .9, interactive: false }).addTo(rpLayer);
    return lyr;
  };
  const cur = BM.posted[k] || [], parts = [];
  if (rpBus.cur) cur.forEach(r => line(r, BM.schools[k], { color: '#4b5563', weight: 2, opacity: .7, dashArray: '4 4' }, `Current PPS route to ${esc(rpName(k))}: ${r.s.length} stop${r.s.length === 1 ? '' : 's'}`));
  parts.push(`<b>Current:</b> ${cur.length ? `${cur.length} PPS morning run${cur.length === 1 ? '' : 's'}, ${cur.reduce((a, r) => a + r.s.length, 0)} stops` : 'no PPS yellow-bus runs posted for this school'}`);
  let simRuns = 0, simRiders = 0;
  const dests = new Map();
  if (!closed) {
    const rs = G[k] || [];
    simRuns = rs.length; simRiders = rs.reduce((a, r) => a + r.s.reduce((b, p) => b + (p[2] || 0), 0), 0);
    if (rpBus.sim) rs.forEach(r => line(r, BM.schools[k], { color: '#7c3aed', weight: 2.6, opacity: .8 }, `Simulated ${esc(simLab)} run to ${esc(rpName(k))}: ${r.s.length} stops, about ${Math.round(r.s.reduce((a, p) => a + (p[2] || 0), 0))} riders`));
    parts.push(`<b>Simulated, ${esc(simLab)}:</b> ${simRuns ? `${simRuns} run${simRuns === 1 ? '' : 's'}, about ${Math.round(simRiders)} riders` : 'no runs (few or no students beyond walking distance)'}`);
  } else {
    // runs in the scenario that pick up inside this school's Status Quo area go to the schools its students now attend
    const geoms = [];
    for (const b of bands) { const S = D.bounds['sq_' + b]; if (S && S.akeys) S.areas.forEach(([, g], i) => { if (S.akeys[i] === k) geoms.push(g); }); }
    // only runs to schools serving this school's grades in the scenario (a K-5's area also has middle school riders)
    const t0 = D.types.SQ[k], serves = to => { const t = (D.types[gsc] || {})[to] || D.types.SQ[to];
      return t0 === 'K8' || t === 'K8' || t === t0; };
    for (const [to, rs] of Object.entries(G)) for (const r of rs) {
      if (!serves(to)) continue;
      const inside = r.s.filter(p => geoms.some(g => rpInGeom(p[0], p[1], g)));
      if (!inside.length) continue;
      const d = dests.get(to) || { runs: 0, riders: 0 }; d.runs++; d.riders += inside.reduce((a, p) => a + (p[2] || 0), 0); dests.set(to, d);
      if (rpBus.sim) {
        const lyr = line(r, BM.schools[to], { color: `hsl(${rpHue(to)} 60% 40%)`, weight: 2.6, opacity: .8 }, `Simulated ${esc(simLab)} run to ${esc(rpName(to))}: picks up ${inside.length} of its ${r.s.length} stops in ${esc(rpName(k))}'s area`);
        all.push(lyr.getBounds());
      }
    }
    if (rpBus.sim) for (const to of dests.keys()) if (BM.schools[to])
      L.circleMarker(BM.schools[to], { radius: 6, color: '#fff', weight: 2, fillColor: `hsl(${rpHue(to)} 60% 35%)`, fillOpacity: 1 }).bindTooltip(`${esc(rpName(to))} (new school)`).addTo(rpLayer);
    parts.push(`<b>Simulated, ${esc(simLab)}:</b> ` + (dests.size ? [...dests].sort((a, b) => b[1].riders - a[1].riders).map(([to, d]) => `${d.runs} run${d.runs === 1 ? '' : 's'} to ${rpLink(to)} (about ${Math.round(d.riders)} rider${Math.round(d.riders) === 1 ? '' : 's'} from this area)`).join('; ') : 'no simulated runs pick up in this area'));
  }
  return `<div class="rpbusctl"><label><input type="checkbox" ${rpBus.cur ? 'checked' : ''} onchange="rpBusToggle('cur', this.checked)"> <i class="k bcur"></i>Current bus routes (PPS)</label>` +
    `<label><input type="checkbox" ${rpBus.sim ? 'checked' : ''} onchange="rpBusToggle('sim', this.checked)"> <i class="k bsim"></i>Simulated routes, ${esc(simLab)}${closed ? ' (to new schools)' : ''}</label></div>` +
    `<p class="rpnote">${parts.join('<br>')}</p>` +
    `<p class="muted rpnote"><b>Simulated, for illustration only.</b> The simulated routes are not PPS plans: this page generates candidate morning runs for ${esc(BM.year)} from projected enrollment to estimate bus costs (see Estimated yellow-bus cost). Current routes are PPS's posted morning runs (located stops only). Lines follow the shortest drive path between stops in pickup order and on to the school, not the exact bus path.${sc === 'C' ? ` Custom scenarios show their starting scenario's simulated routes (${esc(simLab)}).` : ''}${closed ? ` Closed school: the simulated runs shown are those that pick up inside its Status Quo attendance area, colored by the school they go to.` : ''}</p>`;
}

// school suggestions under the search box: the page's own list rather than a <datalist>, whose
// browser-drawn popup covers the keyboard on phones
function rpMatches(v) {
  v = v.trim().toLowerCase(); if (!v) return [];
  const out = [];
  for (const s of D.schools) {
    const names = [rpTitle(s), short(s.name), s.name].map(x => x.toLowerCase());
    const score = names.some(n => n.startsWith(v)) ? 0 : names.some(n => n.split(/[\s(]+/).some(w => w.startsWith(v))) ? 1 : names.some(n => n.includes(v)) ? 2 : -1;
    if (score >= 0) out.push([score, rpTitle(s), s.key]);
  }
  return out.sort((a, b) => a[0] - b[0] || a[1].localeCompare(b[1])).slice(0, 6);
}
function rpSuggest(box, pick) {
  box.removeAttribute('list'); document.getElementById('rplist')?.remove();
  const wrap = document.createElement('span'); wrap.className = 'rpfindwrap';
  box.before(wrap); wrap.append(box);
  const ul = document.createElement('ul'); ul.className = 'rpsuggest'; ul.id = 'rpsuggest'; ul.setAttribute('role', 'listbox'); ul.hidden = true;
  wrap.append(ul);
  box.setAttribute('role', 'combobox'); box.setAttribute('aria-controls', 'rpsuggest'); box.setAttribute('aria-autocomplete', 'list');
  let items = [], on = -1;
  const hide = () => { ul.hidden = true; box.setAttribute('aria-expanded', 'false'); on = -1; };
  const show = () => {
    items = rpMatches(box.value); on = -1;
    if (!items.length || (items.length === 1 && items[0][1] === box.value)) return hide();
    ul.innerHTML = items.map(([, t], i) => `<li role="option" data-i="${i}">${esc(t)}</li>`).join('');
    ul.hidden = false; box.setAttribute('aria-expanded', 'true');
  };
  const choose = i => { box.value = items[i][1]; hide(); pick(); };
  const mark = () => [...ul.children].forEach((li, i) => li.classList.toggle('on', i === on));
  box.addEventListener('input', show);
  box.addEventListener('blur', () => setTimeout(hide, 150));
  box.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (ul.hidden) show(); if (!items.length) return;
      e.preventDefault(); const n = items.length; on = e.key === 'ArrowDown' ? (on + 1 >= n ? -1 : on + 1) : (on < 0 ? n - 1 : on - 1); mark();
    } else if (e.key === 'Enter') {
      e.preventDefault(); if (!ul.hidden && on >= 0) choose(on); else { hide(); pick(); }
    } else if (e.key === 'Escape') hide();
  });
  // pointerdown keeps focus in the box, so the tap is not lost to blur
  ul.addEventListener('pointerdown', e => { e.preventDefault(); const li = e.target.closest('li'); if (li) choose(+li.dataset.i); });
  // on a phone, bring the box to the top of the screen so suggestions sit between it and the keyboard
  box.addEventListener('focus', () => { if (innerWidth < 700) setTimeout(() => box.scrollIntoView({ block: 'start', behavior: 'smooth' }), 300); });
}
function renderReport() {
  const el = document.getElementById('report'); if (!el) return;
  const sel = document.getElementById('rpyear');
  if (sel && !sel.options.length) {
    sel.innerHTML = D.years.map(y => `<option${y === rpYear ? ' selected' : ''}>${y}</option>`).join('');
    sel.onchange = () => { rpYear = sel.value; try { localStorage.setItem('rsReportYear', rpYear); } catch (e) {} renderReport(); };
  }
  const box = document.getElementById('rpfind');
  if (box && !box.onchange) {
    const pick = () => {
      const k = rpFindKey(box.value); if (!k) return;
      rpKey = k; box.value = rpTitle(byKey[k]);
      try { localStorage.setItem('rsReport', rpKey); } catch (e) {}
      renderReport();
    };
    box.onchange = pick; rpSuggest(box, pick);
    const clr = document.getElementById('rpclear');
    if (clr) {
      clr.onclick = () => { rpKey = null; box.value = ''; try { localStorage.removeItem('rsReport'); } catch (e) {} renderReport(); };
      if (!document.getElementById('rpcopy')) {   // "Copy link" beside Clear
        const b = document.createElement('button'); b.type = 'button'; b.id = 'rpcopy'; b.textContent = 'Copy link';
        const msg = document.createElement('span'); msg.id = 'rpcopied'; msg.className = 'muted';
        clr.after(b, msg);
      }
      document.getElementById('rpcopy').onclick = async () => {
        rpSyncUrl();
        const m = document.getElementById('rpcopied');
        try { await navigator.clipboard.writeText(location.href); m.textContent = 'Link copied'; setTimeout(() => { m.textContent = ''; }, 2500); }
        catch (e) { prompt('Copy this link:', location.href); }
      };
    }
  }
  if (!el.onclick) el.onclick = e => {   // school links inside the report
    const a = e.target.closest('a.rplink');
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button) return;
    e.preventDefault(); rpOpen(a.dataset.k);
  };
  const cp = document.getElementById('rpcopy'); if (cp) cp.disabled = !rpKey;
  rpSyncUrl();
  if (!rpKey) { el.innerHTML = '<p class="muted">Search for a school to see its report.</p>'; return; }
  const k = rpKey, s = byKey[k], sc = scen, rl = role(s, sc), t0 = D.types.SQ[k], t1 = (D.types[sc] || {})[k] || t0;
  if (box && !box.value) box.value = rpTitle(s);
  const yi = D.years.indexOf(rpYear), e0 = D.series.SQ[k][yi], e1 = (D.series[sc] || {})[k]?.[yi], d1 = (D.detail[sc] || {})[k] || {};
  const tag = { closes: 'Closes', receives: 'Receives students', other: 'Other change', none: sc === 'SQ' ? 'Status Quo' : 'No change' }[rl];
  const fl = rpFlow(k, sc);
  const thr = D.thresholds[t1], fc = s.fc;
  // columns: where students come from -> this school -> where they go next (if anywhere) -> high school (below HS)
  const nextCol = t0 === 'HS' || t0 === 'MS' ? fl.next : new Map([...fl.next].filter(([key]) => D.types.SQ[key] !== 'HS'));
  const highCol = t0 === 'HS' ? new Map() : fl.high;
  el.innerHTML =
    `<div class="rphead"><div><h3>${esc(rpTitle(s))}</h3><span class="muted">${esc(D.region_of[k] || s.region || '')} &middot; ${RP_TL[t0]}${t1 !== t0 ? ` &rarr; ${RP_TL[t1]} in ${esc(LABEL[sc])}` : ''}</span>${rpDesig(k, sc)}</div>` +
    `<span class="stag ${rl}">${tag}</span>${typeof adjMark === 'function' ? adjMark(k, sc) : ''}</div>` +
    `<div class="rpkpis"><div><b>${D.series.SQ[k][0] ?? '&mdash;'}</b><span>2025-26 enrollment</span></div>` +
    `<div><b>${e0 == null ? '&mdash;' : Math.round(e0)}</b><span>${rpYear} Status Quo</span></div>` +
    (sc === 'SQ' ? '' : `<div><b>${d1.closed ? 'closed' : e1 == null ? '&mdash;' : Math.round(e1)}${d1.closed ? '' : rpMark(k, sc)}</b><span>${rpYear} ${esc(LABEL[sc])}</span></div>`) +
    `<div><b>${fc ? fc.toLocaleString() : '&mdash;'}</b><span>2021 functional capacity${fc && e1 != null && !d1.closed ? ` (${Math.round(100 * e1 / fc)}% used)` : ''}</span></div>` +
    `<div><b>${thr}</b><span>size threshold (${RP_TL[t1]})${e1 != null && !d1.closed ? `: ${e1 >= thr ? 'above' : 'below'}` : ''}</span></div></div>` +
    `<div class="rpgrid">` +
    `<div class="rppanel rpwide"><h3>Where students come from and go</h3><div class="rpflow">` +
      `<div class="rpcol"><h4>Comes from</h4>${rpBoxes(fl.inn, sc)}</div><div class="rparrow">&rarr;</div>` +
      `<div class="rpcol"><h4>This school</h4><div class="rpbox self${d1.closed ? ' rem' : ''}"><b>${esc(short(s.name))}</b> <span class="n">${RP_TL[t1]}</span>${d1.closed ? '<span class="rpbadge rem">closes</span>' : ''}` +
        (fl.out.size ? `<span class="rpmoves"><span class="h">Some students move to another school:</span>${[...fl.out].map(([to, e]) => `<span class="mv"><b>&rarr; ${rpLink(to)}</b>${e.notes.map(n => `<span class="why">${esc(n)}</span>`).join('')}</span>`).join('')}</span>` : '') +
        `</div></div>` +
      (nextCol.size ? `<div class="rparrow">&rarr;</div><div class="rpcol"><h4>${d1.closed ? 'Students go to' : t0 === 'HS' ? 'Students go to' : 'Next school'}</h4>${rpBoxes(nextCol, sc)}</div>` : '') +
      (highCol.size ? `<div class="rparrow">&rarr;</div><div class="rpcol"><h4>High school</h4>${rpBoxes(highCol, sc)}</div>` : '') +
    `</div><p class="muted rpnote">${sc === 'SQ' ? 'Status Quo pathways.' : `Green: new in ${esc(LABEL[sc])}; struck through: no longer. Next school is where students normally go next (or, if the school closes, where its students go); students moved to another school at the same level are listed under This school with the mechanism: PPS boundary change, grade change, program move, receiving share, or the modified enrollment model's estimate.`}</p>${sc === 'SQ' ? '' : rpChanges(k, sc)}</div>` +
    rpSegc(k) +
    `<div class="rppanel"><h3>Building costs</h3>${rpCosts(k, sc)}</div>` +
    `<div class="rppanel"><h3>Attendance area</h3><div id="rpmap"></div><div id="rpmapnote"></div></div>` +
    `<div class="rppanel rpwide"><h3>Getting to school, ${rpYear}${sc === 'SQ' ? '' : `: ${esc(LABEL[sc])} and Status Quo`}</h3>${rpTravel(k, sc)}</div>` +
    `<div class="rppanel rpwide"><h3>Enrollment and capacity, ${D.years[0]} to ${D.years[D.years.length - 1]}: Status Quo and scenarios</h3>${rpPlot(k, sc)}${D.segc?.sch?.[k] ? `<p class="muted rpnote">This school changed in Southeast enrollment balancing Phase 2 (fall 2023; see the SEGC panel above). Boundary changes phase in with new kindergarten and 6th-grade students, so PSU's projection still carries part of the shift.</p>` : ''}${rpFcAcc(k)}</div>` +
    `<div class="rppanel rpwide"><h3>Staffing changes, ${rpYear}: Status Quo and scenarios</h3>${rpStaff(k, sc)}</div>` +
    `<div class="rppanel rpwide"><h3>Students by grade${rpMark(k, sc)}</h3>${rpGrades(k, sc)}</div>` +
    `</div>`;
  // the map element is new each render: rebuild the Leaflet map on it
  if (rpMap) { rpMap.remove(); rpMap = null; }
  document.getElementById('rpmapnote').innerHTML = rpDrawMap(k, sc);
  // opened from a shared link: bring the report into view once
  if (rpScroll) { rpScroll = false; setTimeout(() => document.getElementById('reportcard')?.scrollIntoView({ block: 'start' }), 300); }
}
