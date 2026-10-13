"""Link buttons for every chart: the main map (with its grade filter, layers, attendance boundaries, travel-time mode and
the school whose panel is open), the General Fund cost per student chart and the closures chart (view and enrollment
year), and the homeschooling trends table, in addition to the tables patch_deeplinks covers. Parameters:
  map:     mg (grades), mly (layers: bus=posted|gen, w walk, b bike, d drive, h hazards, f closure arrows), mbd
           (boundary grades), mis (travel time mode), ms (school panel)
  gfper / gfclose: gfm (pp | sub), gfy (year)
Runs after patch_deeplinks, patch_map_layers, patch_hazards, patch_map_defaults and patch_gf_per_student. Code added once.
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

if "['gfper', 'gfper']" not in html:
    rep("""['virtual', 'virtual'], ['fcacc', 'fcacc']];""",
        """['virtual', 'virtual'], ['fcacc', 'fcacc'],
  ['map', 'map'], ['gfper', 'gfper'], ['gfclose', 'gfclose'], ['hstrends', 'hsdistrict']];""")
    rep("""  if (key === 'report' && rpKey) { p.set('school', rpKey); p.set('year', rpYear); }
  p.set('t', key);""", """  if (key === 'report' && rpKey) { p.set('school', rpKey); p.set('year', rpYear); }
  if (key === 'gfper' || key === 'gfclose') { p.set('gfm', gfMode); p.set('gfy', gfYear); }
  if (key === 'map') {
    p.set('mg', gBand || 'all');
    p.set('mly', [mlBus ? 'bus-' + mlBus : '', mlWalk ? 'w' : '', mlBike ? 'b' : '', mlDrive ? 'd' : '', mlHz ? 'h' : '', showFlows ? 'f' : ''].filter(Boolean).join('.') || 'none');
    if (bBand) p.set('mbd', bBand);
    if (isoMode) p.set('mis', isoMode);
    if (isoSel && byKey[isoSel]) p.set('ms', isoSel);
  }
  p.set('t', key);""")
    rep("""  LINK_TARGET = q.get('t');""", """  if (['pp', 'sub'].includes(q.get('gfm'))) gfMode = q.get('gfm');
  if (D.years.includes(q.get('gfy'))) gfYear = q.get('gfy');
  if (q.get('mg')) gBand = q.get('mg') === 'all' ? '' : ['k5', '68', '912'].includes(q.get('mg')) ? q.get('mg') : gBand;
  if (q.get('mly')) { const f = q.get('mly').split('.'), bus = f.find(x => x.startsWith('bus-'));
    mlBus = bus ? bus.slice(4) : ''; mlWalk = f.includes('w'); mlBike = f.includes('b'); mlDrive = f.includes('d'); mlHz = f.includes('h'); showFlows = f.includes('f'); }
  if (q.has('mbd') || q.get('t') === 'map') bBand = ['k5', '68', '912'].includes(q.get('mbd')) ? q.get('mbd') : '';
  if (q.has('mis') || q.get('t') === 'map') isoMode = ['walk', 'bike', 'drive'].includes(q.get('mis')) ? q.get('mis') : '';
  LINK_MS = byKey[q.get('ms')] ? q.get('ms') : null;
  LINK_TARGET = q.get('t');""")
    rep("""let LINK_TARGET = null;""", """let LINK_TARGET = null, LINK_MS = null;""")
    rep("""renderAll();
if (LINK_TARGET && typeof document.querySelectorAll === 'function') setTimeout(() => {""", """renderAll();
if (LINK_MS && typeof openDock === 'function') { const s_ = byKey[LINK_MS]; openDock(() => popup(s_), ll(s_), s_.key); }
if (LINK_TARGET && typeof document.querySelectorAll === 'function') setTimeout(() => {""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
