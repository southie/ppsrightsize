"""Census boundary adjustment: a checkbox beside the scenario buttons (on by default) that adds the attendance-area
changes the enrollment model leaves out (source/block-access/boundary-adjust.json, scripts/build_boundary_adjust.py)
to Scenarios A and B, and so to Custom scenarios built on them. With it on, each move takes the estimated share of the
sending school's Status Quo neighborhood students in that grade band (from 2027-28) and gives them to the receiving
school, with the sending school's student-group rates; every chart and table reading D.series / D.detail follows. PPS's
published measures (region table, district cards) get the change the adjustment makes to this page's own measures
added on top; those cells and the adjusted schools are marked, with a hover tip pointing to the checkbox. Also sorts
school rows alphabetically (no longer closed schools first), so tables keep their order when switching scenarios.
Runs after the other patches. Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
A = json.load(open(os.path.join(ROOT, 'source', 'block-access', 'boundary-adjust.json'), encoding='utf-8'))
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['adjust'] = {sc: [[x['frm'], x['to'], x['band'], x['share']] for x in v] for sc, v in A['moves'].items()}
NOTE = ("Census boundary adjustment (part of the \"Modified enrollment model\" checkbox beside the scenario buttons, on by default): for the attendance-area changes "
        "the enrollment model leaves out (Duniway's southern area to Llewellyn, part of Whitman to Lewis in B, part of Kellogg's "
        "6-8 area to Harrison Park, part of Hayhurst to Rieke, and small high-school edits), the share of the sending school's area "
        "residents of those ages who live in the moved area (2020 Census blocks) is applied to its Status Quo neighborhood students "
        "(excluding immersion), from 2027-28. PPS's published measures shown with it on add the change this makes to this page's "
        "own measures; marked cells differ from PPS's published figures.")
if not any(a.startswith('Census boundary adjustment') for a in D['assumptions']): D['assumptions'].append(NOTE)
else: D['assumptions'] = [NOTE if a.startswith('Census boundary adjustment') else a for a in D['assumptions']]
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function applyAdjust' not in html:
    # checkbox beside the scenario buttons
    rep('<div class="bar"><div class="seg" id="seg"></div><span class="desc" id="desc"></span></div>',
        '<div class="bar"><div class="seg" id="seg"></div><label class="adjtog" id="adjtogl" title="Adds the attendance-area changes PPS drew but this page&#39;s enrollment model does not move (such as Duniway&#39;s southern area to Llewellyn), estimated from 2020 Census residents. Marked figures differ from PPS&#39;s published values."><input type="checkbox" id="adjtog"> Census boundary adjustment</label><span class="desc" id="desc"></span></div>')
    rep('.seg button[aria-pressed="true"] { background: #1c3557; color: #fff; }',
        '.seg button[aria-pressed="true"] { background: #1c3557; color: #fff; }\n'
        '.adjtog { display: inline-flex; align-items: center; gap: 6px; margin-left: 10px; padding: 5px 11px; border: 1px dashed var(--adj); border-radius: 999px; font-size: 13px; cursor: pointer; background: var(--surface-1); }\n'
        '.adjtog.na { opacity: .55; } .adjtog input { margin: 0; accent-color: var(--adj); }\n'
        '.adjd { box-shadow: inset 0 -3px 0 var(--adj); background: color-mix(in srgb, var(--adj) 10%, transparent); cursor: help; }\n'
        '.kpi.adjd { box-shadow: inset 0 -3px 0 var(--adj); }\n'
        '.adjm { color: var(--adj); font-size: 11px; margin-left: 4px; cursor: help; vertical-align: 1px; }\n'
        ':root { --adj: #c27c0e; }\n'
        '@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --adj: #f0b44c; } }\n'
        ':root[data-theme="dark"] { --adj: #f0b44c; }')
    # the adjustment itself, applied before any custom scenario is built
    rep("// ---------- link + persistence ----------", r"""// ---------- Census boundary adjustment (D.adjust, scripts/build_boundary_adjust.py) ----------
