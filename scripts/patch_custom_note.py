"""Custom scenario panel: a note on how each section below handles a custom scenario and where its results are weaker
(this page's model instead of PPS's figures; the starting scenario's attendance areas; students kept open in a
school the starting scenario closes; no attrition). Shown while viewing the custom scenario. Safe to rerun: added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function customNote' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

rep("function renderCustomPanel() {", r"""// how the sections below handle a custom scenario, and where the results are weaker
function customNote() {
  const b = LABEL[custom.base], fromAB = custom.base !== 'SQ';
  const keptOpen = custom.actions.some(a => a.reopen), closed = custom.actions.some(a => !a.reopen);
  const li = (title, body, weak) => `<li><b>${title}</b> ${body}${weak ? ` <span class="cpweak"><b>Weaker:</b> ${weak}</span>` : ''}</li>`;
  return `<details class="cpnote" open><summary>How the sections below handle a custom scenario, and where the results are weaker</summary><ul>` +
    li('Map.', `Your closures and the schools receiving their students are drawn from your changes.`,
      `the attendance boundaries shown are ${b}'s; closing a school does not redraw them.`) +
    li('Scenario impact by region.', `Building costs, operating costs, land value and staffing follow your closures directly.`,
      `PPS has not published measures for your scenario, so schools and students above the size thresholds are recomputed with this page's enrollment model and compared with Status Quo computed the same way. For PPS's own scenarios this model can differ from PPS's published figures by a few points (see "recreated values"). "Students who would change schools" is a district estimate (${b}'s share plus the students your closures move); regions are not reported.`) +
    li('Getting to school (and the yellow-bus cost).', `Uses your scenario's enrollment with ${b}'s attendance areas.`,
      `${closed ? 'students moved by a closure are counted at their new school as if they lived where that school\'s existing neighborhood students live. Most live farther away, so beyond-bus-distance counts, travel times and the added yellow-bus cost are probably understated for your closures.' : 'closures you add would be counted at their new school as if the students lived where that school\'s existing neighborhood students live, which understates distances and bus cost.'}` +
      (fromAB ? ` A school you keep open that ${b} closes has no attendance area in ${b}, so its students appear as a program school and are left out of the distance and bus figures${keptOpen ? ' (this applies to your scenario)' : ''}.` : '')) +
    li('Staffing impact.', `Recomputed for every school from its new enrollment with PPS's staffing formula.`,
      `K-5 homerooms assume the receiving school's 2025-26 grade mix, and positions follow the formula only (not any transition staffing).`) +
    li('Enrollment by school and over capacity.', `A closed school's students move in full from 2027-28, split by the shares you set, and follow each year's projection.`,
      `no students are assumed to leave PPS for private, charter or other districts, so receiving schools' enrollment and over-capacity years are an upper bound.`) +
    li('School panes (private alternatives, traffic drive times).', `Use your closures and receiving schools.`, '') +
    `</ul></details>`;
}
function renderCustomPanel() {""")
rep("""            : `<p class="sub">No changes yet; this currently matches ${LABEL[custom.base]}.</p>`;
  }""", """            : `<p class="sub">No changes yet; this currently matches ${LABEL[custom.base]}.</p>`;
    h += customNote();
  }""")
rep(".dock[hidden] { display: none; }", """.dock[hidden] { display: none; }
.cpnote { margin: 12px 0 0; font-size: 13px; line-height: 1.45; } .cpnote summary { cursor: pointer; font-weight: 600; }
.cpnote ul { margin: 8px 0 0; padding-left: 20px; } .cpnote li { margin: 0 0 6px; } .cpnote .cpweak { color: var(--text-secondary); }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
