"""Region tables (Scenario impact by region; Building, staffing and land costs; Getting to school; Staffing; Class sizes;
Private school capacity; Forecast accuracy; PTA; Room to grow by region): a region filter and sortable columns.
  - Region filter above each table: All regions, or one region. Filtered, the table shows that region's roll-up row and
    its schools (opened automatically); the District row stays for reference in every view.
  - Click a column heading to sort (again to reverse): region groups sort by their roll-up row's value, schools sort
    within their region; the District row stays last.
  - Applied whenever a table redraws (a MutationObserver on its container), so scenario switches, expanding regions and
    year changes keep the filter and sort. Values sort by the first number in a cell ($, %, k and M understood; dashes
    last), text otherwise.
Code added once.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b, n=1):
    global html
    assert html.count(a) == n, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'RT_HOSTS' not in html:
    rep(""".leaflet-tooltip.rpmlabel {""", """.rtctl { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; font-size: 13px; margin: 6px 0; }
.rtctl .muted { font-size: 12px; }
th.rtsort { cursor: pointer; user-select: none; } th.rtsort:hover { text-decoration: underline; } th.rtsort:focus-visible { outline: 2px solid var(--text-primary); outline-offset: -2px; }
th.rtsort .rtar { font-size: 10px; margin-left: 3px; color: var(--text-muted); } th.rtsort.on .rtar { color: var(--text-primary); }
.leaflet-tooltip.rpmlabel {""")
    rep("""function renderAll() {""", r"""// ---------- region tables: filter by region, sort by any column (scripts/patch_region_tables.py) ----------
const RT_HOSTS = ['endpoints', 'bldcosts', 'commute', 'staffing', 'classsize', 'privcap', 'fcacc', 'ptatable', 'roomtable'];
const RT = {};   // per table: { region, col, dir, opened }
function rtVal(td) {
  if (!td) return null;
  const t = td.textContent.replace(/−|&minus;/g, '-').replace(/\s+/g, ' ').trim();
  const m = t.match(/(-?)\$?\s*(-?\d[\d,]*\.?\d*)\s*([kKmM%])?/);
  if (!m) return t ? t.toLowerCase() : null;
  let v = parseFloat(m[2].replace(/,/g, '')) * (m[1] === '-' ? -1 : 1);
  if (/[kK]/.test(m[3] || '')) v *= 1e3; else if (/M/.test(m[3] || '')) v *= 1e6;
  return v;
}
const rtCmp = (a, b, dir) => {
  if (a == null && b == null) return 0; if (a == null) return 1; if (b == null) return -1;
  if (typeof a === 'number' && typeof b === 'number') return (a - b) * dir;
  return String(a).localeCompare(String(b)) * dir;
};
// header cells by column position (rowspan / colspan aware); only single-column cells sort
function rtHeads(table) {
  const grid = [], out = [];
  [...(table.tHead?.rows || [])].forEach((tr, r) => {
    let c = 0; grid[r] = grid[r] || [];
    for (const th of tr.cells) {
      while (grid[r][c]) c++;
      for (let i = 0; i < th.rowSpan; i++) for (let j = 0; j < th.colSpan; j++) (grid[r + i] = grid[r + i] || [])[c + j] = th;
      if (th.colSpan === 1) out[c] = th;
      c += th.colSpan;
    }
  });
  return out;
}
function rtApply(id) {
  const host = document.getElementById(id), table = host && [...host.querySelectorAll('table')].find(t => [...t.querySelectorAll('tbody [data-r]')].some(x => D.region_order.includes(x.dataset.r))); if (!table || !table.tBodies[0]) return;   // the table with region rows
  const st = RT[id] ||= { region: '', col: -1, dir: 1, opened: '' };
  // controls (once, before the table's container)
  if (!document.getElementById('rtctl-' + id)) {
    const bar = document.createElement('div'); bar.className = 'rtctl'; bar.id = 'rtctl-' + id;
    bar.innerHTML = `<label>Region <select id="rtsel-${id}"><option value="">All regions</option>${D.region_order.map(r => `<option>${esc(r)}</option>`).join('')}</select></label><button type="button" id="rtclr-${id}" hidden>Group by region</button><span class="muted">Click a column heading to sort; with all regions, sorting lists every school together. The District row stays for reference.</span>`;
    host.parentNode.insertBefore(bar, host);
    bar.querySelector('select').onchange = e => { st.region = e.target.value; st.opened = ''; rtApply(id); };
    bar.querySelector('button').onclick = () => { st.col = -1; rtApply(id); };
  }
  document.getElementById('rtsel-' + id).value = st.region;
  document.getElementById('rtclr-' + id).hidden = st.col < 0;
  // headings
  const heads = rtHeads(table);
  heads.forEach((th, c) => {
    if (!th || c === 0 && false) return;
    if (!th.classList.contains('rtsort')) {
      th.classList.add('rtsort'); th.tabIndex = 0; th.setAttribute('role', 'button');
      th.insertAdjacentHTML('beforeend', '<span class="rtar">&#8597;</span>');
      const go = () => { st.dir = st.col === c ? -st.dir : (c === 0 ? 1 : -1); st.col = c; rtApply(id); };
      th.onclick = go; th.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } };
    }
    th.classList.toggle('on', st.col === c);
    const ar = th.querySelector('.rtar'); if (ar) ar.innerHTML = st.col === c ? (st.dir > 0 ? '&#9650;' : '&#9660;') : '&#8597;';
    th.setAttribute('aria-sort', st.col === c ? (st.dir > 0 ? 'ascending' : 'descending') : 'none');
  });
  // groups: a region row (it has a region button) and the rows under it; rows after the last group stay last
  const tb = table.tBodies[0], rows = [...tb.rows], groups = [], tail = [], lead = [];
  for (const tr of rows) {
    const b = [...tr.querySelectorAll('[data-r]')].find(x => D.region_order.includes(x.dataset.r));   // a region row (not a nested expander)
    if (b && !tr.classList.contains('dist')) groups.push({ r: b.dataset.r, head: tr, btn: b, kids: [] });
    else if (tr.classList.contains('dist') || (groups.length && tail.length)) tail.push(tr);
    else if (groups.length) {
      // a row under an opened nested expander (a private school's details) stays with it when sorting
      const g = groups[groups.length - 1], last = g.kids[g.kids.length - 1];
      if (last && !tr.querySelector('[data-r]') && last.querySelector('[data-r][aria-expanded="true"]')) (last._rtSub ||= []).push(tr);
      else { tr._rtSub = null; g.kids.push(tr); }
    }
    else lead.push(tr);
  }
  if (!groups.length) return;
  // the chosen region's schools are shown: open it once if it is closed
  if (st.region && st.opened !== st.region) {
    const g = groups.find(x => x.r === st.region);
    st.opened = st.region;
    if (g && g.btn.getAttribute('aria-expanded') === 'false') { g.btn.click(); return; }   // the table redraws and this runs again
  }
  const key = tr => rtVal(tr.cells[st.col]), flat = g => [g.head, ...g.kids.flatMap(k => [k, ...(k._rtSub || [])])];
  // all regions and a sort: one list of every school, regions set aside (each region opens to give its schools)
  if (st.col >= 0 && !st.region) {
    const shut = groups.find(g => g.btn.getAttribute('aria-expanded') === 'false');
    if (shut) { shut.btn.click(); return; }   // the table redraws and this runs again, one region at a time
    const kids = groups.flatMap(g => g.kids).sort((a, b) => rtCmp(key(a), key(b), st.dir));
    for (const g of groups) g.head.style.display = 'none';
    for (const k of kids) for (const tr of [k, ...(k._rtSub || [])]) tr.style.display = '';
    for (const tr of [...lead, ...groups.map(g => g.head), ...kids.flatMap(k => [k, ...(k._rtSub || [])]), ...tail]) tb.appendChild(tr);
    return;
  }
  if (st.col >= 0) {
    groups.sort((a, b) => rtCmp(key(a.head), key(b.head), st.dir));
    for (const g of groups) g.kids.sort((a, b) => rtCmp(key(a), key(b), st.dir));
  }
  for (const g of groups) { const show = !st.region || g.r === st.region; for (const tr of flat(g)) tr.style.display = show ? '' : 'none'; }
  for (const tr of [...lead, ...groups.flatMap(flat), ...tail]) tb.appendChild(tr);
}
if (typeof MutationObserver !== 'undefined')
  for (const id of RT_HOSTS) { const host = document.getElementById(id); if (host) new MutationObserver(() => rtApply(id)).observe(host, { childList: true }); }
function renderAll() {""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
