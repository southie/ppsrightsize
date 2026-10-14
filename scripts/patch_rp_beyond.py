"""School report: a "Beyond the formula" panel after "Staffing changes": the school's actual staffing from PPS's 2026-27
budget, Volume 2 (source/staffing/school-staff-detail.json, scripts/build_school_staff_detail.py), 2023-24 to 2025-26
actual and 2026-27 budget:
  - this page's staffing formula (Status Quo, 2026-27; office staff counted as people) against the budget's school-
    allocated FTE: the gap is what the school gets beyond the formula;
  - school-allocated FTE by position (teachers, counselors, library, interventionists / coaches / specialists,
    educational assistants, clerical, administrators, other);
  - by funding source (General Fund base, General Fund Equity, K-5 Arts, Title I, SIA / Measure 98, Foundation, other);
  - centrally allocated school resources (special education teachers and assistants, ESL / ELD teachers and
    assistants, nutrition, custodial, other), the grand total and students per FTE;
  - in a scenario: for a school receiving students from closing schools, the special education and ESL / ELD FTE per
    student at each sending school times the students it sends (2027-28), i.e. the centrally allocated support that may
    need to follow them; for a closing school, its own special education and ESL / ELD staff.
1.00 FTE = 40 hours a week in the budget. Data: D.staffDetail (refreshed on rerun); code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
S = json.load(open(os.path.join(ROOT, 'source', 'staffing', 'school-staff-detail.json'), encoding='utf-8'))
D['staffDetail'] = dict(source=S['source'], years=S['years'], schools={k: {f: v for f, v in r.items() if f not in ('page',)} for k, r in S['schools'].items()})
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

JS = r'''// ---------- school report: beyond the formula (scripts/patch_rp_beyond.py) ----------
function rpBeyond(k, sc) {
  const SD = D.staffDetail, B = SD?.schools?.[k]; if (!B) return '<p class="muted">No Volume 2 school report for this school.</p>';
  const Y = SD.years, show = [2, 3, 4, 5], z = [0, 0, 0, 0, 0, 0];
  const g = f => B[f] || z, add = (...fs) => Y.map((_, j) => fs.reduce((a, f) => a + (g(f)[j] || 0), 0));
  const f2 = v => !v ? '<span class="muted">&ndash;</span>' : v.toFixed(2);
  const row = (lab, v, o = {}) => `<tr${o.tot ? ' class="tot"' : ''}><td style="text-align:left${o.ind ? ';padding-left:18px' : ''}"${o.tip ? ` title="${esc(o.tip)}"` : ''}>${lab}</td>${show.map(j => `<td${j === 5 ? ' class="cur"' : ''}>${o.fmt ? o.fmt(v[j]) : f2(v[j])}</td>`).join('')}</tr>`;
  const head = lab => `<tr><td colspan="${show.length + 1}" style="text-align:left;font-weight:600;padding-top:8px">${lab}</td></tr>`;
  // this page's formula, Status Quo 2026-27, office staff counted as people (the formula counts them as half a licensed FTE)
  const yi = D.years.indexOf('2026-27'), fr = (D.series.SQ[k] || [])[yi] != null ? schoolFTE(k, 'SQ', yi) : null;
  const formula = fr ? fr.total + fr.office : null, sa = g('school_total')[5], gap = formula != null ? sa - formula : null;
  const e26 = (D.series.SQ[k] || [])[yi];
  const top = `<div class="kpis" style="margin:4px 0 8px">` +
    `<div class="kpi"><div class="v">${formula != null ? formula.toFixed(1) : '&ndash;'}<span class="vt">This page's staffing formula</span></div><div class="l">Status Quo, 2026-27 (base positions only)</div></div>` +
    `<div class="kpi"><div class="v">${sa.toFixed(1)}${gap != null ? `<span class="d" style="color:var(--text-muted)">${gap >= 0 ? '+' : '&minus;'}${Math.abs(gap).toFixed(1)} beyond the formula</span>` : ''}<span class="vt">Budgeted at the school</span></div><div class="l">School-allocated FTE, 2026-27 budget</div></div>` +
    `<div class="kpi"><div class="v">${g('casr_total')[5].toFixed(1)}<span class="vt">Centrally allocated</span></div><div class="l">Special education, ESL / ELD, custodial, nutrition, other</div></div>` +
    `<div class="kpi"><div class="v">${g('grand_total')[5].toFixed(1)}<span class="vt">All staff</span></div><div class="l">${g('students_per_fte')[5] ? `${g('students_per_fte')[5]} students per FTE` : ''}${e26 ? ` &middot; ${Math.round(e26)} students` : ''}</div></div></div>`;
  const tbl = `<div class="tablewrap"><table class="rptable" style="min-width:0"><thead><tr><th style="text-align:left">FTE (1.00 = 40 hours a week)</th>${show.map(j => `<th${j === 5 ? ' class="cur"' : ''}>${Y[j]}<br><span style="font-weight:400">${j === 5 ? 'budget' : 'actual'}</span></th>`).join('')}</tr></thead><tbody>` +
    head('At the school, by position') +
    row('Teachers', g('lic_teachers'), { ind: 1 }) + row('Counselors', g('lic_counseling'), { ind: 1 }) + row('Library / media', add('lic_library', 'cls_library'), { ind: 1 }) +
    row('Interventionists, coaches, specialists', g('lic_coach'), { ind: 1, tip: 'Instructional specialists, coaches and interventionists (licensed)' }) +
    row('Educational assistants', g('cls_ea'), { ind: 1, tip: 'Educational assistants and paraeducators (classified)' }) + row('Clerical', g('cls_clerical'), { ind: 1 }) +
    row('Administrators', g('admin'), { ind: 1 }) + row('Other', add('lic_other', 'cls_other'), { ind: 1 }) + row('School-allocated total', g('school_total'), { tot: 1 }) +
    head('At the school, by funding source') +
    row('General Fund (base)', add('f_lic_gf', 'f_cls_gf', 'f_adm_gf'), { ind: 1 }) +
    row('General Fund Equity', add('f_lic_equity', 'f_cls_equity', 'f_adm_equity'), { ind: 1, tip: 'K-8: 4% of teacher FTE, split between socio-economic status and federally qualified underserved students (special education, English learners, direct certification) at schools over 40%; high schools: 9% of teachers (2026-27 Adopted Budget, Volume 1, pp. 234-237)' }) +
    row('K-5 Arts', g('f_lic_arts'), { ind: 1 }) +
    row('Title I', add('f_lic_title1', 'f_cls_title1', 'f_adm_title1'), { ind: 1, tip: 'Federal Title IA: schools with at least 33% of students directly certified for free meals (high schools if high poverty)' }) +
    row('SIA / Measure 98', add('f_lic_sia', 'f_cls_sia'), { ind: 1, tip: 'Student Investment Account and High School Success (Measure 98)' }) +
    row('Foundation', add('f_lic_foundation', 'f_cls_foundation'), { ind: 1, tip: 'School foundation funding, which ended after 2023-24' }) +
    row('Other grants and funds', add('f_lic_other', 'f_cls_other', 'f_adm_other'), { ind: 1 }) +
    head('Centrally allocated (not in the school’s budget)') +
    row('Special education teachers', g('casr_lic_sped'), { ind: 1 }) + row('Special education assistants', g('casr_cls_sped'), { ind: 1 }) +
    row('ESL / ELD teachers', g('casr_lic_esl'), { ind: 1 }) + row('ESL / ELD assistants', g('casr_cls_esl'), { ind: 1 }) +
    row('Nutrition services', g('casr_cls_nutrition'), { ind: 1 }) + row('Custodial', g('casr_cls_custodial'), { ind: 1 }) +
    row('Other', add('casr_lic_other', 'casr_cls_other'), { ind: 1 }) + row('Centrally allocated total', g('casr_total'), { tot: 1 }) +
    row('<b>All staff</b>', g('grand_total'), { tot: 1 }) + row('Students per FTE (all staff)', g('students_per_fte'), { fmt: v => v ? v.toFixed(1) : '&ndash;' }) +
    `</tbody></table></div>`;
  // scenario: special education and ESL / ELD support that may follow students between schools
  let mv = '';
  const ses = s => { const b = D.staffDetail.schools[s]; if (!b) return null; const e = (D.series.SQ[s] || [])[yi]; const f = ['casr_lic_sped', 'casr_cls_sped', 'casr_lic_esl', 'casr_cls_esl'].reduce((a, x) => a + ((b[x] || z)[5] || 0), 0); return e ? { f, per: f / e } : null; };
  const yr = D.years.indexOf(D.impl_year), base = sc === 'C' ? sc : sc;
  if (sc !== 'SQ' && D.flows[base]) {
    if ((D.detail[sc] || {})[k]?.closed) {
      const me = ses(k), to = (D.flows[base].receivers || []).filter(r => r.from_key === k && byKey[r.to_key]);
      if (me) mv = `<p class="rpnote"><b>${esc(LABEL[sc])}: ${esc(rpName(k))} closes.</b> Its centrally allocated special education and ESL / ELD staff (${me.f.toFixed(1)} FTE in 2026-27, ${(100 * me.per).toFixed(1)} per 100 students) serve its students; they would need to follow them to ${to.map(r => esc(rpName(r.to_key))).filter((v, i, a) => a.indexOf(v) === i).join(', ') || 'their new schools'}.</p>`;
    } else {
      const inc = (D.flows[base].receivers || []).filter(r => r.to_key === k && (D.detail[sc] || {})[r.from_key]?.closed && byKey[r.from_key]);
      const by = {}; for (const r of inc) by[r.from_key] = (by[r.from_key] || 0) + (r.share ?? 0);
      const parts = Object.entries(by).map(([f, sh]) => { const s0 = ses(f), n = sh * ((D.series.SQ[f] || [])[yr] || 0); return s0 && n ? { f, n, need: n * s0.per, per: s0.per } : null; }).filter(Boolean);
      const me = ses(k);
      if (parts.length) mv = `<p class="rpnote"><b>${esc(LABEL[sc])}: students arriving from closing schools.</b> ${parts.map(p => `About ${Math.round(p.n)} from ${esc(rpName(p.f))}, where special education and ESL / ELD staff are ${(100 * p.per).toFixed(1)} FTE per 100 students: about <b>${p.need.toFixed(1)} FTE</b>`).join('; ')}. In all, about <b>${parts.reduce((a, p) => a + p.need, 0).toFixed(1)} FTE</b> of centrally allocated special education and ESL / ELD support may need to follow them (${esc(rpName(k))} has ${me ? `${me.f.toFixed(1)} FTE, ${(100 * me.per).toFixed(1)} per 100 students` : 'no figure'}). Estimated at each sending school's 2026-27 rate per student, ${D.impl_year} students; actual needs depend on the students who move.</p>`;
    }
  }
  return top + tbl + mv + `<p class="muted rpnote">Source: PPS 2026-27 Proposed Budget, Volume 2, individual school reports (2023-24 to 2025-26 actual, 2026-27 budget; 1.00 FTE = 40 hours a week for one position). This page's formula covers the base positions the General Fund staffing formula funds (homerooms, specialists, counselors, administrators, office, 6-12 teachers); equity, Title I, SIA / Measure 98 and grant positions, and the centrally allocated special education, ESL / ELD, custodial and nutrition staff, come on top. Allocation rules: 2026-27 Adopted Budget, Volume 1, pp. 232-238.</p>`;
}
function renderReport() {'''

if 'rpBeyond' not in html:
    rep("function renderReport() {", JS)
    rep("""    `<div class="rppanel rpwide"><h3>Staffing changes, ${rpYear}: Status Quo and scenarios</h3>${rpStaff(k, sc)}</div>` +""",
        """    `<div class="rppanel rpwide"><h3>Staffing changes, ${rpYear}: Status Quo and scenarios</h3>${rpStaff(k, sc)}</div>` +
    `<div class="rppanel rpwide"><h3>Beyond the formula: actual staffing in the budget</h3>${rpBeyond(k, sc)}</div>` +""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