// Attendance-area changes PPS drew that the enrollment model does not move. Each entry: [from, to, band, share], share =
// band-age residents in the moved area / all band-age residents in the from-school's Status Quo area (2020 Census).
const clone = o => JSON.parse(JSON.stringify(o));
const ADJ_BASE = { series: {}, detail: {}, e2031: {}, recv: {}, endpoints: clone(D.endpoints), recreated: clone(D.recreated) };
for (const sc of ['A', 'B']) {
  ADJ_BASE.series[sc] = clone(D.series[sc]); ADJ_BASE.detail[sc] = clone(D.detail[sc]);
  ADJ_BASE.e2031[sc] = Object.fromEntries(D.schools.map(s => [s.key, s.e2031[sc]])); ADJ_BASE.recv[sc] = D.flows[sc].receivers.slice();
}
let adjOn = true;
try { adjOn = localStorage.getItem('rsAdj') !== '0'; } catch (e) {}
const ADJ = { moves: {}, diff: {} };   // per scenario: moves with 2031-32 students; per region and scenario: measures that differ from PPS's
const ADJ_BL = { k5: 'K-5', '68': '6-8', '912': '9-12' };
const ADJ_OFF = 'Uncheck "Census boundary adjustment" beside the scenario buttons to see the figures without it.';
function applyAdjust(on) {
  adjOn = on;
  for (const sc of ['A', 'B']) {
    D.series[sc] = clone(ADJ_BASE.series[sc]); D.detail[sc] = clone(ADJ_BASE.detail[sc]);
    for (const s of D.schools) s.e2031[sc] = ADJ_BASE.e2031[sc][s.key];
    D.flows[sc].receivers = ADJ_BASE.recv[sc].slice();
    ADJ.moves[sc] = [];
  }
  D.endpoints = clone(ADJ_BASE.endpoints); D.recreated = clone(ADJ_BASE.recreated); ADJ.diff = {};
  if (!on) return;
  const sqTot = Object.keys(D.detail.SQ).reduce((a, n) => a + D.detail.SQ[n].e, 0);
  for (const sc of ['A', 'B']) {
    const ser = D.series[sc], det = D.detail[sc], touched = new Set();
    for (const [f, t, band, share] of D.adjust[sc] || []) {
      if (!ser[f] || !ser[t] || det[f].closed || det[t].closed) continue;
      const nb = 1 - (D.dli[f] || 0), amt = CY.map((_, i) => {
        if (i < IMPL_I || ser[f][i] == null || ser[t][i] == null) return 0;
        const fr = D.types.SQ[f] !== 'K8' ? 1 : band === 'k5' ? D.k5_share[CY[i]] : band === '68' ? 1 - D.k5_share[CY[i]] : 0;
        const v = Math.min(Math.round((D.series.SQ[f][i] || 0) * fr * nb * share), ser[f][i]);
        ser[f][i] -= v; ser[t][i] += v; return v;
      });
      const n31 = amt[Y31_I]; if (!n31) continue;
      const src = D.detail.SQ[f], k = src.e ? n31 / src.e : 0;
      for (const g of GRP) if (src.g[g] != null) {
        if (det[f].g[g] != null) det[f].g[g] = Math.max(0, det[f].g[g] - src.g[g] * k);
        if (det[t].g[g] != null) det[t].g[g] += src.g[g] * k;
      }
      touched.add(f); touched.add(t);
      ADJ.moves[sc].push({ f, t, band, n: n31 });
      D.flows[sc].receivers.push({ from: byKey[f].name, to: byKey[t].name, from_key: f, to_key: t, share: null, group: `${ADJ_BL[band]} boundary change (Census estimate)`, adj: true });
    }
    for (const n of touched) {
      const d = det[n], e = ser[n][Y31_I];
      d.e = e; d.above = e >= d.thr - 1e-9; d.util = d.fc ? rndh(100 * e / d.fc) : null;
      for (const g of GRP) if (d.g[g] != null) d.g[g] = rndh(d.g[g]);
      byKey[n].e2031[sc] = e;
    }
    // PPS's published measures plus the change the adjustment makes to this page's own measures
    for (const rn of [...D.region_order, 'District']) {
      const names = Object.keys(D.region_of).filter(n => rn === 'District' || D.region_of[n] === rn);
      const b0 = metricsOf(ADJ_BASE.detail[sc], names), b1 = metricsOf(det, names), E = D.endpoints[rn][sc], R = D.recreated[sc]?.[rn];
      for (const k of ['schools_above', 'students_above', ...GRP]) {
        const d = (b1[k] ?? 0) - (b0[k] ?? 0); if (!d) continue;
        ((ADJ.diff[rn] ||= {})[sc] ||= {})[k] = { pub: E[k], d };
        E[k] += d; if (R && R[k] != null) R[k] += d;
      }
    }
    const moved = ADJ.moves[sc].reduce((a, x) => a + x.n, 0), E = D.endpoints.District[sc], ch = rndh(E.change + 100 * moved / sqTot) - E.change;
    if (ch) { ((ADJ.diff.District ||= {})[sc] ||= {}).change = { pub: E.change, d: ch }; E.change += ch; }
  }
}
// which scenario's adjustment a view shows (a custom scenario inherits its starting scenario's)
const adjScen = sc => adjOn ? (sc === 'C' ? (custom.base === 'SQ' ? null : custom.base) : sc === 'SQ' ? null : sc) : null;
const adjMoveTxt = x => `${short(byKey[x.f].name)} → ${short(byKey[x.t].name)}: ${x.n} ${ADJ_BL[x.band]} students`;
// hover text for a PPS-published measure that the adjustment changed ('' if unchanged)
function adjTip(rn, sc, k, unit = '%') {
  const a = ADJ.diff[rn]?.[sc]?.[k]; if (!a) return '';
  const mv = ADJ.moves[sc].filter(x => rn === 'District' || D.region_of[x.f] === rn || D.region_of[x.t] === rn);
  return `PPS published ${a.pub}${unit}; shown ${a.pub + a.d}${unit} (${a.d > 0 ? '+' : '−'}${Math.abs(a.d)}) with this page's Census estimate of boundary changes PPS drew but its enrollment figures may not move` +
    (mv.length ? ` (2031-32: ${mv.slice(0, 6).map(adjMoveTxt).join('; ')}${mv.length > 6 ? '; …' : ''})` : '') + `. ${ADJ_OFF}`;
}
// marker beside a school whose enrollment the adjustment changed in this view
function adjMark(k, sc = scen) {
  const s = adjScen(sc); if (!s) return '';
  const mv = ADJ.moves[s].filter(x => x.f === k || x.t === k); if (!mv.length) return '';
  const t = `Census boundary adjustment, 2031-32: ${mv.map(x => x.f === k ? `${x.n} ${ADJ_BL[x.band]} students move to ${short(byKey[x.t].name)}` : `${x.n} ${ADJ_BL[x.band]} students arrive from ${short(byKey[x.f].name)}`).join('; ')} (estimated from 2020 Census residents of the redrawn area). This differs from the enrollment behind PPS's published figures. ${ADJ_OFF}`;
  return `<span class="adjm" title="${esc(t)}" aria-label="Census boundary adjustment">&#9670;</span>`;
}
applyAdjust(adjOn);
const adjBox = document.getElementById('adjtog');
adjBox.checked = adjOn;
adjBox.onchange = () => { try { localStorage.setItem('rsAdj', adjBox.checked ? '1' : '0'); } catch (e) {} applyAdjust(adjBox.checked); if (CS || scen === 'C') buildCustom(); renderAll(); };

