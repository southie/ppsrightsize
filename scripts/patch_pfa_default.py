"""District share of county population (PFA study) on by default; its summary section ("What newer population data
changes") moves down to just before "Private school share of PPS-area students".
  The switch is on unless the browser remembers it off (rsPfa = '0'); links carry pfa=0 when it is off.
  The summary's opening sentence says which basis the page is showing.
Code changed once.
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

if 'pfa-default' not in html:
    rep("""let pfaOn = false;
try { pfaOn = localStorage.getItem('rsPfa') === '1'; } catch (e) {}""",
        """let pfaOn = true;   // pfa-default: on unless turned off
try { pfaOn = localStorage.getItem('rsPfa') !== '0'; } catch (e) {}""")
    rep("""  if (pfaOn) p.set('pfa', '1');""", """  if (!pfaOn) p.set('pfa', '0');""")
    # summary: say which basis the page shows
    rep("""host.innerHTML = `<p class="sub">The page's enrollment follows Portland State University's May 2026 PPS forecast. In August 2026 PSU published""",
        """host.innerHTML = `<p class="sub">${pfaOn ? 'By default this page uses the newer population data below; turn the switch off to see Portland State University\\u2019s May 2026 PPS forecast, which PPS\\u2019s published measures use.' : 'The page is showing Portland State University\\u2019s May 2026 PPS forecast, which PPS\\u2019s published measures use.'} In August 2026 PSU published""")
    rep("""Figures below are with the modified enrollment model on; turn the switch on to see them across the page.</p>`""",
        """Figures below compare the two, with the modified enrollment model on.</p>`""")
    # move the section
    m = re.search(r"  <section class=\"card\" id=\"pfacard\">\n    <h2>What newer population data changes</h2>\n    <div id=\"pfasum\"></div>\n  </section>\n\n", html)
    assert m, 'pfacard'
    block = m.group(0); html = html[:m.start()] + html[m.end():]
    rep("""  <section class="card">
    <h2>Private school share of PPS-area students</h2>""", block + """  <section class="card">
    <h2>Private school share of PPS-area students</h2>""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
