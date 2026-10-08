"""Homeschooling table at the end of the private-school section: new homeschool registrations by school year
(Portland School District and Multnomah County) and students registered on November 1, from Multnomah ESD
(source/homeschool/mesd-homeschool.json, scripts/build_homeschool.py). Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
H = json.load(open(os.path.join(ROOT, 'source', 'homeschool', 'mesd-homeschool.json'), encoding='utf-8'))
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['homeschool'] = {k: H[k] for k in ('new_registrations', 'new_registrations_partial_year', 'registered_nov1', 'registered_county_jun1_2022', 'pre_2020_portland_new_registrations', 'years', 'by_district')}
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderHomeschool' not in html:
    rep("""    <div class="tablewrap" id="privcap"></div>
  </section>""", """    <div class="tablewrap" id="privcap"></div>
    <h3 class="cshead">Homeschooling</h3>
    <p class="sub">Families homeschooling in Multnomah County register with Multnomah ESD when they start; they are not required to report when they stop, so the registered totals can overcount (and drop sharply when records are cleaned up), and families unaware of the rule are not counted. Registration applies from age 6, so this is roughly grades 1-12. MESD did not publish registered totals by district before November 2023 (about 3,700 county-wide on June 1, 2022).</p>
    <div class="tablewrap"><table class="hstable" id="homeschool"></table></div>
  </section>""")
    rep("function renderAll() {", r"""// ---------- homeschool registrations (D.homeschool, Multnomah ESD) ----------
