"""Getting-to-school section: a summary card and a table by region and school of walk / bike / drive times and
the number of school-age residents beyond Oregon's bus distance, from source/block-access/school-access.csv
(scripts/build_block_access.py). Replaces the 15-minute access column of the scenario impact table and its card
(D.reach, scripts/patch_reach.py). Safe to rerun: the data is always refreshed, the page code is added once.
"""
import csv, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
ACC = os.path.join(ROOT, 'source', 'block-access')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))

# ---------- data ----------
meta = json.load(open(os.path.join(ACC, 'district-access.json'), encoding='utf-8'))
BUS = meta['bus_headline_miles']
SQ68 = meta['district']['SQ']['68']
S = {}
for r in csv.DictReader(open(os.path.join(ACC, 'school-access.csv'), encoding='utf-8')):
    thr = f"beyond_{BUS[r['band']]:g}mi_share"
    S.setdefault(r['scenario'], {}).setdefault(r['school'], {})[r['band']] = [
        int(r['residents']), float(r[thr]), float(r['mean_walk_mi']), float(r['walk_min_mean']), float(r['bike_min_mean']),
        float(r['drive_min_mean']), float(r['walk_15min_share']), float(r['bike_15min_share']), float(r['drive_15min_share']),
        float(r['nearest_is_assigned_share']), *[[int(x) for x in r[f'{m}_hist'].split(';')] for m in ('walk', 'bike', 'drive')]]
