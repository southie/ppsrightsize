"""Travel-time histograms in the getting-to-school table open a detail pane: a larger histogram (this scenario against
Status Quo, walk / bike / drive), and summary statistics (students, mean, median, 75th and 90th percentile time,
share within 5-45 minutes). Runs after scripts/patch_commute.py and patch_buscost.py. Safe to rerun: added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function cmPaneHtml' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# ---- histogram cells carry their row and mode ----
rep("function cmHist(c, q, m) {", "function cmHist(c, q, m, ri = -1) {")
rep("""  return `<td class="cmh"><svg""",
    """  return `<td class="cmh${ri >= 0 ? ' go' : ''}"${ri >= 0 ? ` data-ri="${ri}" data-m="${m}" tabindex="0" role="button" title="Show ${m} times in detail"` : ''}><svg""")
rep("function cmCells(c, q) {   // c = this scenario, q = Status Quo (same rows)",
    "function cmCells(c, q, row) {   // c = this scenario, q = Status Quo (same rows), row = {keys, label} for the detail pane\n"
    "  const ri = row ? CM_ROWS.push(row) - 1 : -1;")
rep("cmHist(c, q, 'walk') + cmHist(c, q, 'bike') + cmHist(c, q, 'drive')",
    "cmHist(c, q, 'walk', ri) + cmHist(c, q, 'bike', ri) + cmHist(c, q, 'drive', ri)")
rep("cmCells(cmAgg(scen, keys, cmBand), scen === 'SQ' ? null : cmAgg('SQ', keys, cmBand)) + '</tr>';",
    "cmCells(cmAgg(scen, keys, cmBand), scen === 'SQ' ? null : cmAgg('SQ', keys, cmBand), { keys, label: rn }) + '</tr>';")
rep("cmCells(c, scen === 'SQ' ? null : (q.r ? q : null))",
    "cmCells(c, scen === 'SQ' ? null : (q.r ? q : null), { keys: [k], label: short(byKey[k].name) })")
rep("""function renderCommute() {
  const host = document.getElementById('commute'); if (!host) return;""",
    """function renderCommute() {
  const host = document.getElementById('commute'); if (!host) return;
  CM_ROWS = [];""")
rep("""  host.innerHTML = h + '</tbody></table>';""",
    """  host.innerHTML = h + '</tbody></table>';
  host.querySelectorAll('td.cmh.go').forEach(td => {
    const open = () => { const r = CM_ROWS[+td.dataset.ri]; if (r) cmOpenPane(r, td.dataset.m); };
    td.onclick = open; td.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } };
  });
  if (dockFn?.cmPane) document.getElementById('dockbody').innerHTML = dockFn();   // band or year changed""")

