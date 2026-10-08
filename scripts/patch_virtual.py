"""Virtual schools at the end of the private-school section, after homeschooling: PPS's statement that it is below the
3% virtual charter cap (quoted, with a link), Oregon virtual charter enrollment by year and grade band,
the approximate 3% ceiling, and the virtual charter schools by enrollment. Data from
ODE Fall Membership Reports (source/ode-virtual/virtual-charters.json, scripts/build_virtual.py). Runs after
patch_homeschool. Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
V = json.load(open(os.path.join(ROOT, 'source', 'ode-virtual', 'virtual-charters.json'), encoding='utf-8'))
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['virtual'] = {k: V[k] for k in ('source', 'source_url', 'pps_cap', 'years', 'total', 'bands', 'state_total', 'pps_total')}
D['virtual']['schools'] = [dict(name=s['name'], sponsor=s['sponsor'], n=s['enrollment']) for s in V['schools']]
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderVirtual' not in html:
    rep("""    <div class="tablewrap"><table class="hstable" id="hsdistrict"></table></div>
  </section>""", """    <div class="tablewrap"><table class="hstable" id="hsdistrict"></table></div>
    <h3 class="cshead">Virtual schools</h3>
    <p class="sub">Oregon students can enroll full time in a virtual (online) public charter school anywhere in the state. If more than 3% of a district's resident students already attend one, new enrollments need the district's approval (ORS 338.125, OAR 581-020-0342). PPS says it is below that cap:</p>
    <blockquote class="vcquote">&ldquo;Portland Public Schools is currently below the 3% district cap set by OAR 581-020-0342.&rdquo;<cite>&mdash; <a href="https://www.pps.net/Page/1029" target="_blank" rel="noopener">PPS, Other Application Types: Virtual Public Charter Schools</a> (undated; read October 2026)</cite></blockquote>
    <p class="sub">ODE counts students at the school they attend, not the district they live in, so how many Portland residents attend virtual charters is not published. The table shows statewide enrollment in the virtual charter schools ODE flags as virtual in 2025-26 and the 3% ceiling PPS says it is under (3% of PPS enrollment, approximately). District-run online schools such as Scappoose Online Academy and Beaverton FLEX are not charters and are not included.</p>
    <div class="tablewrap"><table class="hstable" id="virtual"></table></div>
    <details class="vcschools"><summary>Virtual charter schools by enrollment</summary><div class="tablewrap"><table class="hstable" id="vcschools"></table></div></details>
  </section>""")
    rep("function renderAll() {", r"""// ---------- virtual charter enrollment (D.virtual, ODE Fall Membership Reports) ----------
function renderVirtual() {
  const t = document.getElementById('virtual'); if (!t || t.dataset.done) return;
  const V = D.virtual, n = v => v == null ? '&mdash;' : Math.round(v).toLocaleString(), first = V.years[0];
  t.innerHTML = `<thead><tr><th>School year</th><th>Virtual charter students<br><span style="font-weight:400">Oregon, October 1</span></th><th>Share of Oregon<br><span style="font-weight:400">public enrollment</span></th>` +
    `<th>K-5</th><th>6-8</th><th>9-12</th><th>3% cap<br><span style="font-weight:400">approximate, PPS says it is below</span></th></tr></thead><tbody>` +
    V.years.map(y => { const r = V.total[y] / V.state_total[y], b = V.bands[y], ch = 100 * (V.total[y] / V.total[first] - 1);
      return `<tr><td>${y}</td><td>${n(V.total[y])}${y !== first ? `<span class="cssub">${ch >= 0 ? '+' : '&minus;'}${Math.abs(Math.round(ch))}% vs ${first}</span>` : ''}</td><td>${(100 * r).toFixed(1)}%</td>` +
        `<td>${n(b['K-5'])}</td><td>${n(b['6-8'])}</td><td>${n(b['9-12'])}</td>` +
        `<td>~${n(0.03 * V.pps_total[y])}</td></tr>`; }).join('') +
    `</tbody><tfoot><tr><td colspan="7" class="muted" style="text-align:left;font-size:12px">Source: <a href="${V.source_url}" target="_blank" rel="noopener">Oregon Department of Education, Fall Membership Reports</a> 2019-20 to 2025-26. Schools followed by ODE school ID (Evergreen Virtual Academy was Oregon Virtual Academy).</td></tr></tfoot>`;
  const s = document.getElementById('vcschools'), last = V.years[V.years.length - 1];
  s.innerHTML = `<thead><tr><th>School</th><th>Sponsoring district</th><th>${first}</th><th>${last}</th><th>${first} to ${last}</th></tr></thead><tbody>` +
    V.schools.map(c => `<tr><td>${esc(c.name)}</td><td>${esc(c.sponsor)}</td><td>${n(c.n[first])}</td><td>${n(c.n[last])}</td>` +
      `<td class="pcspark" title="${esc(V.years.map(y => `${y}: ${c.n[y] ?? 'not open'}`).join(' · '))}">${pcSpark(V.years.map(y => c.n[y] || 0))}</td></tr>`).join('') +
    `<tr class="dist"><td>All virtual charters</td><td></td><td>${n(V.total[first])}</td><td>${n(V.total[last])}</td><td class="pcspark">${pcSpark(V.years.map(y => V.total[y]))}</td></tr></tbody>`;
  t.dataset.done = '1';
}
function renderAll() {""")
    rep("renderHomeschool(); renderHsDistricts(); }", "renderHomeschool(); renderHsDistricts(); renderVirtual(); }")
    rep(".hstable { min-width: 640px; }", ".hstable { min-width: 640px; }\n.vcquote { margin: 4px 0 10px; padding: 8px 14px; border-left: 4px solid var(--priv); background: var(--surface-2); border-radius: 4px; font-size: 14px; }\n.vcquote cite { display: block; margin-top: 4px; font-style: normal; font-size: 12px; color: var(--text-muted); }\n.vcschools { margin-top: 8px; } .vcschools summary { cursor: pointer; font-size: 13px; color: var(--text-secondary); }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
