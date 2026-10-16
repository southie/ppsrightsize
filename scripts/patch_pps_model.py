"""PPS's own model results (source/pps-powerbi/pps-model.json, scripts/build_pps_model.py) on the page.
  - "PPS model results" switch beside the scenario buttons, on by default (localStorage rsPps; links carry pps=0 when
    off). On: Scenarios A and B use PPS's school-by-year enrollment ("Seventy Percent" and "Fifty Percent" runs), types,
    2031-32 detail and this page's measures recalculated from them; schools PPS's model closes that the reconstruction
    keeps open (Odyssey) close. PPS's published district and regional measures are unchanged. The modified enrollment
    model does not apply (it corrects the reconstruction). Off: this page's reconstruction, as before.
  - Two more scenarios, from PPS's model runs "Sixty Percent" (S60) and "Balanced" (BAL): series, types, detail, school
    roles and notes from PPS's move rules, receivers of closing schools, measures (this page's calculation), share of
    students changing schools (PPS's moved share; Balanced estimated). Buttons, links, custom starting point, report
    columns, trend table. Sections with no data for them (travel and bus, attendance-area maps, enrollment
    uncertainty) say so.
Data: D.ppsm (refreshed on rerun); S60/BAL entries in D.series/types/detail/flows/endpoints/recreated/schools
(refreshed on rerun); code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
P = json.load(open(os.path.join(ROOT, 'source', 'pps-powerbi', 'pps-model.json'), encoding='utf-8'))
NEW = ['S60', 'BAL']
# A/B under the switch: what the toggle swaps in
D['ppsm'] = {'source': P['source'], 'runs': P['runs'], 'scen': {sc: {k: P['scen'][sc][k] for k in ('series', 'types', 'detail', 'text', 'recreated', 'change')} for sc in ('A', 'B')},
             'meta': {sc: {'run': P['scen'][sc]['run'], 'change': P['scen'][sc]['change'], 'estimated': bool(P['scen'][sc].get('change_estimated')), 'closures': len(P['scen'][sc]['closing']['District'])} for sc in P['scen']}}
for sc in NEW:
    S = P['scen'][sc]
    D['series'][sc] = S['series']; D['types'][sc] = S['types']; D['detail'][sc] = S['detail']
    D['flows'][sc] = {'receivers': S['receivers'], 'moves': []}
    D['recreated'][sc] = S['recreated']
    for rn in [*D['region_order'], 'District']:
        R = S['recreated'][rn]
        D['endpoints'][rn][sc] = {k: R[k] for k in ('closures', 'schools_above', 'students_above', 'poverty', 'underserved', 'sped', 'ml')}
        if rn != 'District': D['endpoints'][rn].setdefault('closing', {})[sc] = S['closing'][rn]
    D['endpoints']['District'][sc]['change'] = S['change']
    for s in D['schools']:
        k = s['key']; det = S['detail'].get(k, {})
        s['cat'][sc] = S['cat'][k]; s['detail'][sc] = S['text'][k]; s['type'][sc] = S['types'][k]
        s['e2031'][sc] = None if det.get('closed') else det.get('e')
NOTE = ("PPS model results (the switch beside the scenario buttons, on by default): Scenarios A and B use PPS's own school-by-year enrollment from its "
        "Rightsizing Scenarios dashboard (Power BI, version 1.0, October 14, 2026; runs \"Seventy Percent\" and \"Fifty Percent\"), which apply PPS's move rules "
        "by grade and student group, including the sizes of moves PPS had not published (for example 28% of Duniway's area to Llewellyn) and Odyssey's move to "
        "MLC. PPS's published district and regional measures are kept; this page's own measures are recalculated from PPS's enrollment. Student-group counts keep "
        "this page's definitions and take PPS's change in each school's mix. "
        "Unchecked, "
        "Scenarios A and B use this page's reconstruction from PPS's published descriptions.")
D['assumptions'] = [a for a in D['assumptions'] if not a.startswith('PPS model results (the switch')] + [NOTE]
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'ppsApply' not in html:
    # labels, buttons, the stored scenario
    rep("const LABEL = { SQ: 'Status Quo', A: 'Scenario A', B: 'Scenario B', C: 'Custom' };",
        "const LABEL = { SQ: 'Status Quo', A: 'Scenario A', B: 'Scenario B', S60: 'Sixty Percent', BAL: 'Balanced', C: 'Custom' };\n"
        "const SCENS = ['SQ', 'A', 'B'];   // patch_pps_model: PPS's model runs Sixty Percent ('S60') and Balanced ('BAL') stay in the data but are not offered\n"
        "const PPS_ONLY = s => s === 'S60' || s === 'BAL' || (s === 'C' && typeof custom !== 'undefined' && (custom.base === 'S60' || custom.base === 'BAL'));")
    rep("try { scen = localStorage.getItem('rsScen') || 'A'; } catch (e) {}",
        "try { scen = localStorage.getItem('rsScen') || 'A'; } catch (e) {}\nif (![...SCENS, 'C'].includes(scen)) scen = 'A';")
    rep("const STABLE_SCENS = () => ['SQ', 'A', 'B', ...(D.detail.C ? ['C'] : [])];", "const STABLE_SCENS = () => [...SCENS, ...(D.detail.C ? ['C'] : [])];")
    rep("seg.innerHTML = ['SQ', 'A', 'B', 'C'].map(s => `<button data-s=\"${s}\">${LABEL[s]}</button>`).join('');",
        "seg.innerHTML = [...SCENS, 'C'].map(s => `<button data-s=\"${s}\"${s === 'S60' || s === 'BAL' ? ` title=\"PPS's model run &quot;${LABEL[s]}&quot; (Power BI dashboard, October 2026); not one of PPS's two published scenarios\"` : ''}>${LABEL[s]}</button>`).join('');")
    rep("return { base: ['SQ', 'A', 'B'].includes(o.b) ? o.b : 'SQ', name: o.n || '',", "return { base: SCENS.includes(o.b) ? o.b : 'SQ', name: o.n || '',")
    rep("<label>Starts from <select id=\"cp-base\">${['SQ', 'A', 'B'].map(", "<label>Starts from <select id=\"cp-base\">${SCENS.map(")
    rep("  if (['SQ', 'A', 'B'].includes(sc)) scen = sc;", "  if (SCENS.includes(sc)) scen = sc;")
    rep("const rpCols = sc => ['SQ', 'A', 'B', ...(sc === 'C' ? ['C'] : [])];", "const rpCols = sc => ['SQ', 'A', 'B', ...(['S60', 'BAL', 'C'].includes(sc) ? [sc] : [])];")
    rep("const RP_LINE = { SQ: 'lsq', A: 'la', B: 'lb', C: 'lc' };", "const RP_LINE = { SQ: 'lsq', A: 'la', B: 'lb', S60: 'ls6', BAL: 'lbal', C: 'lc' };")
    rep("const TR_COL = { SQ: 'var(--none)', A: 'var(--change)', B: '#0f9b78', C: '#b0369a' };", "const TR_COL = { SQ: 'var(--none)', A: 'var(--change)', B: '#0f9b78', S60: '#c2410c', BAL: '#4f46e5', C: '#b0369a' };")
    rep("impl = Y.indexOf(D.impl_year), cols = ['SQ', 'A', 'B', ...(D.detail.C ? ['C'] : [])];", "impl = Y.indexOf(D.impl_year), cols = [...SCENS, ...(D.detail.C ? ['C'] : [])];")
    rep(""".rpplot .impl { stroke: var(--axis); stroke-dasharray: 3 3; }""",
        """.rpplot .impl { stroke: var(--axis); stroke-dasharray: 3 3; }
