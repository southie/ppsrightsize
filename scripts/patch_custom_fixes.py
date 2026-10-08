"""rightsizing-scenario-explorer.html: fixes for switching between a custom scenario and the published ones.

1. Building a custom scenario adds a District entry to E.closing (closed-school names) for scenario C only.
   Switching back to Status Quo, A or B then read E.closing[scen] (undefined) and threw, which stopped
   renderAll before the endpoints table and the rest of the page were redrawn. Guard on E.closing[scen].
2. Keeping a closed school open took its full Status Quo enrollment back from its receiving schools, even when
   they had gained fewer students than that in the scenario (Sellwood: 350 back from Hosford and Brentwood, which
   gained 299 in Scenario A), pushing a receiver below its own Status Quo. A receiver now gives back at most what
   it gained over Status Quo, and the school gets back what is returned (scripts/custom_fixes_applyReopen.js).
Safe to rerun: each fix is applied once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
html = open(PAGE, encoding='utf-8').read()

def fix(old, new):
    global html
    if new in html: return print('already applied:', new[:70])
    assert html.count(old) == 1, (html.count(old), old[:100])
    html = html.replace(old, new); print('applied:', new[:70])

fix("if (m.key === 'closures' && scen !== 'SQ' && E.closing && !open) cell += `<span class=\"closing\">${esc(E.closing[scen].join(', '))}</span>`;",
    "if (m.key === 'closures' && scen !== 'SQ' && E.closing?.[scen] && !open) cell += `<span class=\"closing\">${esc(E.closing[scen].join(', '))}</span>`;")

new_fn = open(os.path.join(ROOT, 'scripts', 'custom_fixes_applyReopen.js'), encoding='utf-8').read().rstrip() + chr(10)
i = html.index('function applyReopen(st, a) {'); j = html.index('function applyAction(st, a) {', i)
if html[i:j] != new_fn: html = html[:i] + new_fn + html[j:]; print('applied: applyReopen returns at most what receivers gained')
else: print('already applied: applyReopen')
fix("<span>Its Status Quo enrollment returns from ${D.impl_year}, taken back from ${esc(back || 'its receiving schools')}.</span>",
    "<span>From ${D.impl_year} it gets back its Status Quo students from ${esc(back || 'its receiving schools')}, up to what each gained in the scenario.</span>")
fix("It gets back its Status Quo projection from ' + D.impl_year + ', and those students come back out of its receiving schools:",
    "From ' + D.impl_year + ' it gets back its Status Quo students out of its receiving schools, but a receiving school never returns more than it gained over Status Quo in the scenario, so the school can come back below its Status Quo enrollment. Shares:")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)}')
