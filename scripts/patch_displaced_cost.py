"""Building, staffing and land costs by region: a "Staffing cost per displaced student" column after School staffing,
(closed schools only: each closure's net staffing change over its students; regions and the district sum their
closures; earlier versions also counted boundary and program moves, see displacedOf, now unused here),
and set column widths for readability.
  region and district rows   the region's staffing cost change against Status Quo (staffing formula, the year set in
                             Staffing impact) divided by its displaced students: students who change school because of
                             a closure, boundary change or program or grade move: closing schools' students, plus each
                             open school's neighborhood students x the share of its area reassigned (by grade band,
                             source/block-access/move-shares.json, scripts/build_move_shares.py), plus the students of
                             programs that move (immersion share of enrollment)
  other school rows          a school with students changing school: its staffing change divided by those students
  closing school rows        the closure's net staffing change (the school's Status Quo staffing cost, less what its
                             students add at the schools they go to: each destination's staffing with them minus
                             without them) divided by its students
Status Quo has no displaced students. Runs after patch_building_table, patch_bond and patch_repair_costs. Code added
once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
import json, re
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['moveShares'] = json.load(open(os.path.join(ROOT, 'source', 'block-access', 'move-shares.json'), encoding='utf-8'))
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function displacedCell' not in html:
    rep("function renderBuildings() {", r"""// ---------- staffing cost per displaced student (students whose school closes) ----------
