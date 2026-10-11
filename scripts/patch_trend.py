"""Small schools and staffing cost over time: a table after the Scenario impact by region table, one row per school
year (2025-26 to 2035-36):
  schools below their size threshold (K-5 360, K-8 and middle 500, high 1,100) each year, for Status Quo,
          Scenario A, Scenario B and a custom scenario when one is built (this page's enrollment projection; before
          the scenarios take effect every scenario is Status Quo)
  then cumulative staffing cost against Status Quo: each scenario's yearly staffing-formula cost (salary + benefits,
          2026-27 dollars, the class sizes set in Staffing impact) minus Status Quo's, summed from 2025-26
Counts show the share of that scenario's open schools; the scenario being viewed is shaded. Code added once.
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

if 'function renderTrend' not in html:
    rep("""  <section class="card">
    <h2>Building, staffing and land costs by region</h2>""", """  <section class="card">
    <h2>Small schools and staffing cost over time</h2>
    <p class="sub">Schools below their size threshold each year (K-5 under 360 students, K-8 and middle under 500, high under 1,100), from this page's enrollment projection, as a count and a share of that scenario's open schools; and cumulative school staffing cost compared with Status Quo under PPS's staffing formula (salary + benefits, 2026-27 dollars; class sizes as set in Staffing impact), summed from ${D.years[0]}; below zero is savings. The scenarios take effect in ${D.impl_year}; before that they match Status Quo. Hover a point for the values.</p>
    <div id="trend"></div>
  </section>

  <section class="card">
    <h2>Building, staffing and land costs by region</h2>""".replace('${D.years[0]}', '2025-26').replace('${D.impl_year}', '2027-28'))
    rep("function renderAll() {", r"""// ---------- small schools and staffing cost over time ----------
const TR_COL = { SQ: 'var(--none)', A: 'var(--change)', B: '#0f9b78', C: '#b0369a' };
function trendData() {
  const Y = D.years, keys = Object.keys(D.region_of), impl = Y.indexOf(D.impl_year), cols = ['SQ', 'A', 'B', ...(D.detail.C ? ['C'] : [])];
  const below = {}, open = {}, cost = {};
  for (const s of cols) {
    open[s] = Y.map((_, i) => keys.filter(k => D.series[s]?.[k]?.[i] != null).length);
    below[s] = Y.map((_, i) => keys.filter(k => {
      const v = D.series[s]?.[k]?.[i]; if (v == null) return false;
      const t = (i < impl ? D.types.SQ[k] : D.types[s]?.[k]) || D.types.SQ[k];
      return v < (D.thresholds[t] ?? 0) - 1e-9;
    }).length);
    cost[s] = Y.map((_, i) => staffCost(staffAgg(keys, i < impl ? 'SQ' : s, i)));   // before the scenarios take effect: Status Quo
  }
  const cum = {};
  for (const s of cols) { let a = 0; cum[s] = Y.map((_, i) => (a += cost[s][i] - cost.SQ[i])); }
  return { Y, cols, below, open, cum, cost, impl };
}
function renderTrend() {
  const host = document.getElementById('trend'); if (!host) return;
  const { Y, cols, below, open, cum, cost, impl } = trendData(), sc = cols.filter(s => s !== 'SQ'), cur = scen;
  const money = v => (v < -5e5 ? '&minus;' : v > 5e5 ? '+' : '') + '$' + (Math.abs(v) >= 1e9 ? (Math.abs(v) / 1e9).toFixed(2) + 'B' : Math.round(Math.abs(v) / 1e6) + 'M');
  const cc = s => s === cur ? ' class="cur"' : '';
  let h = `<table class="trtable"><thead><tr><th rowspan="2">School year</th><th colspan="${cols.length}">Schools below size threshold<br><span style="font-weight:400">count (share of open schools)</span></th>` +
    `<th colspan="${sc.length}">Cumulative staffing cost vs Status Quo<br><span style="font-weight:400">from ${Y[0]}; below zero is savings</span></th></tr><tr>` +
    cols.map(s => `<th${cc(s)}><i class="trk" style="background:${TR_COL[s]}"></i>${esc(LABEL[s])}</th>`).join('') +
    sc.map(s => `<th${cc(s)}><i class="trk" style="background:${TR_COL[s]}"></i>${esc(LABEL[s])}</th>`).join('') + '</tr></thead><tbody>';
  Y.forEach((y, i) => {
    h += `<tr${i === impl ? ' class="trimpl"' : ''}><td>${y}${i === impl ? '<span class="muted" style="display:block;font-size:11px">scenarios take effect</span>' : ''}</td>` +
      cols.map(s => { const d = below[s][i] - below.SQ[i];
        return `<td${cc(s)} title="${esc(`${LABEL[s]}, ${y}: ${below[s][i]} of ${open[s][i]} open schools below their size threshold`)}"><span class="main">${below[s][i]}</span> <span class="muted">(${Math.round(100 * below[s][i] / Math.max(1, open[s][i]))}%)</span>` +
          (s !== 'SQ' && d ? `<span class="delta ${d < 0 ? 'up' : 'down'}" style="display:block">${d > 0 ? '+' : '&minus;'}${Math.abs(d)} vs SQ</span>` : '') + '</td>'; }).join('') +
      sc.map(s => `<td${cc(s)} title="${esc(`${LABEL[s]}, ${y}: ${money(cost[s][i] - cost.SQ[i]).replace('&minus;', '-')} that year (staffing ${money(cost[s][i]).replace('+', '')} vs Status Quo ${money(cost.SQ[i]).replace('+', '')})`)}">` +
        `<span class="main">${Math.abs(cum[s][i]) < 5e5 ? '$0' : money(cum[s][i])}</span>${i >= impl && Math.abs(cost[s][i] - cost.SQ[i]) >= 5e5 ? `<span class="muted" style="display:block;font-size:11px">${money(cost[s][i] - cost.SQ[i])} that year</span>` : ''}</td>`).join('') + '</tr>';
  });
  host.innerHTML = h + '</tbody></table>';
}
function renderAll() {""")
    rep("renderEndpoints(); renderBuildings();", "renderEndpoints(); renderTrend(); renderBuildings();")
    rep(".hstable { min-width: 640px; }", ".hstable { min-width: 640px; }\n.trtable { min-width: 700px; } .trtable td, .trtable th { text-align: right; } .trtable td:first-child, .trtable th:first-child { text-align: left; } .trtable th.cur, .trtable td.cur { background: var(--surface-2); } .trtable .trk { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; } .trtable tr.trimpl td { border-top: 2px dashed var(--line); }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
