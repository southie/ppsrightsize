"""Yellow-bus cost from neighborhood routes only (source/pps-powerbi/neighborhood-share.json, scripts/build_nbhd_share.py).
The general routes carry neighborhood students: students who live in a school's attendance area and attend its
neighborhood program. Immersion students (on program routes, estimated separately), transfer students (not bused) and
special-program students are left out of the bus-minute estimate.
  - busH (card, bus cost section, the table's bus columns): each school's K-5 and 6-8 bus-eligible students and their
    walking miles are multiplied by its neighborhood-resident share in that band: PPS's projection for Status Quo by
    year; PPS's 2027-28 results after the changes for Scenarios A and B from the year they take effect (custom
    scenarios: their starting scenario's). PPS classifies Lent, Rigler and Richmond as whole-school immersion, so none
    of their students count.
  - Card text: "neighborhood K-8 students eligible for bus service", counted the same way.
  - Method note in the bus cost section.
Data: D.nbhd (refreshed on rerun); code changed once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['nbhd'] = json.load(open(os.path.join(ROOT, 'source', 'pps-powerbi', 'neighborhood-share.json'), encoding='utf-8'))
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'nbShare' not in html:
    rep("""function busH(sc, keys, bands = ['k5', '68']) {
  const [c0, c1, c2] = BC.gen.coef; let h = 0, n = 0, m = 0;
  for (const k of keys) {
    let nk = 0, mk = 0;
    for (const b of bands) { const o = cmAgg(sc, [k], b); nk += o.be8; mk += o.bm; }""",
        """// share of a school's students in a band who ride the neighborhood (general) routes: neighborhood residents attending
// its neighborhood program (D.nbhd, scripts/patch_bus_neighborhood.py). Status Quo: PPS's projection for the table's
// year; A and B: PPS's 2027-28 results after the changes, from the year they take effect.
function nbShare(sc, k, b) {
  if (!D.nbhd) return 1;
  const yi = D.years.indexOf(cmYear), base = sc === 'C' ? custom.base : sc, pre = yi < D.years.indexOf(D.impl_year);
  if (!pre && base !== 'SQ') { const v = D.nbhd[base]?.[k]?.[b]; if (v != null) return v; }
  const S = D.nbhd.SQ[k]?.[b];
  return S?.[yi] ?? S?.[D.years.indexOf(D.impl_year)] ?? S?.find(v => v != null) ?? 1;
}
function busH(sc, keys, bands = ['k5', '68']) {
  const [c0, c1, c2] = BC.gen.coef; let h = 0, n = 0, m = 0;
  for (const k of keys) {
    let nk = 0, mk = 0;
    // neighborhood routes only: bus-eligible neighborhood students and their walking miles
    for (const b of bands) { const o = cmAgg(sc, [k], b), w = nbShare(sc, k, b); nk += o.be8 * w; mk += o.bm * w; }""")
    rep("""  return { d_elig: c.n - q.n, d_walk:""", """  return { n: c.n, d_elig: c.n - q.n, d_walk:""")
    rep("""      `<div class="s">Range: ${bcRange(...BC.gt)} a year<br>${cmN(rq.be8)} K-8 students eligible for bus service, ${cmYear}<br>` +""",
        """      `<div class="s">Range: ${bcRange(...BC.gt)} a year<br>${cmN(busH('SQ', keys).n)} neighborhood K-8 students eligible for bus service, ${cmYear}<br>` +""")
    rep("""K-8 students eligible for bus service: <b>${s.d_elig >= 0 ? '+' : '&minus;'}${cmN(Math.abs(s.d_elig))}</b> <span class="pcs">(${cmN(rc.be8)} in all)</span>`;""",
        """Neighborhood K-8 students eligible for bus service: <b>${s.d_elig >= 0 ? '+' : '&minus;'}${cmN(Math.abs(s.d_elig))}</b> <span class="pcs">(${cmN(s.n)} in all)</span>`;""")
    rep("""    `<li><b>Not included:</b> grades 9-12""",
        """    `<li><b>Neighborhood routes only.</b> The cost change counts students who live in a school's attendance area and attend its neighborhood program: ${D.nbhd ? `PPS's projections by school, grade and student group give each school's share (Status Quo by year; Scenarios A and B from PPS's ${D.impl_year} results after the changes)` : 'all students'}. Immersion students ride program routes (see the immersion program busing table), transfer students are not bused, and special-program students are left out. PPS lists Lent, Rigler and Richmond as whole-school immersion, so none of their students count here.</li>` +
    `<li><b>Not included:</b> grades 9-12""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
