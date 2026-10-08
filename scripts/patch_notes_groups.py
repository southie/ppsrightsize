"""Group the 'Method and assumptions' notes under subheadings, add a staffing note,
and point the pps-explorer reference link at the live site."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'const NOTE_GROUPS' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# container: grouped lists instead of one <ul>
rep('<ul class="notes" id="notes"></ul>', '<div id="notes" class="notegroups"></div>')

# the notes array becomes data; render it in groups
start = html.index("document.getElementById('notes').innerHTML = [")
end_marker = "].map(t => `<li>${esc(t)}</li>`).join('');"
end = html.index(end_marker, start)
body = html[start + len("document.getElementById('notes').innerHTML = ["):end]
staffing_note = ("  'Staffing: PPS\\'s 2026-27 school staffing formula (Proposed Budget Vol. 1, pp. 206-210) applied to every school\\'s projected enrollment under the scenario and under Status Quo in the same year; the difference is positions the formula no longer funds. "
                 "K-5 homerooms are counted grade by grade from each school\\'s 2025-26 grade mix (ODE fall membership) against the class-size maximums (default: budget targets, grade 1 at 31, Title I schools 30; editable). "
                 "Middle and high school teachers follow the formula\\'s ratios (23.5 and 25 students per FTE). Costs are 2026-27 General Fund salary per budgeted FTE by employee type plus payroll costs (p. 100): about $' + Math.round(D.staff.costs.licensed / 1000) + 'k per licensed FTE, $' + Math.round(D.staff.costs.administrator / 1000) + 'k per principal or assistant/vice principal and $' + Math.round(D.staff.costs.classified / 1000) + 'k per administrative assistant. "
                 "Equity, Title I, special education, multilingual, Measure 98 and grant-funded positions are excluded. Checked against PPS\\'s October 6 slide 7 (10 schools, within 0.5 FTE on average).',\n")
new = ("const NOTES = [" + body + staffing_note + "];\n"
"""const NOTE_GROUPS = [
  ['Enrollment, regions and published measures', ['Published measures', 'Status Quo enrollment', 'Scenario enrollment', 'Region assignment', 'Student-group']],
  ['Map, boundaries and travel time', ['Map:', 'Attendance boundaries', 'Residents within', 'Travel time']],
  ['Buildings, costs and land', ['Functional capacity', 'Building costs', 'Building operating cost', 'Land value']],
  ['Staffing', ['Staffing']],
  ['Private schools', ['Private schools']],
  ['Custom scenarios', ['Custom scenario:', 'Custom scenario, keeping']],
];
(function renderNotes() {
  const groups = NOTE_GROUPS.map(([title, prefixes]) => ({ title, prefixes, items: [] }));
  for (const t of NOTES) {
    const g = groups.find(g => g.prefixes.some(p => t.startsWith(p))) || groups[0];   // model assumptions join the enrollment group
    g.items.push(t);
  }
  // within a group, follow the order of its prefixes, keeping unmatched notes (model assumptions) after the matched ones
  const rank = (g, t) => { const i = g.prefixes.findIndex(p => t.startsWith(p)); return i < 0 ? g.prefixes.length : i; };
  document.getElementById('notes').innerHTML = groups.filter(g => g.items.length).map(g =>
    `<h3>${esc(g.title)}</h3><ul class="notes">${g.items.map((t, i) => [t, i]).sort((a, b) => rank(g, a[0]) - rank(g, b[0]) || a[1] - b[1]).map(([t]) => `<li>${esc(t)}</li>`).join('')}</ul>`).join('');
})();""")
html = html[:start] + new + html[end + len(end_marker):]

# styles
rep('ul.notes { color: var(--text-secondary); font-size: 13px; padding-left: 20px; }',
    'ul.notes { color: var(--text-secondary); font-size: 13px; padding-left: 20px; }\n'
    '.notegroups h3 { font-size: 14px; margin: 18px 0 4px; color: var(--text-primary); }\n'
    '.notegroups h3:first-child { margin-top: 4px; }\n'
    '.notegroups ul.notes { margin: 0 0 6px; } .notegroups ul.notes li { margin-bottom: 5px; }')

# reference link: live pps-explorer site
rep('<a href="https://github.com/browniefed/pps-explorer" target="_blank" rel="noopener">pps-explorer</a> (school map from PPS boundary files)',
    '<a href="https://pps-explorer.codedaily.workers.dev/" target="_blank" rel="noopener">pps-explorer</a> (attendance-boundary explorer)')
open(PAGE, 'w', encoding='utf-8').write(html)
print('patched')
