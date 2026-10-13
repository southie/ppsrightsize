"""General Fund cost per student by school: the group average for the scenario and year chosen. The 2026-27 group
average (dashed) stayed the same whatever the scenario or year; with a scenario or later year picked, each group also
gets its average in that year under that scenario (dotted line; heading and legend): the schools still open, their
projected General Fund staffing (the lower bars') over their projected enrollment, enrollment-weighted. Code added once.
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

if 'avg1' not in html:
    rep("""    const fitOK = b > 0, a = my - b * mx, target = fitOK ? a + b / thr : avg;
    return { t, lab, g, avg, thr, target, a, b, fitOK };""",
        """    const fitOK = b > 0, a = my - b * mx, target = fitOK ? a + b / thr : avg;
    // the group's average in the chosen year under the scenario (open schools, lower bars' estimate; scripts/patch_gf_group_avg.py)
    const g1 = g.filter(r => r.c1 != null && !r.closed), e1 = g1.reduce((a, r) => a + r.e1, 0);
    const avg1 = (scen !== 'SQ' || gfYear !== '2026-27') && e1 ? g1.reduce((a, r) => a + r.gf1, 0) / e1 : null;
    return { t, lab, g, avg, avg1, n1: g1.length, thr, target, a, b, fitOK };""")
    rep("""...(SUB ? [] : [G.avg - Z, G.target - Z])])];""",
        """...(SUB ? [] : [G.avg - Z, G.target - Z, ...(G.avg1 != null ? [G.avg1 - Z] : [])])])];""")
    rep("""per student at the ${G.thr}-student threshold &middot; group average ${usd(G.avg)}</tspan></text>`)""",
        """per student at the ${G.thr}-student threshold &middot; group average ${usd(G.avg)} (2026-27)${G.avg1 != null ? `; <tspan font-weight="700" fill="var(--text-primary)">${usd(G.avg1)}</tspan> in ${gfYear} under ${esc(scen === 'SQ' ? 'Status Quo' : LABEL[scen])} (est.)` : ''}</tspan></text>`)""")
    rep("""stroke="var(--text-primary)" stroke-width="1.6" stroke-dasharray="6 4"><title>${esc(`${G.lab} average: ${usd(G.avg)} per student (enrollment-weighted), ${G.avg >= G.target ? usd(G.avg - G.target) + ' above' : usd(G.target - G.avg) + ' below'} the target`)}</title></line>`;""",
        """stroke="var(--text-primary)" stroke-width="1.6" stroke-dasharray="6 4"><title>${esc(`${G.lab} average: ${usd(G.avg)} per student (enrollment-weighted), ${G.avg >= G.target ? usd(G.avg - G.target) + ' above' : usd(G.target - G.avg) + ' below'} the target`)}</title></line>` +
      (G.avg1 != null ? `<line x1="${x(G.avg1 - Z)}" x2="${x(G.avg1 - Z)}" y1="${top - 2}" y2="${bot + 2}" stroke="#c2410c" stroke-width="2" stroke-dasharray="2 3"><title>${esc(`${G.lab} average, ${scen === 'SQ' ? 'Status Quo' : LABEL[scen]} ${gfYear} (est.): ${usd(G.avg1)} per student (enrollment-weighted over the ${G.n1} schools still open; the lower bars' General Fund staffing over projected enrollment), ${G.avg1 <= G.avg ? usd(G.avg - G.avg1) + ' less' : usd(G.avg1 - G.avg) + ' more'} than in 2026-27; ${G.avg1 >= G.target ? usd(G.avg1 - G.target) + ' above' : usd(G.target - G.avg1) + ' below'} the target`)}</title></line>` : '');""")
    rep("""<span><i class="k" style="border-top:2px dashed var(--text-primary);width:18px"></i>group average</span>`) +""",
        """<span><i class="k" style="border-top:2px dashed var(--text-primary);width:18px"></i>group average${SC ? ', 2026-27' : ''}</span>${SC ? `<span><i class="k" style="border-top:2px dotted #c2410c;width:18px"></i>group average, ${esc(scen === 'SQ' ? 'Status Quo' : LABEL[scen])} ${gfYear} (est.)</span>` : ''}`) +""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
