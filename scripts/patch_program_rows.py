"""Getting-to-school table: show students at program schools (no neighborhood attendance area for their grades, e.g.
focus-option and immersion-only schools) instead of leaving them out silently. Region and district rows note
"+N at program schools" under the student count, so totals reconcile with the scenario impact table; expanded school
lists show each program school with its students and its current general bus runs on PPS's posted routes
(source/pps-bus/pps-bus-routes.json). Distances and bus figures still cover neighborhood students only (where program
students live is not known). Runs after patch_commute / patch_buscost. Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
ROUTES = os.path.join(ROOT, 'source', 'pps-bus', 'pps-bus-routes.json')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))

# ---- data: current general bus runs per school (matched by the school's page on the PPS bus schedule site) ----
def norm(n): return re.sub(r'[^a-z0-9]+', ' ', re.sub(r"\b(elementary|middle|high|school|k-8|k8|academy|program|of|the)\b", ' ',
                          n.lower().replace('á', 'a').replace('é', 'e'))).strip()
at = {norm(s['name']): s['key'] for s in D['schools']} | {norm(s['key']): s['key'] for s in D['schools']}
runs = {}
for r in json.load(open(ROUTES, encoding='utf-8'))['routes']:
    if not r['current'] or r['snow']: continue
    k = next((at[norm(p.replace('-', ' '))] for p in r['pages'] if norm(p.replace('-', ' ')) in at), None)
    if k: runs[k] = runs.get(k, 0) + 1
D['commute']['runs'] = runs
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
print(f'bus runs matched to {len(runs)} schools')

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function cmProg' not in html:
    rep("function cmCells(c, q, row) {", r"""// students in the given grades at schools with no neighborhood attendance area for them in the scenario (program
// schools: focus options, immersion-only schools); not in the distance or bus figures because where they live is unknown
function cmProg(sc, keys, band) {
  const Sc = D.years.indexOf(cmYear) < D.years.indexOf(D.impl_year) ? 'SQ' : sc === 'C' ? custom.base : sc;
  const S = D.commute.S[Sc] || {}, bands = band === 'all' ? ['k5', '68', '912'] : [band];
  let n = 0; const at = new Set();
  for (const k of keys) for (const b of bands) {
    const v = S[k]?.[b]; if (v && v[0]) continue;
    const r = cmStu(sc, k, b); if (r) { n += r; at.add(k); }
  }
  return { n, schools: [...at] };
}
function cmCells(c, q, row) {""")
    rep("""  return `<td><span class="main">${cmN(c.r)}</span>${cmD(c.r, q?.r, cmN, 'flat')}</td>` +""",
        """  const pg = row && row.keys.length > 1 ? cmProg(scen, row.keys, cmBand) : null;
  return `<td><span class="main">${cmN(c.r)}</span>${cmD(c.r, q?.r, cmN, 'flat')}` +
    `${pg && Math.round(pg.n) ? `<span class="cmprog" title="Students at ${pg.schools.map(k => short(byKey[k].name)).join(', ')}: program schools with no neighborhood attendance area, not in the distance or bus figures">+${cmN(pg.n)} at program schools</span>` : ''}</td>` +""")
    rep("""      if (!c.r && !q.r) continue;""",
        """      const pg = cmProg(scen, [k], cmBand);
      if (!c.r && !q.r && !Math.round(pg.n)) continue;""")
    rep("""      if (closed || !c.r) {
        h += `<tr class="srow closed">""",
        """      if (!closed && !c.r && Math.round(pg.n)) {   // program school: students, no neighborhood area
        const nr = D.commute.runs?.[k] || 0;
        h += `<tr class="srow prog"><td>${nm}</td><td><span class="main">${cmN(pg.n)}</span></td><td colspan="8" style="text-align:left"><span class="stag other">Program school</span> ` +
          `<span class="muted">no neighborhood attendance area for these grades, so where its students live is not known; not in the distance or bus figures. ` +
          `${nr ? `${nr} general bus run${nr === 1 ? '' : 's'} on PPS's posted routes` : 'No general bus routes on PPS\\'s posted schedules'}` +
          `${q.r ? ` (Status Quo: ${cmN(q.r)} neighborhood students, ${cmN(q.beyond)} beyond bus distance)` : ''}.</span></td></tr>`;
        continue;
      }
      if (closed || !c.r) {
        h += `<tr class="srow closed">""")
    rep("""    (scen === 'C' ? ` A custom scenario uses its own enrollment with ${LABEL[custom.base]}'s attendance areas.` : '') + ' Click a region to see its schools.' +""",
        """    (scen === 'C' ? ` A custom scenario uses its own enrollment with ${LABEL[custom.base]}'s attendance areas.` : '') +
    ((p, pq) => Math.round(p.n) ? ` Not included: <b>${cmN(p.n)}</b> students at ${p.schools.length} program school${p.schools.length === 1 ? '' : 's'} with no neighborhood attendance area${scen !== 'SQ' && Math.round(p.n - pq.n) ? ` (${cmN(pq.n)} under Status Quo)` : ''}, shown in the region rows.` : '')(cmProg(scen, keys, cmBand), cmProg('SQ', keys, cmBand)) +
    ' Click a region to see its schools.' +""")
    rep("""(${cmYear} enrollment, ${cmYear === D.years[0] ? 'actual' : 'projected'})</span></th>""",
        """(${cmYear} enrollment, ${cmYear === D.years[0] ? 'actual' : 'projected'}; neighborhood schools)</span></th>""")
    rep("#commute table { scroll-margin-top: 72px; }",
        "#commute table { scroll-margin-top: 72px; }\n"
        ".commutetable .cmprog { display: block; font-size: 11px; color: var(--text-muted); font-weight: 400; cursor: help; }\n"
        ".commutetable tr.srow.prog td { white-space: normal; } .commutetable tr.srow.prog td:first-child { white-space: nowrap; }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
