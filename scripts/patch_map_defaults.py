"""Main map defaults and an arrows toggle:
  - "Closure arrows" checkbox in the Layers row: the lines and arrows from closing schools to receiving schools (and the
    other program / grade moves) can be turned off; on by default
  - private-school alternatives (violet dotted lines) off by default
  - defaults: grades K-5, attendance boundaries off, travel time to school off, bike corridors on, bus routes off
Settings are remembered in the browser under new keys (rsGrade2, rsBand2, rsIso2, rsMapLayers2, rsFlows, rsAlts), so
every browser starts once from these defaults. Runs after patch_map_layers. Code changed once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b, n=1):
    global html
    assert html.count(a) == n, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'id="ml-flows"' not in html:
    # private alternatives off by default (remembered)
    rep("let showPrivate = true, hidePreK = true, showAlts = true;",
        "let showPrivate = true, hidePreK = true, showAlts = false, showFlows = true;\n"
        "try { showAlts = localStorage.getItem('rsAlts') === '1'; showFlows = localStorage.getItem('rsFlows') !== '0'; } catch (e) {}")
    rep("  const a = document.getElementById('altbox'); if (a) a.onchange = () => { showAlts = a.checked; renderAlts(); };",
        "  const a = document.getElementById('altbox'); if (a) a.onchange = () => { showAlts = a.checked; try { localStorage.setItem('rsAlts', showAlts ? '1' : '0'); } catch (e) {} renderAlts(); };")
    # closure arrows toggle
    rep("""  flowLayer.clearLayers(); lHits = lHits.filter(h => h.set !== 'f'); if (bHover && bHover.set === 'f') setBHover(null);
  if (scen === 'SQ') return;""", """  flowLayer.clearLayers(); lHits = lHits.filter(h => h.set !== 'f'); if (bHover && bHover.set === 'f') setBHover(null);
  if (scen === 'SQ' || !showFlows) return;""")
    rep("""<span class="isoctl-lyr"></span>""", "", 0)
    rep("""    <div class="controls isoctl maplyr"><span>Layers</span>""",
        """    <div class="controls isoctl maplyr"><span>Layers</span><label><input type="checkbox" id="ml-flows"> Closure arrows</label>""")
    rep("""  bs.value = mlBus; bk.checked = mlBike; dr.checked = mlDrive;""",
        """  bs.value = mlBus; bk.checked = mlBike; dr.checked = mlDrive;
  const fl = document.getElementById('ml-flows');
  if (fl) { fl.checked = showFlows; fl.disabled = scen === 'SQ'; fl.parentElement.title = scen === 'SQ' ? 'Pick a scenario to see closure arrows' : 'Lines and arrows from each closing school to the schools that receive its students';
    fl.onchange = () => { showFlows = fl.checked; try { localStorage.setItem('rsFlows', showFlows ? '1' : '0'); } catch (e) {} renderFlows(); }; }""")
    # defaults: K-5, boundaries off, travel time off, bike corridors on
    rep("try { gBand = localStorage.getItem('rsGrade') || ''; } catch (e) {}", "gBand = 'k5';\ntry { gBand = localStorage.getItem('rsGrade2') ?? 'k5'; } catch (e) {}")
    rep("localStorage.setItem('rsGrade', gBand)", "localStorage.setItem('rsGrade2', gBand)")
    rep("try { isoMode = localStorage.getItem('rsIso') ?? 'walk'; } catch (e) {}", "isoMode = '';\ntry { isoMode = localStorage.getItem('rsIso2') ?? ''; } catch (e) {}")
    rep("let isoMode = 'walk', isoSel = null;", "let isoMode = '', isoSel = null;")
    rep("localStorage.setItem('rsIso', isoMode)", "localStorage.setItem('rsIso2', isoMode)")
    rep("try { bBand = localStorage.getItem('rsBand') || ''; bChanged", "try { bBand = localStorage.getItem('rsBand2') || ''; bChanged")
    rep("localStorage.setItem('rsBand', bBand)", "localStorage.setItem('rsBand2', bBand)", 2)
    rep("let mlBus = '', mlBike = false, mlDrive = false;", "let mlBus = '', mlBike = true, mlDrive = false;")
    rep("JSON.parse(localStorage.getItem('rsMapLayers') || 'null')", "JSON.parse(localStorage.getItem('rsMapLayers2') || 'null')")
    rep("localStorage.setItem('rsMapLayers', JSON.stringify", "localStorage.setItem('rsMapLayers2', JSON.stringify")
# areas that change school (gold shading on the attendance boundaries): off by default (key rsBandChanged2)
if 'rsBandChanged2' not in html:
    rep("let bBand = '', bChanged = true;", "let bBand = '', bChanged = false;")
    rep("bChanged = localStorage.getItem('rsBandChanged') !== '0';", "bChanged = localStorage.getItem('rsBandChanged2') === '1';")
    rep("localStorage.setItem('rsBandChanged', bChanged ? '1' : '0')", "localStorage.setItem('rsBandChanged2', bChanged ? '1' : '0')")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
