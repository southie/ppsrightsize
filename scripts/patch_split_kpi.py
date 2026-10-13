"""Split feeders in the summary cards at the top of the page: split-feeder schools under the scenario (vs Status Quo),
how many it resolves, and the students on a smaller pathway in the split-feeder card's school year. Clicking it goes
to the split-feeder table; changing that table's year updates it. Runs after patch_split_feeders. Code added once.
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

if 'splitKPI' not in html:
    rep("""'cost', 'land', 'staff', 'classsize'];""", """'cost', 'land', 'staff', 'classsize', 'splitfeed'];""")
    rep("""  if (target === 'classsize') {
    const t = document.getElementById('classsize'); if (!t) return;""",
        """  if (target === 'classsize' || target === 'splitfeed') {
    const t = document.getElementById(target === 'splitfeed' ? 'sftable' : 'classsize'); if (!t) return;""")
    rep("""t === 'classsize' ? 'Show class sizes and teacher loads by grade' :""",
        """t === 'classsize' ? 'Show class sizes and teacher loads by grade' : t === 'splitfeed' ? 'Show the split feeders by school' :""")
    rep("""extraKPIs() + staffKPI() + classKPI();""", """extraKPIs() + staffKPI() + classKPI() + splitKPI();""")
    rep("""function renderSplitFeeders() {""", """// summary card (scripts/patch_split_kpi.py)
function splitKPI() {
  if (!D.feeders) return '';
  const yi = D.years.indexOf(sfYear), isSQ = scen === 'SQ', S0 = sfSplits('SQ', yi), S1 = isSQ ? S0 : sfSplits(scen, yi);
  const n0 = Object.keys(S0).length, n1 = Object.keys(S1).length, d = n1 - n0;
  const minor = S => Math.round(Object.values(S).reduce((a, v) => a + (v.minor || 0), 0)), m0 = minor(S0), m1 = minor(S1);
  const fixed = Object.keys(S0).filter(k => !S1[k]).length, added = Object.keys(S1).filter(k => !S0[k]).length;
  const nm = k => esc(short(byKey[k]?.name || k));
  return `<div class="kpi"><div class="v">${n1}${!isSQ && d ? `<span class="d" style="color:${d > 0 ? 'var(--down)' : 'var(--up)'}">${d > 0 ? '+' : '&minus;'}${Math.abs(d)} vs SQ</span>` : ''}</div>` +
    `<div class="l">Split-feeder schools (neighborhood students go on to two different schools)</div>` +
    `<div class="s">${isSQ ? '' : `<b>${fixed}</b> resolved${added ? `, <b>${added}</b> new` : ''} <span class="pcs">(Status Quo ${n0})</span><br>`}` +
    `About <b>${m1.toLocaleString()}</b> students on a smaller pathway, ${sfYear}${isSQ || m1 === m0 ? '' : ` <span class="pcs">(Status Quo ${m0.toLocaleString()})</span>`}<br>` +
    `<span class="pcs" style="white-space:normal">${isSQ ? 'Split' : 'Still split'}: ${Object.keys(S1).sort().map(nm).join(', ') || 'none'}</span></div></div>`;
}
function renderSplitFeeders() {""")
    rep("""sel.onchange = () => { sfYear = sel.value; renderSplitFeeders(); }; }""",
        """sel.onchange = () => { sfYear = sel.value; renderSplitFeeders(); renderKPIs(); }; }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
