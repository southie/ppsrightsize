"""Hover tooltips (enrollment charts, map boundaries) are cleared when the page or a table box scrolls or the mouse
wheel turns: scrolling moves content under a still mouse, which fires no mouseleave, so the tooltip and the chart's
highlighted line used to stay up. The next mouse move shows them again. Safe to rerun: added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'function clearHovers' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# each enrollment chart exposes its hover reset on its svg
rep("""    hit.addEventListener('mouseleave', () => { if (hot && paths[hot]) paths[hot].setAttribute('stroke-width', 1.6); hot = null; dot.setAttribute('opacity', 0); hideTip(); });""",
    """    const reset = () => { if (hot && paths[hot]) paths[hot].setAttribute('stroke-width', 1.6); hot = null; dot.setAttribute('opacity', 0); hideTip(); };
    hit.addEventListener('mouseleave', reset); svg._hoverReset = reset;""")
# clear on scroll (capture: also table boxes and the side pane) and wheel
rep("const hideTip = () => tip.style.opacity = 0;",
    """const hideTip = () => tip.style.opacity = 0;
// scrolling moves content under a still mouse without a mouseleave: clear the tooltip and any chart highlight
function clearHovers() {
  if (tip.style.opacity === '0') return;
  hideTip();
  document.querySelectorAll('#panels svg').forEach(s => s._hoverReset?.());
  if (typeof setBHover === 'function') setBHover(null);
}
addEventListener('scroll', clearHovers, { capture: true, passive: true });
addEventListener('wheel', clearHovers, { passive: true });""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
