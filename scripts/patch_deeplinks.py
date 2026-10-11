"""Links into specific tables with their settings: each table's heading gets a "Link" button that copies a URL with the
scenario, the Census boundary adjustment (when off), that table's dropdowns, filters and expanded regions, and a
t=<table> target; opening the URL restores those settings before the first render and scrolls to the table. A custom
scenario keeps its own #custom=... link. Parameters (regions as indexes into D.region_order, dot-separated):
  scenario, adj=0, t, ex (impact table regions), rec=1, bco (cost table regions), bcc=1 (closed only), cmy / cmb / cmo
  (getting to school year, band, regions), sty / stp / sto (staffing year, contract caps, regions), csy (class sizes
  year), lr / lf (enrollment charts region, search), pcb / pco (private capacity band, regions), school / year (report)
Runs after the table patches (needs their state variables). Code added once.
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

if 'function linkParams' not in html:
    rep("\nrenderAll();\n", r"""
// ---------- links into tables (scripts/patch_deeplinks.py) ----------
const LINK_TABLES = [['report', 'rpfind'], ['endpoints', 'endpoints'], ['trend', 'trend'], ['costcurve', 'costcurve'], ['bldcosts', 'bldcosts'],
  ['commute', 'commute'], ['busmap', 'bmwrap'], ['staffing', 'staffing'], ['lines', 'lineswrap'], ['classsize', 'classsize'], ['privshare', 'privshare'],
  ['privcap', 'privcap'], ['homeschool', 'homeschool'], ['virtual', 'virtual']];
const rIdx = set => [...set].map(r => D.region_order.indexOf(r)).filter(i => i >= 0).join('.');
const rSet = (str, set) => { set.clear(); (str || '').split('.').forEach(i => { const r = D.region_order[+i]; if (r) set.add(r); }); };
function linkParams(key) {
  const p = new URLSearchParams();
  if (scen !== 'C') p.set('scenario', scen);
  if (!adjOn) p.set('adj', '0');
  if (key === 'endpoints') { if (expanded.size) p.set('ex', rIdx(expanded)); if (document.getElementById('showrec')?.checked) p.set('rec', '1'); }
  if (key === 'bldcosts') { if (bcOpen.size) p.set('bco', rIdx(bcOpen)); if (bcClosedOnly) p.set('bcc', '1'); p.set('sty', staffYear); }
  if (key === 'commute') { p.set('cmy', cmYear); p.set('cmb', cmBand); if (cmOpen.size) p.set('cmo', rIdx(cmOpen)); }
  if (key === 'staffing' || key === 'trend' || key === 'costcurve') {
    p.set('sty', staffYear); if (capPreset === 'contract') p.set('stp', 'contract');
    if (key === 'staffing' && staffOpen.size) p.set('sto', rIdx(staffOpen));
  }
  if (key === 'lines') { const r = document.getElementById('region')?.value, f = document.getElementById('find')?.value; if (r) p.set('lr', r); if (f) p.set('lf', f); }
  if (key === 'classsize') p.set('csy', csYear);
  if (key === 'privcap') { p.set('pcb', pcBand); if (pcOpen.size) p.set('pco', rIdx(pcOpen)); }
  if (key === 'report' && rpKey) { p.set('school', rpKey); p.set('year', rpYear); }
  p.set('t', key);
  return p;
}
function linkUrl(key) { return location.origin + location.pathname + '?' + linkParams(key) + (scen === 'C' ? '#custom=' + encodeCustom() : ''); }
// restore a link's settings before the first render
let LINK_TARGET = null;
(function applyLink() {
  const q = new URLSearchParams(location.search); if (!q.get('t')) return;
  if (q.get('adj') === '0' && adjOn) { applyAdjust(false); const b = document.getElementById('adjtog'); if (b) b.checked = false; }
  if (q.get('ex')) rSet(q.get('ex'), expanded);
  if (q.get('rec') === '1') { const c = document.getElementById('showrec'); if (c) c.checked = true; }
  if (q.get('bco')) rSet(q.get('bco'), bcOpen);
  if (q.has('bcc')) bcClosedOnly = q.get('bcc') === '1';
  if (D.years.includes(q.get('cmy'))) cmYear = q.get('cmy');
  if (CM_BANDS.some(b => b[0] === q.get('cmb'))) cmBand = q.get('cmb');
  if (q.get('cmo')) rSet(q.get('cmo'), cmOpen);
  if (STAFF_YEARS.includes(q.get('sty'))) staffYear = q.get('sty');
  if (q.get('stp') === 'contract') { capPreset = 'contract'; caps = JSON.parse(JSON.stringify(SF.caps_contract)); }
  if (q.get('sto')) rSet(q.get('sto'), staffOpen);
  if (D.years.includes(q.get('csy'))) csYear = q.get('csy');
  if (PC_BANDS.some(b => b[0] === q.get('pcb'))) pcBand = q.get('pcb');
  if (q.get('pco')) rSet(q.get('pco'), pcOpen);
  if (q.get('lr') != null && document.getElementById('region')) document.getElementById('region').value = q.get('lr');
  if (q.get('lf') && document.getElementById('find')) document.getElementById('find').value = q.get('lf');
  LINK_TARGET = q.get('t');
  const det = { lines: 'lineswrap', busmap: 'bmwrap' }[LINK_TARGET]; if (det && document.getElementById(det)) document.getElementById(det).open = true;
})();
// a "Link" button on each table's heading
(function addLinkButtons() {
  if (typeof document.querySelectorAll !== 'function') return;
  for (const [key, id] of LINK_TABLES) {
    let n = document.getElementById(id); if (!n) continue;
    while (n.parentElement && n.parentElement.tagName !== 'SECTION') n = n.parentElement;
    let h = n; while (h && !/^H[23]$/.test(h.tagName)) h = h.previousElementSibling;
    if (!h || h.querySelector('.linkbtn')) continue;
    const b = document.createElement('button'); b.type = 'button'; b.className = 'linkbtn'; b.textContent = 'Link';
    b.title = 'Copy a link to this table with its current scenario and settings';
    b.onclick = () => { const u = linkUrl(key);
      const done = ok => { b.textContent = ok ? 'Copied' : 'Link'; if (!ok) prompt('Link to this table:', u); setTimeout(() => b.textContent = 'Link', 1600); };
      navigator.clipboard?.writeText ? navigator.clipboard.writeText(u).then(() => done(true), () => done(false)) : done(false); };
    h.appendChild(b); h.dataset.linkt = key;
  }
})();
renderAll();
if (LINK_TARGET && typeof document.querySelectorAll === 'function') setTimeout(() => {
  const h = document.querySelector(`[data-linkt="${LINK_TARGET}"]`); if (h) h.scrollIntoView({ behavior: 'smooth', block: 'start' });
}, 400);
""")
    rep(".tablewrap { overflow-x: auto; }", ".tablewrap { overflow-x: auto; }\n.linkbtn { margin-left: 10px; font: inherit; font-size: 12px; font-weight: 500; padding: 2px 9px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface-1); color: var(--text-secondary); cursor: pointer; vertical-align: 3px; } .linkbtn:hover { color: var(--text-primary); border-color: var(--text-muted); }\nh2[data-linkt], h3[data-linkt] { scroll-margin-top: 72px; }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
