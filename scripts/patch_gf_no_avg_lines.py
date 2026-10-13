"""General Fund cost per student by school: no group-average lines (they cluttered the chart). The 2026-27 group average
(dashed) and the scenario-year group average (dotted) are no longer drawn or in the legend, and no longer widen the
axis; their values stay in each group's heading. Runs after patch_gf_group_avg and patch_threshold_both. Code removed once.
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

def cut(pattern):   # remove one regex match
    global html
    m = re.findall(pattern, html, re.S); assert len(m) == 1, (len(m), pattern[:80])
    html = re.sub(pattern, '', html, count=1, flags=re.S)

if 'gf-no-avg-lines' not in html:
    rep("""...(SUB ? [] : [G.avg - Z, G.target - Z, ...(G.avg1 != null ? [G.avg1 - Z] : []), ...(G.form != null ? [G.form - Z] : [])])])];""",
        """...(SUB ? [] : [G.target - Z, ...(G.form != null ? [G.form - Z] : [])])])];   // gf-no-avg-lines: group averages are in the headings only""")
    # the 2026-27 group-average line (keeps the + joining the target line to the formula line)
    cut(r"`<line x1=\"\$\{x\(G\.avg - Z\)\}\".*?</title></line>` \+\n      ")
    # the scenario-year group-average line
    cut(r" \+\n      \(G\.avg1 != null \? `<line x1=\"\$\{x\(G\.avg1 - Z\)\}\".*?</title></line>` : ''\)")
    # legend entries
    rep("""<span><i class="k" style="border-top:2px dashed var(--text-primary);width:18px"></i>group average${SC ? ', 2026-27' : ''}</span>""", '')
    rep("""${SC ? `<span><i class="k" style="border-top:2px dotted #c2410c;width:18px"></i>group average, ${esc(scen === 'SQ' ? 'Status Quo' : LABEL[scen])} ${gfYear} (est.)</span>` : ''}""", '')
    rep("""<b>Group average</b> (dashed) is enrollment-weighted.""", """<b>Group average</b> (in each heading) is enrollment-weighted.""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
