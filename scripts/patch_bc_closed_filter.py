"""Building, staffing and land costs by region: a "Closed schools only" checkbox. When on, every region opens and its
school rows are limited to the schools the scenario being viewed closes (region and district totals are unchanged);
under Status Quo a note says no schools close. Remembered in the browser. Runs after patch_building_table. Code added
once.
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

if 'bcClosedOnly' not in html:
    rep("""    <div class="controls tabletools"><button id="bc-expand">Expand all regions</button></div>""",
        """    <div class="controls tabletools"><button id="bc-expand">Expand all regions</button><label><input type="checkbox" id="bc-closed"> Closed schools only</label></div>""")
    rep("const bcOpen = new Set();", """const bcOpen = new Set();
let bcClosedOnly = false;
try { bcClosedOnly = localStorage.getItem('rsBcClosed') === '1'; } catch (e) {}""")
    rep("""isReg = rn !== 'District', open = bcOpen.has(rn);""", """isReg = rn !== 'District', open = bcClosedOnly || bcOpen.has(rn);""")
    rep("""    if (!isReg || !open) continue;
    for (const k of [...keys].sort(byStatusName)) {""", """    if (!isReg || !open) continue;
    if (bcClosedOnly && (isSQ || !keys.some(k => det[k]?.closed))) {
      h += `<tr class="srow"><td colspan="11" class="muted" style="text-align:left">${isSQ ? 'No schools close under Status Quo; pick a scenario.' : 'No schools close in this region.'}</td></tr>`; continue;
    }
    for (const k of [...keys].sort(byStatusName)) {
      if (bcClosedOnly && !det[k]?.closed) continue;""")
    rep("""  const ex = document.getElementById('bc-expand');""", """  const cb = document.getElementById('bc-closed');
  if (cb) { cb.checked = bcClosedOnly; cb.onchange = () => { bcClosedOnly = cb.checked; try { localStorage.setItem('rsBcClosed', bcClosedOnly ? '1' : '0'); } catch (e) {} renderBuildings(); }; }
  const ex = document.getElementById('bc-expand');""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