.rpplot path.ls6, .rpplot path.lbal { fill: none; stroke-width: 1.8; opacity: .85; } .rpplot .ls6 { stroke: #c2410c; } .rpplot .lbal { stroke: #4f46e5; } .rpplot circle.ls6 { fill: #c2410c; } .rpplot circle.lbal { fill: #4f46e5; }
.rpplot path.rng.ls6 { fill: #c2410c; } .rpplot path.rng.lbal { fill: #4f46e5; } .rplegend .k.ls6 { border-color: #c2410c; } .rplegend .k.lbal { border-color: #4f46e5; } .rplegend .k.rng.ls6 { background: #c2410c; } .rplegend .k.rng.lbal { background: #4f46e5; }""")
    # the switch
    rep("""<label class="adjtog" id="adjtogl" """,
        """<label class="adjtog" id="ppstogl" title="Scenarios A and B use PPS's own school-by-year enrollment results from its Rightsizing Scenarios dashboard (Power BI, version 1.0, October 14, 2026: the &quot;Seventy Percent&quot; and &quot;Fifty Percent&quot; runs), which apply PPS's move rules by grade and student group. Unchecked: this page's reconstruction of the scenarios from PPS's published descriptions."><input type="checkbox" id="ppstog"> PPS model results</label><label class="adjtog" id="adjtogl" """)
    rep("""let pfaOn = true;   // pfa-default: on unless turned off""",
        """let ppsOn = true;   // PPS model results for A and B (scripts/patch_pps_model.py): on unless turned off
try { ppsOn = localStorage.getItem('rsPps') !== '0'; } catch (e) {}
let pfaOn = true;   // pfa-default: on unless turned off""")
    rep("""const ADJ_BASE = { series: {}, detail: {}, e2031: {}, recv: {}, endpoints: clone(D.endpoints), recreated: clone(D.recreated) };
for (const sc of ['A', 'B']) {
  ADJ_BASE.series[sc] = clone(D.series[sc]); ADJ_BASE.detail[sc] = clone(D.detail[sc]);""",
        """const ADJ_BASE = { series: {}, detail: {}, e2031: {}, recv: {}, types: {}, cat: {}, txt: {}, endpoints: clone(D.endpoints), recreated: clone(D.recreated) };
for (const sc of ['A', 'B', 'S60', 'BAL']) {
  ADJ_BASE.series[sc] = clone(D.series[sc]); ADJ_BASE.detail[sc] = clone(D.detail[sc]); ADJ_BASE.types[sc] = clone(D.types[sc]);
  ADJ_BASE.cat[sc] = Object.fromEntries(D.schools.map(s => [s.key, s.cat[sc]])); ADJ_BASE.txt[sc] = Object.fromEntries(D.schools.map(s => [s.key, s.detail[sc]]));""")
    rep("""  adjOn = on; MODEL_ON = on;
  for (const sc of ['A', 'B']) {
    D.series[sc] = clone(ADJ_BASE.series[sc]); D.detail[sc] = clone(ADJ_BASE.detail[sc]);""",
        """  adjOn = on; MODEL_ON = on && !ppsOn;
  for (const sc of ['A', 'B', 'S60', 'BAL']) {
    D.series[sc] = clone(ADJ_BASE.series[sc]); D.detail[sc] = clone(ADJ_BASE.detail[sc]); D.types[sc] = clone(ADJ_BASE.types[sc]);
    for (const s of D.schools) { s.cat[sc] = ADJ_BASE.cat[sc][s.key]; s.detail[sc] = ADJ_BASE.txt[sc][s.key]; s.type[sc] = D.types[sc][s.key]; }""")
    rep("""  D.endpoints = clone(ADJ_BASE.endpoints); D.recreated = clone(ADJ_BASE.recreated); ADJ.diff = {};
  if (!on) return;""",
        """  D.endpoints = clone(ADJ_BASE.endpoints); D.recreated = clone(ADJ_BASE.recreated); ADJ.diff = {};
  ppsApply();
  if (!on || ppsOn) return;   // the modified model corrects the reconstruction; PPS's own results need no correction""")
    rep("""function applyAdjust(on) {""", r"""// PPS's own results for A and B (D.ppsm, scripts/patch_pps_model.py): enrollment by school and year, types, 2031-32
// detail; this page's measures recalculated; PPS's published measures kept
function ppsApply() {
  if (!ppsOn || !D.ppsm) return;
  for (const sc of ['A', 'B']) {
    const P = D.ppsm.scen[sc]; if (!P) continue;
    D.series[sc] = clone(P.series); D.types[sc] = clone(P.types); D.detail[sc] = clone(P.detail); D.recreated[sc] = clone(P.recreated);
    for (const s of D.schools) {
      const d = P.detail[s.key]; if (!d) continue;
      s.e2031[sc] = d.closed ? null : d.e; s.type[sc] = P.types[s.key];
      if (d.closed && s.cat[sc] !== 'closes') { s.cat[sc] = 'closes'; s.detail[sc] = P.text[s.key] || 'Closes (PPS model)'; }
    }
  }
}
function applyAdjust(on) {""")
    rep("""  for (const sc of ['SQ', 'A', 'B']) {
    const ser = D.series[sc], det = D.detail[sc], before = clone(det);""", """  for (const sc of SCENS) {
    const ser = D.series[sc], det = D.detail[sc], before = clone(det);""")
    rep("""if (pfaBox) { pfaBox.checked = pfaOn;""", """const ppsBox = document.getElementById('ppstog');
if (ppsBox) { ppsBox.checked = ppsOn; ppsBox.onchange = () => { ppsOn = ppsBox.checked; try { localStorage.setItem('rsPps', ppsOn ? '1' : '0'); } catch (e) {} applyAdjust(adjOn); if (CS || scen === 'C') buildCustom(); renderAll(); }; }
if (pfaBox) { pfaBox.checked = pfaOn;""")
    rep("""  if (!pfaOn) p.set('pfa', '0');""", """  if (!pfaOn) p.set('pfa', '0');
  if (!ppsOn) p.set('pps', '0');""")
    rep("""  if (q.has('pfa') && (q.get('pfa') === '1') !== pfaOn) {""", """  if ((q.get('pps') !== '0') !== ppsOn) { ppsOn = q.get('pps') !== '0'; applyAdjust(adjOn); const b = document.getElementById('ppstog'); if (b) b.checked = ppsOn; }
  if (q.has('pfa') && (q.get('pfa') === '1') !== pfaOn) {""")
    # scenario description and the modified-model switch
    rep("""    scen === 'A' ? '14 closures; 7 K-8s become K-5; 13 program moves.' : scen === 'B' ? '11 closures (Stephenson, Rose City Park and Lewis stay open).' :""",
        """    scen === 'A' ? '14 closures; 7 K-8s become K-5; 13 program moves.' : scen === 'B' ? '11 closures (Stephenson, Rose City Park and Lewis stay open).' :
    scen === 'S60' || scen === 'BAL' ? `${D.ppsm.meta[scen].closures} closures. PPS's model run "${D.ppsm.meta[scen].run}" (Power BI dashboard, October 2026), not one of its two published scenarios; measures are this page's calculation.` :""")
    rep("""  for (const b of seg.querySelectorAll('button')) b.setAttribute('aria-pressed', b.dataset.s === scen ? 'true' : 'false');""",
        """  if (ppsOn && (scen === 'A' || scen === 'B')) document.getElementById('desc').textContent += ` Enrollment: PPS's model results ("${D.ppsm.meta[scen].run}" run).`;
  if (!ppsOn && (scen === 'S60' || scen === 'BAL')) document.getElementById('desc').textContent += ' (PPS model results: no reconstruction exists for this run.)';
  document.getElementById('ppstogl')?.classList?.toggle('na', !['A', 'B'].includes(scen === 'C' ? custom.base : scen));
  for (const b of seg.querySelectorAll('button')) b.setAttribute('aria-pressed', b.dataset.s === scen ? 'true' : 'false');""")
    rep("""  document.getElementById('adjtogl')?.classList?.toggle('na', (scen === 'C' ? custom.base : scen) === 'SQ');""",
        """  document.getElementById('adjtogl')?.classList?.toggle('na', (scen === 'C' ? custom.base : scen) === 'SQ' || ppsOn || PPS_ONLY(scen));""")
    # sections without data for the new runs
    rep("""  const sc = scen === 'C' ? custom.base : scen, d = D.bounds[`${sc.toLowerCase()}_${bBand}`];""",
        """  const sc = scen === 'C' ? custom.base : scen, d = D.bounds[`${sc.toLowerCase()}_${bBand}`];
  if (!d) { lg.innerHTML = `<span class="muted">Attendance-area maps are not available for ${esc(LABEL[sc])} (PPS published maps for Scenarios A and B only).</span>`; return; }""")
    rep("""function commuteKPI() {""", """function commuteKPI() {
  if (PPS_ONLY(scen)) return '';   // no attendance areas for PPS's other model runs""")
    rep("""function busKPI() {""", """function busKPI() {
  if (PPS_ONLY(scen)) return '';""")
    rep("""function renderAll() {""", r"""// sections with no data for PPS's other model runs (scripts/patch_pps_model.py)
const PPS_NA = (what, why) => `<p class="muted" style="border-left:3px solid var(--line);padding:4px 10px">${what} ${esc(LABEL[scen === 'C' ? custom.base : scen])}: ${why} Pick Status Quo, Scenario A or Scenario B.</p>`;
{ const _rc = renderCommute; renderCommute = function () { if (PPS_ONLY(scen)) { const h = document.getElementById('commute'); if (h) h.innerHTML = PPS_NA('Travel distances and busing are not estimated for', 'they need attendance-area maps, which PPS published for Scenarios A and B only.'); return; } return _rc(); }; }
{ const _rm = renderMC; renderMC = function () { _rm(); if (PPS_ONLY(scen)) { const h = document.getElementById('mckpis'); if (h) h.innerHTML = PPS_NA('The enrollment uncertainty simulation was not run for', 'it covers Status Quo and Scenarios A and B.'); } }; }
function renderAll() {""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
