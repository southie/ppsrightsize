"""School report, "Staffing changes" table: Students per adult (above Students per teacher) and Core class ratio (after it).
  Students per adult = students / every position under the staffing formula, office staff counted as people (the
  formula counts an administrative assistant as half a licensed FTE, so its office FTE is doubled back).
  Core class ratio = students / core classroom teachers: K-5 homeroom teachers and 6-8 and 9-12 teachers (PE, arts and
  library specialists, counselors, support staff and administrators left out).
Runs after patch_rp_pat_rows. Code changed once.
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

if 'Core class ratio' not in html:
    rep("""    ((teach, row) => row('Students', r => r.enroll, 0, '') + row('Students per teacher', r => teach(r) ? r.enroll / teach(r) : null, 1,
        'Projected students over classroom teachers under the staffing formula (K-5 homeroom, PE / arts / library, 6-8 and 9-12 teachers); counselors, support staff and administrators are not counted') +""",
        """    ((teach, row) => row('Students', r => r.enroll, 0, '') +
      row('Students per adult', r => { const a = r.total + r.office; return a ? r.enroll / a : null; }, 1,
        'Projected students over every position under the staffing formula: principals, assistant principals, office staff (counted as people: the formula counts an administrative assistant as half a licensed FTE), teachers, PE / arts / library, counselors, social workers and discretionary support') +
      row('Students per teacher', r => teach(r) ? r.enroll / teach(r) : null, 1,
        'Projected students over classroom teachers under the staffing formula (K-5 homeroom, PE / arts / library, 6-8 and 9-12 teachers); counselors, support staff and administrators are not counted') +
      row('Core class ratio', r => { const c = r.homeroom + r.t68 + r.t912; return c ? r.enroll / c : null; }, 1,
        'Projected students over core classroom teachers: K-5 homeroom teachers and 6-8 and 9-12 teachers (PE, arts and library specialists, counselors, support staff and administrators are not counted). Roughly the average class size for K-5; for 6-8 and 9-12, students per teacher before the daily schedule') +""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
