"""Receiving schools from PPS's model (source/pps-powerbi/receiving.json, scripts/build_receiving.py), 2027-28.
  - Summary card (after the four headline cards; not under Status Quo): schools that only receive students (no boundary
    change sending students elsewhere, no grade, program-type or immersion change of their own), of all receiving
    schools; students arriving, students at receiving schools, students at closing schools. Clicking it goes to the
    section. Custom scenarios show their starting scenario's figures.
  - Section after "Scenario impact by region": a histogram for Scenario A and one for Scenario B of receiving schools by
    the share of their 2027-28 students who are new (10-point buckets; hover or focus a bar for its schools), the
    viewed scenario outlined; a totals note; a table by school.
  - wireKPIs: a card may name its own target (data-go), so cards that appear only in some views don't shift the others.
Data: D.recv (refreshed on rerun); code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
R = json.load(open(os.path.join(ROOT, 'source', 'pps-powerbi', 'receiving.json'), encoding='utf-8'))
D['recv'] = {'source': R['source'], 'runs': {k: R['runs'][k] for k in ('A', 'B')}}
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

CARD = r'''
// schools whose population changes by more than a third in 2027-28: receiving schools where over a third of students are new,
// and open schools that lose over a third of their students (scripts/patch_receiving.py)
function recvBigKPI() {
  const sc = scen === 'C' ? custom.base : scen, R = D.recv?.runs?.[sc]; if (!R) return '';
  const big = R.receivers.filter(p => p[4] > 1 / 3), sh = R.shrink || [], f = v => Math.round(v).toLocaleString();
  const top = big.slice().sort((p, q) => q[4] - p[4]).slice(0, 4).map(p => `${esc(rcvName(p[0]))} ${Math.round(100 * p[4])}%`).join(', ');
  return `<div class="kpi" data-go="recv"><div class="v">${big.length + sh.length}<span class="vt">Schools whose population changes by more than a third</span></div>` +
    `<div class="l">2027-28, PPS's model${scen === 'C' ? ` <span class="pcs">(${esc(LABEL[sc])})</span>` : ''}</div>` +
    `<div class="s"><b>${big.length}</b> receiving schools where over a third of students are new: <b>${f(big.reduce((a, p) => a + p[2], 0))}</b> new among ${f(big.reduce((a, p) => a + p[3], 0))} students (most: ${top})` +
    (sh.length ? `<br><b>${sh.length}</b> open school${sh.length === 1 ? '' : 's'} losing over a third: ${sh.map(([k, b0, a0]) => `${esc(rcvName(k))} ${f(b0)} &rarr; ${f(a0)}`).join(', ')}` : '') + `</div></div>`;
}
let rcvTip = null;'''

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'recvBigKPI' not in html and 'renderRecv' in html:
    # second card added after the section (refresh of an earlier patch)
    rep("\nlet rcvTip = null;", CARD)
    rep("  }).join('') + recvKPI() + extraKPIs() + staffKPI()", "  }).join('') + recvKPI() + recvBigKPI() + extraKPIs() + staffKPI()")
if 'renderRecv' not in html:
    rep("""  <section class="card" id="roomcard">""", """  <section class="card" id="recvcard">
    <h2>Receiving schools: how much of each is new</h2>
    <p class="sub" id="recvsub"></p>
    <div class="rcvhists" id="recvhists"></div>
    <p class="muted" id="recvnote" style="font-size:12px"></p>
    <details class="rcvtv"><summary>Show the table by school</summary><div class="tablewrap" id="recvtable"></div></details>
  </section>

  <section class="card" id="roomcard">""")
    rep(""".leaflet-tooltip.rpmlabel {""", """.rcvhists { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 8px 0; } @media (max-width: 640px) { .rcvhists { grid-template-columns: minmax(0, 1fr); } }
.rcvh { border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px 6px; position: relative; min-width: 0; background: var(--surface-1); }
.rcvh.cur { border: 2px solid var(--text-primary); }
.rcvh .hd { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; flex-wrap: wrap; font-size: 14px; font-weight: 700; }
.rcvh .hd .s { font-size: 12px; font-weight: 400; color: var(--text-muted); }
.rcvh svg { display: block; width: 100%; height: auto; }
.rcvh .ax { font-size: 10.5px; fill: var(--text-muted); }
.rcvh .hit { fill: transparent; } .rcvh .hit:focus-visible { outline: none; stroke: var(--text-primary); stroke-width: 2; }
.rcvtip { position: absolute; z-index: 5; pointer-events: none; background: var(--surface-1); color: var(--text-primary); border: 1px solid var(--line); border-radius: 6px;
  box-shadow: 0 4px 14px rgb(0 0 0 / .14); padding: 8px 10px; font-size: 12.5px; width: max-content; max-width: 270px; display: grid; gap: 3px; }
.rcvtip .row { display: flex; justify-content: space-between; gap: 12px; font-size: 11.5px; }
.rcvtv summary { cursor: pointer; font-size: 13px; }
.leaflet-tooltip.rpmlabel {""")
    # summary card and its wiring
    rep("""  }).join('') + extraKPIs() + staffKPI()""", """  }).join('') + recvKPI() + recvBigKPI() + extraKPIs() + staffKPI()""")
    rep("""function wireKPIs() {
  document.querySelectorAll('#kpis .kpi').forEach((k, i) => {
    const t = KPI_TARGETS[i]; if (!t) return;""", """function wireKPIs() {
  let j = 0;   // cards that name their own target (data-go) don't take a place in KPI_TARGETS
  document.querySelectorAll('#kpis .kpi').forEach(k => {
    const t = k.dataset.go || KPI_TARGETS[j++]; if (!t) return;""")
    rep("""t === 'room' ? 'Show demographic factors impacting sustainability' :""", """t === 'room' ? 'Show demographic factors impacting sustainability' : t === 'recv' ? 'Show the receiving schools' :""")
    rep("""function goTo(target) {""", """function goTo(target) {
  if (target === 'recv') { const t = document.getElementById('recvcard'); if (t) { t.scrollIntoView({ behavior: 'smooth', block: 'start' }); flash([t]); } return; }""")
    rep("""function renderAll() {""", r"""// ---------- receiving schools in PPS's model, 2027-28 (scripts/patch_receiving.py) ----------
const RCV_COL = { A: 'var(--change)', B: '#0f9b78' };
const rcvName = k => short(byKey[k]?.name || k);
function recvKPI() {
  const sc = scen === 'C' ? custom.base : scen, R = D.recv?.runs?.[sc]; if (!R) return '';
  const n = R.receivers.length, f = v => Math.round(v).toLocaleString();
  return `<div class="kpi" data-go="recv"><div class="v">${R.only.length}<span class="vt">Additional schools affected</span></div>` +
    `<div class="l">2027-28, PPS's model: they take in students from other schools but have no closure, boundary, grade or program change of their own (${n} receiving schools in all)${scen === 'C' ? ` <span class="pcs">(${esc(LABEL[sc])})</span>` : ''}</div>` +
    `<div class="s"><b>${f(R.arriving)}</b> students move to the ${n} receiving schools (<b>${f(R.at_receivers)}</b> students in all); ${f(R.closing_students)} from closing schools</div></div>`;
}
// schools whose population changes by more than a third in 2027-28: receiving schools where over a third of students are new,
// and open schools that lose over a third of their students (scripts/patch_receiving.py)
function recvBigKPI() {
  const sc = scen === 'C' ? custom.base : scen, R = D.recv?.runs?.[sc]; if (!R) return '';
  const big = R.receivers.filter(p => p[4] > 1 / 3), sh = R.shrink || [], f = v => Math.round(v).toLocaleString();
  const top = big.slice().sort((p, q) => q[4] - p[4]).slice(0, 4).map(p => `${esc(rcvName(p[0]))} ${Math.round(100 * p[4])}%`).join(', ');
  return `<div class="kpi" data-go="recv"><div class="v">${big.length + sh.length}<span class="vt">Schools whose population changes by more than a third</span></div>` +
    `<div class="l">2027-28, PPS's model${scen === 'C' ? ` <span class="pcs">(${esc(LABEL[sc])})</span>` : ''}</div>` +
    `<div class="s"><b>${big.length}</b> receiving schools where over a third of students are new: <b>${f(big.reduce((a, p) => a + p[2], 0))}</b> new among ${f(big.reduce((a, p) => a + p[3], 0))} students (most: ${top})` +
    (sh.length ? `<br><b>${sh.length}</b> open school${sh.length === 1 ? '' : 's'} losing over a third: ${sh.map(([k, b0, a0]) => `${esc(rcvName(k))} ${f(b0)} &rarr; ${f(a0)}`).join(', ')}` : '') + `</div></div>`;
}
let rcvTip = null;
function renderRecv() {
  const host = document.getElementById('recvhists'); if (!host || !D.recv) return;
  const sc = scen === 'C' ? custom.base : scen, NB = 7, f = v => Math.round(v).toLocaleString(), pct = v => Math.round(100 * v) + '%';
  const runs = ['A', 'B'].filter(k => D.recv.runs[k]);
  const counts = Object.fromEntries(runs.map(k => { const c = Array.from({ length: NB }, () => []); D.recv.runs[k].receivers.forEach(p => c[Math.min(NB - 1, Math.floor(p[4] * 10 + 1e-9))].push(p)); return [k, c]; }));
  const yTop = Math.ceil(Math.max(...Object.values(counts).flatMap(c => c.map(b => b.length))) / 4) * 4;
  const W = 420, H = 210, ml = 30, mr = 6, mt = 14, mb = 38, iw = W - ml - mr, ih = H - mt - mb, bw = iw / NB;
  const med = a => { const s = a.map(p => p[4]).sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
  host.innerHTML = runs.map(k => {
    const c = counts[k], y = v => mt + ih - ih * v / yTop, R = D.recv.runs[k];
    let g = '';
    for (let v = 0; v <= yTop; v += yTop / 4) g += `<line x1="${ml}" x2="${W - mr}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text class="ax" x="${ml - 6}" y="${y(v) + 3.5}" text-anchor="end">${v}</text>`;
    c.forEach((b, i) => {
      const x = ml + i * bw + 1, w = bw - 2, h = ih * b.length / yTop, top = mt + ih - h, r = Math.min(4, h / 2, w / 2);
      if (b.length) g += `<path d="M${x},${mt + ih}V${top + r}Q${x},${top} ${x + r},${top}H${x + w - r}Q${x + w},${top} ${x + w},${top + r}V${mt + ih}Z" fill="${RCV_COL[k]}"/>` +
        `<text class="ax" x="${x + w / 2}" y="${top - 4}" text-anchor="middle" style="fill:var(--text-primary)">${b.length}</text>`;
      g += `<text class="ax" x="${x + w / 2}" y="${mt + ih + 14}" text-anchor="middle">${i * 10}&ndash;${(i + 1) * 10}</text>` +
        `<rect class="hit" x="${ml + i * bw}" y="${mt}" width="${bw}" height="${ih}" tabindex="0" data-k="${k}" data-i="${i}" aria-label="${LABEL[k]}: ${b.length} schools with ${i * 10} to ${(i + 1) * 10} percent new students"/>`;
    });
    g += `<line x1="${ml}" x2="${W - mr}" y1="${mt + ih}" y2="${mt + ih}" stroke="var(--text-muted)"/><text class="ax" x="${ml + iw / 2}" y="${H - 4}" text-anchor="middle">share of the school's 2027-28 students who are new (%)</text>`;
    return `<div class="rcvh${k === sc ? ' cur' : ''}"><div class="hd"><span><i style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${RCV_COL[k]};margin-right:6px"></i>${esc(LABEL[k])}</span>` +
      `<span class="s">${R.receivers.length} receiving schools &middot; median ${pct(med(R.receivers))} new &middot; ${R.only.length} additional schools affected</span></div><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LABEL[k])}: receiving schools by share of new students">${g}</svg></div>`;
  }).join('');
  if (!rcvTip) { rcvTip = document.createElement('div'); rcvTip.className = 'rcvtip'; rcvTip.hidden = true; }
  const show = el => {
    const panel = el.closest('.rcvh'), k = el.dataset.k, i = +el.dataset.i, b = counts[k][i].slice().sort((p, q) => q[4] - p[4]);
    rcvTip.innerHTML = `<b>${esc(LABEL[k])}: ${i * 10}&ndash;${(i + 1) * 10}% new</b><span style="color:var(--text-muted)">${b.length} school${b.length === 1 ? '' : 's'}${b.length ? ' (new students of total)' : ''}</span>` +
      b.slice(0, 12).map(p => `<span class="row"><span>${esc(rcvName(p[0]))}${p[5] ? ' <span style="color:var(--text-muted)">additional</span>' : ''}</span><span>${p[2]} of ${p[3]}</span></span>`).join('') + (b.length > 12 ? `<span style="color:var(--text-muted)">and ${b.length - 12} more</span>` : '');
    panel.appendChild(rcvTip); rcvTip.hidden = false;
    const pr = panel.getBoundingClientRect(), er = el.getBoundingClientRect();
    rcvTip.style.left = Math.max(4, Math.min(er.left - pr.left + er.width / 2 - rcvTip.offsetWidth / 2, pr.width - rcvTip.offsetWidth - 4)) + 'px';
    rcvTip.style.top = Math.max(4, er.top - pr.top + 20) + 'px';
  };
  host.querySelectorAll('.hit').forEach(el => { el.onpointerenter = el.onfocus = () => show(el); el.onpointerleave = el.onblur = () => { rcvTip.hidden = true; }; });
  const R = D.recv.runs[sc];
  document.getElementById('recvsub').innerHTML = `Schools that take in students from another school under PPS's model (closing schools' areas and programs, boundary changes, K-8s becoming K-5), by the share of their students in ${D.impl_year}, the year the changes take effect, who are new. Scenarios A and B side by side${R ? `; ${esc(LABEL[sc])} outlined` : ''}. Hover or tab to a bar for its schools.`;
  const F = D.forecast52, fi = F.years.indexOf(D.impl_year), pps = fi < 0 ? null : Object.values(F.grades).reduce((a, g) => a + g[fi], 0);   // all PPS students (PSU)
  const tot = k => { const r = D.recv.runs[k];
    return `<b>${esc(LABEL[k])}:</b> <b>${f(r.arriving)}</b> students move to ${r.receivers.length} receiving schools, including about ${f(r.closing_students)} from the schools that close. The receiving schools together have <b>${f(r.at_receivers)}</b> students in ${D.impl_year}${pps ? ` (${Math.round(100 * r.at_receivers / pps)}% of PPS students)` : ''}. <b>${r.only.length}</b> of them are additional schools affected, taking in students with no closure, boundary, grade or program change of their own: ${r.only.map(rcvName).join(', ')}.`; };
  document.getElementById('recvnote').innerHTML = runs.map(tot).join('<br>') + `<br>Students moving: each receiving school's increase over its Status Quo projection, by grade and student group (a school that gains and loses students in the same grade counts only its net gain, so this is a floor), in PPS's ${D.impl_year} model results. High-school boundary changes phase in with new 9th graders, so few high-school students move in the first year. Closing schools: their Status Quo ${D.impl_year} enrollment. Source: ${esc(D.recv.source)}.`;
  const keys = [...new Set(runs.flatMap(k => D.recv.runs[k].receivers.map(p => p[0])))].sort((a, b) => rcvName(a).localeCompare(rcvName(b)));
  document.getElementById('recvtable').innerHTML = `<table style="min-width:0"><thead><tr><th style="text-align:left">School</th>${runs.map(k => `<th>${esc(LABEL[k])}<br><span style="font-weight:400">new of total (share)</span></th>`).join('')}</tr></thead><tbody>` +
    keys.map(x => `<tr><td style="text-align:left">${esc(rcvName(x))}</td>${runs.map(k => { const p = D.recv.runs[k].receivers.find(q => q[0] === x);
      return `<td style="text-align:right">${p ? `${p[2]} of ${p[3]} (${pct(p[4])})${p[5] ? ' <span class="muted">additional</span>' : ''}` : '<span class="muted">&ndash;</span>'}</td>`; }).join('')}</tr>`).join('') + '</tbody></table>';
}
function renderAll() {""")
    rep("renderMap(); renderEndpoints(); renderRoom();", "renderMap(); renderEndpoints(); renderRecv(); renderRoom();")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
