"""School report, "Staffing changes" table: two rows under the positions, Students (the school's projected enrollment in
the report year) and Students per teacher (enrollment / classroom teachers under the staffing formula: K-5 homeroom,
PE / arts / library, 6-8 and 9-12 teachers; counselors, support and administrators excluded), each scenario with its
change from Status Quo; a closing school shows "closes". A note explains the ratio. Code added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'rp-ratio' not in html:
    rep("""    `<tr><td>Staffing cost</td>${cols.map(cost).join('')}</tr></tbody></table>` + rpActualStaff(k) +""",
        """    `<tr><td>Staffing cost</td>${cols.map(cost).join('')}</tr>` +
    ((teach, row) => row('Students', r => r.enroll, 0) + row('Students per teacher', r => teach(r) ? r.enroll / teach(r) : null, 1))(   // rp-ratio
      r => r.homeroom + r.specialists + r.t68 + r.t912,
      (lab, val, dp) => `<tr><td${dp ? ' title="Projected students over classroom teachers under the staffing formula (K-5 homeroom, PE / arts / library, 6-8 and 9-12 teachers); counselors, support staff and administrators are not counted"' : ''}>${lab}</td>` + cols.map(s => {
        const r = F[s]; if (!r) return s !== 'SQ' && F.SQ ? `<td class="muted${s === sc ? ' cur' : ''}">closes</td>` : '<td class="muted">closed</td>';
        const v = val(r), q = F.SQ ? val(F.SQ) : null; if (v == null) return `<td${s === sc ? ' class="cur"' : ''}>&mdash;</td>`;
        const d = s !== 'SQ' && q != null ? v - q : 0;
        return `<td${s === sc ? ' class="cur"' : ''}>${dp ? v.toFixed(1) : Math.round(v).toLocaleString()}${Math.abs(d) >= (dp ? 0.05 : 0.5) ? `<span class="sq">${d > 0 ? '+' : '&minus;'}${dp ? Math.abs(d).toFixed(1) : Math.round(Math.abs(d)).toLocaleString()} vs SQ</span>` : ''}</td>`;
      }).join('') + '</tr>') +
    `</tbody></table>` + rpActualStaff(k) +""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