function renderHomeschool() {
  const t = document.getElementById('homeschool'); if (!t || t.dataset.done) return;
  const H = D.homeschool, NP = H.new_registrations.Portland, NC = H.new_registrations['Multnomah County'];
  const RP = H.registered_nov1.Portland, RC = H.registered_nov1['Multnomah County'], n = v => v == null ? '&mdash;' : v.toLocaleString();
  const pre = Object.values(H.pre_2020_portland_new_registrations), preAvg = Math.round(pre.reduce((a, b) => a + b, 0) / pre.length);
  t.innerHTML = `<thead><tr><th>School year</th><th>New registrations<br><span style="font-weight:400">Portland School District</span></th><th>New registrations<br><span style="font-weight:400">Multnomah County</span></th>` +
    `<th>Registered on Nov. 1<br><span style="font-weight:400">Portland School District</span></th><th>Registered on Nov. 1<br><span style="font-weight:400">Multnomah County</span></th></tr></thead><tbody>` +
    Object.keys(NP).map(y => { const nov = y.slice(0, 4), part = y === H.new_registrations_partial_year.split(' ')[0];
      return `<tr><td>${y}${part ? ' <span class="muted">(July to Oct.)</span>' : ''}</td><td>${n(NP[y])}${!part ? `<span class="cssub">${NP[y] >= preAvg ? '+' : '&minus;'}${Math.abs(Math.round(100 * (NP[y] / preAvg - 1)))}% vs 2017-20 average</span>` : ''}</td>` +
        `<td>${n(NC[y])}</td><td>${n(RP[nov])}</td><td>${n(RC[nov])}</td></tr>`; }).join('') +
    `</tbody><tfoot><tr><td colspan="5" class="muted" style="text-align:left;font-size:12px">Before the pandemic, about ${preAvg.toLocaleString()} Portland students a year started homeschooling (2017-18 to 2019-20). Source: Multnomah ESD Homeschool Data Briefs (Nov. 2023, 2024, 2025) and registration report.</td></tr></tfoot>`;
  t.dataset.done = '1';
}
function renderAll() {""")
    rep("renderLines(); renderClassSizes(); renderPrivCap(); }", "renderLines(); renderClassSizes(); renderPrivCap(); renderHomeschool(); }")
    rep(".pctable td, .pctable th { white-space: nowrap; }", ".hstable { min-width: 640px; } .hstable .cssub { display: block; font-size: 11px; color: var(--text-muted); }\n.pctable td, .pctable th { white-space: nowrap; }")
if 'function renderHsDistricts' not in html:
    rep("""    <div class="tablewrap"><table class="hstable" id="homeschool"></table></div>
  </section>""", """    <div class="tablewrap"><table class="hstable" id="homeschool"></table></div>
    <h3 class="cshead">Homeschooling trends by school district</h3>
    <p class="sub">Multnomah ESD reports homeschool registrations by school district only, not by PPS region, so this compares Portland with the other districts in Multnomah County. New registrations by school year; the chart runs from 2017-18 to 2024-25 (2025-26 is July to October only). Students registered on November 1 can overcount, since families need not report when they stop.</p>
    <div class="tablewrap"><table class="hstable" id="hsdistrict"></table></div>
  </section>""")
    rep("function renderAll() {", r"""// homeschool trends by MESD component district (D.homeschool.by_district)
function renderHsDistricts() {
  const t = document.getElementById('hsdistrict'); if (!t || t.dataset.done) return;
  const H = D.homeschool, Y = H.years, show = Y.filter(y => y >= '2020-21'), full = Y.filter(y => !H.new_registrations_partial_year.startsWith(y));
  const pre = Y.filter(y => y < '2020-21'), last = full[full.length - 1], NOV = ['2023', '2024', '2025'];
  const n = v => v == null ? '&mdash;' : v.toLocaleString();
  const rows = Object.entries(H.by_district).map(([d, v]) => ({ d, v })).sort((a, b) => (b.v.registered_nov1['2025'] || 0) - (a.v.registered_nov1['2025'] || 0));
  const total = { d: 'Multnomah County', v: { new: Object.fromEntries(Y.map(y => [y, rows.reduce((a, r) => a + (r.v.new[y] || 0), 0)])),
    registered_nov1: Object.fromEntries(NOV.map(y => [y, rows.reduce((a, r) => a + (r.v.registered_nov1[y] || 0), 0)])) } };
  const pc = v => v == null ? '&mdash;' : `<span class="${v > 0.5 ? 'pcup' : v < -0.5 ? 'pcdown' : ''}">${v > 0 ? '+' : v < 0 ? '&minus;' : ''}${Math.abs(Math.round(v))}%</span>`;
  const row = (r, cls) => {
    const avg = pre.reduce((a, y) => a + (r.v.new[y] || 0), 0) / pre.length, ch = avg ? 100 * (r.v.new[last] / avg - 1) : null;
    const r23 = r.v.registered_nov1['2023'], r25 = r.v.registered_nov1['2025'], rc = r23 ? 100 * (r25 / r23 - 1) : null;
    return `<tr class="${cls || ''}"><td>${esc(r.d)}</td>` + show.map(y => `<td>${n(r.v.new[y])}</td>`).join('') +
      `<td>${pc(ch)}<span class="cssub">${Math.round(avg)} a year before</span></td>` +
      `<td class="pcspark" title="${esc(full.map(y => `${y}: ${r.v.new[y]}`).join(' · '))}">${pcSpark(full.map(y => r.v.new[y] || 0))}</td>` +
      NOV.map(y => `<td>${n(r.v.registered_nov1[y])}</td>`).join('') + `<td>${pc(rc)}</td></tr>`;
  };
  t.innerHTML = `<thead><tr><th>School district</th>` + show.map(y => `<th>${y}${H.new_registrations_partial_year.startsWith(y) ? '<br><span style="font-weight:400">July-Oct.</span>' : ''}</th>`).join('') +
    `<th>New, ${last}<br><span style="font-weight:400">vs 2017-20 average</span></th><th>New registrations<br><span style="font-weight:400">${full[0]} to ${last}</span></th>` +
    NOV.map(y => `<th>Registered<br><span style="font-weight:400">Nov. 1, ${y}</span></th>`).join('') + `<th>Registered<br><span style="font-weight:400">2023 to 2025</span></th></tr></thead><tbody>` +
    rows.map(r => row(r, r.d === 'Portland' ? 'hsport' : '')).join('') + row(total, 'dist') + '</tbody>';
  t.dataset.done = '1';
}
function renderAll() {""")
    rep("renderClassSizes(); renderPrivCap(); renderHomeschool(); }", "renderClassSizes(); renderPrivCap(); renderHomeschool(); renderHsDistricts(); }")
    rep(".hstable { min-width: 640px; }", ".hstable { min-width: 640px; } .hstable td.pcspark svg { display: block; margin-left: auto; } .hstable .pcup { color: var(--up); font-weight: 600; } .hstable .pcdown { color: var(--down); font-weight: 600; }\n.hstable tr.hsport td { font-weight: 600; background: var(--surface-2); }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
