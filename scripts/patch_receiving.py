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
D['recv'] = {'source': R['source'], 'waves': R['waves'], 'year': R['waves'][-1], 'runs': {k: R['runs'][k] for k in ('A', 'B')}}   # year: enrollment after both waves
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

CARD = r'''
// schools whose population changes by more than 20% in 2027-28: receiving schools where over 20% of students are new,
// and open schools that lose over 20% of their students (scripts/patch_receiving.py)
function recvBigKPI() {
  const sc = scen === 'C' ? custom.base : scen, R = D.recv?.runs?.[sc];
  if (!D.recv) return '';
  if (!R) return `<div class="kpi" data-go="recv"><div class="v">&ndash;<span class="vt">Schools whose population changes by more than 20%</span></div><div class="l">No school's population changes under ${esc(LABEL[sc] || 'this scenario')}</div></div>`;
  const big = R.receivers.filter(p => p[4] > 0.20), sh = R.shrink || [], f = v => Math.round(v).toLocaleString();
  // students who attend those schools after the change, as a share of all PPS students (PSU's district total that year)
  const F = D.forecast52, fi = F ? F.years.indexOf(D.recv.year || D.impl_year) : -1, pps = fi < 0 ? null : Object.values(F.grades).reduce((a, g) => a + g[fi], 0);
  const stu = big.reduce((a, p) => a + p[3], 0) + sh.reduce((a, s) => a + s[2], 0);
  const top = big.slice().sort((p, q) => q[4] - p[4]).slice(0, 4).map(p => `${esc(rcvName(p[0]))} ${Math.round(100 * p[4])}%`).join(', ');
  return `<div class="kpi" data-go="recv"><div class="v">${big.length + sh.length}<span class="vt">Schools whose population changes by more than 20%</span></div>` +
    `<div class="l">Changes in ${D.recv.waves[0]} and ${D.recv.waves[1]}, PPS's model${scen === 'C' ? ` <span class="pcs">(${esc(LABEL[sc])})</span>` : ''}</div>` +
    `<div class="s"><b>${f(stu)}</b> students attend them${pps ? ` (<b>${Math.round(100 * stu / pps)}%</b> of PPS students)` : ''}<br>` +
    `<b>${big.length}</b> receiving schools where over 20% of students are new: <b>${f(big.reduce((a, p) => a + p[2], 0))}</b> new among ${f(big.reduce((a, p) => a + p[3], 0))} students (most: ${top})` +
    (sh.length ? `<br><b>${sh.length}</b> open school${sh.length === 1 ? '' : 's'} losing over 20%: ${sh.map(([k, b0, a0]) => `${esc(rcvName(k))} ${f(b0)} &rarr; ${f(a0)}`).join(', ')}` : '') + `</div></div>`;
}
'''

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'recvBigKPI' not in html and 'renderRecv' in html:
    # second card added after the section (refresh of an earlier patch)
    rep("\nfunction renderRecv() {", CARD + "\nfunction renderRecv() {")
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
    rep(""".leaflet-tooltip.rpmlabel {""", """.rcvhists { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 24px; margin: 8px 0; } @media (max-width: 640px) { .rcvhists { grid-template-columns: minmax(0, 1fr); } }
.rcvh { min-width: 0; } .rcvh .hd { font-size: 13px; font-weight: 600; } .rcvh .hd .s { font-weight: 400; color: var(--text-muted); font-size: 12px; }
.rcvh svg { width: 100%; height: auto; display: block; margin: 4px 0; }
.rcvh .cmleg { font-size: 11.5px; color: var(--text-muted); } .rcvh .cmleg .sw { display: inline-block; width: 10px; height: 10px; margin: 0 3px 0 8px; vertical-align: -1px; }
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
const rcvName = k => short(byKey[k]?.name || k);
function recvKPI() {
  const sc = scen === 'C' ? custom.base : scen, R = D.recv?.runs?.[sc];
  if (!D.recv) return '';
  if (!R) return `<div class="kpi" data-go="recv"><div class="v">&ndash;<span class="vt">Additional schools affected</span></div><div class="l">No school receives students under ${esc(LABEL[sc] || 'this scenario')}</div></div>`;
  const n = R.receivers.length, f = v => Math.round(v).toLocaleString();
  // share of all PPS students (PSU's district total for the year the changes take effect)
  const F = D.forecast52, fi = F ? F.years.indexOf(D.recv.year || D.impl_year) : -1, pps = fi < 0 ? null : Object.values(F.grades).reduce((a, g) => a + g[fi], 0);
  const pc = v => Math.round(100 * v / pps) + '%', onlyN = R.receivers.filter(p => p[5]).reduce((a, p) => a + p[3], 0);
  return `<div class="kpi" data-go="recv"><div class="v">${R.only.length}<span class="vt">Additional schools affected</span></div>` +
    `<div class="l">Changes in ${D.recv.waves[0]} and ${D.recv.waves[1]}, PPS's model: they take in students from other schools but have no closure, boundary, grade or program change of their own (${n} receiving schools in all)${scen === 'C' ? ` <span class="pcs">(${esc(LABEL[sc])})</span>` : ''}</div>` +
    `<div class="s"><b>${f(onlyN)}</b> students attend these ${R.only.length} schools${pps ? ` (<b>${pc(onlyN)}</b> of PPS students)` : ''}` +
    `<br><b>${f(R.arriving)}</b> students move to the ${n} receiving schools: ${f(R.arriving_waves[0])} in ${D.recv.waves[0]} + ${f(R.arriving_waves[1])} in ${D.recv.waves[1]} (<b>${f(R.at_receivers)}</b> students in all after both); ${f(R.closing_students)} from closing schools` +
    (pps ? `<br>In all, <b>${pc(R.at_receivers + R.closing_students)}</b> of PPS students attend a receiving or closing school` : '') + `</div></div>`;
}
// schools whose population changes by more than 20% in 2027-28: receiving schools where over 20% of students are new,
// and open schools that lose over 20% of their students (scripts/patch_receiving.py)
function recvBigKPI() {
  const sc = scen === 'C' ? custom.base : scen, R = D.recv?.runs?.[sc];
  if (!D.recv) return '';
  if (!R) return `<div class="kpi" data-go="recv"><div class="v">&ndash;<span class="vt">Schools whose population changes by more than 20%</span></div><div class="l">No school's population changes under ${esc(LABEL[sc] || 'this scenario')}</div></div>`;
  const big = R.receivers.filter(p => p[4] > 0.20), sh = R.shrink || [], f = v => Math.round(v).toLocaleString();
  // students who attend those schools after the change, as a share of all PPS students (PSU's district total that year)
  const F = D.forecast52, fi = F ? F.years.indexOf(D.recv.year || D.impl_year) : -1, pps = fi < 0 ? null : Object.values(F.grades).reduce((a, g) => a + g[fi], 0);
  const stu = big.reduce((a, p) => a + p[3], 0) + sh.reduce((a, s) => a + s[2], 0);
  const top = big.slice().sort((p, q) => q[4] - p[4]).slice(0, 4).map(p => `${esc(rcvName(p[0]))} ${Math.round(100 * p[4])}%`).join(', ');
  return `<div class="kpi" data-go="recv"><div class="v">${big.length + sh.length}<span class="vt">Schools whose population changes by more than 20%</span></div>` +
    `<div class="l">Changes in ${D.recv.waves[0]} and ${D.recv.waves[1]}, PPS's model${scen === 'C' ? ` <span class="pcs">(${esc(LABEL[sc])})</span>` : ''}</div>` +
    `<div class="s"><b>${f(stu)}</b> students attend them${pps ? ` (<b>${Math.round(100 * stu / pps)}%</b> of PPS students)` : ''}<br>` +
    `<b>${big.length}</b> receiving schools where over 20% of students are new: <b>${f(big.reduce((a, p) => a + p[2], 0))}</b> new among ${f(big.reduce((a, p) => a + p[3], 0))} students (most: ${top})` +
    (sh.length ? `<br><b>${sh.length}</b> open school${sh.length === 1 ? '' : 's'} losing over 20%: ${sh.map(([k, b0, a0]) => `${esc(rcvName(k))} ${f(b0)} &rarr; ${f(a0)}`).join(', ')}` : '') + `</div></div>`;
}
function renderRecv() {
  const host = document.getElementById('recvhists'); if (!host || !D.recv) return;
  const sc = scen === 'C' ? custom.base : scen, NB = 7, f = v => Math.round(v).toLocaleString(), pct = v => Math.round(100 * v) + '%';
  const runs = ['A', 'B'].filter(k => D.recv.runs[k]);
  const counts = Object.fromEntries(runs.map(k => { const c = Array.from({ length: NB }, () => []); D.recv.runs[k].receivers.forEach(p => c[Math.min(NB - 1, Math.floor(p[4] * 10 + 1e-9))].push(p)); return [k, c]; }));
  // styled like the travel-time histograms: grey bars, darker for buckets at or above 20% new (the summary card), a dashed line at 20%
  const top = Math.ceil(Math.max(...Object.values(counts).flatMap(c => c.map(b => b.length))) / 4) * 4;
  const W = 560, H = 170, L0 = 26, B0 = 34, T0 = 16, bw = (W - L0) / NB, y = v => T0 + (H - T0) * (1 - v / top);
  const med = a => { const s = a.map(p => p[4]).sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
  host.innerHTML = runs.map(k => {
    const c = counts[k], R = D.recv.runs[k];
    let g = '';
    for (let t = 0; t <= top; t += top / 4) g += `<line x1="${L0}" x2="${W}" y1="${y(t)}" y2="${y(t)}" stroke="var(--line)"/><text x="${L0 - 4}" y="${y(t) + 3}" font-size="10.5" text-anchor="end" fill="var(--text-muted)">${t}</text>`;
    c.forEach((b, i) => {
      const x = L0 + i * bw + 2, w = bw - 4, bs = b.slice().sort((p, q) => q[4] - p[4]);
      const tip = `${i * 10}-${(i + 1) * 10}% new: ${b.length} school${b.length === 1 ? '' : 's'}${bs.length ? '\n' + bs.map(p => `${rcvName(p[0])}: ${p[2]} of ${p[3]} new${p[5] ? ' (additional school affected)' : ''}`).join('\n') : ''}`;
      g += `<rect x="${x}" y="${y(b.length)}" width="${w}" height="${Math.max(H - y(b.length), .5)}" fill="var(--text-secondary)" opacity="${i >= 2 ? .85 : .3}" tabindex="0" aria-label="${esc(tip.split('\n')[0])}"><title>${esc(tip)}</title></rect>`;
      if (b.length) g += `<text x="${x + w / 2}" y="${y(b.length) - 3}" font-size="10.5" text-anchor="middle" fill="var(--text-primary)">${b.length}</text>`;
      g += `<text x="${x + w / 2}" y="${H + 12}" font-size="10.5" text-anchor="middle" fill="var(--text-muted)">${i * 10}-${(i + 1) * 10}</text>`;
    });
    const x3 = L0 + (W - L0) * 2 / NB;   // 20%
    g += `<line x1="${x3}" x2="${x3}" y1="${T0}" y2="${H}" stroke="var(--text-muted)" stroke-dasharray="3 3"/><text x="${x3 + 3}" y="${T0 - 4}" font-size="11" fill="var(--text-muted)">20%</text>` +
      `<text x="${L0 + (W - L0) / 2}" y="${H + 27}" font-size="11" text-anchor="middle" fill="var(--text-muted)">Share of the school's ${D.recv.year} students who are new (%)</text>`;
    return `<div class="rcvh"><div class="hd">${esc(LABEL[k])}${k === sc ? ' <span class="s">(Viewing)</span>' : ''} <span class="s">&middot; Receiving schools: ${R.receivers.length} &middot; Median new: ${pct(med(R.receivers))} &middot; Additional schools affected: ${R.only.length}</span></div>` +
      `<svg viewBox="0 0 ${W} ${H + B0}" role="img" aria-label="${esc(LABEL[k])}: receiving schools by share of new students">${g}</svg></div>`;
  }).join('') + `<div class="cmleg" style="grid-column:1/-1">Number of receiving schools in each band: <span class="sw" style="background:var(--text-secondary);opacity:.85"></span>20% or more new <span class="sw" style="background:var(--text-secondary);opacity:.3"></span>Under 20%. Dashed line: 20%, the summary card's threshold. Hover a bar for its schools.</div>`;
  const R = D.recv.runs[sc];
  document.getElementById('recvsub').innerHTML = `Schools that take in students from another school under PPS's model (closing schools' areas and programs, boundary changes, K-8s becoming K-5), by the share of their students who are new once both waves of changes are in place: most changes in ${D.recv.waves[0]}, and Sellwood's and Marysville's students in ${D.recv.waves[1]}, each counted from its own enrollment changes and summed. Scenarios A and B side by side${R ? `` : ''}. Hover a bar for its schools.`;
  const F = D.forecast52, fi = F.years.indexOf(D.recv.year || D.impl_year), pps = fi < 0 ? null : Object.values(F.grades).reduce((a, g) => a + g[fi], 0);   // all PPS students (PSU)
  const tot = k => { const r = D.recv.runs[k];
    return `<b>${esc(LABEL[k])}:</b> <b>${f(r.arriving)}</b> students move to ${r.receivers.length} receiving schools: <b>${f(r.arriving_waves[0])}</b> in ${D.recv.waves[0]} and <b>${f(r.arriving_waves[1])}</b> in ${D.recv.waves[1]} (${r.closing_schools[1].map(rcvName).join(' and ')}). That includes about ${f(r.closing_students)} from the schools that close (${f(r.closing_waves[0])} + ${f(r.closing_waves[1])}). The receiving schools together have <b>${f(r.at_receivers)}</b> students after both${pps ? ` (${Math.round(100 * r.at_receivers / pps)}% of PPS students)` : ''}. <b>${r.only.length}</b> of them are additional schools affected, taking in students with no closure, boundary, grade or program change of their own: ${r.only.map(rcvName).join(', ')}.`; };
  document.getElementById('recvnote').innerHTML = runs.map(tot).join('<br>') + `<br>Students moving, ${D.recv.waves[0]}: each receiving school's increase over its Status Quo projection by grade and student group in PPS's ${D.recv.waves[0]} results (a school that gains and loses students in the same grade counts only its net gain, so this is a floor). ${D.recv.waves[1]}: PPS's move rules that take effect in 2028 times the students they move (PPS's ${D.recv.waves[1]} Status Quo projection by group and grade). The two are summed. High-school boundary changes phase in with new 9th graders, so few high-school students move at first. Closing schools: their Status Quo enrollment in the year they close. Source: ${esc(D.recv.source)}.`;
  const keys = [...new Set(runs.flatMap(k => D.recv.runs[k].receivers.map(p => p[0])))].sort((a, b) => rcvName(a).localeCompare(rcvName(b)));
  document.getElementById('recvtable').innerHTML = `<table style="min-width:0"><thead><tr><th style="text-align:left">School</th>${runs.map(k => `<th>${esc(LABEL[k])}<br><span style="font-weight:400">new of total (share)</span></th>`).join('')}</tr></thead><tbody>` +
    keys.map(x => `<tr><td style="text-align:left">${esc(rcvName(x))}</td>${runs.map(k => { const p = D.recv.runs[k].receivers.find(q => q[0] === x);
      return `<td style="text-align:right">${p ? `${p[2]} of ${p[3]} (${pct(p[4])})${p[5] ? ' <span class="muted">additional</span>' : ''}` : '<span class="muted">&ndash;</span>'}</td>`; }).join('')}</tr>`).join('') + '</tbody></table>';
}
function renderAll() {""")
    rep("renderMap(); renderEndpoints(); renderRoom();", "renderMap(); renderEndpoints(); renderRecv(); renderRoom();")
if "['recv', 'recvhists']" not in html:
    rep("['room', 'roomkpis'], ['pfasum', 'pfasum']];", "['room', 'roomkpis'], ['pfasum', 'pfasum'], ['recv', 'recvhists']];")
    rep("renderMap = stableLayout(renderMap, 'legend', ['mapsub', 'legend']);", "renderMap = stableLayout(renderMap, 'legend', ['mapsub', 'legend']);\nrenderRecv = stableLayout(renderRecv, 'recvhists', ['recvsub', 'recvnote']);   // patch_receiving")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
