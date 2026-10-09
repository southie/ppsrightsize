"""Stable table layout across scenarios: the region table, getting to school, staffing and class-size tables, their
summary lines, the bus cost block, the enrollment charts (subtitle and over-capacity list) and the summary cards are
rendered once for each scenario (Status Quo, A, B, and Custom when one is built),
and each row gets the tallest height, each column the widest width, and each card and summary the tallest height seen,
so switching scenarios changes values without moving rows. Measured again on every render (window width, expanded
regions and the selected year all change the layout), except that a scenario switch reuses the last measurement, so
the map and tables are drawn once per switch. The map's description and legend are kept steady the same way. Code
added once.
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

if 'function stableLayout' not in html:
    rep("const byKey = Object.fromEntries(D.schools.map(s => [s.key, s]));\n", r"""const byKey = Object.fromEntries(D.schools.map(s => [s.key, s]));

// ---------- stable layout across scenarios ----------
// Renders a table once per scenario and keeps each row's tallest height, each column's widest width and each listed
// block's tallest height, so switching scenarios changes values without moving rows.
const STABLE_SCENS = () => ['SQ', 'A', 'B', ...(D.detail.C ? ['C'] : [])];
const rowKeys = host => { const seen = {};
  return [...host.querySelectorAll('tbody tr')].map(tr => {
    const k = (tr.querySelector('.nm, .xbtn')?.textContent || tr.cells[0]?.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60);
    seen[k] = (seen[k] || 0) + 1; return [k + '#' + seen[k], tr];
  }); };
// a scenario switch reuses the last measurement (set by the scenario buttons); anything else measures again
let STABLE_REUSE = false;
const STABLE_CACHE = {};
function stableLayout(fn, hostId, extra = [], items = null) {
  let busy = false;
  return function (...args) {
    if (busy) return fn.apply(this, args);
    const host = document.getElementById(hostId);
    if (!host || !host.getBoundingClientRect || typeof window.matchMedia !== 'function') return fn.apply(this, args);
    const blocks = () => [...(items ? host.querySelectorAll(items) : []), ...extra.map(id => document.getElementById(id)).filter(Boolean)];
    const apply = ({ H, W, X }) => {
      [...(host.querySelector('thead tr')?.cells || [])].forEach((th, i) => { if (W[i]) th.style.minWidth = W[i] + 'px'; });
      for (const [k, tr] of rowKeys(host)) if (H[k]) tr.style.height = H[k] + 'px';
      blocks().forEach((b, i) => { if (X[i]) b.style.minHeight = X[i] + 'px'; });
    };
    const scens = STABLE_SCENS().join(), c = STABLE_CACHE[hostId];
    if (STABLE_REUSE && c && c.scens === scens && c.width === innerWidth) {
      const r = fn.apply(this, args); apply(c);
      // still valid only if no row or block outgrew its kept size (fonts loading late, for example)
      if (rowKeys(host).every(([k, tr]) => !c.H[k] || tr.getBoundingClientRect().height <= c.H[k] + 0.5) &&
          blocks().every((b, i) => !c.X[i] || b.getBoundingClientRect().height <= c.X[i] + 0.5)) return r;
    }
    busy = true;
    const keep = scen, H = {}, W = [], X = {};
    try {
      for (const pass of host.querySelector('table') ? ['w', 'h'] : ['h']) for (const sc of STABLE_SCENS()) {
        scen = sc; fn.apply(this, args);
        const ths = host.querySelector('thead tr')?.cells || [];
        if (pass === 'w') { [...ths].forEach((th, i) => { th.style.minWidth = ''; W[i] = Math.max(W[i] || 0, th.getBoundingClientRect().width); }); continue; }
        [...ths].forEach((th, i) => { if (W[i]) th.style.minWidth = W[i] + 'px'; });
        for (const [k, tr] of rowKeys(host)) H[k] = Math.max(H[k] || 0, tr.getBoundingClientRect().height);
        blocks().forEach((b, i) => { b.style.minHeight = ''; X[i] = Math.max(X[i] || 0, b.getBoundingClientRect().height); });
      }
    } finally { scen = keep; busy = false; }
    const r = fn.apply(this, args);
    apply(STABLE_CACHE[hostId] = { H, W, X, scens, width: innerWidth });
    return r;
  };
}
renderEndpoints = stableLayout(renderEndpoints, 'endpoints');
renderCommute = stableLayout(renderCommute, 'commute', ['commutesum', 'buscost']);
renderStaffing = stableLayout(renderStaffing, 'staffing', ['staffsum']);
renderClassSizes = stableLayout(renderClassSizes, 'classsize');
renderKPIs = stableLayout(renderKPIs, 'kpis', ['desc'], '.kpi');
renderLines = stableLayout(renderLines, 'panels', ['linesub', 'overwrap', 'panels']);
// the map's description and legend (drawn for every scenario only when something other than the scenario changes)
renderMap = stableLayout(renderMap, 'legend', ['mapsub', 'legend']);
""")
    # blocks given a kept height must contain their children's margins, or the last margin spills past them
    rep(".seg button[aria-pressed=\"true\"] { background: #1c3557; color: #fff; }",
        ".seg button[aria-pressed=\"true\"] { background: #1c3557; color: #fff; }\n#buscost, #overwrap { display: flow-root; }")
    # measure again once web fonts have loaded (text widths change)
    rep("\nrenderAll();\n", "\nrenderAll();\ndocument.fonts?.ready?.then(() => renderAll());\n")
    rep("if (scen === 'C') buildCustom(); renderAll(); });",
        "if (scen === 'C') buildCustom(); STABLE_REUSE = true; try { renderAll(); } finally { STABLE_REUSE = false; } });")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
