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
      if (r.to_key === k) rpAdd(inn, r.from_key, 'sc', `${det[r.from_key]?.closed ? 'closes; ' : ''}${r.group}${sh}`);
      if (r.from_key === k) {
        if (det[k]?.closed) rpAdd(next, r.to_key, 'sc', `closes; ${r.group}${sh}`);
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
function rpStaff(k, sc) {
  const yi = D.years.indexOf(rpYear), cols = rpCols(sc);
  const F = Object.fromEntries(cols.map(s => [s, (D.series[s] || {})[k] ? schoolFTE(k, s, yi) : null]));
  if (cols.every(s => !F[s])) return '<p class="muted">No staffing estimate for this school.</p>';
  const f = v => v == null ? '&mdash;' : (Math.round(v * 10) / 10).toFixed(1);
  const dl = (d, money) => Math.abs(d) < (money ? 5e4 : 0.05) ? '' : `<span class="sq">${money ? (d > 0 ? '+' : '') + staffUSD(d) : (d > 0 ? '+' : '&minus;') + Math.abs(d).toFixed(1)} vs SQ</span>`;
  const cell = (s, c) => {
    const r = F[s]; if (!r) return '<td class="muted">closed</td>';
    return `<td${s === sc ? ' class="cur"' : ''}>${f(r[c])}${s !== 'SQ' ? dl(r[c] - (F.SQ ? F.SQ[c] : 0)) : ''}</td>`;
  };
  const rows = STAFF_COLS.filter(([c]) => cols.some(s => F[s] && F[s][c])).map(([c, l]) =>
    `<tr${c === 'total' ? ' class="tot"' : ''}><td>${esc(l)}</td>${cols.map(s => cell(s, c)).join('')}</tr>`).join('');
  const cost = s => { const r = F[s]; if (!r) return '<td class="muted">closed</td>'; const v = staffCost(r);
    return `<td${s === sc ? ' class="cur"' : ''}>${staffUSD(v)}${s !== 'SQ' ? dl(v - (F.SQ ? staffCost(F.SQ) : 0), true) : ''}</td>`; };
  const P = Object.fromEntries(cols.map(s => [s, F[s] ? rpPat(k, s, yi) : null]));
  const pat = p => !p ? 'closed' : [p.h ? `${p.over} of ${p.h} K-5 classes over` : '', p.load68 ? `6-8 load ${Math.round(p.load68)} a day (limit ${PAT_MS})` : '',
    p.load912 ? `9-12 load ${Math.round(p.load912)} a day (limit ${PAT_HS})` : ''].filter(Boolean).join('; ') + `; <b>${p.extra.toFixed(1)}</b> more FTE to stay under`;
  const pg = P[sc] || P.SQ;
  const grade = !pg || !pg.grades.length ? '' : `<h4>K-5 classes, ${esc(LABEL[P[sc] ? sc : 'SQ'])}${rpMark(k, P[sc] ? sc : 'SQ')}</h4><table class="rptable sm"><thead><tr><th>Grade</th><th>Students</th><th>Homerooms</th><th>Largest class</th><th>PAT threshold</th><th>Over</th></tr></thead><tbody>` +
    pg.grades.map(g => `<tr><td>${g.g}</td><td>${g.n}</td><td>${g.h}</td><td>${g.max}</td><td>${g.thr}</td><td${g.over ? ' class="over"' : ''}>${g.over || ''}</td></tr>`).join('') + '</tbody></table>';
  return `<table class="rptable"><thead><tr><th>${rpYear}</th>${cols.map(s => `<th${s === sc ? ' class="cur"' : ''}>${esc(LABEL[s])}${rpMark(k, s)}</th>`).join('')}</tr></thead><tbody>${rows}` +
    `<tr><td>Staffing cost</td>${cols.map(cost).join('')}</tr></tbody></table>` +
    `<h4>Under the PAT thresholds (K over 24, grades 1-3 over 26, 4-5 over 28; 6-8 over ${PAT_MS} and 9-12 over ${PAT_HS} students a day)</h4>` +
    cols.map(s => `<p class="rpline${s === sc ? ' cur' : ''}">${esc(LABEL[s])}${rpMark(k, s)}: ${pat(P[s])}</p>`).join('') + grade +
    `<p class="muted rpnote">Budget formula FTE: PPS 2026-27 adopted staffing formula at its largest class sizes. "More FTE to stay under" adds the homeroom teachers needed to keep every K-5 class at or under its PAT threshold, and the 6-8 and 9-12 teachers needed to keep daily student loads at or under ${PAT_MS} and ${PAT_HS}.` +
    (cols.some(s => rpMark(k, s)) ? ' &#9670;: this scenario\'s enrollment for the school includes the modified enrollment model; hover it for the moves.' : '') + '</p>';
}
// costs and land
function rpCosts(k, sc) {
  const c = (D.costs || {})[k], l = (D.land || {})[k], closed = (D.detail[sc] || {})[k]?.closed;
  if (!c && !l) return '<p class="muted">No cost estimate for this school.</p>';
  const v = x => x == null ? '&mdash;' : usdM(x);
  return (closed ? `<p class="rpline"><span class="stag closes">closes in ${esc(LABEL[sc])}</span> these costs are avoided</p>` : '') +
    `<table class="rptable"><tbody>` +
    (c ? `<tr class="tot"><td>Must-fix</td><td>${v(c.mf)}</td></tr><tr><td>&nbsp;&nbsp;Deferred maintenance (2021 FCI ${c.fci ?? 'n/a'})</td><td>${v(c.dm)}</td></tr>` +
      `<tr><td>&nbsp;&nbsp;Seismic retrofit${c.urm ? ` (URM part ${usdM(c.urm)})` : ''}</td><td>${v(c.se)}</td></tr>` +
      `<tr class="tot"><td>Full modernization</td><td>${v(c.mod)}</td></tr><tr><td>&nbsp;&nbsp;Building area</td><td>${c.sf ? c.sf.toLocaleString() + ' sq ft' : '&mdash;'}</td></tr>` : '') +
    (l ? `<tr><td>Assessor land value (2025 roll)</td><td>${usdM(l.land)}</td></tr><tr><td>&nbsp;&nbsp;Land + buildings</td><td>${usdM(l.land + l.imp)}</td></tr>` : '') +
    `</tbody></table><p class="muted rpnote">2026 dollars. Must-fix = deferred maintenance + remaining seismic retrofit; full modernization = replacement value (see Method).</p>`;
}

// boundary map: Status Quo area outlined, scenario area filled, changing parts in gold
function rpDrawMap(k, sc) {
  const el = document.getElementById('rpmap'); if (!el) return '';
  if (!rpMap) {
    rpMap = L.map(el, { scrollWheelZoom: false, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(rpMap);
    rpLayer = L.layerGroup().addTo(rpMap);
  }
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
  L.circleMarker(ll(s), { radius: 6, color: '#fff', weight: 2, fillColor: closed ? css('--close') : css('--change'), fillOpacity: 1, interactive: false }).addTo(rpLayer);
  setTimeout(() => {
    rpMap.invalidateSize();
    if (all.length) { const bb = all.reduce((a, b) => a.extend(b), L.latLngBounds(all[0].getSouthWest(), all[0].getNorthEast())); rpMap.fitBounds(bb, { padding: [12, 12] }); }
    else rpMap.setView(ll(s), 14);
  }, 50);
  return (all.length ? '' : '<p class="muted">No neighborhood attendance area for this school (focus option or program school).</p>') +
    `<div class="rplegend"><span><i class="k sqa"></i>Status Quo area</span>${sc !== 'SQ' && !closed ? `<span><i class="k sca"></i>${esc(LABEL[sc])} area</span>` : ''}${jn ? '<span><i class="k jn"></i>area joining this school</span>' : ''}${lv ? '<span><i class="k lv"></i>area leaving this school</span>' : ''}</div>` +
    (notes.length ? `<p class="muted rpnote">Joining and leaving areas are drawn on top of the other shading and overlap it: an area joining this school lies inside its ${esc(LABEL[sc])} area, and an area leaving it lies inside its Status Quo area (dashed outline).</p>` : '') +
    (notes.length ? `<ul class="rplist">${notes.map(n => `<li>${n}</li>`).join('')}</ul>` : '');
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
    `<div class="rphead"><div><h3>${esc(rpTitle(s))}</h3><span class="muted">${esc(D.region_of[k] || s.region || '')} &middot; ${RP_TL[t0]}${t1 !== t0 ? ` &rarr; ${RP_TL[t1]} in ${esc(LABEL[sc])}` : ''}</span></div>` +
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
    `<div class="rppanel"><h3>Building costs</h3>${rpCosts(k, sc)}</div>` +
    `<div class="rppanel"><h3>Attendance area</h3><div id="rpmap"></div><div id="rpmapnote"></div></div>` +
    `<div class="rppanel rpwide"><h3>Enrollment and capacity, ${D.years[0]} to ${D.years[D.years.length - 1]}: Status Quo and scenarios</h3>${rpPlot(k, sc)}</div>` +
    `<div class="rppanel rpwide"><h3>Staffing changes, ${rpYear}: Status Quo and scenarios</h3>${rpStaff(k, sc)}</div>` +
    `<div class="rppanel rpwide"><h3>Students by grade${rpMark(k, sc)}</h3>${rpGrades(k, sc)}</div>` +
    `</div>`;
  // the map element is new each render: rebuild the Leaflet map on it
  if (rpMap) { rpMap.remove(); rpMap = null; }
  document.getElementById('rpmapnote').innerHTML = rpDrawMap(k, sc);
  // opened from a shared link: bring the report into view once
  if (rpScroll) { rpScroll = false; setTimeout(() => document.getElementById('reportcard')?.scrollIntoView({ block: 'start' }), 300); }
}
