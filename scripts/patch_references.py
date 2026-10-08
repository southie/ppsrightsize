"""rightsizing-scenario-explorer.html: add related-work links to the page's "Related:" reference row. Safe to rerun."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
ANCHOR = '<a href="https://pps-explorer.codedaily.workers.dev/" target="_blank" rel="noopener">pps-explorer</a> (attendance-boundary explorer)'
LINK = '\n      <a href="https://chrisloer.github.io/pps-closures/" target="_blank" rel="noopener">PPS Closure Commutes</a> (walk, bike and drive time by closure)'
html = open(PAGE, encoding='utf-8').read()
# an earlier version of this script added a separate paragraph; fold it into the Related row instead
start = html.find('<p class="lede related">')
if start != -1:
    end = html.index('</p>', start) + len('</p>')
    html = html[:html.rfind('\n', 0, start)] + html[end:]
html = html.replace('.lede.related { margin-top: -8px; font-size: 13px; }\n', '')
if 'chrisloer.github.io/pps-closures' in html:
    print('already present')
else:
    assert html.count(ANCHOR) == 1, html.count(ANCHOR)
    html = html.replace(ANCHOR, ANCHOR + LINK)
    print('added PPS Closure Commutes to the Related row')
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