D['commute'] = dict(bus=BUS, walk_mph=meta['walk_mph'], bike_mph=meta['bike_mph'], drive_factor=meta['drive_factor_vs_osrm'], hist_min=meta['hist_min'], S=S)
D.pop('reach', None)
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b, count=1):
    global html
    assert html.count(a) == count, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderCommute' not in html:
    # ---- remove the 15-minute column from the scenario impact table ----
    a = html.index('// share of attendance area within 15 min of the school (D.reach;'); b = html.index('// building costs (D.costs, 2026 dollars)')
    html = html[:a] + html[b:]
    rep("""<th>Attendance-area residents within 15 min<br><span style="font-weight:400">(of their school, 2020 Census; roll-ups weighted by 2031-32 enrollment; change vs Status Quo in pts)</span></th>""", '')
    rep("    h += reachCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));\n", '')
    rep("""'<td class="reach muted">&mdash;</td>' + costCell([n])""", "costCell([n])")
    rep("""over capacity' : ''}</span>` : '<span class="muted">no data</span>'}</td>` + reachCell([n]) + costCell([n])""",
        """over capacity' : ''}</span>` : '<span class="muted">no data</span>'}</td>` + costCell([n])""")
    rep("function endpointCols() { return ['region', ...MEAS.map(m => m.key), 'util', 'reach', 'cost', 'staff', 'land', 'change']; }",
        "function endpointCols() { return ['region', ...MEAS.map(m => m.key), 'util', 'cost', 'staff', 'land', 'change']; }")
    rep("<h2>Scenario impact by region: enrollment, access, buildings, staffing and costs</h2>",
        "<h2>Scenario impact by region: enrollment, buildings, staffing and costs</h2>")
    rep("The remaining columns are this analysis's estimates: building utilization, residents within 15 minutes of their school, building costs",
        "The remaining columns are this analysis's estimates: building utilization, building costs")

    # ---- summary card: replaces the 15-minute card ----
    a = html.index("    `<div class=\"kpi\"><div class=\"v\">${r.w == null ? '&mdash;' : r.w + '%'}")
    b = html.index("    ((a, t) => scen === 'SQ'", a)
    html = html[:a] + "    commuteKPI() +\n" + html[b:]
    rep("  const keys = Object.keys(D.region_of), r = reachRoll(scen, keys), rs = reachRoll('SQ', keys);\n"
        "  const sub = (m, l) => r[m] == null ? '' : `${l} <b>${r[m]}%</b>${scen !== 'SQ' && rs[m] != null && r[m] !== rs[m] ? ` (${r[m] > rs[m] ? '+' : '&minus;'}${Math.abs(r[m] - rs[m])})` : ''}`;\n", '')
    rep("const KPI_TARGETS = ['closures', 'schools_above', 'students_above', 'change', 'overcap', 'reach', 'cost', 'land', 'staff'];",
        "const KPI_TARGETS = ['closures', 'schools_above', 'students_above', 'change', 'overcap', 'commute', 'cost', 'land', 'staff'];")
    rep("""  if (target === 'overcap') {""",
        """  if (target === 'commute') {
    const t = document.querySelector('#commute table'); if (!t) return;
    t.scrollIntoView({ behavior: 'smooth', block: 'start' }); flash([...t.rows].map(r => r.cells[2]).filter(Boolean)); return;
  }
  if (target === 'overcap') {""")
    rep("    k.title = t === 'overcap' ? 'Show the schools over capacity' : 'Show this in the table by region';",
        "    k.title = t === 'overcap' ? 'Show the schools over capacity' : t === 'commute' ? 'Show getting to school by region' : 'Show this in the table by region';")

    # ---- section ----
    rep("""  <section class="card">
    <h2>Staffing impact: positions no longer needed</h2>""",
"""  <section class="card">
    <h2>Getting to school: walk, bike and drive times, and bus distance</h2>
    <p class="sub">For each school's students, the walking, biking and driving route from home to school over the OpenStreetMap street and path network. <b>Students</b> are the school's enrollment in the selected year (this page's projection; K-8 schools split into K-5 and 6-8 by the district's K-5 share). <b>Where they live</b>, and so the share beyond bus distance, travel times and their spread, comes from the 2020 Census school-age residents of the school's attendance area. <b>Beyond bus distance</b> counts students who live farther than Oregon's state-reimbursed transportation distances (ORS 327.043) by walking route: more than 1 mile for K-5, more than 1.5 miles for grades 6-12. PPS gives high school students TriMet passes rather than yellow buses, so 9-12 counts are students who would need transit. Under a scenario, changes are against Status Quo in the same year.</p>
    <div class="controls"><label>Grades <select id="cm-band"></select></label><label>Year <select id="cm-year"></select></label></div>
    <p class="sub" id="commutesum"></p>
    <div class="tablewrap" id="commute"></div>
  </section>

  <section class="card">
    <h2>Staffing impact: positions no longer needed</h2>""")

    # ---- code ----
    rep("// building costs (D.costs, 2026 dollars)", r"""// ---------- getting to school (D.commute, from scripts/build_block_access.py) ----------
// per scenario, school and grade band: [residents, share beyond bus distance, mean walk miles, mean walk / bike /
// drive minutes, share within 15 min walk / bike / drive, share whose nearest school is the assigned one,
// residents per travel-time bin for walk / bike / drive (bins edged at D.commute.hist_min minutes, last bin open)].
// Counts are students: each school's projected enrollment in cmYear (D.series), K-8 schools split by the district's
// K-5 share; the census shares and distributions of its attendance area are applied to them. Custom scenarios use
// their own enrollment with their starting scenario's attendance areas.
const CM_YEARS = D.years;   // 2025-26 actual, later years projected
let cmYear = '2031-32';
try { const y = localStorage.getItem('rsCmYear'); if (CM_YEARS.includes(y)) cmYear = y; } catch (e) {}
function cmStu(sc, k, b) {
  const v = D.series[sc]?.[k]?.[D.years.indexOf(cmYear)]; if (!v) return 0;
  const pre = D.years.indexOf(cmYear) < D.years.indexOf(D.impl_year);   // scenarios not yet in effect: Status Quo grade spans
  const t = (pre ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k], f = D.k5_share[cmYear];
  if (b === 'k5') return t === 'ES' ? v : t === 'K8' ? v * f : 0;
  if (b === '68') return t === 'MS' ? v : t === 'K8' ? v * (1 - f) : 0;
  return t === 'HS' ? v : 0;
}
const CM_BANDS = [['all', 'All grades (K-12)'], ['k5', 'K-5'], ['68', '6-8'], ['912', '9-12']];
let cmBand = 'all';
try { cmBand = localStorage.getItem('rsCmBand') || 'all'; } catch (e) {}
const cmOpen = new Set();
function cmAgg(sc, keys, band) {
  // before the scenarios take effect (D.impl_year) every scenario still has Status Quo's attendance areas
  const Sc = D.years.indexOf(cmYear) < D.years.indexOf(D.impl_year) ? 'SQ' : sc === 'C' ? custom.base : sc;
  const S = D.commute.S[Sc] || {};
  const bands = band === 'all' ? ['k5', '68', '912'] : [band];
  const nb = D.commute.hist_min.length + 1;
  const MB = D.buscost?.M?.[Sc] || {};   // eligible K-8 walking miles per area (bus columns)
  const o = { r: 0, beyond: 0, wmi: 0, wmin: 0, bmin: 0, dmin: 0, w15: 0, b15: 0, d15: 0, near: 0, n: 0, bm: 0, bn: 0,
    h: { walk: Array(nb).fill(0), bike: Array(nb).fill(0), drive: Array(nb).fill(0) } };
  for (const k of keys) for (const b of bands) {
    const v = S[k]?.[b]; if (!v || !v[0]) continue;
    const r = cmStu(sc, k, b); if (!r) continue;
    const x = r / v[0];   // students per census resident of the area
    if (MB[k]?.[b] != null) { o.bm += MB[k][b] * x; o.bn++; }
    o.n++; o.r += r; o.beyond += r * v[1]; o.wmi += r * v[2]; o.wmin += r * v[3]; o.bmin += r * v[4]; o.dmin += r * v[5];
    o.w15 += r * v[6]; o.b15 += r * v[7]; o.d15 += r * v[8]; o.near += r * v[9];
    ['walk', 'bike', 'drive'].forEach((m, j) => v[10 + j].forEach((y, i) => { o.h[m][i] += y * x; }));
  }
  if (o.r) for (const f of ['wmi', 'wmin', 'bmin', 'dmin', 'w15', 'b15', 'd15', 'near']) o[f] /= o.r;
  return o;
}
// value with change vs Status Quo underneath; good = which direction is an improvement
function cmD(v, s, fmt, good) {
  if (scen === 'SQ' || s == null) return '';
  const d = v - s, z = Math.abs(d) < 1e-9 || fmt(Math.abs(d)) === fmt(0);
  return `<span class="delta ${z || good === 'flat' ? 'flat' : (d > 0) === (good === 'up') ? 'up' : 'down'}">${z ? '&plusmn;0' : (d > 0 ? '+' : '&minus;') + fmt(Math.abs(d))}</span>`;
}
const cmN = v => Math.round(v).toLocaleString(), cmP = v => Math.round(100 * v) + '%', cmPt = v => Math.round(100 * v) + ' pts';
// travel-time histogram: share of residents per time bin; darker bars are within 15 minutes; outline = Status Quo
function cmHist(c, q, m) {
  const E = D.commute.hist_min, nb = E.length + 1, W = 120, H = 34, bw = W / nb;
  const sh = o => o && o.r ? o.h[m].map(x => x / Math.max(1, o.h[m].reduce((a, y) => a + y, 0))) : null;
  const cs = sh(c), qs = sh(q), top = Math.max(...cs, ...(qs || [0]), 0.01);
  const lab = i => i === 0 ? `under ${E[0]} min` : i === nb - 1 ? `${E[nb - 2]}+ min` : `${E[i - 1]}-${E[i]} min`;
  let g = '';
  for (let i = 0; i < nb; i++) {
    const hgt = H * cs[i] / top, x = i * bw + 1;
    const tip = `${lab(i)}: ${Math.round(100 * cs[i])}% (${cmN(c.h[m][i])} students)${qs ? `; Status Quo ${Math.round(100 * qs[i])}%` : ''}`;
    g += `<rect x="${x}" y="${H - hgt}" width="${bw - 2}" height="${Math.max(hgt, 0.5)}" fill="var(--text-secondary)" opacity="${E[i] <= 15 ? 0.85 : 0.3}"><title>${tip}</title></rect>`;
    if (qs) { const qh = H * qs[i] / top; g += `<rect x="${x}" y="${H - qh}" width="${bw - 2}" height="${Math.max(qh, 0.5)}" fill="none" stroke="var(--change)" stroke-width="1.2" pointer-events="none"/>`; }
  }
  const ix = v => (E.indexOf(v) + 1) * bw;   // x at the end of the bin closing at v minutes
  const ax = `<line x1="0" x2="${W}" y1="${H + .5}" y2="${H + .5}" stroke="var(--line)"/>` +
    `<text x="0" y="${H + 10}" font-size="9" fill="var(--text-muted)">0</text>` +
    [15, 30, 60].map(v => `<text x="${ix(v)}" y="${H + 10}" font-size="9" fill="var(--text-muted)" text-anchor="middle">${v}${v === 60 ? '+' : ''}</text>`).join('') +
    `<line x1="${ix(15)}" x2="${ix(15)}" y1="0" y2="${H}" stroke="var(--text-muted)" stroke-dasharray="2 2"/>`;
  return `<td class="cmh"><svg width="${W}" height="${H + 12}" viewBox="0 0 ${W} ${H + 12}" role="img" aria-label="${m} time histogram">${g}${ax}</svg></td>`;
}
function cmCells(c, q) {   // c = this scenario, q = Status Quo (same rows)
  if (!c.r) return '<td class="muted">&mdash;</td>'.repeat(7);
  const w15 = [['w15', 'Walk'], ['b15', 'Bike'], ['d15', 'Drive']].map(([f, l]) => {
    const dv = q ? Math.round(100 * c[f]) - Math.round(100 * q[f]) : 0;
    return `<span class="rm">${l}</span>${cmP(c[f])}${scen !== 'SQ' && q && dv ? ` <span class="rd ${dv > 0 ? 'up' : 'down'}">${dv > 0 ? '+' : '&minus;'}${Math.abs(dv)}</span>` : ''}`;
  }).join('<br>');
  return `<td><span class="main">${cmN(c.r)}</span>${cmD(c.r, q?.r, cmN, 'flat')}</td>` +
    `<td><span class="main">${cmN(c.beyond)}</span><span class="muted" style="display:block;font-size:11px">${cmP(c.beyond / c.r)} of students</span>${cmD(c.beyond, q?.beyond, cmN, 'down')}</td>` +
    `<td class="reach">${w15}</td>` + cmHist(c, q, 'walk') + cmHist(c, q, 'bike') + cmHist(c, q, 'drive') +
    `<td><span class="main">${cmP(c.near)}</span>${cmD(c.near, q?.near, cmPt, 'up')}</td>`;
}
function commuteKPI() {
  const keys = Object.keys(D.region_of), B = D.commute.bus;
  const c = cmAgg(scen, keys, 'all'), q = cmAgg('SQ', keys, 'all');
  const by = b => cmAgg(scen, keys, b), bq = b => cmAgg('SQ', keys, b);
  const d = c.beyond - q.beyond, isSQ = scen === 'SQ';
  const line = (b, l) => { const x = by(b), y = bq(b), dd = x.beyond - y.beyond;
    return `${l}: <b>${cmN(x.beyond)}</b> <span class="pcs">(${cmP(x.beyond / x.r)}${!isSQ && Math.round(dd) ? `, ${dd > 0 ? '+' : '&minus;'}${cmN(Math.abs(dd))}` : ''})</span>`; };
  const wd = Math.round(100 * c.w15) - Math.round(100 * q.w15);
  return `<div class="kpi"><div class="v">${cmN(c.beyond)}${isSQ || !Math.round(d) ? '' : `<span class="d" style="color:${d > 0 ? 'var(--down)' : 'var(--up)'}">${d > 0 ? '+' : '&minus;'}${cmN(Math.abs(d))} vs SQ</span>`}</div>` +
    `<div class="l">Students beyond bus distance from their school, ${cmYear} (walking route: K-5 over ${B.k5} mile, 6-12 over ${B['912']} miles)</div>` +
    `<div class="s">${line('k5', 'K-5')}<br>${line('68', '6-8')}<br>${line('912', '9-12 (TriMet)')}<br>` +
    `Within a 15-minute walk: <b>${cmP(c.w15)}</b>${isSQ || !wd ? '' : ` <span class="pcs">(${wd > 0 ? '+' : '&minus;'}${Math.abs(wd)} pts)</span>`}</div></div>`;
}
function renderCommute() {
  const host = document.getElementById('commute'); if (!host) return;
  const ysel = document.getElementById('cm-year');
  if (!ysel.options.length) {
    ysel.innerHTML = CM_YEARS.map(y => `<option value="${y}">${y}${y === D.years[0] ? ' (actual)' : y === D.impl_year ? ' (scenarios take effect)' : ''}</option>`).join('');
    ysel.onchange = () => { cmYear = ysel.value; try { localStorage.setItem('rsCmYear', cmYear); } catch (e) {} renderKPIs(); renderCommute(); };
  }
  ysel.value = cmYear;
  const sel = document.getElementById('cm-band');
  if (!sel.options.length) {
    sel.innerHTML = CM_BANDS.map(([v, l]) => `<option value="${v}">${l}</option>`).join('');
    sel.onchange = () => { cmBand = sel.value; try { localStorage.setItem('rsCmBand', cmBand); } catch (e) {} renderCommute(); };
  }
  sel.value = cmBand;
  const keysOf = rn => Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn);
  const B = D.commute.bus, thr = cmBand === 'all' ? `K-5 over ${B.k5} mi, 6-12 over ${B['912']} mi` : `over ${B[cmBand]} ${B[cmBand] === 1 ? 'mile' : 'miles'}`;
  let h = `<table class="commutetable"><thead><tr><th>Region</th><th>Students<br><span style="font-weight:400">(${cmYear} enrollment, ${cmYear === D.years[0] ? 'actual' : 'projected'})</span></th>` +
    `<th>Beyond bus distance<br><span style="font-weight:400">(walking route, ${thr})</span></th>` +
    `<th>Within 15 min of school<br><span style="font-weight:400">(share of students${scen === 'SQ' ? '' : '; change vs SQ in pts'})</span></th>` +
    ['Walk', 'Bike', 'Drive'].map(l => `<th>${l} time<br><span style="font-weight:400">(minutes)</span></th>`).join('') +
    `<th>Assigned school is their nearest</th></tr></thead><tbody>`;
  for (const rn of [...D.region_order, 'District']) {
    const keys = keysOf(rn), isReg = rn !== 'District', open = cmOpen.has(rn);
    h += `<tr class="${isReg ? '' : 'dist'}"><td>${isReg ? `<button class="xbtn cm-x" data-r="${esc(rn)}" aria-expanded="${open}"><span class="car">&#9656;</span><span>${esc(rn)}</span></button>` : esc(rn)}</td>` +
      cmCells(cmAgg(scen, keys, cmBand), scen === 'SQ' ? null : cmAgg('SQ', keys, cmBand)) + '</tr>';
    if (isReg && open) for (const k of keys.sort(byStatusName)) {
      const c = cmAgg(scen, [k], cmBand), q = cmAgg('SQ', [k], cmBand), closed = D.detail[scen]?.[k]?.closed;
      if (!c.r && !q.r) continue;
      const nm = `<span class="nm">${esc(short(byKey[k].name))}</span><span class="ty">${TYPE_LABEL[(!closed && D.detail[scen]?.[k]?.type) || D.detail.SQ[k].type]}</span>`;
      if (closed || !c.r) {
        h += `<tr class="srow closed"><td>${nm}</td><td colspan="7" style="text-align:left">${closed ? '<span class="stag closes">Closes</span> ' : ''}<span class="muted">` +
          `${closed ? 'its students are assigned to other schools' : 'no students in these grades in this scenario'}${q.r ? ` (Status Quo: ${cmN(q.r)} students, ${cmN(q.beyond)} beyond bus distance)` : ''}</span></td></tr>`;
        continue;
      }
      h += `<tr class="srow"><td>${nm}</td>${cmCells(c, scen === 'SQ' ? null : (q.r ? q : null))}</tr>`;
    }
  }
  host.innerHTML = h + '</tbody></table>';
  host.querySelectorAll('.cm-x').forEach(b => b.onclick = () => { const r = b.dataset.r; cmOpen.has(r) ? cmOpen.delete(r) : cmOpen.add(r); renderCommute(); });
  const keys = keysOf('District'), c = cmAgg(scen, keys, 'all'), q = cmAgg('SQ', keys, 'all');
  document.getElementById('commutesum').innerHTML = (scen === 'SQ'
    ? `Status Quo, ${cmYear}: <b>${cmN(c.beyond)}</b> of ${cmN(c.r)} students (${cmP(c.beyond / c.r)}) live beyond bus distance from their school; ${cmP(c.w15)} are within a 15-minute walk.`
    : `${LABEL[scen]}, ${cmYear}: <b>${cmN(c.beyond)}</b> of ${cmN(c.r)} students (${cmP(c.beyond / c.r)}) live beyond bus distance from their school, ` +
      `<b>${c.beyond >= q.beyond ? cmN(c.beyond - q.beyond) + ' more' : cmN(q.beyond - c.beyond) + ' fewer'}</b> than under Status Quo (${cmN(q.beyond)}); ` +
      `${cmP(c.w15)} are within a 15-minute walk (Status Quo ${cmP(q.w15)}).`) +
    (scen === 'C' ? ` A custom scenario uses its own enrollment with ${LABEL[custom.base]}'s attendance areas.` : '') + ' Click a region to see its schools.' +
    `<br>Travel-time histograms show the share of students in each band (${(E => ['under ' + E[0], ...E.slice(1).map((v, i) => E[i] + '-' + v), E[E.length - 1] + '+'].join(', '))(D.commute.hist_min)} minutes); ` +
    `darker bars are within 15 minutes${scen === 'SQ' ? '' : ', and the <span style="color:var(--change);font-weight:600">outline</span> is Status Quo'}. Hover a bar for its count.`;
}
// building costs (D.costs, 2026 dollars)""")
    rep("function renderAll() { renderKPIs(); renderCustomPanel(); renderMap(); renderEndpoints(); renderStaffing(); renderLines(); }",
        "function renderAll() { renderKPIs(); renderCustomPanel(); renderMap(); renderEndpoints(); renderCommute(); renderStaffing(); renderLines(); }")

    # ---- styles: sticky first column ----
    rep(""".stafftable th:first-child, .stafftable td:first-child,
#overlist table""", """.stafftable th:first-child, .stafftable td:first-child,
.commutetable th:first-child, .commutetable td:first-child,
#overlist table""")
    rep("#endpoints table tr.srow td:first-child, .stafftable tr.srow td:first-child { background: var(--surface-2); }",
        "#endpoints table tr.srow td:first-child, .stafftable tr.srow td:first-child, .commutetable tr.srow td:first-child { background: var(--surface-2); }\n"
        ".commutetable td, .commutetable th { white-space: nowrap; } .commutetable td .main { font-size: 14px; font-weight: 600; }\n"
        "#commute table { scroll-margin-top: 72px; }\n"
        ".commutetable td.cmh { padding-top: 6px; padding-bottom: 4px; } .commutetable td.cmh svg { display: block; margin-left: auto; overflow: visible; }")

    # ---- method note: replaces the 15-minute note ----
    a = html.index("  'Residents within 15 min:"); b = html.index("  'Travel time:", a)
    html = html[:a] + "  " + json.dumps(
        "Getting to school: walking, biking and driving routes from where people live to their assigned school, over the "
        "OpenStreetMap street and path network (one shortest-path search per school and mode). Counts are students: each "
        "school's enrollment in the selected year (2025-26 actual, or projected to 2035-36; scenarios take effect in 2027-28; K-8 schools split into K-5 and 6-8 by the "
        "district's K-5 share). Where they live comes from the 2020 Census: school-age residents of each attendance area, "
        "from blocks spread over a 40 m grid of points, give the share beyond bus distance, travel times and their spread, "
        "which are applied to the school's students. School-age residents by grade band come from the Census age table (P12): "
        "K-5 = ages 5-9 plus a fifth of 10-14, 6-8 = three fifths of 10-14, 9-12 = a fifth of 10-14 plus 15-17. Walking is "
        f"{meta['walk_mph']:g} mph, biking {meta['bike_mph']:g} mph on streets, paths and bike-legal footways (one-way streets "
        "respected, hills ignored), driving at posted or typical speeds scaled by "
        f"{meta['drive_factor_vs_osrm']:.2f} so school-to-school times match the OSRM driving matrix used elsewhere on this page. "
        "Bus distance follows ORS 327.043 (state-reimbursed transportation beyond 1 mile for elementary and 1.5 miles for "
        "secondary students), measured along the walking route; grades 6-8 use 1.5 miles (at 1 mile, about "
        f"{round(SQ68['beyond_1mi'] - SQ68['beyond_1.5mi'], -2):,.0f} more 6-8 residents would count under Status Quo). Hazard-based busing is not modeled. Assignment uses the K-5, 6-8 and "
        "9-12 attendance-area layers, so K-8 schools count in both K-5 and 6-8. A custom scenario uses its starting "
        "scenario's attendance areas. Block-level results are in source/block-access; built by scripts/build_block_access.py "
        "and embedded by scripts/patch_commute.py.") + ",\n" + html[b:]
    rep("  ['Map, boundaries and travel time', ['Map:', 'Attendance boundaries', 'Residents within', 'Travel time']],",
        "  ['Map, boundaries and travel time', ['Map:', 'Attendance boundaries', 'Getting to school', 'Travel time']],")

open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
