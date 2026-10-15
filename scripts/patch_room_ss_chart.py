"""Room to grow: a bar chart of each open school's steady-state enrollment, grouped by school type (K-5, K-8, middle, high),
laid out like the General Fund cost-per-student chart (a row per school, collapsible group headings).
  Steady state: the long-run district kindergarten class (2031-35 average of the page's projection, as in the steady
  state card) x the school's enrollment per district kindergartner (roomFill: each grade band at steady state, PSU's
  grade progression ratios, at the school's share of the district's band in the chosen year).
  Bar: steady-state enrollment, green at or above the school's size threshold, red below; tick: projected enrollment in
  the chosen year; bracket: 2021 capacity; line down each group: the threshold. Group heading: schools below the
  threshold at steady state, enrollment / seats. Follows the scenario and the section's year.
Code added once.
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

if 'renderRoomSS' not in html:
    rep("""    <div id="roomscale"></div>
    <h3 class="cshead">By region</h3>""",
        """    <div id="roomscale"></div>
    <h3 class="cshead">Steady-state enrollment by school</h3>
    <p class="sub" id="roomsssub"></p>
    <div class="controls tabletools"><button id="roomss-shut">Collapse all</button></div>
    <div class="gfperwrap" id="roomss"></div>
    <h3 class="cshead">By region</h3>""")
    rep("""    if (per > 0) out[k] = { K: fc / per, v, fc, th, Kt: th / per };""",
        """    if (per > 0) out[k] = { K: fc / per, v, fc, th, Kt: th / per, per, t };""")
    rep("""function renderRoom() {""", r"""// steady-state enrollment by school, grouped by type (scripts/patch_room_ss_chart.py)
const roomSSShut = new Set();
function renderRoomSS(sc, yi) {
  const host = document.getElementById('roomss'); if (!host) return;
  const FILL = roomFill(sc, yi), lab = sc === 'SQ' ? 'Status Quo' : LABEL[sc], n0 = v => Math.round(v).toLocaleString();
  const Klr = D.mc?.medium_bands ? D.mc.medium_bands.slice(6, 11).reduce((a, r) => a + r[0], 0) / 5 : 2700;
  const TYPES = [['ES', 'K-5'], ['K8', 'K-8'], ['MS', 'Middle (6-8)'], ['HS', 'High (9-12)']];
  const groups = TYPES.map(([t, gl]) => {
    const g = Object.entries(FILL).filter(([, f]) => f.t === t).map(([k, f]) => ({ k, ss: Klr * f.per, v: f.v, fc: f.fc, th: f.th })).sort((a, b) => b.ss - a.ss);
    return g.length ? { t, gl, g, th: D.thresholds[t] } : null;
  }).filter(Boolean);
  const W = 900, Lm = 210, R = 60, BH = 17, GH = 40, GAP = 14, T = 8, AX = 30;
  const xhi = Math.ceil(Math.max(...groups.flatMap(G => G.g.flatMap(r => [r.ss, r.v, r.fc]))) * 1.04 / 250) * 250, step = xhi > 2000 ? 250 : 100;
  const x = v => Lm + (W - Lm - R) * v / xhi, nRows = G => roomSSShut.has(G.t) ? 0 : G.g.length;
  const H = T + groups.reduce((a, G) => a + GH + nRows(G) * BH + GAP, 0) + AX, plotBot = H - AX;
  let s = '', y0 = T;
  for (let v = 0; v <= xhi + 1e-9; v += step) s += `<line x1="${x(v)}" x2="${x(v)}" y1="${T}" y2="${plotBot}" stroke="var(--line)"/>` + (v % (step * 2) === 0 ? `<text x="${x(v)}" y="${plotBot + 14}" text-anchor="middle" font-size="10.5" fill="var(--text-muted)">${v.toLocaleString()}</text>` : '');
  s += `<text x="${(Lm + W - R) / 2}" y="${plotBot + 27}" text-anchor="middle" font-size="10.5" fill="var(--text-muted)">Students at steady state (about ${n0(Math.round(Klr / 10) * 10)} kindergartners a year district-wide)</text>`;
  for (const G of groups) {
    const shut = roomSSShut.has(G.t), top = y0 + GH, bot = top + nRows(G) * BH, below = G.g.filter(r => r.ss < r.th).length;
    const sss = G.g.reduce((a, r) => a + r.ss, 0), cap = G.g.reduce((a, r) => a + r.fc, 0), avgSS = sss / G.g.length, avgV = G.g.reduce((a, r) => a + r.v, 0) / G.g.length;   // average school size
    // first quartile (25th percentile, linear interpolation) of school sizes: a quarter of the schools are smaller
    const q1 = arr => { const a = arr.slice().sort((p, q) => p - q), i = 0.25 * (a.length - 1), lo = Math.floor(i); return a[lo] + (a[Math.min(lo + 1, a.length - 1)] - a[lo]) * (i - lo); };
    const q1SS = q1(G.g.map(r => r.ss)), q1V = q1(G.g.map(r => r.v));
    s += `<g data-rssg="${G.t}" role="button" tabindex="0" aria-expanded="${!shut}" style="cursor:pointer"><title>${shut ? 'Show' : 'Hide'} the ${G.gl} schools</title>` +
      `<rect x="0" y="${y0 + 2}" width="${W}" height="${GH - 6}" fill="var(--surface-2, rgba(0,0,0,.035))"/>` +
      `<text x="8" y="${y0 + 18}" font-size="13" font-weight="700" fill="var(--text-primary)">${shut ? '&#9656;' : '&#9662;'} ${G.gl} (${G.g.length} schools)${shut ? ' <tspan font-size="10.5" font-weight="400" fill="var(--text-muted)">click to show</tspan>' : ''}<tspan font-size="11" font-weight="400" fill="var(--text-muted)">  &#183;  </tspan><tspan font-size="11.5" fill="#b45309">average school ${n0(avgSS)} at steady state</tspan><tspan font-size="11" font-weight="400" fill="var(--text-muted)"> (${n0(avgV)} in ${esc(roomYear)})  &#183;  </tspan><tspan font-size="11.5" fill="#0e7490">1st quartile ${n0(q1SS)}</tspan><tspan font-size="11" font-weight="400" fill="var(--text-muted)"> (${n0(q1V)})  &#183;  threshold ${G.th}</tspan></text>` +
      `<text x="8" y="${y0 + 32}" font-size="10.5"><tspan fill="var(--down)" font-weight="700">${below} below</tspan><tspan fill="var(--text-muted)"> the ${G.th}-student threshold at steady state &middot; ${n0(sss)} students in ${n0(cap)} seats (${Math.round(100 * sss / cap)}% full) &middot; ${G.g.filter(r => r.v < r.th).length} below it in ${esc(roomYear)}</tspan></text></g>`;
    if (shut) { y0 = bot + GAP; continue; }
    G.g.forEach((r, j) => {
      const yy = top + j * BH, nm = short(byKey[r.k]?.name || r.k), ok = r.ss >= r.th, col = ok ? 'var(--up)' : 'var(--down)', bh = BH - 5;
      s += `<text x="${Lm - 8}" y="${yy + BH / 2 + 3}" text-anchor="end" font-size="11" fill="var(--text-secondary)">${esc(nm)}</text>` +
        `<rect x="${x(0)}" y="${yy + 2}" width="${Math.max(0.5, x(r.ss) - x(0))}" height="${bh}" fill="${col}" opacity=".78"><title>${esc(`${nm}: about ${n0(r.ss)} students at steady state (${lab}); ${n0(r.v)} projected in ${roomYear}; size threshold ${r.th}${ok ? ` (${n0(r.ss - r.th)} above)` : ` (${n0(r.th - r.ss)} short)`}; 2021 capacity ${n0(r.fc)} (${Math.round(100 * r.ss / r.fc)}% full at steady state)`)}</title></rect>` +
        `<line x1="${x(r.v)}" x2="${x(r.v)}" y1="${yy + 1}" y2="${yy + bh + 3}" stroke="var(--text-primary)" stroke-width="2"><title>${esc(`${nm}: ${n0(r.v)} projected in ${roomYear}`)}</title></line>` +
        `<path d="M${x(r.fc) - 3},${yy + 2}H${x(r.fc)}V${yy + bh + 2}H${x(r.fc) - 3}" fill="none" stroke="var(--text-muted)" stroke-width="1.4"><title>${esc(`${nm}: 2021 capacity ${n0(r.fc)}`)}</title></path>` +
        `<text x="${Math.max(x(r.ss), x(r.fc), x(r.v)) + 5}" y="${yy + 2 + bh / 2 + 3.5}" font-size="9.5" fill="var(--text-muted)">${n0(r.ss)}</text>`;
    });
    s += `<line x1="${x(G.th)}" x2="${x(G.th)}" y1="${top - 2}" y2="${bot + 2}" stroke="#6d28d9" stroke-width="2.2" stroke-dasharray="6 3"><title>${G.gl} size threshold: ${G.th} students</title></line>` +
      `<line x1="${x(avgSS)}" x2="${x(avgSS)}" y1="${top - 2}" y2="${bot + 2}" stroke="#b45309" stroke-width="2.2"><title>${G.gl} average school at steady state: ${n0(avgSS)} students (${n0(avgV)} projected in ${roomYear}; ${G.g.length} schools)</title></line>` +
      `<line x1="${x(q1SS)}" x2="${x(q1SS)}" y1="${top - 2}" y2="${bot + 2}" stroke="#0e7490" stroke-width="2" stroke-dasharray="3 2"><title>${G.gl} 1st quartile at steady state: ${n0(q1SS)} students; a quarter of the ${G.g.length} schools are smaller (${n0(q1V)} projected in ${roomYear})</title></line>`;
    y0 = bot + GAP;
  }
  host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px;height:auto" role="img" aria-label="Steady-state enrollment by school, grouped by type">${s}</svg>` +
    `<div class="rplegend" style="margin-top:2px"><span><i class="k" style="height:9px;width:14px;background:var(--up);opacity:.78;border:none"></i>steady state, at or above threshold</span><span><i class="k" style="height:9px;width:14px;background:var(--down);opacity:.78;border:none"></i>below threshold</span>` +
    `<span><i class="k" style="border-top:2.2px dashed #6d28d9;width:18px"></i>size threshold</span><span><i class="k" style="border-top:2.2px solid #b45309;width:18px"></i>average school, steady state</span><span><i class="k" style="border-top:2px dashed #0e7490;width:18px"></i>1st quartile (a quarter of schools smaller)</span><span><i class="k" style="border-left:2px solid var(--text-primary);height:10px;width:0;border-top:none"></i> projected, ${esc(roomYear)}</span><span><i class="k" style="border:1.4px solid var(--text-muted);border-left:none;height:9px;width:4px"></i> 2021 capacity</span></div>`;
  const tog = t => { roomSSShut.has(t) ? roomSSShut.delete(t) : roomSSShut.add(t); renderRoomSS(sc, yi); };
  host.querySelectorAll('[data-rssg]').forEach(g => { g.onclick = () => tog(g.dataset.rssg); g.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tog(g.dataset.rssg); } }; });
  const sb = document.getElementById('roomss-shut');
  if (sb) { sb.textContent = groups.every(G => roomSSShut.has(G.t)) ? 'Expand all' : 'Collapse all'; sb.onclick = () => { const all = groups.every(G => roomSSShut.has(G.t)); groups.forEach(G => all ? roomSSShut.delete(G.t) : roomSSShut.add(G.t)); renderRoomSS(sc, yi); }; }
  const nAll = groups.reduce((a, G) => a + G.g.length, 0), nBelow = groups.reduce((a, G) => a + G.g.filter(r => r.ss < r.th).length, 0);
  const sub = document.getElementById('roomsssub');
  if (sub) sub.innerHTML = `Each open school's enrollment once every grade is grown from the long-run kindergarten class (about ${n0(Math.round(Klr / 10) * 10)} a year district-wide, the 2031-35 average of this page's projection), at the school's ${esc(roomYear)} share of the district's students in each grade band (PSU's grade progression ratios), ${esc(lab)}. <b>${nBelow} of ${nAll}</b> schools would be below their size threshold. Schools run from largest to smallest within each type; click a heading to collapse it.`;
}
function renderRoom() {""")
    rep("""  const tb = document.getElementById('roomtable'); tb.innerHTML = h + '</tbody></table>';""",
        """  const tb = document.getElementById('roomtable'); tb.innerHTML = h + '</tbody></table>';
  renderRoomSS(sc, yi);""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
