"""School report, "Staffing changes" table: Students and Students per teacher move above Total FTE and Staffing cost, and two
rows follow each total for keeping every class under the PAT overload thresholds: Total FTE if PAT thresholds kept
(total + the teachers in "more FTE to stay under": K-5 homerooms to keep every class at or under its threshold, 6-8 and
9-12 teachers to keep daily loads under 150 / 160) and Staffing cost if PAT thresholds kept (+ those teachers at the
licensed cost per FTE). Each scenario shows its change from Status Quo; a closing school shows "closes".
Runs after patch_rp_ratio. Code changed once.
"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'rp-pat-rows' not in html:
    # split the position rows: everything but the total, then the total
    rep("""  const rows = STAFF_COLS.filter(([c]) => cols.some(s => F[s] && F[s][c])).map(([c, l]) =>
    `<tr${c === 'total' ? ' class="tot"' : ''}><td>${esc(l)}</td>${cols.map(s => cell(s, c)).join('')}</tr>`).join('');""",
        """  const rowOf = ([c, l]) => `<tr${c === 'total' ? ' class="tot"' : ''}><td>${esc(l)}</td>${cols.map(s => cell(s, c)).join('')}</tr>`;   // rp-pat-rows
  const rows = STAFF_COLS.filter(([c]) => c !== 'total' && cols.some(s => F[s] && F[s][c])).map(rowOf).join('');
  const rowTot = rowOf(STAFF_COLS.find(([c]) => c === 'total'));""")
    # remove the students rows from after Staffing cost (patch_rp_ratio) and rebuild the table body in the new order
    m = re.search(r"""    `<tr><td>Staffing cost</td>\$\{cols\.map\(cost\)\.join\(''\)\}</tr>` \+\n    \(\(teach, row\) => .*?\)\.join\(''\) \+ '</tr>'\) \+\n    `</tbody></table>` \+ rpActualStaff\(k\) \+""", html, re.S)
    assert m, 'students rows block'
    html = html[:m.start()] + r"""    ((teach, row) => row('Students', r => r.enroll, 0, '') + row('Students per teacher', r => teach(r) ? r.enroll / teach(r) : null, 1,
        'Projected students over classroom teachers under the staffing formula (K-5 homeroom, PE / arts / library, 6-8 and 9-12 teachers); counselors, support staff and administrators are not counted') +
      rowTot + row('Total FTE if PAT thresholds kept', (r, p) => p ? r.total + p.extra : null, 1, 'Total FTE plus the teachers needed to keep every K-5 class at or under its PAT threshold and 6-8 and 9-12 daily loads under ' + PAT_MS + ' and ' + PAT_HS + ' students (the "more FTE to stay under" below)', 'tot') +
      `<tr><td>Staffing cost</td>${cols.map(cost).join('')}</tr>` +
      row('Staffing cost if PAT thresholds kept', (r, p) => p ? staffCost(r) + p.extra * SC.licensed : null, 'usd', 'Staffing cost plus the extra teachers at the licensed cost per FTE (salary and benefits, 2026-27 $)'))(
      r => r.homeroom + r.specialists + r.t68 + r.t912,
      (lab, val, dp, tip, cls) => `<tr${cls ? ` class="${cls}"` : ''}><td${tip ? ` title="${esc(tip)}"` : ''}>${lab}</td>` + cols.map(s => {
        const r = F[s]; if (!r) return s !== 'SQ' && F.SQ ? `<td class="muted${s === sc ? ' cur' : ''}">closes</td>` : '<td class="muted">closed</td>';
        const v = val(r, P[s]), q = F.SQ ? val(F.SQ, P.SQ) : null; if (v == null) return `<td${s === sc ? ' class="cur"' : ''}>&mdash;</td>`;
        const d = s !== 'SQ' && q != null ? v - q : 0, usd = dp === 'usd';
        const show = usd ? staffUSD(v) : dp ? v.toFixed(dp) : Math.round(v).toLocaleString();
        const dd = usd ? (Math.abs(d) >= 5e4 ? `<span class="sq">${d > 0 ? '+' : ''}${staffUSD(d)} vs SQ</span>` : '') :
          Math.abs(d) >= (dp ? 0.05 : 0.5) ? `<span class="sq">${d > 0 ? '+' : '&minus;'}${dp ? Math.abs(d).toFixed(dp) : Math.round(Math.abs(d)).toLocaleString()} vs SQ</span>` : '';
        return `<td${s === sc ? ' class="cur"' : ''}>${show}${dd}</td>`;
      }).join('') + '</tr>') +
    `</tbody></table>` + rpActualStaff(k) +""" + html[m.end():]
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
