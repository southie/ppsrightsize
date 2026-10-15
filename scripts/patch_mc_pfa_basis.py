"""Enrollment uncertainty section, centered on the page's default projection (D.mc.basis = 'pfa': PSU's May 2026
forecast with kindergarten from the district share of PSU's August 2026 county population projections, PFA study):
  - the introduction says what the simulations are centered on; a note appears only when the page's switch shows a
    different basis from the simulations';
  - cards say "Baseline projection" for the value without uncertainty;
  - the district fan chart draws the updated projection as the main line, with PSU's medium (dotted) and low / high
    (dashed) for comparison;
  - the threshold population's students at schools not on the page use the updated district totals.
Needs D.mc.basis (patch_mc_section.py). Code changed once.
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

if 'mc-pfa-basis' not in html:
    rep("""`The figures elsewhere on this page use Portland State University's medium enrollment forecast. This section simulates ${D.mc.n.toLocaleString()} other plausible futures, varying the two things that drive PSU's forecast:""",
        """`${D.mc.basis === 'pfa' ? 'This section is centered on the page\\u2019s default projection: Portland State University\\u2019s May 2026 PPS forecast, with kindergarten from the district share of PSU\\u2019s August 2026 county population projections (PFA study).' : 'This section is centered on Portland State University\\u2019s May 2026 PPS forecast.'} It simulates ${D.mc.n.toLocaleString()} other plausible futures, varying the two things that drive the projection:""")   # mc-pfa-basis
    rep("""most likely PSU's ${tri.m.toFixed(3)}, measured against births five years earlier)""",
        """most likely the projection's ${tri.m.toFixed(3)}, measured against births five years earlier)""")
    rep("""${pfaOn ? ' <b>District share of county population (PFA study) is on:</b> the summary cards, district chart and ranges stay on the simulations around PSU’s forecast; the school table and school charts are centered on this page’s figures with the switch applied.' : ''}`;""",
        """${(D.mc.basis === 'pfa') !== pfaOn ? ` <b>Note:</b> the page is showing ${pfaOn ? 'the district share of county population (PFA study)' : 'PSU\\u2019s May 2026 forecast'}, but these simulations are centered on ${D.mc.basis === 'pfa' ? 'the district share of county population (PFA study)' : 'PSU\\u2019s forecast'}: the cards, district chart and ranges show the simulations\\u2019 baseline; the school table and school charts follow the page.` : ''}`;""")
    rep("""<div class="s">Page value (PSU medium forecast): <b>""", """<div class="s">${D.mc.basis === 'pfa' ? 'Baseline projection' : 'Page value (PSU medium forecast)'}: <b>""")
    rep("""and the page's value (PSU medium forecast); click a range""", """and the page's value; click a range""")
    # fan chart: updated projection as the main line
    rep("""  for (const [sname, dash, wdt] of [['medium', '', 2], ['low', '5 4', 1.3], ['high', '5 4', 1.3]]) {""",
        """  const UPD = D.mc.basis === 'pfa';
  if (UPD) s += `<polyline points="${F.map((f, j) => `${x(f)},${y(val(D.mc.medium_bands[j]))}`).join(' ')}" fill="none" stroke="var(--text-primary)" stroke-width="2.2"><title>Updated projection: district share of county population (PFA study)</title></polyline>`;
  for (const [sname, dash, wdt] of [['medium', UPD ? '2 3' : '', UPD ? 1.4 : 2], ['low', '5 4', 1.3], ['high', '5 4', 1.3]]) {""")
    rep("""<span><i class="k" style="border-top:2px solid var(--text-primary);width:18px;opacity:.8"></i>PSU medium</span>""",
        """${D.mc.basis === 'pfa' ? '<span><i class="k" style="border-top:2.2px solid var(--text-primary);width:18px"></i>updated projection (district share, PFA study)</span><span><i class="k" style="border-top:1.6px dotted var(--text-primary);width:18px;opacity:.8"></i>PSU medium (May 2026)</span>' : '<span><i class="k" style="border-top:2px solid var(--text-primary);width:18px;opacity:.8"></i>PSU medium</span>'}""")
    # threshold population: students not on the page from the updated district totals
    rep("""(D.mc.psu.medium[nameOf[p]][pi] - pageSQ[p])""",
        """((D.mc.medium_bands ? D.mc.medium_bands[fall - 2025][{ k5: 1, m68: 2, h912: 3 }[p]] : D.mc.psu.medium[nameOf[p]][pi]) - pageSQ[p])""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
