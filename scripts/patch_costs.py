"""Building costs per school (2026 dollars) and the costs avoided when a scenario closes buildings, added to
rightsizing-scenario-explorer.html (the endpoints table and a summary card).

  must-fix           = deferred maintenance + remaining seismic retrofit
    deferred maint.  = 2021 LRFP facility condition index (FCI) x replacement value
    seismic retrofit = Holmes 2024 COMPLETE remaining ROM retrofit cost (whole campus; includes the URM-only
                       subset, which is shown for reference but not added again)
  full modernization = replacement value = building area x 2021 LRFP regional cost per square foot
                       (elementary and K-8 $510, middle $540, high $590)

Escalated to 2026 dollars with the Turner Building Cost Index (2Q 2021 1187, 2Q 2024 1421, 2Q 2026 1552).
Inputs: source/lrfp/lrfp-2021-fci.csv (scripts/extract_lrfp_fci.py), source/pps-data/data/pps_schools.csv.
Writes source/lrfp/building-costs-2026.csv. Safe to rerun: data is refreshed, page code added once.
  python scripts/patch_costs.py [--check]
"""
import csv, json, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
FCI = os.path.join(ROOT, 'source', 'lrfp', 'lrfp-2021-fci.csv')
SCHOOLS = os.path.join(ROOT, 'source', 'pps-data', 'data', 'pps_schools.csv')
OUT = os.path.join(ROOT, 'source', 'lrfp', 'building-costs-2026.csv')
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
CHECK = '--check' in sys.argv[1:]
TURNER = {'2021Q2': 1187, '2024Q2': 1421, '2026Q2': 1552}
F2021, F2024 = TURNER['2026Q2'] / TURNER['2021Q2'], TURNER['2026Q2'] / TURNER['2024Q2']
RATE_2021 = {'ES': 510, 'K8': 510, 'MS': 540, 'HS': 590}   # $/SF, LRFP 2021 Vol. 1 p. 38

html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))

