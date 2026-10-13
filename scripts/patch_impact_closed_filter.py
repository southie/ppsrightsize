"""Scenario impact by region table: a "Closed schools only" checkbox. When on, every region opens and its school rows are
limited to the schools the scenario being viewed closes (region and district rows are unchanged); under Status Quo a
note says no schools close. Remembered in the browser and carried by the table's Link (exc=1). Runs after
patch_deeplinks. Code added once.
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

if 'exClosed' not in html:
    rep("""<button id="expandall">Expand all regions</button><label><input type="checkbox" id="showrec">""",
        """<button id="expandall">Expand all regions</button><label><input type="checkbox" id="exclosed"> Closed schools only</label><label><input type="checkbox" id="showrec">""")
    rep("""function schoolRows(rn) {
  const det = D.detail[scen], sqd = D.detail.SQ;
  const names = Object.keys(D.region_of).filter(n => D.region_of[n] === rn);""",
        """// closed schools only (scripts/patch_impact_closed_filter.py)
let exClosed = false;
try { exClosed = localStorage.getItem('rsExClosed') === '1'; } catch (e) {}
function schoolRows(rn) {
  const det = D.detail[scen], sqd = D.detail.SQ;
  const names = Object.keys(D.region_of).filter(n => D.region_of[n] === rn && (!exClosed || det[n]?.closed));
  if (exClosed && !names.length) return `<tr class="srow"><td colspan="${endpointCols().length}" class="muted" style="text-align:left">${scen === 'SQ' ? 'No schools close under Status Quo; pick a scenario.' : 'No schools close in this region.'}</td></tr>`;""")
    rep("""    const isReg = rn !== 'District', open = expanded.has(rn);
    const n = isReg ? Object.values(D.region_of).filter(r => r === rn).length : 0;""",
        """    const isReg = rn !== 'District', open = exClosed || expanded.has(rn);
    const n = isReg ? Object.values(D.region_of).filter(r => r === rn).length : 0;""")
    rep("""document.getElementById('showrec').onchange = renderEndpoints;""",
        """document.getElementById('showrec').onchange = renderEndpoints;
{ const xc = document.getElementById('exclosed');
  if (xc) { xc.checked = exClosed; xc.onchange = () => { exClosed = xc.checked; try { localStorage.setItem('rsExClosed', exClosed ? '1' : '0'); } catch (e) {} renderEndpoints(); }; } }""")
    rep("""  if (key === 'endpoints') { if (expanded.size) p.set('ex', rIdx(expanded));""",
        """  if (key === 'endpoints') { if (exClosed) p.set('exc', '1'); if (expanded.size) p.set('ex', rIdx(expanded));""")
    rep("""  if (q.get('ex')) rSet(q.get('ex'), expanded);""",
        """  if (q.get('ex')) rSet(q.get('ex'), expanded);
  if (q.has('exc') || q.get('t') === 'endpoints') { exClosed = q.get('exc') === '1'; const xc = document.getElementById('exclosed'); if (xc) xc.checked = exClosed; }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