# ---- the pane ----
rep("function renderCommute() {", r"""// ---------- histogram detail pane ----------
let CM_ROWS = [], cmPaneSel = null;   // rows of the current table; the pane's {keys, label, m}
const CM_MODE = { walk: ['Walk', 'wmin'], bike: ['Bike', 'bmin'], drive: ['Drive', 'dmin'] };
function cmOpenPane(row, m) {
  cmPaneSel = { ...row, m };
  const fn = () => cmPaneHtml(); fn.cmPane = true;
  openDock(fn, null, null);
}
function cmPaneMode(m) { if (!cmPaneSel) return; cmPaneSel.m = m; document.getElementById('dockbody').innerHTML = cmPaneHtml(); }
// share of students in each time band; percentile p (0-1) by straight-line interpolation inside its band
function cmShares(o, m) { const h = o.h[m], t = h.reduce((a, y) => a + y, 0); return t ? h.map(y => y / t) : null; }
function cmPct(sh, p) {
  const E = D.commute.hist_min; let cum = 0;
  for (let i = 0; i < sh.length; i++) {
    if (cum + sh[i] >= p - 1e-9 && sh[i] > 0) {
      if (i === sh.length - 1) return { v: E[E.length - 1], open: true };
      const lo = i ? E[i - 1] : 0; return { v: lo + (p - cum) / sh[i] * (E[i] - lo), open: false };
    }
    cum += sh[i];
  }
  return { v: E[E.length - 1], open: true };
}
function cmWithin(sh, x) { const i = D.commute.hist_min.indexOf(x); return sh.slice(0, i + 1).reduce((a, y) => a + y, 0); }
function cmPaneHtml() {
  const s = cmPaneSel; if (!s) return '';
  const c = cmAgg(scen, s.keys, cmBand), isSQ = scen === 'SQ', q = isSQ ? null : cmAgg('SQ', s.keys, cmBand), m = s.m;
  const band = CM_BANDS.find(([v]) => v === cmBand)[1];
  let h = `<div class="pop cmpane"><b>${esc(s.label)}</b><div class="muted">${LABEL[scen]}${isSQ ? '' : ' vs Status Quo'} &middot; ${band} &middot; ${cmYear}</div>` +
    `<div class="seg2 cmmodes">${Object.entries(CM_MODE).map(([k, [l]]) => `<button type="button" aria-pressed="${k === m}" onclick="cmPaneMode('${k}')">${l}</button>`).join('')}</div>`;
  const cs = c.r ? cmShares(c, m) : null, qs = q?.r ? cmShares(q, m) : null;
  if (!cs) return h + `<p class="muted">No students in these grades here in this scenario${qs ? ` (Status Quo: ${cmN(q.r)})` : ''}.</p></div>`;
  // chart
  const E = D.commute.hist_min, nb = E.length + 1, W = 320, H = 150, L0 = 30, B0 = 34, bw = (W - L0) / nb;
  const lab = i => i === 0 ? `<${E[0]}` : i === nb - 1 ? `${E[nb - 2]}+` : `${E[i - 1]}-${E[i]}`;
  const T0 = 14, top = Math.ceil(Math.max(...cs, ...(qs || [0]), 0.05) * 10) / 10, y = v => T0 + (H - T0) * (1 - v / top);
  let g = '';
  for (let t = 0; t <= top + 1e-9; t += top > 0.5 ? 0.2 : 0.1)
    g += `<line x1="${L0}" x2="${W}" y1="${y(t)}" y2="${y(t)}" stroke="var(--line)"/><text x="${L0 - 4}" y="${y(t) + 3}" font-size="9" text-anchor="end" fill="var(--text-muted)">${Math.round(100 * t)}%</text>`;
  for (let i = 0; i < nb; i++) {
    const x = L0 + i * bw + 2, w = bw - 4, tip = `${lab(i)} min: ${Math.round(100 * cs[i])}% (${cmN(c.h[m][i])} students)${qs ? `; Status Quo ${Math.round(100 * qs[i])}% (${cmN(q.h[m][i])})` : ''}`;
    g += `<rect x="${x}" y="${y(cs[i])}" width="${w}" height="${Math.max(H - y(cs[i]), .5)}" fill="var(--text-secondary)" opacity="${E[i] <= 15 ? .85 : .3}"><title>${tip}</title></rect>`;
    if (qs) g += `<rect x="${x}" y="${y(qs[i])}" width="${w}" height="${Math.max(H - y(qs[i]), .5)}" fill="none" stroke="var(--change)" stroke-width="1.5" pointer-events="none"/>`;
    g += `<text x="${x + w / 2}" y="${y(cs[i]) - 3}" font-size="9" text-anchor="middle" fill="var(--text-primary)">${Math.round(100 * cs[i])}</text>` +
      `<text x="${x + w / 2}" y="${H + 12}" font-size="9" text-anchor="middle" fill="var(--text-muted)">${lab(i)}</text>`;
  }
  const x15 = L0 + (E.indexOf(15) + 1) * bw;
  g += `<line x1="${x15}" x2="${x15}" y1="${T0}" y2="${H}" stroke="var(--text-muted)" stroke-dasharray="3 3"/><text x="${x15 + 3}" y="${T0 - 4}" font-size="9" fill="var(--text-muted)">15 min</text>` +
    `<text x="${L0 + (W - L0) / 2}" y="${H + 27}" font-size="10" text-anchor="middle" fill="var(--text-muted)">minutes (${CM_MODE[m][0].toLowerCase()}, home to school)</text>`;
  h += `<svg class="cmbig" viewBox="0 0 ${W} ${H + B0}" role="img" aria-label="${CM_MODE[m][0]} time histogram">${g}</svg>` +
    `<div class="muted cmleg"><span class="sw" style="background:var(--text-secondary);opacity:.85"></span>${LABEL[scen]}, within 15 min <span class="sw" style="background:var(--text-secondary);opacity:.3"></span>over 15 min` +
    (qs ? ` <span class="sw" style="border:1.5px solid var(--change)"></span>Status Quo` : '') + '</div>';
  // statistics
  const pc = (sh, p) => { const r = cmPct(sh, p); return r.open ? `${r.v}+ min` : `${r.v.toFixed(1)} min`; };
  const pcD = (p) => { const a = cmPct(cs, p), b = cmPct(qs, p); return a.open || b.open ? '' : cmDelta(a.v - b.v, ' min', 1); };
  const mean = o => o[CM_MODE[m][1]];
  const rows = [
    ['Students', cmN(c.r), qs ? cmN(q.r) : '', qs ? cmDelta(c.r - q.r, '', 0, true) : ''],
    ['Mean time', mean(c).toFixed(1) + ' min', qs ? mean(q).toFixed(1) + ' min' : '', qs ? cmDelta(mean(c) - mean(q), ' min', 1) : ''],
    ['Median time', pc(cs, .5), qs ? pc(qs, .5) : '', qs ? pcD(.5) : ''],
    ['75th percentile', pc(cs, .75), qs ? pc(qs, .75) : '', qs ? pcD(.75) : ''],
    ['90th percentile', pc(cs, .9), qs ? pc(qs, .9) : '', qs ? pcD(.9) : ''],
    ...[5, 10, 15, 20, 30, 45].map(x => [`Within ${x} min`, cmP(cmWithin(cs, x)), qs ? cmP(cmWithin(qs, x)) : '',
      qs ? cmDelta(100 * (cmWithin(cs, x) - cmWithin(qs, x)), ' pts', 0, false, true) : ''])];
  h += `<h4>Summary statistics</h4><table class="cmstat"><thead><tr><th></th><th>${isSQ ? 'Status Quo' : LABEL[scen]}</th>${qs ? '<th>Status Quo</th><th>Change</th>' : ''}</tr></thead><tbody>` +
    rows.map(r => `<tr><td>${r[0]}</td><td><b>${r[1]}</b></td>${qs ? `<td>${r[2]}</td><td>${r[3]}</td>` : ''}</tr>`).join('') + '</tbody></table>' +
    `<p class="muted cmnote">Students are ${cmYear} enrollment (${cmYear === D.years[0] ? 'actual' : 'projected'}); where they live, and so their travel times, comes from the 2020 Census school-age residents of each attendance area. ` +
    `Mean is exact; median and percentiles are interpolated within the time bands shown. ${CM_MODE[m][0]} times are along the OpenStreetMap network at ${m === 'walk' ? D.commute.walk_mph + ' mph' : m === 'bike' ? D.commute.bike_mph + ' mph' : 'free-flow speeds (no traffic)'}.</p></div>`;
  return h;
}
// signed change; up = higher is better (green), otherwise higher is worse (red); neutral = grey
function cmDelta(d, unit, dp, neutral = false, up = false) {
  const r = Number(d.toFixed(dp)); if (!r) return '<span class="muted">&plusmn;0</span>';
  const cls = neutral ? 'muted' : (r > 0) === up ? 'cmup' : 'cmdown';
  return `<span class="${cls}">${r > 0 ? '+' : '&minus;'}${Math.abs(r).toFixed(dp).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}${unit}</span>`;
}
function renderCommute() {""")

