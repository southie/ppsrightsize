"""Main map: the zoom buttons move to the top-right corner, so the school details panel (fixed at the top left of the
window) no longer covers them. Code added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
a = "const map = L.map('map', { scrollWheelZoom: false }).setView([45.535, -122.65], 12);"
if 'map.zoomControl.setPosition' not in html:
    assert html.count(a) == 1
    html = html.replace(a, a + "\nmap.zoomControl.setPosition('topright');   // the details panel sits at the top left (scripts/patch_map_zoom.py)")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
