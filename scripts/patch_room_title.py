"""Room to grow section renamed for what it now shows (births, capture and fertility needed, steady-state school sizes,
thresholds, capacity): "Demographic factors impacting sustainability". Heading and the summary card's link tooltip. Once."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'Demographic factors impacting sustainability' not in html:
    rep("<h2>Room to grow: capacity after the scenarios</h2>", "<h2>Demographic factors impacting sustainability</h2>")
    rep("'Show capacity after the scenarios (Room to grow)'", "'Show demographic factors impacting sustainability'")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
