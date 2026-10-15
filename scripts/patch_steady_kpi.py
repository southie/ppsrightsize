"""Summary cards at the top of the page: a steady-state card: the long-run kindergarten class (the projection's 2031-35
average, about 2,700) and the district-wide K-12 enrollment it implies once every grade is that size (x about 12.9
students per kindergartner, PSU's grade progression ratios), against fall 2025, and how full the scenario's open
buildings would be then. Clicking it goes to "Room to grow". Uses roomMult / roomAgg / roomDist from
patch_room_to_grow. Code added once.
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

if 'steadyKPI' not in html:
    rep("'classsize', 'splitfeed'];", "'classsize', 'splitfeed', 'room'];")
    rep("""  if (target === 'classsize' || target === 'splitfeed') {
    const t = document.getElementById(target === 'splitfeed' ? 'sftable' : 'classsize'); if (!t) return;""",
        """  if (target === 'classsize' || target === 'splitfeed' || target === 'room') {
    const t = document.getElementById(target === 'splitfeed' ? 'sftable' : target === 'room' ? 'roomkpis' : 'classsize'); if (!t) return;""")
    rep("""t === 'splitfeed' ? 'Show the split feeders by school' :""", """t === 'splitfeed' ? 'Show the split feeders by school' : t === 'room' ? 'Show capacity after the scenarios (Room to grow)' :""")
    rep("""extraKPIs() + staffKPI() + classKPI() + splitKPI();""", """extraKPIs() + staffKPI() + classKPI() + splitKPI() + steadyKPI();""")
    rep("""function renderRoom() {""", """// summary card: steady-state kindergarten and district enrollment (scripts/patch_steady_kpi.py)
function steadyKPI() {
  if (!D.mc?.medium_bands || typeof roomMult !== 'function') return '';
  const M = roomMult(), Mt = M.k5 + M.m68 + M.h912, P = D.mc.psu, Klr = pfaOn ? D.mc.medium_bands.slice(6, 11).reduce((a, r) => a + r[0], 0) / 5 : [2031, 2032, 2033, 2034, 2035].reduce((a, f) => a + P.medium.K[P.falls.indexOf(f)], 0) / 5, ss = Klr * Mt;
  const H = D.mc.hist, now = H.bands['K-5'].slice(-1)[0] + H.bands['6-8'].slice(-1)[0] + H.bands['9-12'].slice(-1)[0];
  const yi = D.years.length - 1, A = roomAgg(scen, yi), dist = roomDist(yi), share = b => dist ? A.enr[b] / dist[{ k5: 1, m68: 2, h912: 3 }[b]] : 1;
  const fill = ['k5', 'm68', 'h912'].reduce((a, b) => a + Klr * M[b] * share(b), 0), cap = A.cap.k5 + A.cap.m68 + A.cap.h912;
  return `<div class="kpi"><div class="v">${Math.round(ss).toLocaleString()}<span class="d" style="color:var(--down)">${Math.round(100 * (ss / now - 1))}% vs fall 2025</span><span class="vt">Steady state: about ${(Math.round(Klr / 100) * 100).toLocaleString()} kindergartners a year</span></div>` +
    `<div class="l">District-wide K-12 (all PPS) once every grade is that size, about the mid-2040s (${Mt.toFixed(1)} students per kindergartner; ${Math.round(now).toLocaleString()} in fall 2025)</div>` +
    `<div class="s">${scen === 'SQ' ? 'Status Quo' : esc(LABEL[scen])}'s open buildings would be <b>${Math.round(100 * fill / cap)}%</b> full <span class="pcs">(${pfaOn ? 'district share of county population, PFA study' : 'PSU’s May 2026 forecast'})</span></div></div>`;
}
function renderRoom() {""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
