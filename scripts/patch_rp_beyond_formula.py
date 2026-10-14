"""School report, "Beyond the formula" panel: for rows the staffing formula sets, the formula's 2026-27 value (Status Quo)
and the budget's difference from it, in two columns beside the actuals:
  Teachers = K-5 homerooms + PE / music / art + 6-8 and 9-12 teachers (library left out);
  Library / media = K-5 librarian at one per 25 homerooms (0.2 FTE steps), 0.5 in a middle school, a high school's
    librarian (HS_BANDS);
  Counselors and other licensed support = counselors, the K-5 / K-8 discretionary position, high school social worker;
    compared with the budget's counseling and other licensed rows;
  Clerical = office staff counted as people (the formula counts an administrative assistant as half a licensed FTE);
  Administrators = principal and assistant / vice principals;
  School-allocated total and General Fund (base) = the formula's total, office staff as people.
Interventionists, educational assistants and the equity, Title I, SIA / Measure 98 and centrally allocated rows have no
formula level. Runs after patch_rp_beyond. Code changed once.
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

if 'rp-beyond-formula' not in html:
    # the formula's values by budget row (Status Quo, 2026-27) and two more columns
    rep("""  const row = (lab, v, o = {}) => `<tr${o.tot ? ' class="tot"' : ''}><td style="text-align:left${o.ind ? ';padding-left:18px' : ''}"${o.tip ? ` title="${esc(o.tip)}"` : ''}>${lab}</td>${show.map(j => `<td${j === 5 ? ' class="cur"' : ''}>${o.fmt ? o.fmt(v[j]) : f2(v[j])}</td>`).join('')}</tr>`;
  const head = lab => `<tr><td colspan="${show.length + 1}" style="text-align:left;font-weight:600;padding-top:8px">${lab}</td></tr>`;""",
        """  // rp-beyond-formula: the formula's 2026-27 level for the rows it sets
  const fy = D.years.indexOf('2026-27'), FR = (D.series.SQ[k] || [])[fy] != null ? schoolFTE(k, 'SQ', fy) : null;
  const FL = FR ? (() => { const lib = FR.type === 'HS' ? FR.specialists : (FR.homeroom ? ceil02(FR.homeroom / 25) : 0) + (FR.type === 'MS' ? 0.5 : 0);
    return { teachers: FR.homeroom + FR.specialists - lib + FR.t68 + FR.t912, library: lib, support: FR.support, clerical: FR.office * 2, admin: FR.principal + FR.ap, total: FR.total + FR.office }; })() : null;
  const fcell = (key, v) => { if (!FL || FL[key] == null) return '<td></td><td></td>'; const f = FL[key], d = (v[5] || 0) - f;
    return `<td style="border-left:2px solid var(--line)">${f.toFixed(2)}</td><td style="color:${Math.abs(d) < 0.05 ? 'var(--text-muted)' : d > 0 ? 'var(--change)' : 'var(--down)'}">${Math.abs(d) < 0.05 ? '0' : (d > 0 ? '+' : '&minus;') + Math.abs(d).toFixed(2)}</td>`; };
  const row = (lab, v, o = {}) => `<tr${o.tot ? ' class="tot"' : ''}><td style="text-align:left${o.ind ? ';padding-left:18px' : ''}"${o.tip ? ` title="${esc(o.tip)}"` : ''}>${lab}</td>${show.map(j => `<td${j === 5 ? ' class="cur"' : ''}>${o.fmt ? o.fmt(v[j]) : f2(v[j])}</td>`).join('')}${o.f ? fcell(o.f, v) : '<td style="border-left:2px solid var(--line)"></td><td></td>'}</tr>`;
  const head = lab => `<tr><td colspan="${show.length + 3}" style="text-align:left;font-weight:600;padding-top:8px">${lab}</td></tr>`;""")
    rep("""${show.map(j => `<th${j === 5 ? ' class="cur"' : ''}>${Y[j]}<br><span style="font-weight:400">${j === 5 ? 'budget' : 'actual'}</span></th>`).join('')}</tr></thead><tbody>` +""",
        """${show.map(j => `<th${j === 5 ? ' class="cur"' : ''}>${Y[j]}<br><span style="font-weight:400">${j === 5 ? 'budget' : 'actual'}</span></th>`).join('')}<th style="border-left:2px solid var(--line)" title="This page's staffing formula for the school, Status Quo, 2026-27">Formula<br><span style="font-weight:400">2026-27</span></th><th title="The 2026-27 budget less the formula: above it (blue) or below it (red)">Budget &minus;<br><span style="font-weight:400">formula</span></th></tr></thead><tbody>` +""")
    # rows with a formula level (teachers and library split; counselors with other licensed support)
    rep("""    row('Teachers', g('lic_teachers'), { ind: 1 }) + row('Counselors', g('lic_counseling'), { ind: 1 }) + row('Library / media', add('lic_library', 'cls_library'), { ind: 1 }) +""",
        """    row('Teachers', g('lic_teachers'), { ind: 1, f: 'teachers', tip: 'Formula: K-5 homerooms, PE / music / art, and 6-8 and 9-12 teachers' }) +
    row('Library / media', add('lic_library', 'cls_library'), { ind: 1, f: 'library', tip: 'Formula: K-5 librarian at one per 25 homerooms (0.2 FTE steps), 0.5 in a middle school, a high school librarian' }) +
    row('Counselors and other licensed support', add('lic_counseling', 'lic_other'), { ind: 1, f: 'support', tip: 'Budget: counseling services and other licensed positions. Formula: counselors by enrollment, plus the discretionary position (K-5 and K-8) or social worker (high school)' }) +""")
    rep("""row('Educational assistants', g('cls_ea'), { ind: 1, tip: 'Educational assistants and paraeducators (classified)' }) + row('Clerical', g('cls_clerical'), { ind: 1 }) +
    row('Administrators', g('admin'), { ind: 1 }) + row('Other', add('lic_other', 'cls_other'), { ind: 1 }) + row('School-allocated total', g('school_total'), { tot: 1 }) +""",
        """row('Educational assistants', g('cls_ea'), { ind: 1, tip: 'Educational assistants and paraeducators (classified)' }) +
    row('Clerical', g('cls_clerical'), { ind: 1, f: 'clerical', tip: 'Formula office staff counted as people (the formula counts an administrative assistant as half a licensed FTE; high schools include the athletic director and support)' }) +
    row('Administrators', g('admin'), { ind: 1, f: 'admin', tip: 'Formula: principal and assistant / vice principals' }) + row('Other classified', g('cls_other'), { ind: 1 }) +
    row('School-allocated total', g('school_total'), { tot: 1, f: 'total' }) +""")
    rep("""    row('General Fund (base)', add('f_lic_gf', 'f_cls_gf', 'f_adm_gf'), { ind: 1 }) +""",
        """    row('General Fund (base)', add('f_lic_gf', 'f_cls_gf', 'f_adm_gf'), { ind: 1, f: 'total', tip: 'The General Fund staffing the formula sets; compared with the formula total (office staff as people)' }) +""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
