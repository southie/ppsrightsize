"""Private school capacity table (last section, before the method notes): comparable private schools' enrollment, demonstrated capacity,
estimated available capacity and enrollment trend from five NCES PSS waves (source/nces-pss/private-capacity.json, from
scripts/build_private_capacity.py), by region, drilling down to schools and then grades, with a grade-band selector.
Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
J = json.load(open(os.path.join(ROOT, 'source', 'nces-pss', 'private-capacity.json'), encoding='utf-8'))
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['privcap'] = dict(source=J['source'], waves=J['waves'],
                    schools=[{k: s[k] for k in ('name', 'region', 'area', 'character', 'grades_served', 'latest_wave', 'peak_total', 'latest', 'capacity', 'series')}
                             for s in J['schools']])
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderPrivCap' not in html:
    rep("""  <section class="card">
    <h2>Method and assumptions</h2>""", """  <section class="card">
    <h2>Private school capacity: comparable schools by region</h2>
    <p class="sub">Comparable private schools are regular Catholic, other religious and nonsectarian schools (not special program emphasis or special education) inside PPS, plus schools just outside the district within 3.5 miles by road of a PPS school (or listed on the map as an alternative for one), counted in the region of their nearest PPS school. From five NCES Private School Universe Surveys, 2015-16 to 2023-24 (every two years). <b>Capacity</b> is each school's highest total K-12 enrollment in those surveys, split across its grades by its latest enrollment, so it is room a school has shown it can fill, not its building's limit. <b>Estimated available capacity</b> = capacity &minus; latest enrollment. <b>Trend</b> is the average change a year from a log-linear fit through the five surveys (a school's missing surveys between two reports are filled in by straight line). Click a region to see its schools, and a school to see its grades.</p>
    <div class="controls"><label>Grades <select id="pc-band"></select></label></div>
    <div class="tablewrap" id="privcap"></div>
  </section>

  <section class="card">
    <h2>Method and assumptions</h2>""")
    rep("function renderAll() {", r"""// ---------- private school capacity (D.privcap, from scripts/build_private_capacity.py) ----------
const PC = D.privcap, PC_BANDS = [['all', 'All grades (K-12)', 0, 12], ['k5', 'K-5', 0, 5], ['68', '6-8', 6, 8], ['912', '9-12', 9, 12]];
const PC_YEARS = PC.waves.map(w => +w.slice(0, 4) + 0.75);
let pcBand = 'all'; try { const b = localStorage.getItem('rsPcBand'); if (PC_BANDS.some(x => x[0] === b)) pcBand = b; } catch (e) {}
const pcOpen = new Set(), pcOpenSchool = new Set();
// average change a year: log-linear fit through the surveys with enrollment
function pcTrend(v) {
  const p = v.map((x, i) => [PC_YEARS[i], x]).filter(([, x]) => x > 0); if (p.length < 3) return null;
  const n = p.length, mx = p.reduce((a, [x]) => a + x, 0) / n, my = p.reduce((a, [, y]) => a + Math.log(y), 0) / n;
  const k = p.reduce((a, [x, y]) => a + (x - mx) * (Math.log(y) - my), 0) / p.reduce((a, [x]) => a + (x - mx) ** 2, 0);
  return 100 * (Math.exp(k) - 1);
}
// totals over a set of (school, grades)
function pcAgg(list, lo, hi) {
  const o = { n: 0, latest: 0, cap: 0, series: PC.waves.map(() => 0) };
  for (const s of list) {
    let any = false;
    for (let g = lo; g <= hi; g++) {
      o.latest += s.latest[g]; o.cap += s.capacity[g]; s.series[g].forEach((x, i) => { o.series[i] += x; });
      if (s.latest[g] || s.series[g].some(x => x)) any = true;
    }
    if (any) o.n++;
  }
  return o;
}
function pcSpark(v) {
  const W = 92, H = 22, top = Math.max(...v, 1), dx = W / (v.length - 1);
  const pts = v.map((x, i) => `${(i * dx).toFixed(1)},${(H - 2 - (H - 4) * x / top).toFixed(1)}`).join(' ');
  return `<svg width="${W}" height="${H}" viewBox="-2 0 ${W + 4} ${H}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="var(--priv)" stroke-width="1.6"/>` +
    v.map((x, i) => `<circle cx="${(i * dx).toFixed(1)}" cy="${(H - 2 - (H - 4) * x / top).toFixed(1)}" r="1.8" fill="var(--priv)"/>`).join('') + '</svg>';
}
function pcCells(o, showN = true) {
  const t = pcTrend(o.series), open = Math.max(0, o.cap - o.latest), r = v => Math.round(v).toLocaleString();
  const tip = PC.waves.map((w, i) => `${w}: ${r(o.series[i])}`).join(' · ');
  return (showN ? `<td>${o.n || '&mdash;'}</td>` : '<td></td>') +
    `<td><span class="main">${r(o.latest)}</span></td><td>${r(o.cap)}</td>` +
    `<td><span class="main">${r(open)}</span><span class="pcsub">${o.cap ? Math.round(100 * open / o.cap) + '% of capacity' : ''}</span></td>` +
    `<td class="${t == null ? 'muted' : t > 0.05 ? 'pcup' : t < -0.05 ? 'pcdown' : ''}">${t == null ? '&mdash;' : `${t > 0 ? '+' : t < 0 ? '&minus;' : ''}${Math.abs(t).toFixed(1)}%`}</td>` +
    `<td class="pcspark" title="${esc(tip)}">${pcSpark(o.series)}</td>`;
}
function renderPrivCap() {
  const host = document.getElementById('privcap'); if (!host) return;
  const sel = document.getElementById('pc-band');
  if (!sel.options.length) {
    sel.innerHTML = PC_BANDS.map(([v, l]) => `<option value="${v}">${l}</option>`).join('');
    sel.onchange = () => { pcBand = sel.value; try { localStorage.setItem('rsPcBand', pcBand); } catch (e) {} renderPrivCap(); };
  }
  sel.value = pcBand;
  const [, , lo, hi] = PC_BANDS.find(b => b[0] === pcBand), G = CS_GRADES;
  const serves = s => s.latest.slice(lo, hi + 1).some(x => x) || s.series.slice(lo, hi + 1).some(v => v.some(x => x));
  let h = `<table class="pctable"><thead><tr><th>Region</th><th>Comparable schools</th><th>Students<br><span style="font-weight:400">(latest survey)</span></th>` +
    `<th>Capacity<br><span style="font-weight:400">(highest enrollment)</span></th><th>Estimated available capacity<br><span style="font-weight:400">(capacity &minus; latest enrollment)</span></th><th>Trend<br><span style="font-weight:400">(change a year)</span></th>` +
    `<th>Enrollment<br><span style="font-weight:400">${PC.waves[0]} to ${PC.waves[PC.waves.length - 1]}</span></th></tr></thead><tbody>`;
  const all = [];
  for (const rn of D.region_order) {
    const list = PC.schools.filter(s => s.region === rn && serves(s)).sort((a, b) => b.latest.slice(lo, hi + 1).reduce((x, y) => x + y, 0) - a.latest.slice(lo, hi + 1).reduce((x, y) => x + y, 0));
    all.push(...list);
    const open = pcOpen.has(rn);
    h += `<tr><td><button class="xbtn pc-x" data-r="${esc(rn)}" aria-expanded="${open}"><span class="car">&#9656;</span><span>${esc(rn)}</span></button></td>${pcCells(pcAgg(list, lo, hi))}</tr>`;
    if (!open) continue;
    for (const s of list) {
      const so = pcOpenSchool.has(s.name);
      h += `<tr class="srow"><td><button class="xbtn pc-s" data-s="${esc(s.name)}" aria-expanded="${so}"><span class="car">&#9656;</span><span class="nm">${esc(s.name)}</span></button>` +
        `<span class="pcsub">${esc(s.grades_served || '')} &middot; ${esc((s.character || '').replace(/^Private, /, ''))} &middot; ${esc(s.area)}${s.latest_wave !== PC.waves[PC.waves.length - 1] ? ` &middot; last reported ${s.latest_wave}` : ''}</span></td>${pcCells(pcAgg([s], lo, hi), false)}</tr>`;
      if (!so) continue;
      for (let g = lo; g <= hi; g++) {
        if (!s.latest[g] && !s.series[g].some(x => x)) continue;
        h += `<tr class="srow pcgrade"><td>${G[g] === 'K' ? 'Kindergarten' : 'Grade ' + G[g]}</td>${pcCells({ n: 0, latest: s.latest[g], cap: s.capacity[g], series: s.series[g] }, false)}</tr>`;
      }
    }
  }
  h += `<tr class="dist"><td>District</td>${pcCells(pcAgg(all, lo, hi))}</tr>`;
  host.innerHTML = h + '</tbody></table>';
  host.querySelectorAll('.pc-x').forEach(b => b.onclick = () => { const r = b.dataset.r; pcOpen.has(r) ? pcOpen.delete(r) : pcOpen.add(r); renderPrivCap(); });
  host.querySelectorAll('.pc-s').forEach(b => b.onclick = () => { const r = b.dataset.s; pcOpenSchool.has(r) ? pcOpenSchool.delete(r) : pcOpenSchool.add(r); renderPrivCap(); });
}
function renderAll() {""")
    rep("renderLines(); renderClassSizes(); }", "renderLines(); renderClassSizes(); renderPrivCap(); }")
    # ---- styles: like the other large tables ----
    rep(".cstable th:first-child, .cstable td:first-child {", ".cstable th:first-child, .cstable td:first-child,\n.pctable th:first-child, .pctable td:first-child {")
    rep(".cstable tr.srow td:first-child { background: var(--surface-2); }",
        ".cstable tr.srow td:first-child, .pctable tr.srow td:first-child { background: var(--surface-2); }\n"
        ".pctable td, .pctable th { white-space: nowrap; } .pctable td .main { font-size: 14px; font-weight: 600; }\n"
        ".pctable .pcsub { display: block; font-size: 11px; color: var(--text-muted); font-weight: 400; white-space: normal; max-width: 360px; }\n"
        ".pctable td.pcup { color: var(--up); font-weight: 600; } .pctable td.pcdown { color: var(--down); font-weight: 600; }\n"
        ".pctable tr.pcgrade td:first-child { padding-left: 52px; } .pctable tr.pcgrade td { font-size: 12px; }\n"
        ".pctable .pc-s .nm { white-space: normal; text-align: left; } .pctable td.pcspark svg { display: block; margin-left: auto; }")
    rep("#endpoints, #commute, #overlist, #classsize,", "#endpoints, #commute, #overlist, #classsize, #privcap,")
    rep("#overlist thead th, .cstable thead th {", "#overlist thead th, .cstable thead th, .pctable thead th {")
    rep("#overlist thead th:first-child, .cstable thead th:first-child {", "#overlist thead th:first-child, .cstable thead th:first-child, .pctable thead th:first-child {")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
