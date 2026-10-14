"""A summary section above the school report: what newer population data (PSU's August 2026 Multnomah County projections
for Preschool for All) changes, from source/pfa-impact.json (scripts/build_pfa_impact.js, run with the modified
enrollment model on): the kindergarten path, the scenario measures (schools below threshold, schools and students above
it, students), schools that fall below or near their threshold (each opens its school report), the largest
enrollment drops, the regions affected, and the main takeaways, with a button to turn the switch on or off.
Also: the school report's search ignores accents and punctuation ("cesar chavez", "ida b wells", "boise eliot").
Data: D.pfaImpact (refreshed on rerun); code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['pfaImpact'] = json.load(open(os.path.join(ROOT, 'source', 'pfa-impact.json'), encoding='utf-8'))
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

SECTION = '''  <section class="card" id="pfacard">
    <h2>What newer population data changes</h2>
    <div id="pfasum"></div>
  </section>

  <section class="card" id="reportcard">'''

JS = r'''// ---------- summary: what the county population (PFA study) data changes (scripts/patch_pfa_summary.py) ----------
function renderPfaSummary() {
  const host = document.getElementById('pfasum'), P = D.pfaImpact; if (!host || !P) return;
  const nm = k => P.names[k] || k, lk = k => `<a href="#" class="pfa-sch" data-k="${esc(k)}" title="Open the school report">${esc(nm(k))}</a>`;
  const L = { SQ: 'Status Quo', A: 'Scenario A', B: 'Scenario B' }, arrow = (a, b, u = '') => a === b ? `${a}${u}` : `${a}${u} &rarr; <b>${b}${u}</b>`;
  const ky = Object.keys(P.pfa.k_psu);
  const kt = `<div class="tablewrap"><table style="min-width:0;font-size:12.5px"><thead><tr><th style="text-align:left">Kindergarten, fall</th>${ky.map(y => `<th style="text-align:right">${y.slice(0, 4)}</th>`).join('')}</tr></thead><tbody>` +
    `<tr><td style="text-align:left">PSU PPS forecast (May 2026)</td>${ky.map(y => `<td style="text-align:right">${P.pfa.k_psu[y].toLocaleString()}</td>`).join('')}</tr>` +
    `<tr><td style="text-align:left">District share of county population (PFA study)</td>${ky.map(y => `<td style="text-align:right;${P.pfa.k_pfa[y] < P.pfa.k_psu[y] - 50 ? 'color:var(--down);font-weight:600' : ''}">${P.pfa.k_pfa[y].toLocaleString()}</td>`).join('')}</tr></tbody></table></div>`;
  const st = `<div class="tablewrap"><table style="min-width:0"><thead><tr><th style="text-align:left"></th><th>Schools below threshold<br><span style="font-weight:400">2031-32 / 2035-36</span></th><th>Schools above threshold<br><span style="font-weight:400">district measure, 2031-32</span></th><th>Students above threshold</th><th>Students at this page's schools<br><span style="font-weight:400">2031-32 / 2035-36</span></th></tr></thead><tbody>` +
    ['SQ', 'A', 'B'].map(s => { const v = P.scen[s];
      return `<tr><td style="text-align:left"><b>${L[s]}</b></td><td style="text-align:right">${arrow(...v.below[0])} / ${arrow(...v.below[1])}</td><td style="text-align:right">${arrow(...v.schools_above, '%')}</td><td style="text-align:right">${arrow(...v.students_above, '%')}</td>` +
        `<td style="text-align:right">${v.students.map(([a, b]) => arrow(Math.round(a).toLocaleString(), Math.round(b).toLocaleString())).join(' / ')}</td></tr>`; }).join('') + `</tbody></table></div>`;
  const flips = (y, s) => { const f = P.schools[`${y}|${s}`].flips; return f.length ? f.map(([k, a, b, th]) => `${lk(k)} <span class="muted">(${a} &rarr; ${b}; threshold ${th})</span>`).join(', ') : '<span class="muted">none</span>'; };
  const near = (y, s) => P.schools[`${y}|${s}`].near.map(([k, b, th]) => `${lk(k)} <span class="muted">${b}/${th}</span>`).join(', ');
  const ft = `<div class="tablewrap"><table style="min-width:0"><thead><tr><th style="text-align:left"></th><th style="text-align:left">2031-32 (elementary)</th><th style="text-align:left">2035-36 (middle and high)</th></tr></thead><tbody>` +
    ['SQ', 'A', 'B'].map(s => `<tr><td style="text-align:left;vertical-align:top"><b>${L[s]}</b></td><td style="text-align:left;vertical-align:top;white-space:normal">${flips('2031-32', s)}</td><td style="text-align:left;vertical-align:top;white-space:normal">${flips('2035-36', s)}</td></tr>`).join('') + `</tbody></table></div>`;
  const nearAll = [...new Set(['2031-32', '2035-36'].flatMap(y => ['SQ', 'A', 'B'].flatMap(s => P.schools[`${y}|${s}`].near.map(x => x[0]))))];
  const drops = y => [...new Map(['SQ', 'A', 'B'].flatMap(s => P.schools[`${y}|${s}`].drops).map(x => [x[0], x])).values()].sort((p, q) => (p[2] - p[1]) - (q[2] - q[1])).slice(0, 7).map(([k, a, b]) => `${lk(k)} <span class="muted">${b - a}</span>`).join(', ');
  const rg = D.region_order.map(r => { const R = P.regions[r]; const ms = R.measures.map(([s, kk, a, b]) => `${L[s]} ${kk === 'schools_above' ? 'schools' : 'students'} above ${a}&rarr;${b}%`).join('; ');
    return `<li><b>${esc(r)}</b>: ${ms || 'no change in its measures'}</li>`; }).join('');
  const sA = P.scen.A, sB = P.scen.B;
  host.innerHTML = `<p class="sub">The page's enrollment follows Portland State University's May 2026 PPS forecast. In August 2026 PSU published new Multnomah County population projections for Preschool for All, built on the Census Bureau's 2025 estimates: fewer young children, with small birth cohorts in 2021 and 2023 and continued out-migration of families with young children. The study covers the whole county; this page uses the part in the PPS district (the county's 5-year-olds &times; PPS's share of the county's children, about 54-57% &times; a capture rate of ${(100 * P.pfa.capture).toFixed(0)}%, which keeps PSU's long-run kindergarten of about 2,700), kindergarten through 2029 comes in lower than PSU's forecast, and the smaller classes reach the middle schools by 2035. Figures below are with the modified enrollment model on; turn the switch on to see them across the page.</p>` +
    `<div class="controls"><button type="button" id="pfa-go">${pfaOn ? 'Turn off' : 'Turn on'} &ldquo;District share of county population (PFA study)&rdquo;</button><span class="muted">${pfaOn ? 'On: the page uses the district share of the county population projections.' : 'Off: the page shows PSU’s May 2026 forecast.'}</span></div>` +
    `<h3 class="cshead">Key takeaways</h3><ul class="sub" style="margin-top:4px">` +
    `<li><b>Scenario B is the most exposed:</b> schools below threshold ${sB.below[0].join('&rarr;')} in 2031-32 and ${sB.below[1].join('&rarr;')} by 2035-36; schools above threshold ${sB.schools_above.join('&rarr;')}%, students in them ${sB.students_above.join('&rarr;')}%. It keeps more small elementary and middle schools open, so smaller classes push more of them under.</li>` +
    `<li><b>Scenario A holds up better:</b> ${sA.below[0].join('&rarr;')} schools below threshold in 2031-32, ${sA.below[1].join('&rarr;')} by 2035-36; schools above threshold ${sA.schools_above.join('&rarr;')}%, students in them ${sA.students_above.join('&rarr;')}%.</li>` +
    `<li><b>Fewer students overall:</b> about ${Math.round(P.scen.SQ.students[0][0] - P.scen.SQ.students[0][1]).toLocaleString()} fewer at this page's schools in 2031-32 and ${Math.round(P.scen.SQ.students[1][0] - P.scen.SQ.students[1][1]).toLocaleString()} fewer in 2035-36, nearly all from smaller kindergarten classes born 2021-2025 moving up.</li>` +
    `<li><b>Elementary first (2031-32):</b> ${['SQ', 'A', 'B'].flatMap(s => P.schools['2031-32|' + s].flips.map(x => x[0])).filter((v, i, a) => a.indexOf(v) === i).map(lk).join(', ')} fall below their threshold.</li>` +
    `<li><b>Middle schools next (2035-36):</b> ${['A', 'B'].flatMap(s => P.schools['2035-36|' + s].flips.map(x => x[0])).filter((v, i, a) => a.indexOf(v) === i).map(lk).join(', ')} fall below under the scenarios as the smaller classes reach grades 6-8.</li>` +
    `<li><b>Ida B. Wells / Lincoln is least affected</b>; Grant / McDaniel and Jefferson / Roosevelt see the largest changes in the district's measures.</li></ul>` +
    `<h3 class="cshead">Kindergarten</h3>${kt}` +
    `<h3 class="cshead">By scenario (switch off &rarr; on)</h3>${st}` +
    `<h3 class="cshead">Schools that fall below their size threshold with the newer data</h3>${ft}` +
    `<p class="sub" style="margin-top:6px"><b>Within 3% of their threshold</b> with the newer data (one more weak year away): ${nearAll.map(lk).join(', ')}. <b>Largest enrollment drops:</b> 2031-32 ${drops('2031-32')}; 2035-36 ${drops('2035-36')}.</p>` +
    `<h3 class="cshead">By region (district measures, 2031-32)</h3><ul class="sub" style="margin-top:4px">${rg}</ul>` +
    `<p class="muted" style="font-size:12px">Source: PSU Population Research Center, Multnomah County Population Projections 2026-2036 (Aug 11, 2026), medium scenario; PSU's PPS share of the county's children from its PPS Table 5.1. School names open their school report.</p>`;
  const go = document.getElementById('pfa-go');
  if (go) go.onclick = () => { const b = document.getElementById('pfatog'); if (!b) return; b.checked = !b.checked; b.onchange?.(); };
  host.querySelectorAll('.pfa-sch').forEach(a => a.onclick = e => { e.preventDefault(); if (typeof rpOpen === 'function') rpOpen(a.dataset.k); });
}
function renderAll() {'''

if 'renderPfaSummary' not in html:
    rep('''  <section class="card" id="reportcard">''', SECTION)
    rep("function renderAll() {", JS)
    rep("function renderAll() { renderReport();", "function renderAll() { renderPfaSummary(); renderReport();")
    rep("['mc', 'mckpis']];", "['mc', 'mckpis'], ['pfasum', 'pfasum']];")
    # accent- and punctuation-insensitive school search
    rep("""function rpMatches(v) {
  v = v.trim().toLowerCase(); if (!v) return [];""",
        """// school names compared without accents, case or punctuation ("cesar chavez", "ida b wells", "boise eliot")
const rpFold = s => (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().replace(/[.'’,]/g, '').replace(/[-–—/]/g, ' ').replace(/\\s+/g, ' ').trim();
function rpMatches(v) {
  v = rpFold(v); if (!v) return [];""")
    rep("""    const names = [rpTitle(s), short(s.name), s.name].map(x => x.toLowerCase());""",
        """    const names = [rpTitle(s), short(s.name), s.name, s.key].map(rpFold);""")
    rep("""const rpFindKey = v => {
  v = (v || '').trim().toLowerCase(); if (!v) return null;
  const s = D.schools.find(x => x.key.toLowerCase() === v || x.name.toLowerCase() === v || rpTitle(x).toLowerCase() === v || short(x.name).toLowerCase() === v) ||
    D.schools.find(x => x.name.toLowerCase().includes(v) || short(x.name).toLowerCase().includes(v));""",
        """const rpFindKey = v => {
  const f = s => (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().replace(/[.'’,]/g, '').replace(/[-–—/]/g, ' ').replace(/\\s+/g, ' ').trim();   // accents, case, punctuation ignored
  v = f(v); if (!v) return null;
  const s = D.schools.find(x => [x.key, x.name, rpTitle(x), short(x.name)].some(n => f(n) === v)) ||
    D.schools.find(x => [x.name, short(x.name), rpTitle(x), x.key].some(n => f(n).includes(v)));""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
