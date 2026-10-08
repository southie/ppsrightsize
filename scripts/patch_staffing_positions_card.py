"""Staffing KPI card and staffing summary sentence lead with positions no longer needed; dollars become secondary."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

a = html.index('function staffKPI() {'); b = html.index('function schoolRows(rn) {')
html = html[:a] + r"""function staffKPI() {
  const s = staffDelta(D.schools.map(x => x.key));
  // headline: positions (licensed-equivalent FTE); split administration vs teachers and direct student support; dollars secondary
  const pos = v => staffUSD(Math.abs(v)).replace('&minus;', '');
  const f1 = v => Math.abs(v).toFixed(1);
  if (scen === 'SQ') {
    const sh = v => `${Math.round(100 * v / s.base.fte)}%`;
    return `<div class="kpi"><div class="v">${Math.round(s.base.fte).toLocaleString()}<span class="d" style="color:var(--text-muted)">positions</span></div>` +
      `<div class="l">School positions under PPS's staffing formula, ${staffYear} (licensed-equivalent FTE)</div>` +
      `<div class="s">Administration: <b>${f1(s.base.aFte)}</b> <span class="pcs">(${sh(s.base.aFte)})</span><br>` +
      `Teachers &amp; direct support: <b>${f1(s.base.tFte)}</b> <span class="pcs">(${sh(s.base.tFte)})</span><br>` +
      `Cost: <b>${pos(s.base.usd)}</b> a year (salary + benefits, 2026-27 $)</div></div>`;
  }
  return `<div class="kpi"><div class="v">${Math.round(Math.abs(s.fte))}<span class="d" style="color:var(--text-muted)">positions &middot; ${pctOf(s.fte, s.base.fte)} vs SQ</span></div>` +
    `<div class="l">School positions no longer needed under PPS's staffing formula, ${staffYear} vs Status Quo (licensed-equivalent FTE)</div>` +
    `<div class="s">Administration: <b>${f1(s.aFte)}</b>${pcS(s.aFte, s.base.aFte)}<br>` +
    `Teachers &amp; direct support: <b>${f1(s.tFte)}</b>${pcS(s.tFte, s.base.tFte)}<br>` +
    `Cost: about <b>${pos(s.usd)}</b> a year${pcS(s.usd, s.base.usd)} (salary + benefits, 2026-27 $)</div></div>`;
}
""" + html[b:]

# staffing section summary sentence: positions first, dollars after
rep("""    : `${LABEL[scen]} in ${staffYear}, compared with Status Quo the same year: about <b>${staffUSD(staffCost(dsq) - staffCost(dist)).replace('&minus;', '')}</b> a year in formula staffing (2026-27 dollars, salary plus benefits), from about <b>${(dsq.total - dist.total).toFixed(0)}</b> fewer formula positions (licensed-equivalent FTE): """,
    """    : `${LABEL[scen]} in ${staffYear}, compared with Status Quo the same year: about <b>${(dsq.total - dist.total).toFixed(0)}</b> formula positions no longer needed (licensed-equivalent FTE), about <b>${staffUSD(staffCost(dsq) - staffCost(dist)).replace('&minus;', '')}</b> a year in salary plus benefits (2026-27 dollars): """)
open(PAGE, 'w', encoding='utf-8').write(html)
print('patched')
