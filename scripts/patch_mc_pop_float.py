"""Enrollment uncertainty section, school pop-up: a floating, movable panel instead of a modal overlay. Drag it by its
title bar (mouse or touch); the rest of the page stays usable, and changing the section's settings (year, uncertainty
option, capture range) or the page's scenario redraws the open school's chart in place, at the same position. Close
with the x or Escape. Code changed once.
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

if 'mcPopK' not in html:
    rep("""function mcSchoolFan(k, sc) {
  document.getElementById('mcpop')?.remove();""",
        """// floating, movable panel (scripts/patch_mc_pop_float.py); redrawn in place when the settings change
let mcPopK = null, mcPopPos = null, mcPopEsc = null;
function mcSchoolFan(k, sc, refresh) {
  const old = document.getElementById('mcpop');
  if (old) { const r = old.getBoundingClientRect?.(); if (r && r.width) mcPopPos = [r.left, r.top]; old.remove(); }
  mcPopK = k;""")
    rep("""pop.setAttribute('aria-modal', 'true');""", """pop.setAttribute('aria-modal', 'false');""")
    rep("""  pop.style.cssText = 'position:fixed;inset:0;z-index:3000;background:rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;padding:16px';""",
        """  const pw = Math.min(760, innerWidth * 0.96), [pl, pt] = mcPopPos || [Math.max(8, (innerWidth - pw) / 2), 40];
  pop.style.cssText = `position:fixed;z-index:3000;width:${pw}px;left:${Math.min(Math.max(0, pl), Math.max(0, innerWidth - 80))}px;top:${Math.min(Math.max(0, pt), Math.max(0, (window.innerHeight || 800) - 60))}px`;""")
    rep("""box-shadow:0 10px 40px rgba(0,0,0,.3);max-width:760px;width:100%;max-height:92vh;overflow:auto;padding:14px 16px">`""",
        """box-shadow:0 10px 40px rgba(0,0,0,.3);border:1px solid var(--line);width:100%;max-height:86vh;overflow:auto;padding:14px 16px">`""")
    rep("""`<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px"><h3 style="margin:0;font-size:16px">${esc(nm)}: projected students, ${esc(lab)}</h3>""",
        """`<div id="mcpop-h" title="Drag to move" style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;cursor:move;touch-action:none;user-select:none"><h3 style="margin:0;font-size:16px">${esc(nm)}: projected students, ${esc(lab)} <span class="muted" style="font-size:11px;font-weight:400">drag to move &middot; updates with the settings</span></h3>""")
    rep("""  document.body.appendChild(pop);
  const close = () => { pop.remove(); document.removeEventListener('keydown', esc_); };
  const esc_ = e => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', esc_);
  pop.onclick = e => { if (e.target === pop) close(); };
  document.getElementById('mcpop-x').onclick = close; document.getElementById('mcpop-x').focus();""",
        """  document.body.appendChild(pop);
  if (mcPopEsc) document.removeEventListener('keydown', mcPopEsc);
  const close = () => { pop.remove(); mcPopK = null; if (mcPopEsc) document.removeEventListener('keydown', mcPopEsc); mcPopEsc = null; };
  mcPopEsc = e => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', mcPopEsc);
  const xb = document.getElementById('mcpop-x'); xb.onclick = close; if (!refresh) xb.focus?.();
  const hd = document.getElementById('mcpop-h');   // drag by the title bar
  if (hd) hd.onpointerdown = e => {
    if (e.target.closest?.('button')) return;
    const r = pop.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top; hd.setPointerCapture?.(e.pointerId);
    hd.onpointermove = ev => { const l = Math.min(Math.max(0, ev.clientX - dx), innerWidth - 80), t = Math.min(Math.max(0, ev.clientY - dy), innerHeight - 40);
      pop.style.left = l + 'px'; pop.style.top = t + 'px'; mcPopPos = [l, t]; };
    hd.onpointerup = hd.onpointercancel = () => { hd.onpointermove = null; hd.onpointerup = null; hd.onpointercancel = null; };
  };""")
    rep("""renderMCFan(w); renderMCRanges(w, sc); renderMCDrivers(sc); renderMCSchools(w, sc); renderMCMethod();""",
        """renderMCFan(w); renderMCRanges(w, sc); renderMCDrivers(sc); renderMCSchools(w, sc); renderMCMethod();
  if (mcPopK && typeof document.querySelector === 'function' && document.querySelector('#mcpop')) mcSchoolFan(mcPopK, sc, true);   // keep the open school chart in step""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
