"""A "Room to grow: capacity after the scenarios" section after "Scenario impact by region": how full the buildings that
stay open would be, and how large an enrollment they could hold.
  Capacity: each open school's 2021 functional capacity (PPS Long-Range Facility Plan; byKey .fc), K-8s split between
  K-5 and 6-8 by their K-5 share; the schools on this page (programs not on it, such as Benson and ACCESS, left out).
  Enrollment: this page's projection (with whichever enrollment switches are on), and, from the enrollment uncertainty
  section's district simulations, its 50% and 90% ranges (each band's simulated change applied to these schools).
  Threshold line: the sum of the size thresholds of the open schools (K-5 360, middle and K-8 500, high 1,100).
  Steady state: each kindergartner becomes about 12.9 K-12 students (PSU's medium grade progression ratios,
  2031-2040 averages: K-5 about 6.1, 6-8 2.8, 9-12 3.9); the largest district kindergarten class the buildings hold
  = capacity / those multipliers / these schools' share of the district's band (the binding band sets it).
  The scale converts kindergarten class sizes to a capture rate (PPS-area 5-year-olds: the county's projected
  5-year-olds x PPS's share, D.pfa) and to births a year at today's capture (fall 2025 kindergarten / 2020 births).
  Region table: capacity, enrollment, empty seats and percent full by band; each region opens to its schools.
Follows the scenario toggle (a custom scenario uses its own closures), the population switch and a year menu;
Link button. Code added once.
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

SECTION = '''  <section class="card" id="roomcard">
    <h2>Room to grow: capacity after the scenarios</h2>
    <p class="sub" id="roomsub"></p>
    <div class="controls"><label>Year <select id="room-year"></select></label></div>
    <div class="kpis" id="roomkpis"></div>
    <h3 class="cshead">Capacity and enrollment by grade band</h3>
    <div id="roomcharts" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px"></div>
    <div class="rplegend" id="roomlegend"></div>
    <h3 class="cshead">What would fill the buildings</h3>
    <div id="roomscale"></div>
    <h3 class="cshead">By region</h3>
    <div class="controls tabletools"><button id="room-expand">Expand all regions</button></div>
    <div class="tablewrap" id="roomtable"></div>
    <p class="muted" id="roomnote" style="font-size:12px"></p>
  </section>

  <section class="card">
    <h2>Small schools and staffing cost over time - How much does it cost to wait?</h2>'''

JS = r'''// ---------- room to grow: capacity after the scenarios (scripts/patch_room_to_grow.py) ----------
let roomYear = '2035-36';
const roomOpen = new Set();
const ROOM_B = [['k5', 'K-5'], ['m68', '6-8'], ['h912', '9-12']];
function roomSplit(k, s, yi, v) {   // a school's value split into grade bands by its type in that year
  const t = (yi < D.years.indexOf(D.impl_year) ? D.types.SQ[k] : D.types[s]?.[k]) || D.types.SQ[k], f = k5Of(k, D.years[yi]) ?? 0.66;
  return t === 'ES' ? { k5: v, m68: 0, h912: 0 } : t === 'MS' ? { k5: 0, m68: v, h912: 0 } : t === 'HS' ? { k5: 0, m68: 0, h912: v } : { k5: f * v, m68: (1 - f) * v, h912: 0 };
}
function roomAgg(s, yi, keys = Object.keys(D.region_of)) {   // capacity, enrollment, threshold sum by band for the open schools
  const o = { cap: { k5: 0, m68: 0, h912: 0 }, enr: { k5: 0, m68: 0, h912: 0 }, thr: { k5: 0, m68: 0, h912: 0 }, n: 0 };
  for (const k of keys) {
    const v = D.series[s]?.[k]?.[yi]; if (v == null) continue; o.n++;
    const t = (yi < D.years.indexOf(D.impl_year) ? D.types.SQ[k] : D.types[s]?.[k]) || D.types.SQ[k];
    for (const [x, val] of [['cap', byKey[k]?.fc || 0], ['enr', v], ['thr', D.thresholds[t] || 0]]) { const sp = roomSplit(k, s, yi, val); for (const b in sp) o[x][b] += sp[b]; }
  }
  return o;
}
let roomMultCache = null;
function roomMult() {   // students per kindergartner at steady state, from PSU's medium grade progression ratios (2031-2040)
  if (roomMultCache) return roomMultCache;
  const F = D.forecast52, GR = ['K', ...Array.from({ length: 12 }, (_, i) => String(i + 1))], i0 = F.years.indexOf('2031-32');
  const gpr = g => { let s = 0, n = 0; for (let j = i0; j < F.years.length; j++) { s += F.grades[GR[g]][j] / F.grades[GR[g - 1]][j - 1]; n++; } return s / n; };
  let c = 1; const ch = [1]; for (let g = 1; g <= 12; g++) { c *= gpr(g); ch.push(c); }
  const sum = (a, b) => ch.slice(a, b + 1).reduce((x, y) => x + y, 0);
  return roomMultCache = { k5: sum(0, 5), m68: sum(6, 8), h912: sum(9, 12) };
}
const roomDist = yi => {   // district band totals (all PPS) behind the page's projection in that year: [K, K-5, 6-8, 9-12]
  const f = 2025 + yi;
  if (pfaOn && D.mc?.medium_bands?.[yi]) return D.mc.medium_bands[yi];
  const P = D.mc?.psu, i = P ? P.falls.indexOf(f) : -1; return i < 0 ? null : [P.medium.K[i], P.medium['K-5'][i], P.medium['6-8'][i], P.medium['9-12'][i]];
};
function renderRoom() {
  const host = document.getElementById('roomkpis'); if (!host) return;
  const sc = scen, lab = sc === 'SQ' ? 'Status Quo' : LABEL[sc], yi = D.years.indexOf(roomYear), M = roomMult();
  const ys = document.getElementById('room-year');
  if (ys) { ys.innerHTML = D.years.map(y => `<option${y === roomYear ? ' selected' : ''}>${y}</option>`).join(''); ys.onchange = () => { roomYear = ys.value; renderRoom(); }; }
  const n0 = v => Math.round(v).toLocaleString(), pc = (a, b) => b ? Math.round(100 * a / b) + '%' : '&ndash;';
  const A = roomAgg(sc, yi), Q = roomAgg('SQ', yi), dist = roomDist(yi);
  const tot = o => o.k5 + o.m68 + o.h912;
  // the largest district kindergarten class the open buildings hold at steady state, by band
  const share = b => dist ? A.enr[b] / dist[{ k5: 1, m68: 2, h912: 3 }[b]] : 1;
  const kmax = Object.fromEntries(ROOM_B.map(([b]) => [b, A.cap[b] / M[b] / share(b)])), kthr = Object.fromEntries(ROOM_B.map(([b]) => [b, A.thr[b] / M[b] / share(b)]));
  const bind = ROOM_B.reduce((a, [b]) => kmax[b] < kmax[a] ? b : a, 'k5'), Kmax = kmax[bind], Kthr = Math.max(...Object.values(kthr));
  const Kproj = dist ? dist[0] : null;
  const fy = String(2025 + yi) + '-' + String((2026 + yi) % 100).padStart(2, '0'), capt = D.pfa ? D.pfa.capture : null;
  const age5 = D.pfa?.k_pfa?.[fy] && capt ? D.pfa.k_pfa[fy] / capt : (D.pfa?.k_pfa && capt ? Object.values(D.pfa.k_pfa).slice(-1)[0] / capt : null);
  const capNow = 2919 / 4121;   // fall 2025 kindergarten / 2020 births to PPS-area residents
  // steady state: the long-run kindergarten class (2031-35 average of the projection) x students per kindergartner
  const Klr = D.mc?.medium_bands ? D.mc.medium_bands.slice(6, 11).reduce((a, r) => a + r[0], 0) / 5 : 2700;
  const Mt = M.k5 + M.m68 + M.h912, ssK12 = Klr * Mt, H = D.mc?.hist, now = H ? H.bands['K-5'].slice(-1)[0] + H.bands['6-8'].slice(-1)[0] + H.bands['9-12'].slice(-1)[0] : 42622;
  const ssFill = ROOM_B.reduce((a, [b]) => a + Klr * M[b] * share(b), 0);   // the page's share of that steady state
  host.innerHTML =
    `<div class="kpi"><div class="v">${n0(ssK12)}<span class="d" style="color:var(--text-muted)">students</span><span class="vt">Steady state: about ${n0(Math.round(Klr / 100) * 100)} kindergartners a year</span></div><div class="l">District-wide K-12 (all PPS) once every grade is that size (${Mt.toFixed(1)} students per kindergartner): ${Math.round(100 * (ssK12 / now - 1))}% from ${n0(now)} in fall 2025, about 13 years after kindergarten levels off (mid-2040s). The open buildings would be ${pc(ssFill, tot(A.cap))} full.</div></div>` +
    `<div class="kpi"><div class="v">${pc(tot(A.enr), tot(A.cap))}<span class="d" style="color:var(--text-muted)">full</span><span class="vt">Buildings left: ${n0(tot(A.cap))} seats</span></div><div class="l">${A.n} schools open, ${esc(lab)}, ${roomYear}${sc !== 'SQ' ? ` (Status Quo: ${Q.n} schools, ${n0(tot(Q.cap))} seats, ${pc(tot(Q.enr), tot(Q.cap))} full)` : ''}</div></div>` +
    `<div class="kpi"><div class="v">${n0(tot(A.cap) - tot(A.enr))}<span class="vt">Empty seats</span></div><div class="l">${ROOM_B.map(([b, l]) => `${l} ${n0(A.cap[b] - A.enr[b])}`).join(' &middot; ')}</div></div>` +
    `<div class="kpi"><div class="v">${n0(Kmax)}<span class="d" style="color:var(--text-muted)">a year</span><span class="vt">Largest kindergarten the buildings could hold</span></div><div class="l">At steady state; limited by ${ROOM_B.find(x => x[0] === bind)[1]}${Kproj ? `; projected ${n0(Kproj)} (${Kmax > Kproj ? '+' : ''}${Math.round(100 * (Kmax / Kproj - 1))}%)` : ''}</div></div>` +
    `<div class="kpi"><div class="v">${n0(Kmax / capNow)}<span class="d" style="color:var(--text-muted)">births a year</span><span class="vt">What it would take to fill them</span></div><div class="l">At today's kindergarten capture (2025: about 3,650 births; 2008 peak 5,802)${age5 ? `; or ${Math.round(100 * Kmax / age5)}% of the district's 5-year-olds (today about 75%)` : ''}</div></div>`;
  document.getElementById('roomsub').innerHTML = `How full the buildings that stay open would be, and how large an enrollment they could hold. Capacity is each school's 2021 functional capacity (PPS Long-Range Facility Plan) for the schools on this page; enrollment is this page's projection${pfaOn ? ' (district share of county population, PFA study)' : ' (PSU’s May 2026 forecast)'}${D.mc ? ', with the 50% and 90% ranges from the enrollment uncertainty section' : ''}. Follows the scenario buttons; ${esc(lab)} shown.`;
  // band charts
  const F = D.years.map((_, i) => 2025 + i), sims = D.mc?.variants?.district?.bands, ones = sims ? sims.map(() => 1) : null;
  const PE = F.map((_, j) => roomAgg(sc, j).enr);   // this page's enrollment by band, each year
  const ranges = b => !sims ? null : F.map((f, j) => {   // each band's simulated change applied to this page's schools
    const idx = { k5: 1, m68: 2, h912: 3 }, base = D.mc.medium_bands[j];
    const vals = sims.map(sm => b === 'all' ? ROOM_B.reduce((a, [x]) => a + PE[j][x] * sm[j][idx[x]] / base[idx[x]], 0) : PE[j][b] * sm[j][idx[b]] / base[idx[b]]);
    return mcQ(vals, ones, [0.05, 0.25, 0.5, 0.75, 0.95]);
  });
  const chart = (b, title) => {
    const capS = F.map((_, j) => { const o = roomAgg(sc, j); return b === 'all' ? tot(o.cap) : o.cap[b]; }), capQ = F.map((_, j) => { const o = roomAgg('SQ', j); return b === 'all' ? tot(o.cap) : o.cap[b]; });
    const enr = F.map((_, j) => { const o = roomAgg(sc, j); return b === 'all' ? tot(o.enr) : o.enr[b]; }), thr = F.map((_, j) => { const o = roomAgg(sc, j); return b === 'all' ? tot(o.thr) : o.thr[b]; });
    const R = ranges(b);
    const all = [...capS, ...capQ, ...enr, ...thr, ...(R ? R.flatMap(q => [q[0], q[4]]) : [])], yhi = Math.max(...all) * 1.06, ylo = 0;
    const W = 360, H = 210, L = 52, Rm = 8, T = 10, B = 24, x = f => L + (W - L - Rm) * (f - 2025) / 10, y = v => T + (H - T - B) * (1 - (v - ylo) / (yhi - ylo));
    let s = '';
    const step = yhi > 40000 ? 10000 : yhi > 20000 ? 5000 : yhi > 8000 ? 2000 : 1000;
    for (let v = 0; v <= yhi; v += step) s += `<line x1="${L}" x2="${W - Rm}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 5}" y="${y(v) + 3.5}" text-anchor="end" font-size="9.5" fill="var(--text-muted)">${v.toLocaleString()}</text>`;
    for (let f = 2025; f <= 2035; f += 2) s += `<text x="${x(f)}" y="${H - B + 13}" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">${f}</text>`;
    const stp = arr => arr.map((v, j) => `${j ? `L${x(F[j]) - 0.01},${y(arr[j - 1])} ` : 'M'}${x(F[j])},${y(v)}`).join(' ');
    if (R) { const poly = (a, c) => F.map((f, j) => `${x(f)},${y(R[j][c])}`).join(' ') + ' ' + F.map((f, j) => `${x(f)},${y(R[j][a])}`).reverse().join(' ');
      s += `<polygon points="${poly(0, 4)}" fill="var(--change)" opacity=".14"/><polygon points="${poly(1, 3)}" fill="var(--change)" opacity=".26"/>`; }
    if (sc !== 'SQ') s += `<path d="${stp(capQ)}" fill="none" stroke="var(--text-muted)" stroke-width="1.4" stroke-dasharray="2 3"><title>Status Quo capacity</title></path>`;
    s += `<path d="${stp(capS)}" fill="none" stroke="var(--text-primary)" stroke-width="2.2"><title>Capacity, ${esc(lab)}</title></path>`;
    s += `<polyline points="${F.map((f, j) => `${x(f)},${y(thr[j])}`).join(' ')}" fill="none" stroke="var(--down)" stroke-width="1.6" stroke-dasharray="6 4"><title>Size threshold: every open school at its threshold</title></polyline>`;
    s += `<polyline points="${F.map((f, j) => `${x(f)},${y(enr[j])}`).join(' ')}" fill="none" stroke="var(--change)" stroke-width="2"><title>Projected enrollment (this page)</title></polyline>`;
    F.forEach((f, j) => { s += `<rect x="${x(f) - 8}" y="${T}" width="16" height="${H - T - B}" fill="transparent"><title>${D.years[j]}: capacity ${n0(capS[j])}${sc !== 'SQ' ? ` (Status Quo ${n0(capQ[j])})` : ''}; projected ${n0(enr[j])} (${pc(enr[j], capS[j])} full)${R ? `; 90% range ${n0(R[j][0])}-${n0(R[j][4])}` : ''}; every school at its threshold ${n0(thr[j])}; empty seats ${n0(capS[j] - enr[j])}</title></rect>`; });
    const j = yi;
    return `<div><div style="font-size:13px;font-weight:600">${title}</div><div class="muted" style="font-size:11.5px">${roomYear}: ${n0(enr[j])} of ${n0(capS[j])} seats (${pc(enr[j], capS[j])}), ${n0(capS[j] - enr[j])} empty</div><svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto" role="img" aria-label="${title} capacity and enrollment">${s}</svg></div>`;
  };
  document.getElementById('roomcharts').innerHTML = chart('k5', 'K-5') + chart('m68', '6-8') + chart('h912', '9-12') + chart('all', 'K-12');
  document.getElementById('roomlegend').innerHTML = `<span><i class="k" style="border-top:2.2px solid var(--text-primary);width:18px"></i>capacity, ${esc(lab)}</span>${sc !== 'SQ' ? '<span><i class="k" style="border-top:1.6px dotted var(--text-muted);width:18px"></i>Status Quo capacity</span>' : ''}<span><i class="k" style="border-top:2px solid var(--change);width:18px"></i>projected enrollment</span>${sims ? '<span><i class="k" style="height:10px;width:16px;background:var(--change);opacity:.35"></i>50% / 90% range</span>' : ''}<span><i class="k" style="border-top:1.6px dashed var(--down);width:18px"></i>every open school at its size threshold</span>`;
  // what would fill the buildings: a kindergarten scale with capture and births equivalents
  const P = D.mc?.psu, ih = P ? P.falls.indexOf(2025 + yi) : -1, Khigh = ih >= 0 ? P.high.K[ih] : null, Kpeak = 4277;
  const marks = [[Kthr, 'Schools average their size threshold', 'var(--down)'], [Kproj, 'Projected', 'var(--change)'], [Khigh, 'PSU high scenario', 'var(--text-secondary)'], [Kmax, 'Buildings full', 'var(--text-primary)'], [Kpeak, 'Actual peak (2012)', 'var(--text-muted)']].filter(m => m[0]);
  const lo = 2000, hi = Math.max(5000, ...marks.map(m => m[0])) * 1.04, W = 760, AX = 104, LM = 92, RM = 24, X = v => LM + (W - LM - RM) * (v - lo) / (hi - lo);   // room-scale-labels
  let g = `<line x1="${X(lo)}" x2="${X(hi)}" y1="${AX}" y2="${AX}" stroke="var(--text-secondary)" stroke-width="1.5"/>`;
  for (let v = 2000; v <= hi; v += 500) g += `<line x1="${X(v)}" x2="${X(v)}" y1="${AX - 4}" y2="${AX + 4}" stroke="var(--text-secondary)"/><text x="${X(v)}" y="${AX + 16}" text-anchor="middle" font-size="10" fill="var(--text-muted)">${v.toLocaleString()}</text>` +
    (age5 ? `<text x="${X(v)}" y="${AX + 31}" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">${Math.round(100 * v / age5)}%</text>` : '') + `<text x="${X(v)}" y="${AX + 46}" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">${n0(v / capNow)}</text>`;
  g += `<text x="${LM - 22}" y="${AX + 16}" text-anchor="end" font-size="10" fill="var(--text-secondary)">Kindergarten</text>${age5 ? `<text x="${LM - 22}" y="${AX + 31}" text-anchor="end" font-size="9.5" fill="var(--text-secondary)">Capture</text>` : ''}<text x="${LM - 22}" y="${AX + 46}" text-anchor="end" font-size="9.5" fill="var(--text-secondary)">Births a year</text>`;
  // labels: rows above the axis (0 = closest). Each label sits centered on, right of or left of its marker; a placement is
  // valid when no two labels on a row overlap, no marker's line (axis up to its own label) passes through another label,
  // and labels stay inside the chart.
  const ROWS = [0, 1, 2, 3, 4, 5].map(r => AX - 14 - r * 16), items = marks.map(([v, l, c]) => ({ v, l, c, cx: X(v), txt: `${l} ${n0(v)}`, w: `${l} ${n0(v)}`.length * 6 + 4 }));
  const boxAt = (it, a) => a === 'm' ? [it.cx - it.w / 2, it.cx + it.w / 2] : a === 's' ? [it.cx + 5, it.cx + 5 + it.w] : [it.cx - 5 - it.w, it.cx - 5];
  const fits = (it, r, b, placed) => b[0] >= 2 && b[1] <= W - 2 && placed.every(p =>
    !(p.r === r && !(b[1] < p.b[0] - 6 || b[0] > p.b[1] + 6)) &&            // overlap on the same row
    !(p.r < r && it.cx > p.b[0] - 3 && it.cx < p.b[1] + 3) &&               // this line would cross a lower label
    !(p.r > r && p.cx > b[0] - 3 && p.cx < b[1] + 3));                      // a higher label's line would cross this one
  // backtracking over every label's row and anchor (left to right), keeping the layout with the fewest rows
  items.sort((a, b) => a.cx - b.cx);
  let best = null;
  const dfs = (i, placed, top) => {
    if (best && top >= best.top) return;
    if (i === items.length) { best = { top, placed: placed.slice() }; return; }
    const it = items[i];
    for (let r = 0; r < ROWS.length; r++) for (const a of ['m', 's', 'e']) { const b = boxAt(it, a); if (fits(it, r, b, placed)) { placed.push({ ...it, r, b, a }); dfs(i + 1, placed, Math.max(top, r)); placed.pop(); } }
  };
  dfs(0, [], 0);
  const lay = best ? best.placed : items.map((it, i) => ({ ...it, r: i, b: boxAt(it, 'm') }));
  for (const p of lay) {
    const ty = ROWS[p.r];
    g += `<line x1="${p.cx}" x2="${p.cx}" y1="${ty + 3}" y2="${AX}" stroke="${p.c}" stroke-width="1.6"/><circle cx="${p.cx}" cy="${AX}" r="4.5" fill="${p.c}"/>` +
      `<text x="${(p.b[0] + p.b[1]) / 2}" y="${ty}" text-anchor="middle" font-size="10.5" font-weight="600" fill="${p.c}">${esc(p.txt)}</text>`;
  }
  document.getElementById('roomscale').innerHTML = `<svg viewBox="0 0 ${W} ${AX + 54}" style="width:100%;max-width:${W}px;height:auto" role="img" aria-label="Kindergarten class sizes">${g}</svg>` +
    `<p class="sub" style="margin:2px 0 0">Kindergarten class size a year (district), with the matching share of the district's 5-year-olds (capture${age5 ? `; about ${n0(age5)} 5-year-olds live in PPS in ${roomYear}` : ''}) and the births a year it would take at today's capture. At steady state each kindergartner becomes about ${(M.k5 + M.m68 + M.h912).toFixed(1)} K-12 students (K-5 ${M.k5.toFixed(1)}, 6-8 ${M.m68.toFixed(1)}, 9-12 ${M.h912.toFixed(1)}; PSU's grade progression ratios). ${Kproj && Kmax > Kproj ? `Filling ${esc(lab)}'s buildings would take a kindergarten about ${Math.round(100 * (Kmax / Kproj - 1))}% above projections${age5 && Kmax > age5 ? ', more than every 5-year-old in the district' : ''}.` : ''}</p>`;
  // region table
  const rows = [...D.region_order, 'District'];
  const cell = (o, b) => { const c = b === 'all' ? tot(o.cap) : o.cap[b], e = b === 'all' ? tot(o.enr) : o.enr[b]; return c ? `<td style="text-align:right">${n0(e)} / ${n0(c)}<span class="muted" style="display:block;font-size:11px">${pc(e, c)} full &middot; ${n0(c - e)} empty</span></td>` : '<td class="muted" style="text-align:right">&ndash;</td>'; };
  let h = `<table><thead><tr><th style="text-align:left">Region</th><th>Schools open</th>${ROOM_B.map(([, l]) => `<th>${l}<br><span style="font-weight:400">enrolled / seats</span></th>`).join('')}<th>K-12</th></tr></thead><tbody>`;
  for (const rn of rows) {
    const keys = Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn), o = roomAgg(sc, yi, keys), isReg = rn !== 'District', open = roomOpen.has(rn);
    h += `<tr class="${isReg ? '' : 'dist'}"><td style="text-align:left">${isReg ? `<button class="xbtn room-x" data-r="${esc(rn)}" aria-expanded="${open}"><span class="car">&#9656;</span><span>${esc(rn)}</span></button>` : 'District (this page)'}</td><td style="text-align:right">${o.n}</td>${ROOM_B.map(([b]) => cell(o, b)).join('')}${cell(o, 'all')}</tr>`;
    if (isReg && open) for (const k of keys.sort((a, b) => short(byKey[a]?.name || a).localeCompare(short(byKey[b]?.name || b)))) {
      const v = D.series[sc]?.[k]?.[yi], fc = byKey[k]?.fc || 0, t = (yi < D.years.indexOf(D.impl_year) ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k];
      h += `<tr class="srow${v == null ? ' closed' : ''}"><td style="text-align:left"><span class="nm">${esc(short(byKey[k]?.name || k))}</span><span class="ty">${TYPE_LABEL[t] || ''}</span></td>` +
        (v == null ? `<td colspan="5" class="muted" style="text-align:left">closed in ${esc(lab)}</td>` : `<td></td>${ROOM_B.map(([b]) => { const sp = roomSplit(k, sc, yi, 1); return sp[b] ? `<td style="text-align:right">${n0(v * sp[b])} / ${n0(fc * sp[b])}</td>` : '<td></td>'; }).join('')}<td style="text-align:right;${v > fc ? 'color:var(--down);font-weight:600' : ''}">${n0(v)} / ${n0(fc)}<span class="muted" style="display:block;font-size:11px">${pc(v, fc)} full</span></td>`) + '</tr>';
    }
  }
  const tb = document.getElementById('roomtable'); tb.innerHTML = h + '</tbody></table>';
  tb.querySelectorAll('.room-x').forEach(b => b.onclick = () => { const r = b.dataset.r; roomOpen.has(r) ? roomOpen.delete(r) : roomOpen.add(r); renderRoom(); });
  const ex = document.getElementById('room-expand');
  if (ex) { ex.textContent = D.region_order.every(r => roomOpen.has(r)) ? 'Collapse all regions' : 'Expand all regions'; ex.onclick = () => { if (D.region_order.every(r => roomOpen.has(r))) roomOpen.clear(); else D.region_order.forEach(r => roomOpen.add(r)); renderRoom(); }; }
  document.getElementById('roomnote').innerHTML = `Capacity: 2021 functional capacity (PPS Long-Range Facility Plan) for each building's grades at the time; where a scenario changes a school's grades (K-8 to K-5, new programs) it is indicative. Schools and programs not on this page (Benson, ACCESS and others) are left out of capacity and enrollment; the largest kindergarten scales up by these schools' share of the district's students in each band. Steady state assumes PSU's grade progression ratios; more families moving in during the school years would fill the upper grades sooner. Births at today's capture: fall 2025 kindergarten (2,919) over 2020 births to PPS-area residents (4,121).`;
}
function renderAll() {'''

if 'renderRoom' not in html:
    rep('''  <section class="card">
    <h2>Small schools and staffing cost over time - How much does it cost to wait?</h2>''', SECTION)
    rep("function renderAll() {", JS)
    rep("renderMap(); renderEndpoints();", "renderMap(); renderEndpoints(); renderRoom();")
    rep("['mc', 'mckpis'],", "['mc', 'mckpis'], ['room', 'roomkpis'],")
    rep("  if (key === 'classsize') p.set('csy', csYear);", "  if (key === 'classsize') p.set('csy', csYear);\n  if (key === 'room') p.set('rmy', roomYear);")
    rep("  if (D.years.includes(q.get('csy'))) csYear = q.get('csy');", "  if (D.years.includes(q.get('csy'))) csYear = q.get('csy');\n  if (D.years.includes(q.get('rmy'))) roomYear = q.get('rmy');")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