# ---- styles ----
rep("#commute table { scroll-margin-top: 72px; }", """#commute table { scroll-margin-top: 72px; }
.commutetable td.cmh.go { cursor: pointer; } .commutetable td.cmh.go:hover svg, .commutetable td.cmh.go:focus-visible svg { outline: 2px solid var(--change); outline-offset: 2px; border-radius: 3px; }
.commutetable td.cmh.go:focus-visible { outline: none; }
.cmpane .cmmodes { margin: 10px 0 6px; display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
.cmpane .cmmodes button { font: inherit; font-size: 12.5px; border: 0; background: var(--surface-1); color: var(--text-primary); padding: 3px 12px; cursor: pointer; }
.cmpane .cmmodes button + button { border-left: 1px solid var(--line); } .cmpane .cmmodes button[aria-pressed="true"] { background: #1c3557; color: #fff; }
 .cmpane svg.cmbig { width: 100%; height: auto; display: block; margin: 4px 0; }
.cmpane .cmleg { font-size: 11.5px; } .cmpane .cmleg .sw { display: inline-block; width: 10px; height: 10px; margin: 0 3px 0 8px; vertical-align: -1px; }
.cmpane table.cmstat { min-width: 0; width: 100%; font-size: 12.5px; } .cmpane .cmstat td, .cmpane .cmstat th { padding: 4px 6px; }
.cmpane .cmup { color: var(--up); font-weight: 600; } .cmpane .cmdown { color: var(--down); font-weight: 600; } .cmpane .cmnote { font-size: 11.5px; margin-top: 8px; }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
