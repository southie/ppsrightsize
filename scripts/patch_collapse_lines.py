"""Projected enrollment by school: the charts (with their region filter, school search and legend) sit in a section
that is collapsed by default ("Enrollment charts by school type"); the heading, subtitle and over-capacity list stay
visible. The charts are redrawn when the section is opened. Code added once.
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

if 'id="lineswrap"' not in html:
    rep("""    <div class="controls">
      <label>Region <select id="region"></select></label>
      <label>Find a school <input type="search" id="find" placeholder="e.g. Ockley Green" list="schoollist"></label>
      <datalist id="schoollist"></datalist>
    </div>
    <div class="legend" id="legend2" style="margin:0 0 10px"></div>
    <div class="panels" id="panels"></div>""", """    <details id="lineswrap" class="lineswrap"><summary>Enrollment charts by school type</summary>
    <div class="controls">
      <label>Region <select id="region"></select></label>
      <label>Find a school <input type="search" id="find" placeholder="e.g. Ockley Green" list="schoollist"></label>
      <datalist id="schoollist"></datalist>
    </div>
    <div class="legend" id="legend2" style="margin:0 0 10px"></div>
    <div class="panels" id="panels"></div>
    </details>""")
    rep(".tablewrap { overflow-x: auto; }", ".tablewrap { overflow-x: auto; }\n.lineswrap { margin: 4px 0 14px; } .lineswrap > summary { cursor: pointer; font-weight: 600; font-size: 15px; padding: 6px 0; }")
    rep("function renderAll() {", "document.getElementById('lineswrap')?.addEventListener('toggle', e => { if (e.target.open) renderLines(); });\nfunction renderAll() {")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