STRIP = r"\b(elementary|middle|high|school|k-8|k8|k-5|academy|program|of|the)\b"
def norm(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode()   # César Chávez -> Cesar Chavez
    n = re.sub(STRIP, ' ', n.lower().replace('’', "'").replace('.', ''))
    return re.sub(r'[^a-z0-9]+', ' ', n).strip()
ALIAS = {'brentwood': 'Lane', 'sunrise': 'Lee', 'martin luther king jr': 'MLK Jr', 'king': 'MLK Jr',
         'boise eliot humboldt': 'Boise-Eliot/Humboldt', 'boise eliot': 'Boise-Eliot/Humboldt', 'wells barnett': 'Ida B Wells-Barnett',
         'ida b wells barnett': 'Ida B Wells-Barnett', 'beverly cleary fernwood': 'Beverly Cleary', 'beverly cleary hollyrood': 'Beverly Cleary',
         'beverly cleary hollyrood k 1': 'Beverly Cleary', 'bridger': 'Bridger Creative Science', 'clark creative science': 'Clark',
         'east sylvan': 'Odyssey', 'sunnyside': 'Sunnyside Environmental'}   # Odyssey uses the East Sylvan building
bykey = {}
for s in D['schools']:
    for n in {s['key'], s['name']}: bykey[norm(n)] = s['key']
key_of = lambda n: ALIAS.get(norm(n)) or bykey.get(norm(n))

num = lambda v: float(v) if v not in ('', None) else None
lrfp, unmatched = {}, []
for r in csv.DictReader(open(FCI, encoding='utf-8')):
    k = key_of(r['school'])
    if not k: unmatched.append(r['school']); continue
    e = lrfp.setdefault(k, {'area': 0, 'fcis': []})   # campuses (Beverly Cleary) add up
    a = num(r['bldg_area_sf']) or 0
    e['area'] += a
    if r['fci']: e['fcis'].append((num(r['fci']), a))
csvrows = {}
for r in csv.DictReader(open(SCHOOLS, encoding='utf-8')):
    k = key_of(r['school_name'].strip())
    if k: csvrows[k] = r

costs, rows = {}, []
for s in D['schools']:
    k, t = s['key'], D['types']['SQ'].get(s['key'])
    l, c = lrfp.get(k, {}), csvrows.get(k, {})
    area = l.get('area') or num(c.get('square_feet')) or 0
    rate = RATE_2021.get(t)
    repl = area * rate * F2021 if area and rate else None
    f = l.get('fcis') or []   # area-weighted across campuses; a plain mean when the LRFP gives no area
    fci = (sum(x * a for x, a in f) / sum(a for _, a in f)) if f and all(a for _, a in f) else (sum(x for x, _ in f) / len(f) if f else None)
    dm = repl * fci if repl and fci is not None else None
    seis = num(c.get('retrofit_cost_remaining_usd'))
    seis = seis * F2024 if seis is not None else None
    urm = num(c.get('urm_retrofit_cost_usd'))
    urm = urm * F2024 if urm is not None else None
    mf = (dm or 0) + (seis or 0) if (dm is not None or seis is not None) else None
    r1 = lambda v: None if v is None else int(round(v, -3))
    costs[k] = {'mf': r1(mf), 'mod': r1(repl), 'dm': r1(dm), 'se': r1(seis), 'urm': r1(urm),
                'fci': None if fci is None else round(fci, 3), 'sf': int(area) if area else None}
    rows.append({'key': k, 'type': t, 'bldg_area_sf': costs[k]['sf'] or '', 'fci_2021': costs[k]['fci'] if costs[k]['fci'] is not None else '',
                 'deferred_maintenance_2026usd': costs[k]['dm'] or '', 'seismic_retrofit_2026usd': costs[k]['se'] if costs[k]['se'] is not None else '',
                 'urm_retrofit_subset_2026usd': costs[k]['urm'] or '', 'must_fix_2026usd': costs[k]['mf'] if costs[k]['mf'] is not None else '',
                 'full_modernization_2026usd': costs[k]['mod'] or ''})
print('LRFP profiles not matched to an explorer school:', ', '.join(unmatched) or 'none')
print('explorer schools missing: area', [k for k, v in costs.items() if not v['sf']], '| FCI', [k for k, v in costs.items() if v['fci'] is None],
      '| seismic', [k for k, v in costs.items() if v['se'] is None])
tot = lambda f: sum(v[f] or 0 for v in costs.values())
print(f"district (all {len(costs)} schools, 2026$): must-fix ${tot('mf')/1e6:,.0f}M (deferred ${tot('dm')/1e6:,.0f}M + seismic ${tot('se')/1e6:,.0f}M; URM subset ${tot('urm')/1e6:,.0f}M), full modernization ${tot('mod')/1e6:,.0f}M")
for sc in ['A', 'B']:
    closed = [k for k in costs if D['detail'][sc].get(k, {}).get('closed')]
    print(f"{sc}: {len(closed)} closures avoid must-fix ${sum(costs[k]['mf'] or 0 for k in closed)/1e6:,.0f}M, full modernization ${sum(costs[k]['mod'] or 0 for k in closed)/1e6:,.0f}M")
if CHECK: sys.exit()

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
D['costs'] = costs
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function costCell' not in html:
    rep("td.reach .rd { font-size: 11px;",
        "td.cost { white-space: nowrap; font-size: 12px; line-height: 1.35; text-align: left; } td.cost .rm { color: var(--text-muted); display: inline-block; width: 66px; }\n"
        "td.cost .ca { color: var(--up); font-weight: 600; font-size: 11px; }\n"
        "td.reach .rd { font-size: 11px;")
    rep("function schoolRows(rn) {",
"""// building costs (D.costs, 2026 dollars): school rows show the building's costs (marked avoided when it closes);
// region and district rows add up the buildings the scenario closes
const usdM = v => v >= 1e9 ? '$' + (v / 1e9).toFixed(2) + 'B' : '$' + Math.round(v / 1e6).toLocaleString() + 'M';
function avoidedCosts(keys) {
  const det = D.detail[scen] || {}, C = D.costs || {}, closed = keys.filter(k => det[k]?.closed);
  return { n: closed.length, mf: closed.reduce((a, k) => a + (C[k]?.mf || 0), 0), mod: closed.reduce((a, k) => a + (C[k]?.mod || 0), 0) };
}
function totalCosts(keys) {   // Status Quo: every building open
  const C = D.costs || {};
  return { mf: keys.reduce((a, k) => a + (C[k]?.mf || 0), 0), mod: keys.reduce((a, k) => a + (C[k]?.mod || 0), 0) };
}
const pctOf = (d, base) => base ? `${d > 0 ? '+' : d < 0 ? '&minus;' : '&plusmn;'}${Math.abs(Math.round(100 * d / base))}%` : '';
function costCell(keys) {
  if (keys.length === 1) {
    const c = (D.costs || {})[keys[0]], closed = (D.detail[scen] || {})[keys[0]]?.closed;
    if (!c || (c.mf == null && c.mod == null)) return '<td class="cost muted">&mdash;</td>';
    const tip = `Deferred maintenance ${c.dm == null ? 'n/a' : usdM(c.dm)} (2021 FCI ${c.fci ?? 'n/a'}) + seismic retrofit ${c.se == null ? 'n/a' : usdM(c.se)}${c.urm ? ` (URM part ${usdM(c.urm)})` : ''}; ${c.sf ? c.sf.toLocaleString() + ' sq ft' : ''}`;
    return `<td class="cost" title="${esc(tip)}">${closed ? '<span class="ca">avoided</span><br>' : ''}<span class="rm">Must-fix</span>${c.mf == null ? '&mdash;' : usdM(c.mf)}<br><span class="rm">Modernize</span>${c.mod == null ? '&mdash;' : usdM(c.mod)}</td>`;
  }
  const a = avoidedCosts(keys), t = totalCosts(keys);
  if (scen === 'SQ') return `<td class="cost"><span class="muted" style="font-size:11px">Status Quo total, all buildings</span><br><span class="rm">Must-fix</span><b>${usdM(t.mf)}</b><br><span class="rm">Modernize</span><b>${usdM(t.mod)}</b></td>`;
  const line = (l, v, tot) => `<span class="rm">${l}</span>${a.n ? `<b>${usdM(v)}</b> <span class="muted">of ${usdM(tot)}</span> <span class="ca">${pctOf(-v, tot)}</span>` : `$0 <span class="muted">of ${usdM(tot)}</span>`}`;
  return `<td class="cost">${line('Must-fix', a.mf, t.mf)}<br>${line('Modernize', a.mod, t.mod)}<br><span class="muted" style="font-size:11px">${a.n ? `${a.n} building${a.n === 1 ? '' : 's'} closed` : 'none closed'}; totals are Status Quo</span></td>`;
}
function schoolRows(rn) {""")
    rep("<th>Students who would change schools</th>",
        "<th>Building costs avoided by closures<br><span style=\"font-weight:400\">(2026 $; must-fix = deferred maintenance + seismic retrofit; school rows show each building)</span></th><th>Students who would change schools</th>")
    rep("    h += reachCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));",
        "    h += reachCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));\n"
        "    h += costCell(Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn));")
    rep("+ reachCell([n]) + '<td></td></tr>';", "+ reachCell([n]) + costCell([n]) + '<td></td></tr>';")
    rep("+ '<td class=\"reach muted\">&mdash;</td><td></td></tr>';", "+ '<td class=\"reach muted\">&mdash;</td>' + costCell([n]) + '<td></td></tr>';")
    # summary card: Status Quo shows the totals; scenarios show what closures avoid, as a percent of those totals
    rep("""<div class="s">${[sub('b', 'Bike'), sub('d', 'Drive')].filter(Boolean).join(' &middot; ')}</div></div>`;""",
        """<div class="s">${[sub('b', 'Bike'), sub('d', 'Drive')].filter(Boolean).join(' &middot; ')}</div></div>` +
    ((a, t) => scen === 'SQ'
      ? `<div class="kpi"><div class="v">${usdM(t.mf)}</div><div class="l">Must-fix building costs, all buildings (deferred maintenance + seismic retrofit, 2026 $)</div>` +
        `<div class="s">Full modernization, all buildings: <b>${usdM(t.mod)}</b></div></div>`
      : `<div class="kpi"><div class="v">${usdM(a.mf)}<span class="d" style="color:var(--up)">${pctOf(-a.mf, t.mf)} vs SQ</span></div>` +
        `<div class="l">Must-fix building costs avoided by closures, of ${usdM(t.mf)} under Status Quo (deferred maintenance + seismic retrofit, 2026 $)</div>` +
        `<div class="s">Full modernization avoided: <b>${usdM(a.mod)}</b> (${pctOf(-a.mod, t.mod)} of ${usdM(t.mod)})${a.n ? ` &middot; ${a.n} building${a.n === 1 ? '' : 's'}` : ''}</div></div>`)(avoidedCosts(D.schools.map(s => s.key)), totalCosts(D.schools.map(s => s.key)));""")
    # method note
    rep("  'Private schools:",
        "  'Building costs (2026 dollars): must-fix = deferred maintenance + remaining seismic retrofit; full modernization = replacement value. Replacement value is building area times the 2021 Long-Range Facility Plan regional cost per square foot (elementary and K-8 $510, middle $540, high $590); deferred maintenance is the plan facility condition index (FCI, repair cost over replacement value) times that value; seismic retrofit is the Holmes 2024 complete remaining cost for the campus, which already includes the unreinforced-masonry (URM) work (shown in each school tooltip, not added again). Escalated with the Turner Building Cost Index (2Q 2021 1187, 2Q 2024 1421, 2Q 2026 1552). Kellogg, Lincoln and McDaniel were new or rebuilt and have no FCI; Forest Park has no seismic estimate. Costs avoided are the totals for buildings a scenario closes; receiving schools may need added space, which is not counted. Built by scripts/extract_lrfp_fci.py and scripts/patch_costs.py.',\n  'Private schools:")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.relpath(OUT, ROOT)} and {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