// ---------- link + persistence ----------""")
    # checkbox state shown with the scenario buttons (no effect under Status Quo)
    rep("  for (const b of seg.querySelectorAll('button')) b.setAttribute('aria-pressed', b.dataset.s === scen ? 'true' : 'false');",
        "  for (const b of seg.querySelectorAll('button')) b.setAttribute('aria-pressed', b.dataset.s === scen ? 'true' : 'false');\n"
        "  document.getElementById('adjtogl')?.classList?.toggle('na', (scen === 'C' ? custom.base : scen) === 'SQ');   // no effect under Status Quo")
    # district cards: mark measures that differ from PPS's published values
    rep("""    return `<div class="kpi"><div class="v">${cur[k]}${u}${dt}</div><div class="l">District, 2031-32: ${l}</div></div>`;""",
        """    const at = scen === 'A' || scen === 'B' ? adjTip('District', scen, k) : '';
    return `<div class="kpi${at ? ' adjd' : ''}"${at ? ` data-adjtip="${esc(at)}"` : ''}><div class="v">${cur[k]}${u}${dt}${at ? `<span class="adjm" title="${esc(at)}">&#9670;</span>` : ''}</div><div class="l">District, 2031-32: ${l}</div></div>`;""")
    # region table: measures and the district change cell
    rep("""      h += `<td>${cell}</td>`;
    }
    const names = Object.keys(D.region_of)""", """      const at = scen === 'A' || scen === 'B' ? adjTip(rn, scen, m.key) : '';
      h += `<td${at ? ` class="adjd" title="${esc(at)}"` : ''}>${cell}${at ? '<span class="adjm">&#9670;</span>' : ''}</td>`;
    }
    const names = Object.keys(D.region_of)""")
    rep("""    h += `<td>${rn === 'District' ? `<span class="main">${cur.change}%</span>` : '<span class="rec" style="display:block">not reported</span>'}</td></tr>`;""",
        """    const atc = rn === 'District' && (scen === 'A' || scen === 'B') ? adjTip('District', scen, 'change') : '';
    h += `<td${atc ? ` class="adjd" title="${esc(atc)}"` : ''}>${rn === 'District' ? `<span class="main">${cur.change}%</span>${atc ? '<span class="adjm">&#9670;</span>' : ''}` : '<span class="rec" style="display:block">not reported</span>'}</td></tr>`;""")
    # region table school rows, staffing, class sizes and the over-capacity list: mark adjusted schools
    rep("""    h += `<tr class="srow"><td><span class="nm">${esc(nm)}</span><span class="ty">${TYPE_LABEL[d.type]}</span>${conv}</td>` +""",
        """    h += `<tr class="srow"><td><span class="nm">${esc(nm)}</span>${adjMark(n)}<span class="ty">${TYPE_LABEL[d.type]}</span>${conv}</td>` +""")
    rep("""        h += `<tr class="srow${b ? '' : ' closed'}"><td><span class="nm">${esc(short(byKey[k].name))}</span><span class="ty">""",
        """        h += `<tr class="srow${b ? '' : ' closed'}"><td><span class="nm">${esc(short(byKey[k].name))}</span>${adjMark(k)}<span class="ty">""")
    rep("""      const nm = `<span class="nm">${esc(short(byKey[k].name))}</span><span class="ty">${TYPE_LABEL[r ? r.t""",
        """      const nm = `<span class="nm">${esc(short(byKey[k].name))}</span>${adjMark(k)}<span class="ty">${TYPE_LABEL[r ? r.t""")
    rep("""    rowsOver.map(r => `<tr><td><b>${esc(short(byKey[r.n].name))}</b>""", """    rowsOver.map(r => `<tr><td><b>${esc(short(byKey[r.n].name))}</b>${adjMark(r.n)}""")
    # alphabetical school order everywhere (stable when switching scenarios)
    rep("""// school rows within a region: closed schools first, then open schools; alphabetical within each
const isClosedRow = k => (byKey[k] ? role(byKey[k], scen) : 'none') === 'closes';
const byStatusName = (a, b) => (isClosedRow(b) - isClosedRow(a)) || short(byKey[a]?.name || a).localeCompare(short(byKey[b]?.name || b));""",
        """// school rows within a region: alphabetical, so rows keep their place when switching scenarios
const byStatusName = (a, b) => short(byKey[a]?.name || a).localeCompare(short(byKey[b]?.name || b));""")
    rep("  }).filter(Boolean).sort((a, b) => b.pk - a.pk);", "  }).filter(Boolean).sort((a, b) => short(byKey[a.n].name).localeCompare(short(byKey[b.n].name)));")
    # the cards' click hint (wireKPIs) would replace the adjustment tip: keep the tip first
    rep("    k.title = t === 'overcap'", "    k.title = (k.dataset.adjtip ? k.dataset.adjtip + ' Click the card: ' : '') + (t === 'overcap'")
    rep("'Show class sizes and teacher loads by grade' : 'Show this in the table by region';", "'Show class sizes and teacher loads by grade' : 'Show this in the table by region');")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
