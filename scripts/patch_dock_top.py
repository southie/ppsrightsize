"""School details panel (the map popup on the left): placed below the sticky scenario bar, so the scenario toggle stays
visible and clickable. The panel's top follows the bar's height (it wraps on narrow screens) when it opens and on
resize. Code added once.
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

if 'function placeDock' not in html:
    rep(".dock { position: fixed; left: 16px; top: 16px; width: 360px; max-height: calc(100vh - 32px);",
        ".dock { position: fixed; left: 16px; top: var(--dock-top, 84px); width: 360px; max-height: calc(100vh - var(--dock-top, 84px) - 16px);")
    rep("""function openDock(fn, at, key) {""", """// keep the panel below the sticky scenario bar (scripts/patch_dock_top.py)
function placeDock() {
  const bar = document.querySelector('.bar'), d = document.getElementById('dock'); if (!bar || !d) return;
  d.style.setProperty('--dock-top', Math.max(16, Math.round(bar.getBoundingClientRect().bottom) + 10) + 'px');
}
addEventListener('resize', placeDock);
function openDock(fn, at, key) {
  placeDock();""")
# movable on desktop: drag the grip strip at the top of the panel; double-click it to put the panel back. The position
# holds while the page is open; on touch screens and narrow windows the panel stays where it is.
if 'function dockDrag' not in html:
    rep("""<aside class="dock" id="dock" hidden aria-label="School details"><button class="dock-x\"""",
        """<aside class="dock" id="dock" hidden aria-label="School details"><div class="dock-grip" id="dockgrip" title="Drag to move (double-click to put it back)" aria-hidden="true"></div><button class="dock-x\"""")
    rep("""function placeDock() {
  const bar = document.querySelector('.bar'), d = document.getElementById('dock'); if (!bar || !d) return;""",
        """let dockMoved = false;
function placeDock() {
  const bar = document.querySelector('.bar'), d = document.getElementById('dock'); if (!bar || !d) return;
  if (dockMoved) { dockClamp(d); return; }""")
    rep("""addEventListener('resize', placeDock);""", """addEventListener('resize', placeDock);
// keep a moved panel inside the window
let dockPos = null;   // where the panel was dragged to
function dockClamp(d) {
  if (!dockPos) return;
  const L0 = Math.min(Math.max(0, dockPos.l), innerWidth - 80), T0 = Math.min(Math.max(0, dockPos.t), innerHeight - 60);
  d.style.left = L0 + 'px'; d.style.top = T0 + 'px'; d.style.maxHeight = `calc(100vh - ${Math.round(T0) + 16}px)`;
}
(function dockDrag() {
  if (typeof document.getElementById !== 'function' || typeof matchMedia !== 'function') return;
  const g = document.getElementById('dockgrip'), d = document.getElementById('dock'); if (!g || !d || !g.addEventListener) return;
  let sx = 0, sy = 0, ox = 0, oy = 0, on = false;
  g.addEventListener('pointerdown', e => {
    if (!matchMedia('(pointer: fine) and (min-width: 700px)').matches || e.button !== 0) return;
    const r = d.getBoundingClientRect(); on = true; sx = e.clientX; sy = e.clientY; ox = r.left; oy = r.top;
    g.setPointerCapture(e.pointerId); d.classList.add('dragging'); e.preventDefault();
  });
  g.addEventListener('pointermove', e => {
    if (!on) return;
    const L0 = Math.min(Math.max(0, ox + e.clientX - sx), innerWidth - 80), T0 = Math.min(Math.max(0, oy + e.clientY - sy), innerHeight - 60);
    d.style.left = L0 + 'px'; d.style.top = T0 + 'px'; d.style.maxHeight = `calc(100vh - ${Math.round(T0) + 16}px)`; dockMoved = true; dockPos = { l: L0, t: T0 };
  });
  const end = e => { if (!on) return; on = false; d.classList.remove('dragging'); try { g.releasePointerCapture(e.pointerId); } catch (x) {} };
  g.addEventListener('pointerup', end); g.addEventListener('pointercancel', end);
  g.addEventListener('dblclick', () => { dockMoved = false; dockPos = null; d.style.left = d.style.top = d.style.maxHeight = ''; placeDock(); });
})();""")
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
.dock-grip { display: none; }
@media (pointer: fine) and (min-width: 700px) {
  .dock-grip { display: block; position: sticky; top: -16px; height: 14px; margin: -16px -16px 4px; cursor: move; border-radius: 12px 12px 0 0;
    background: radial-gradient(circle, var(--text-muted) 1.1px, transparent 1.4px) center / 7px 5px repeat-x, var(--surface-1); background-size: 7px 5px; background-position: center; background-repeat: repeat-x; z-index: 2; opacity: .8; }
  .dock-grip:hover { opacity: 1; background-color: color-mix(in srgb, var(--line) 50%, var(--surface-1)); }
  .dock.dragging { user-select: none; box-shadow: 0 16px 48px rgba(0, 0, 0, .35); }
}""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
