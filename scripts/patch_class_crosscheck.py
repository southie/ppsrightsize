"""Class-size table, forecast cross-check rows in this order under the district total: these schools' share of the
forecast; schools not on this page; PPS forecast Table 5.2; and a last row giving each part's share of Table 5.2
(this page + not on this page = 100%). Runs after patch_class_gpr and patch_class_other. Safe to rerun: applied once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'Share of Table 5.2' in html: sys.exit('already patched')
a = html.index("    // students the forecast counts at schools this page does not model: Table 5.2 minus this page, by grade")
b = html.index("  }\n  host.innerHTML = h + '</tbody></table>';", a)
html = html[:a] + r"""    // these schools' share of the forecast, by grade
    h += `<tr class="csfc"><td>These schools' share<span class="cssub">of the forecast, by grade</span></td><td>${pc(dist.E / ft)}</td>` +
      cells((v, i) => `<td title="${esc(`${n0(ours(i))} students at the schools on this page in grade ${CS_GRADES[i]}, of ${n0(v)} in the district forecast`)}">${pc(ours(i) / v)}</td>`) + '</tr>';
    // students the forecast counts at schools this page does not model: Table 5.2 minus this page, by grade
    const oth = Object.entries(D.forecast_other?.schools || {}).map(([n, v]) => [n, v[csYear]]).filter(([, v]) => v).sort((a, b) => b[1] - a[1]);
    const oshare = a => `<span class="cssub">${100 - Math.round(100 * a)}% of Table 5.2</span>`;   // from this page's rounded share, so the two add to 100
    h += `<tr class="csfc"><td>Schools not on this page<span class="cssub">${oth.map(([n, v]) => `${esc(n)} ${n0(v)}`).join(' &middot; ')}</span></td><td>${n0(ft - dist.E)}${oshare(dist.E / ft)}</td>` +
      cells((v, i) => `<td title="${esc(`grade ${CS_GRADES[i]}: ${n0(v)} in the forecast, ${n0(ours(i))} at the schools on this page`)}">${n0(v - ours(i))}${oshare(ours(i) / v)}</td>`) + '</tr>';
    h += `<tr class="csfc"><td>PPS forecast, Table 5.2<span class="cssub">medium scenario, all PPS schools (this page + schools not on it)</span></td><td>${n0(ft)}</td>` +
      cells(v => `<td>${n0(v)}</td>`) + '</tr>';
    // each part's share of Table 5.2: this page + not on this page = 100%
    // total share of Table 5.2: these schools' share + schools not on this page = 100%
    const tot = x => `<span class="main">100%</span><span class="cssub">${Math.round(100 * x)}% + ${100 - Math.round(100 * x)}%</span>`;
    h += `<tr class="csfc cstotal"><td>Share of Table 5.2<span class="cssub">these schools' share + schools not on this page</span></td><td>${tot(dist.E / ft)}</td>` +
      cells((v, i) => `<td title="${esc(`grade ${CS_GRADES[i]}: ${pc(ours(i) / v)} at the schools on this page + ${100 - Math.round(100 * ours(i) / v)}% at schools not on it = 100%`)}">${tot(ours(i) / v)}</td>`) + '</tr>';
""" + html[b:]
a = ".cstable tr.csfc td { color: var(--text-secondary); font-size: 12.5px; }"
assert html.count(a) == 1
html = html.replace(a, a + " .cstable tr.cstotal td { border-top: 1px solid var(--line); font-weight: 600; color: var(--text-primary); }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
