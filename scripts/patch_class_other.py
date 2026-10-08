"""Class-size table: a "Schools not on this page" row in the forecast cross-check, so this page's schools plus that
row equal the district forecast (Table 5.2). Its grade cells are Table 5.2 minus this page's count; its label names
the schools and programs the forecast includes but the page does not model (no attendance areas, outside the
scenarios), with their enrollment from the forecast's school table (Table 5.5,
archive/pps-enrollment-forecast-2026-27-table-5.5.json). Runs after patch_class_gpr. Data refreshed on rerun;
code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
T55 = json.load(open(os.path.join(ROOT, 'archive', 'pps-enrollment-forecast-2026-27-table-5.5.json'), encoding='utf-8'))
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
norm = lambda n: re.sub(r'[^a-z]', '', n.lower())
ours = {norm(k) for k in D['region_of']} | {norm(s['name']) for s in D['schools']}
LABEL = {'Other (incl. Charters)': 'charter schools and other programs', 'Benson Polytechnic': 'Benson Polytechnic',
         'da Vinci': 'da Vinci Arts', 'ACCESS': 'ACCESS', 'MLC': 'Metropolitan Learning Center'}
other = {}
for name, s in T55['schools'].items():
    if norm(name) in ours or any(norm(name).startswith(o[:6]) for o in ours): continue
    tot = s['programs'].get('Total', {})
    other[LABEL.get(name, name)] = {y: tot.get(y) for y in D['years'] if tot.get(y) is not None}
D['forecast_other'] = dict(source='PPS Enrollment Forecast 2026-27, Table 5.5 (school totals)', schools=other)
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
print('not on this page:', ', '.join(f"{k} ({v.get('2027-28')})" for k, v in other.items()))

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if "Schools not on this page" not in html:
    rep("""    h += `<tr class="csfc"><td>PPS forecast, Table 5.2<span class="cssub">medium scenario, all PPS schools</span></td><td>${n0(ft)}</td>` +""",
        """    // students the forecast counts at schools this page does not model: Table 5.2 minus this page, by grade
    const oth = Object.entries(D.forecast_other?.schools || {}).map(([n, v]) => [n, v[csYear]]).filter(([, v]) => v).sort((a, b) => b[1] - a[1]);
    h += `<tr class="csfc"><td>Schools not on this page<span class="cssub">${oth.map(([n, v]) => `${esc(n)} ${n0(v)}`).join(' &middot; ')}</span></td><td>${n0(ft - dist.E)}</td>` +
      cells((v, i) => `<td title="${esc(`grade ${CS_GRADES[i]}: ${n0(v)} in the forecast, ${n0(ours(i))} at the schools on this page`)}">${n0(v - ours(i))}</td>`) + '</tr>';
    h += `<tr class="csfc"><td>PPS forecast, Table 5.2<span class="cssub">medium scenario, all PPS schools (this page + schools not on it)</span></td><td>${n0(ft)}</td>` +""")
    rep(".cstable tr.csfc td { color: var(--text-secondary); font-size: 12.5px; }",
        ".cstable tr.csfc td { color: var(--text-secondary); font-size: 12.5px; } .cstable tr.csfc .cssub { white-space: normal; max-width: 260px; }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