// net staffing change of closing school k in scenario s, year yi: minus its Status Quo cost, plus what its students add
// at each destination (the destination's staffing with them minus without them; shares as the custom reopen uses)
function closureStaffNet(k, s, yi) {
  const a = schoolFTE(k, 'SQ', yi); if (!a) return null;
  const n = D.series.SQ[k][yi] || 0, dests = [...new Set((D.flows[s]?.receivers || []).filter(r => r.from_key === k && byKey[r.to_key]).map(r => r.to_key))];
  let usd = -staffCost(a);
  for (const t of dests) {
    const ser = (D.series[s] || {})[t]; if (!ser || ser[yi] == null) continue;
    const w = reopenWeights(k, s, yi).filter(x => x.to === t).reduce((q, x) => q + x.w, 0), sent = w * n;
    const withS = schoolFTE(t, s, yi), keep = ser[yi]; ser[yi] = Math.max(0, keep - sent);
    let without; try { without = schoolFTE(t, s, yi); } finally { ser[yi] = keep; }
    usd += staffCost(withS) - (without ? staffCost(without) : 0);
  }
  return { usd, n };
}
// students who change school in a scenario (D.moveShares, scripts/build_move_shares.py):
//   closing school          all its Status Quo students
//   open school             its neighborhood students (excluding immersion programs) in each grade band x the share of
//                           its Status Quo area the scenario assigns elsewhere (boundary changes, a K-8's 6-8 grades)
//                           + its program students when the scenario moves its program (immersion share of enrollment)
// A custom scenario uses its starting scenario's areas and moves, plus its own closures.
function displacedOf(keys, yi) {
  const s = scen, base = s === 'C' ? custom.base : s, det = D.detail[s] || {}, M = D.moveShares?.[base] || {};
  const progFrom = new Set((D.flows[base]?.moves || []).filter(m => m.kind === 'program').map(m => m.from_key));
  const f = D.k5_share[D.years[yi]] ?? 0.65;
  return keys.reduce((a, k) => {
    const q = D.series.SQ[k]?.[yi] || 0; if (!q) return a;
    if (det[k]?.closed) return a + q;
    if (base === 'SQ') return a;
    const t = D.types.SQ[k], dli = D.dli[k] || 0, sh = M[k] || {};
    const bands = t === 'ES' ? [['k5', q]] : t === 'K8' ? [['k5', q * f], ['68', q * (1 - f)]] : t === 'MS' ? [['68', q]] : t === 'HS' ? [['912', q]] : [];
    let n = bands.reduce((x, [b, v]) => x + v * (1 - dli) * (sh[b] || 0), 0);
    if (progFrom.has(k)) n += q * dli;
    return a + Math.min(q, n);
  }, 0);
}
function displacedCell(keys) {
  // closed schools only: each closure's net staffing change (its Status Quo staffing less what its students add at
  // the schools they go to) over its students; regions and the district sum their closures
  if (scen === 'SQ') return '<td class="muted dispc">&mdash;</td>';
  const yi = D.years.indexOf(staffYear), det = D.detail[scen] || {}, base = scen === 'C' ? custom.base : scen;
  const fm = v => (v < 0 ? '&minus;' : '+') + '$' + Math.round(Math.abs(v)).toLocaleString();
  const closed = keys.filter(k => det[k]?.closed && D.series.SQ[k]?.[yi]);
  if (keys.length === 1) {
    if (!closed.length) return '<td class="muted dispc"></td>';
    const r = closureStaffNet(keys[0], base, yi);
    if (!r || !r.n) return '<td class="muted dispc">&mdash;</td>';
    return `<td class="dispc" title="${esc(`Net staffing change of closing ${short(byKey[keys[0]].name)}, ${staffYear}: ${fm(r.usd).replace('&minus;', '-')} a year (its Status Quo staffing less what its students add at their new schools), for its ${Math.round(r.n)} students`)}"><span class="main">${fm(r.usd / r.n)}</span><span class="muted" style="display:block;font-size:11px">${Math.round(r.n)} students; net of receiving schools</span></td>`;
  }
  if (!closed.length) return '<td class="muted dispc">no closures</td>';
  let usd = 0, n = 0;
  for (const k of closed) { const r = closureStaffNet(k, base, yi); if (r) { usd += r.usd; n += r.n; } }
  if (!n) return '<td class="muted dispc">&mdash;</td>';
  return `<td class="dispc" title="${esc(`${staffYear}: the ${closed.length} closing school${closed.length === 1 ? '' : 's'}' net staffing change, ${fm(usd).replace('&minus;', '-')} a year (their Status Quo staffing less what their students add at receiving schools), over their ${Math.round(n).toLocaleString()} students`)}"><span class="main">${fm(usd / n)}</span>` +
    `<span class="muted" style="display:block;font-size:11px">${Math.round(n).toLocaleString()} students at ${closed.length} closing school${closed.length === 1 ? '' : 's'}</span></td>`;
}
function renderBuildings() {""")
    rep("""    `<th>Land value (assessor)<br><span style="font-weight:400">${isSQ ? 'all sites' : 'sites closed'}; land, and land + buildings</span></th></tr></thead><tbody>`;""",
        """    `<th class="dispc">Staffing cost per displaced student<br><span style="font-weight:400">closed schools, a year: net staffing change &divide; their students</span></th>` +
    `<th>Land value (assessor)<br><span style="font-weight:400">${isSQ ? 'all sites' : 'sites closed'}; land, and land + buildings</span></th></tr></thead><tbody>`;""")
    rep("""+ bondCell(keys) + staffCell(keys) + landCell(keys) + '</tr>';""", """+ bondCell(keys) + staffCell(keys) + displacedCell(keys) + landCell(keys) + '</tr>';""")
    rep("""+ bondCell([k], closed) + staffCell([k]) + landCell([k]) + '</tr>';""", """+ bondCell([k], closed) + staffCell([k]) + displacedCell([k]) + landCell([k]) + '</tr>';""")
    # column widths: name, four money columns, buildings, bond, staffing, per displaced student, land
    rep("""  let h = `<table class="bltable"><thead><tr><th>Region</th>""",
        """  let h = `<table class="bltable"><colgroup><col style="width:220px"><col style="width:104px"><col style="width:104px"><col style="width:104px"><col style="width:96px"><col style="width:72px"><col style="width:200px"><col style="width:240px"><col style="width:140px"><col style="width:210px"></colgroup><thead><tr><th>Region</th>""")
    rep(".bltable { min-width: 1120px; }",
        ".bltable { min-width: 1490px; table-layout: fixed; } .bltable td, .bltable td span { white-space: normal !important; overflow-wrap: anywhere; } .bltable td.cost .rm { display: inline-block; min-width: 64px; } .bltable th { white-space: normal; vertical-align: bottom; font-size: 12.5px; line-height: 1.3; } .bltable th span { font-size: 11px; color: var(--text-muted); } .bltable td { vertical-align: top; } .bltable td.cost { font-size: 12.5px; } .bltable td.dispc, .bltable th.dispc { text-align: right; }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
