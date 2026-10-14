"""School report, "Staffing changes" table: "Core class ratio" becomes "Average class size", with the daily schedule for
grades 6-12, and a "Daily load per teacher (6-12)" row follows it.
  Average class size: K-5 students / K-5 homeroom teachers; grades 6-12 students x periods in the day (7) / (teachers x
  periods taught, 5: the budget's 5-of-7 schedule, CS_DAY / CS_TAUGHT); a K-8 school weights its K-5 and 6-8 parts by
  their students (its K-5 share, k5Of). PE, arts and library specialists, counselors, support and administrators are
  left out. The 6-8 and 9-12 teachers include every subject the formula funds, not only core subjects.
  Daily load per teacher (6-12): the students a 6-8 or 9-12 teacher sees a day (students x 7 / teachers), compared with
  the PAT overload limits (150 for 6-8, 160 for 9-12); shown red when over. Blank for K-5 schools.
Runs after patch_rp_ratios2. Code changed once.
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

if 'Average class size' not in html:
    rep("""      row('Core class ratio', r => { const c = r.homeroom + r.t68 + r.t912; return c ? r.enroll / c : null; }, 1,
        'Projected students over core classroom teachers: K-5 homeroom teachers and 6-8 and 9-12 teachers (PE, arts and library specialists, counselors, support staff and administrators are not counted). Roughly the average class size for K-5; for 6-8 and 9-12, students per teacher before the daily schedule') +""",
        """      ((parts, row2) => row('Average class size', r => { const p = parts(r), n = p.k5 + p.m68 + p.h912;   // rp-classsize
          const c5 = r.homeroom ? p.k5 / r.homeroom : null, c68 = r.t68 ? p.m68 * CS_DAY / (r.t68 * CS_TAUGHT) : null, c912 = r.t912 ? p.h912 * CS_DAY / (r.t912 * CS_TAUGHT) : null;
          const w = [[p.k5, c5], [p.m68, c68], [p.h912, c912]].filter(([s, c]) => s > 0 && c != null);
          return w.length ? w.reduce((a, [s, c]) => a + s * c, 0) / w.reduce((a, [s]) => a + s, 0) : null; }, 1,
          `Students per class, averaged over students. K-5: students / homeroom teachers. Grades 6-12: students x ${CS_DAY} periods / (teachers x ${CS_TAUGHT} periods taught), the budget's ${CS_TAUGHT}-of-${CS_DAY} schedule. A K-8 weights its K-5 and 6-8 parts by their students. PE, arts and library, counselors, support and administrators are not counted; 6-8 and 9-12 teachers include every subject the formula funds, not only core subjects, and not every student takes ${CS_DAY} periods.`) +
        row2('Daily load per teacher (6-12)', r => { const p = parts(r); return r.t68 + r.t912 ? (p.m68 + p.h912) * CS_DAY / (r.t68 + r.t912) : null; },
          `Students a 6-8 or 9-12 teacher sees a day: students x ${CS_DAY} periods / teachers. PAT overload limits: ${PAT_MS} a day in grades 6-8, ${PAT_HS} in 9-12 (red when over).`))(
        r => { const f = r.type === 'K8' ? (k5Of(k, rpYear) ?? 0.66) : r.type === 'ES' ? 1 : 0;
          return { k5: r.type === 'ES' || r.type === 'K8' ? r.enroll * f : 0, m68: r.type === 'MS' ? r.enroll : r.type === 'K8' ? r.enroll * (1 - f) : 0, h912: r.type === 'HS' ? r.enroll : 0 }; },
        (lab, val, tip) => row(lab, val, 0, tip).replace(/<td( class="cur")?>(\\d[\\d,]*)/g, (m, c, v) => {
          const lim = (F.SQ || Object.values(F).find(Boolean))?.type === 'HS' ? PAT_HS : PAT_MS;
          return +v.replace(/,/g, '') > lim ? `<td${c || ''} style="color:var(--down);font-weight:600">${v}` : m; })) +""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
