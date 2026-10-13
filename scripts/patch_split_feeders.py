"""Split feeders: a card after "Projected enrollment by school" with summary cards and a table of the schools whose
neighborhood students go on to more than one next school (an elementary or K-8 school feeding two middle or high
schools, a middle school feeding two high schools), under Status Quo and under the scenario being viewed.
Feeder patterns: D.feeders (a custom scenario uses its base scenario's, less the schools it closes). Program pathways
(immersion) are left out: they send students on by program by design. Pathway shares at a split middle school are
estimated from the projected enrollment of the elementary schools feeding each pathway in the chosen year (D.series);
an elementary school split by address within its area has no published share. "Students on a smaller pathway" =
the school's projected students times the shares of its pathways other than the largest. The school year menu starts
when the scenarios take effect. Also adds the feeder-arrow layer to the map's Link (mly 'fd'). Code added once.
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

if 'renderSplitFeeders' not in html:
    rep("""  <section class="card">
    <h2>Private school share of PPS-area students</h2>""",
        """  <section class="card">
    <h2>Split feeders: schools whose students go on to different schools</h2>
    <p class="sub">A split feeder sends its neighborhood students on to more than one next school: an elementary or K-8 school whose area feeds two middle (or high) schools, or a middle school whose students go on to two high schools. Classmates are separated at the next step, and the receiving schools draw from partial cohorts. This compares PPS's feeder patterns under Status Quo with the selected scenario's (a custom scenario uses its base scenario's patterns, less the schools it closes). Immersion and other program pathways are left out: they send students on by program by design. <b>Pathway shares</b> at a split middle school are estimated from the projected enrollment of the elementary schools feeding each pathway; an elementary school split by address within its area has no published share. <b>Students on a smaller pathway</b> are the school's projected students times the shares of its pathways other than the largest: students who go on to a different school than most of their classmates.</p>
    <div class="controls"><label>School year <select id="sf-year"></select></label></div>
    <div class="kpis" id="sfkpis"></div>
    <div class="tablewrap" id="sftable"></div>
  </section>

  <section class="card">
    <h2>Private school share of PPS-area students</h2>""")
    rep("""function renderAll() {""", """// ---------- split feeders (scripts/patch_split_feeders.py) ----------
let sfYear = '2031-32';
function sfSplits(sc, yi) {   // {school: {lvl, paths: [[to, share | null]], enr}}
  const base = sc === 'C' ? custom.base : sc, shut = k => sc !== 'SQ' && (D.detail[sc] || {})[k]?.closed;
  const F = ((D.feeders || {})[base] || D.feeders?.SQ || []).filter(r => (!r[3] || /^neighborhood$/i.test(r[3])) && ![r[0], r[1], r[2]].some(x => x && shut(x)));
  const nxt = {}, ms = {};
  for (const [es, m, hs] of F) {
    if (es && (m || hs) && es !== (m || hs)) (nxt[es] = nxt[es] || new Set()).add(m || hs);
    if (m && hs && m !== hs) (ms[m] = ms[m] || new Map()).set(hs, 0);
  }
  const ser = k => D.series[sc]?.[k]?.[yi] || 0, out = {};
  for (const [k, s] of Object.entries(nxt)) if (s.size > 1) out[k] = { lvl: 'ES', paths: [...s].sort().map(t => [t, null]), enr: ser(k) };
  for (const [m, h] of Object.entries(ms)) {
    if (h.size < 2) continue;
    for (const [es, m2, hs] of F) if (m2 === m && es && hs) h.set(hs, h.get(hs) + ser(es) / (nxt[es]?.size || 1));
    const tot = [...h.values()].reduce((a, v) => a + v, 0);
    out[m] = { lvl: 'MS', paths: [...h].sort((a, b) => b[1] - a[1]).map(([t, w]) => [t, tot ? w / tot : null]), enr: ser(m) };
  }
  for (const v of Object.values(out)) { const sh = v.paths.map(p => p[1]); v.minor = sh.every(x => x != null) ? v.enr * (1 - Math.max(...sh)) : null; }
  return out;
}
function renderSplitFeeders() {
  const host = document.getElementById('sftable'), kp = document.getElementById('sfkpis'); if (!host || !D.feeders) return;
  const yrs = D.years.slice(Math.max(0, D.years.indexOf(D.impl_year)));
  if (!yrs.includes(sfYear)) sfYear = yrs.includes('2031-32') ? '2031-32' : yrs[0];
  const sel = document.getElementById('sf-year');
  if (sel) { sel.innerHTML = yrs.map(y => `<option${y === sfYear ? ' selected' : ''}>${y}</option>`).join(''); sel.onchange = () => { sfYear = sel.value; renderSplitFeeders(); }; }
  const yi = D.years.indexOf(sfYear), isSQ = scen === 'SQ', S0 = sfSplits('SQ', yi), S1 = isSQ ? S0 : sfSplits(scen, yi);
  const nm = k => esc(short(byKey[k]?.name || k)), n0 = v => Math.round(v).toLocaleString();
  const sum = (S, f) => Object.values(S).reduce((a, v) => a + (f(v) || 0), 0);
  const unk = S => Object.values(S).some(v => v.minor == null);
  const dl = (c, q, lowGood = true) => { const d = Math.round(c - q); return isSQ || !d ? '' : `<span class="d" style="color:${(d > 0) === lowGood ? 'var(--down)' : 'var(--up)'}">${d > 0 ? '+' : '&minus;'}${Math.abs(d).toLocaleString()} vs SQ</span>`; };
  const keys = [...new Set([...Object.keys(S0), ...Object.keys(S1)])];
  const status = k => isSQ ? 'split' : S0[k] && S1[k] ? 'still' : S0[k] ? ((D.detail[scen] || {})[k]?.closed ? 'closes' : 'resolved') : 'new';
  const ST = { split: ['Split', 'var(--text-secondary)'], still: ['Still split', 'var(--down)'], new: ['New split', 'var(--down)'], resolved: ['Resolved', 'var(--up)'], closes: ['School closes', 'var(--text-secondary)'] };
  const cnt = s => keys.filter(k => status(k) === s).length;
  const lab = isSQ ? 'Status Quo' : esc(LABEL[scen]);
  kp.innerHTML = `<div class="kpi"><div class="v">${Object.keys(S1).length}${dl(Object.keys(S1).length, Object.keys(S0).length)}</div><div class="l">Split-feeder schools, ${lab}</div>` +
      `<div class="s">${isSQ ? `${Object.values(S0).filter(v => v.lvl === 'MS').length} middle schools feeding two high schools; ${Object.values(S0).filter(v => v.lvl === 'ES').length} elementary or K-8 feeding two next schools` : `<b>${cnt('resolved') + cnt('closes')}</b> resolved${cnt('closes') ? ` (${cnt('closes')} by closing)` : ''} &middot; <b>${cnt('still')}</b> still split &middot; <b>${cnt('new')}</b> new`}</div></div>` +
    `<div class="kpi"><div class="v">${n0(sum(S1, v => v.enr))}${dl(sum(S1, v => v.enr), sum(S0, v => v.enr))}</div><div class="l">Students at split-feeder schools, ${sfYear} (projected)</div>` +
      `<div class="s">${isSQ ? '' : `Status Quo: <b>${n0(sum(S0, v => v.enr))}</b>`}</div></div>` +
    `<div class="kpi"><div class="v">${n0(sum(S1, v => v.minor))}${dl(sum(S1, v => v.minor), sum(S0, v => v.minor))}</div><div class="l">Students on a smaller pathway, ${sfYear} (est.)</div>` +
      `<div class="s">Go on to a different school than most of their classmates${isSQ ? '' : `; Status Quo <b>${n0(sum(S0, v => v.minor))}</b>`}${unk(S0) || unk(S1) ? '; excludes elementary splits with no published share' : ''}</div></div>`;
  const order = { new: 0, still: 1, split: 1, resolved: 2, closes: 3 };
  keys.sort((a, b) => order[status(a)] - order[status(b)] || ((S1[a] || S0[a]).lvl === 'MS') - ((S1[b] || S0[b]).lvl === 'MS') || short(byKey[a]?.name || a).localeCompare(short(byKey[b]?.name || b)));
  const paths = v => v ? v.paths.map(([t, s]) => `${nm(t)}${s != null ? ` <span class="muted">${Math.round(100 * s)}%</span>` : ''}`).join('<br>') : '<span class="muted">&mdash;</span>';
  const typ = k => TYPE_LABEL[(D.types[scen === 'C' ? custom.base : scen] || {})[k] || D.types.SQ[k]] || '';
  const enrC = (v, q) => v ? `${n0(v.enr)}${q && !isSQ ? ` <span class="muted" style="display:block;font-size:11px">SQ ${n0(q.enr)}</span>` : ''}` : '<span class="muted">&mdash;</span>';
  const minC = v => !v ? '<span class="muted">&mdash;</span>' : v.minor == null ? '<span class="muted" title="Split by address within the school\\u2019s area; PPS publishes no share">not known</span>' : n0(v.minor);
  let h = `<table style="min-width:640px"><thead><tr><th style="text-align:left">School</th><th style="text-align:left">Status Quo pathways</th>${isSQ ? '' : `<th style="text-align:left">${lab} pathways</th><th style="text-align:left">Change</th>`}` +
    `<th>Students, ${sfYear}</th><th>On a smaller pathway</th></tr></thead><tbody>`;
  for (const k of keys) {
    const st = status(k), v = S1[k], q = S0[k], show = isSQ ? q : v;
    h += `<tr><td style="text-align:left"><b>${nm(k)}</b> <span class="muted">${esc(typ(k))}${D.region_of[k] ? ' &middot; ' + esc(D.region_of[k]) : ''}</span></td><td style="text-align:left">${paths(q)}</td>` +
      (isSQ ? '' : `<td style="text-align:left">${st === 'resolved' ? (() => { const one = sfOne(k); return one ? `${nm(one)} <span class="muted">(all)</span>` : '<span class="muted">one pathway</span>'; })() : st === 'closes' ? '<span class="muted">closes</span>' : paths(v)}</td>` +
        `<td style="text-align:left"><span style="color:${ST[st][1]};font-weight:600">${ST[st][0]}</span></td>`) +
      `<td style="text-align:right">${st === 'closes' ? '<span class="muted">&mdash;</span>' : enrC(show || { enr: D.series[scen]?.[k]?.[yi] || 0 }, q)}</td><td style="text-align:right">${minC(show)}</td></tr>`;
  }
  if (!keys.length) h += `<tr><td colspan="6" class="muted">No split feeders.</td></tr>`;
  host.innerHTML = h + '</tbody></table>';
}
// a resolved split: the one school its neighborhood students now go on to
function sfOne(k) {
  const base = scen === 'C' ? custom.base : scen, F = ((D.feeders || {})[base] || []).filter(r => !r[3] || /^neighborhood$/i.test(r[3]));
  const t = new Set(); for (const [es, m, hs] of F) { if (es === k && (m || hs)) t.add(m || hs); if (m === k && hs) t.add(hs); }
  return t.size === 1 ? [...t][0] : null;
}
function renderAll() {""")
    rep("""renderLines(); renderClassSizes();""", """renderLines(); renderSplitFeeders(); renderClassSizes();""")
    rep("""['map', 'map'], ['gfper', 'gfper'], ['gfclose', 'gfclose'], ['hstrends', 'hsdistrict']];""",
        """['map', 'map'], ['gfper', 'gfper'], ['gfclose', 'gfclose'], ['hstrends', 'hsdistrict'], ['splitfeed', 'sftable']];""")
    rep("""  if (key === 'classsize') p.set('csy', csYear);""",
        """  if (key === 'classsize') p.set('csy', csYear);
  if (key === 'splitfeed') p.set('sfy', sfYear);""")
    rep("""  if (D.years.includes(q.get('csy'))) csYear = q.get('csy');""",
        """  if (D.years.includes(q.get('csy'))) csYear = q.get('csy');
  if (D.years.includes(q.get('sfy'))) sfYear = q.get('sfy');""")
    # map link carries the feeder-arrow layer
    rep("""mlHz ? 'h' : '', showFlows ? 'f' : ''].filter(Boolean)""", """mlHz ? 'h' : '', showFlows ? 'f' : '', mlFeed ? 'fd' : ''].filter(Boolean)""")
    rep("""mlHz = f.includes('h'); showFlows = f.includes('f'); }""", """mlHz = f.includes('h'); showFlows = f.includes('f'); mlFeed = f.includes('fd'); }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
