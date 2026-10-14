"""The "Modified enrollment model" switch is off by default (PPS's own enrollment model); on when the browser remembers
it on (rsAdj = '1') or a link says adj=1. Links carry adj=1 when it is on. The population summary (D.pfaImpact, from
scripts/build_pfa_impact.js) is computed with the modified model off to match. Code changed once.
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

if 'adj-default-off' not in html:
    rep("var MODEL_ON = true;\ntry { MODEL_ON = localStorage.getItem('rsAdj') !== '0'; } catch (e) {}",
        "var MODEL_ON = false;   // adj-default-off: the modified enrollment model is off unless turned on\ntry { MODEL_ON = localStorage.getItem('rsAdj') === '1'; } catch (e) {}")
    rep("let adjOn = true;\ntry { adjOn = localStorage.getItem('rsAdj') !== '0'; } catch (e) {}",
        "let adjOn = false;\ntry { adjOn = localStorage.getItem('rsAdj') === '1'; } catch (e) {}")
    rep("  if (!adjOn) p.set('adj', '0');", "  if (adjOn) p.set('adj', '1');")
    rep("  if (q.get('adj') === '0' && adjOn) { applyAdjust(false); const b = document.getElementById('adjtog'); if (b) b.checked = false; }",
        "  if (q.has('adj') && (q.get('adj') === '1') !== adjOn) { applyAdjust(q.get('adj') === '1'); const b = document.getElementById('adjtog'); if (b) b.checked = adjOn; }")
    rep("Figures below compare the two, with the modified enrollment model on.</p>`",
        "Figures below compare the two, with the modified enrollment model off (the default).</p>`")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
