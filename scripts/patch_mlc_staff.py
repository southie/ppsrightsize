"""Metropolitan Learning Center (MLC) in the staffing model. MLC is not one of the page's schools (it has no attendance
area), but under PPS's model Odyssey closes and 80% of its students move to MLC, so leaving MLC out counted Odyssey's
staff as saved. PPS's model treats MLC as a K-8 focus school (its 9-12 grades go to neighborhood high schools).
  D.staffExtra.MLC: type K8; enrollment by page year: Status Quo from PSU's 2026-27 forecast (Table 5.5 school
  totals, D.forecast_other); Scenarios A and B from PPS's model results (2027-28 on), used while the "PPS model results"
  switch is on (the reconstruction keeps Odyssey open, so MLC stays at Status Quo). Grade mix: PPS's 2027-28 Status Quo
  projection by grade.
  - schoolFTE reads MLC from D.staffExtra.
  - Consolidated-positions card and the staffing table's District row include MLC.
Data refreshed on rerun; code added once.
"""
import json, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
TB = os.path.join(ROOT, 'source', 'pps-powerbi', 'tables')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
L = lambda t: (lambda d: [dict(zip(d['cols'], r)) for r in d['rows']])(json.load(open(os.path.join(TB, t + '.json'), encoding='utf-8')))
num = lambda v: float(v) if v not in (None, '') else 0.0
FO = D['forecast_other']['schools']; FO = dict(FO) if isinstance(FO, list) else FO
sq = [FO['Metropolitan Learning Center'].get(y) for y in D['years']]
U = L('2027 utilization before and after')
pps = {sc: list(sq) for sc in ('A', 'B')}
for r in U:
    if r['school'] != 'Metro. Learning Center': continue
    sc = {'Seventy Percent': 'A', 'Fifty Percent': 'B'}.get(r['eval_scenario'])
    y = int(r['year']); yr = f'{y}-{(y + 1) % 100:02d}'
    if sc and yr in D['years']: pps[sc][D['years'].index(yr)] = round(num(r['projected enrollment after changes']))
g = collections.Counter()
for r in L('2027 Summary'):
    if r['school'] == 'Metro. Learning Center' and r['eval_scenario'] == 'Seventy Percent': g[int(r['grade'])] += num(r['Original'])
# share of each closing school's students MLC receives (PPS's move rules: Odyssey -> MLC)
frm = {}
for r in L('scenarios'):
    if r['school_to'] == 'Metro. Learning Center' and r['scenario_name'] == 'Seventy Percent' and num(r['percent_of_projections_to_move']) > 0:
        frm[r['school_from']] = max(frm.get(r['school_from'], 0), num(r['percent_of_projections_to_move']))
D['staffExtra'] = {'MLC': {'name': 'Metropolitan Learning Center', 'type': 'K8', 'series': {'SQ': sq, **pps}, 'from': frm}}
D['staff']['schools']['MLC'] = {'ode_name': 'Metropolitan Learning Center', 'title1': False, 'grades_2526': [round(g[i]) for i in range(13)]}
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'staffExtra' not in html.split('const D = ', 1)[1].split('\nconst esc', 1)[1]:
    rep("""function schoolFTE(k, sc, yi, enrollOverride, typeOverride) {
  const t = typeOverride || D.types[sc][k], E = enrollOverride ?? D.series[sc][k][yi];""",
        """// programs outside the page's schools that the staffing model still counts (D.staffExtra, scripts/patch_mlc_staff.py):
// MLC takes most of Odyssey's students under PPS's model
const STAFF_EXTRA = () => Object.keys(D.staffExtra || {});
const staffKeys = () => [...D.schools.map(x => x.key), ...STAFF_EXTRA()];
function extraSeries(X, sc) { const b = sc === 'C' ? custom.base : sc; return b !== 'SQ' && ppsOn && X.series[b] ? X.series[b] : X.series.SQ; }
function schoolFTE(k, sc, yi, enrollOverride, typeOverride) {
  const X = D.staffExtra?.[k];
  const t = typeOverride || (X ? X.type : D.types[sc][k]), E = enrollOverride ?? (X ? extraSeries(X, sc)[yi] : D.series[sc][k][yi]);""")
    rep("""  const s = staffDelta(D.schools.map(x => x.key));""", """  const s = staffDelta(staffKeys());""")
    rep("""General Fund est.: <b>${pos(staffGF(D.schools.map(x => x.key), 'SQ', D.years.indexOf(staffYear)))}</b>""",
        """General Fund est.: <b>${pos(staffGF(staffKeys(), 'SQ', D.years.indexOf(staffYear)))}</b>""")
    rep("""return `<br><span title="${sgfTip}">General Fund est.: about <b>${pos(g1 - g0)}</b> a year${pcS(g1 - g0, g0)}</span>`; })(D.schools.map(x => x.key), D.years.indexOf(staffYear))""",
        """return `<br><span title="${sgfTip}">General Fund est.: about <b>${pos(g1 - g0)}</b> a year${pcS(g1 - g0, g0)}</span>`; })(staffKeys(), D.years.indexOf(staffYear))""")
if 'programs outside the page that take a closing' not in html:
    # closures chart (gfCloseNet): MLC counts as a receiving school for the students it takes
    rep("""    added += a; to.push([t, Math.round(sent), a, ratio(t)]);
  }
  return { k, saved, added, net: added - saved, n, to, g, fk0: staffCost(fk0), fk: staffCost(fk) };""",
        """    added += a; to.push([t, Math.round(sent), a, ratio(t)]);
  }
  // programs outside the page that take a closing school's students (MLC from Odyssey, PPS's model; patch_mlc_staff)
  for (const [x, X] of Object.entries(D.staffExtra || {})) {
    const w = X.from?.[k], ser = w ? extraSeries(X, base) : null; if (!ser || ser === X.series.SQ || ser[ys] == null) continue;
    const sent = w * n, withS = schoolFTE(x, base, ys), keep = ser[ys]; ser[ys] = Math.max(0, keep - sent);
    let without; try { without = schoolFTE(x, base, ys); } finally { ser[ys] = keep; }
    const a = (staffCost(withS) - (without ? staffCost(without) : 0)) * staffGFRatio(x);
    added += a; to.push([x, Math.round(sent), a, staffGFRatio(x)]);
  }
  return { k, saved, added, net: added - saved, n, to, g, fk0: staffCost(fk0), fk: staffCost(fk) };""")
if 'District includes MLC' not in html:
    # the staffing table's District row
    old = "  const keysOf = rn => Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn);"
    i = html.index('function renderStaffing() {'); j = html.index(old, i)
    html = html[:j] + "  const keysOf = rn => rn === 'District' ? staffKeys() : Object.keys(D.region_of).filter(k => D.region_of[k] === rn);   // District includes MLC (patch_mlc_staff)" + html[j + len(old):]
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched; MLC SQ', sq[2:5], 'A', pps['A'][2:5], 'B', pps['B'][2:5])
