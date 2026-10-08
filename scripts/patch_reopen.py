"""Custom scenarios: allow keeping open a school that the starting scenario (A or B) closes.

A reopen action gives the school back its Status Quo projection from the implementation year
and takes those students back out of the schools that received them in the starting scenario:
PPS's published shares where given; otherwise immersion receivers take the school's 2025-26
DLI share (pps-data pps_schools.csv), K-8 grade-band receivers take the K-5 / 6-8 share, and
the remaining neighborhood students come back evenly from the neighborhood receivers.
Deaf and Hard of Hearing program moves are left in place (no size published).
Safe to rerun: the data is refreshed, the page code is only added once.
"""
import csv, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
SCHOOLS = os.path.join(ROOT, 'source', 'pps-data', 'data', 'pps_schools.csv')
NEWLINE = '\r\n'   # the page is kept with CRLF line endings
html = open(PAGE, encoding='utf-8').read()

# ---------- data: DLI share per school ----------
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
rows = {r['school_name'].strip(): r for r in csv.DictReader(open(SCHOOLS, encoding='utf-8'))}
D['dli'] = {}
for s in D['schools']:
    v = rows.get(s['name'].strip(), {}).get('pct_dli_2526')
    if v: D['dli'][s['key']] = round(float(v), 4)
print('DLI share for', len(D['dli']), 'schools')
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function applyReopen' not in html:
    # ---------- model ----------
    rep("""function applyAction(st, a) {
  const x = a.k, t = st.typ[x];
  if (st.closed.has(x)) return false;""",
"""// share of a closing school's students that went to each of its receivers in the starting scenario, for year index yi
function reopenWeights(x, base, yi) {
  const rs = D.flows[base].receivers.filter(r => r.from_key === x && byKey[r.to_key]);
  const t = D.types.SQ[x], k5 = D.k5_share[CY[yi]];
  const w = rs.map(r => r.share != null ? r.share : /immersion/i.test(r.group) ? (D.dli[x] || 0) : /Hearing/i.test(r.group) ? 0
    : t === 'K8' && /K-5/.test(r.group) ? k5 : t === 'K8' && /middle|6-8/i.test(r.group) ? 1 - k5 : null);
  const fixed = w.reduce((a, v) => a + (v || 0), 0), nb = w.filter(v => v === null).length;
  return rs.map((r, i) => ({ to: r.to_key, w: w[i] !== null ? w[i] : Math.max(0, 1 - fixed) / nb }));
}
function applyReopen(st, a) {
  const x = a.k, base = custom.base;
  if (base === 'SQ' || !st.closed.has(x) || !D.detail[base][x]?.closed) return false;
  for (let i = IMPL_I; i < CY.length; i++) {
    const v = D.series.SQ[x][i]; if (v == null) continue;
    st.ser[x][i] = v;
    for (const { to, w } of reopenWeights(x, base, i)) if (st.ser[to][i] != null) st.ser[to][i] = Math.max(0, st.ser[to][i] - v * w);
  }
  const ws = reopenWeights(x, base, Y31_I), e31 = D.series.SQ[x][Y31_I] || 0;
  st.typ[x] = D.types.SQ[x];
  st.g[x] = Object.fromEntries(GRP.map(g => [g, D.detail.SQ[x].g[g]]));
  for (const { to, w } of ws) {
    for (const g of GRP) { const src = st.g[x][g]; if (src != null && st.g[to][g] != null) st.g[to][g] = Math.max(0, st.g[to][g] - src * w); }
    if (w > 0) (st.notes[to] ||= []).push(`Custom: no longer receives ${short(byKey[x].name)} students (${short(byKey[x].name)} stays open)`);
  }
  st.moved -= e31 * ws.reduce((a, r) => a + r.w, 0);
  st.closed.delete(x); st.reopened.add(x);
  (st.notes[x] ||= []).push(`Custom: stays open (${LABEL[base]} closes it)`);
  return true;
}
function applyAction(st, a) {
  if (a.reopen) return applyReopen(st, a);
  const x = a.k, t = st.typ[x];
  if (st.closed.has(x)) return false;""")
    rep("const st = { ser: {}, typ: {}, g: {}, closed: new Set(), moved: 0, notes: {}, receivers: [] };",
        "const st = { ser: {}, typ: {}, g: {}, closed: new Set(), reopened: new Set(), moved: 0, notes: {}, receivers: [] };")
    # reopenings first, so a closure added later can send students to a reopened school
    rep("  custom.actions = custom.actions.filter(a => applyAction(st, a));",
        "  custom.actions = [...custom.actions.filter(a => a.reopen), ...custom.actions.filter(a => !a.reopen)].filter(a => applyAction(st, a));")
    rep("""  const customClosed = new Set(custom.actions.map(a => a.k));
  for (const s of D.schools) {
    s.cat.C = customClosed.has(s.key) ? 'closes' : (b === 'SQ' ? (st.notes[s.key] ? 'other' : 'none') : s.cat[b]);
    s.detail.C = [b === 'SQ' ? '' : s.detail[b], ...(st.notes[s.key] || [])].filter(Boolean).join('; ');""",
"""  const customClosed = new Set(custom.actions.filter(a => !a.reopen).map(a => a.k));
  for (const s of D.schools) {
    const ro = st.reopened.has(s.key);
    s.cat.C = customClosed.has(s.key) ? 'closes' : ro ? 'other' : (b === 'SQ' ? (st.notes[s.key] ? 'other' : 'none') : s.cat[b]);
    s.detail.C = [b === 'SQ' || ro ? '' : s.detail[b], ...(st.notes[s.key] || [])].filter(Boolean).join('; ');""")
    rep("D.flows.C = { receivers: [...(b === 'SQ' ? [] : D.flows[b].receivers), ...st.receivers],",
        "D.flows.C = { receivers: [...(b === 'SQ' ? [] : D.flows[b].receivers.filter(r => !st.reopened.has(r.from_key))), ...st.receivers],")

    # ---------- link encoding: [index, 'r'] for a reopen ----------
    rep("a: custom.actions.map(a => [SIDX[a.k], a.parts.map(",
        "a: custom.actions.map(a => a.reopen ? [SIDX[a.k], 'r'] : [SIDX[a.k], a.parts.map(")
    rep("actions: (o.a || []).map(([i, parts]) => ({ k: D.schools[i].key, parts:",
        "actions: (o.a || []).map(([i, parts]) => parts === 'r' ? { k: D.schools[i].key, reopen: true } : ({ k: D.schools[i].key, parts:")

    # ---------- right-click menu ----------
    rep("""  if (custom.actions.some(a => a.k === s.key)) {
    return head + `<h4>Custom scenario</h4><button class="cm-btn" data-act="reopen" data-k="${s.key}">Reopen ${esc(short(s.name))} (undo this closure)</button></div>`;
  }
  if (st.closed.has(s.key)) return head + `<div class="row cmnote">Already closed in ${LABEL[custom.actions.length ? custom.base : viewBase]}.</div></div>`;""",
"""  const mine = custom.actions.find(a => a.k === s.key);
  if (mine) {
    return head + `<h4>Custom scenario</h4><button class="cm-btn" data-act="reopen" data-k="${s.key}">${mine.reopen ? `Close ${esc(short(s.name))} again (as in ${LABEL[custom.base]})` : `Reopen ${esc(short(s.name))} (undo this closure)`}</button></div>`;
  }
  const b0 = custom.actions.length ? custom.base : viewBase;
  if (st.closed.has(s.key)) {
    if (b0 === 'SQ' || !D.detail[b0][s.key]?.closed) return head + `<div class="row cmnote">Already closed in ${LABEL[b0]}.</div></div>`;
    const back = reopenWeights(s.key, b0, Y31_I).filter(r => r.w > 0).map(r => `${short(byKey[r.to].name)} (${Math.round(100 * r.w)}%)`).join(', ');
    return head + working + `<h4>${LABEL[b0]} closes this school</h4><button class="cm-btn" data-act="keep" data-k="${s.key}">Keep ${esc(short(s.name))} open<span>Its Status Quo enrollment returns from ${D.impl_year}, taken back from ${esc(back || 'its receiving schools')}.</span></button>` +
      `<div class="row cmnote">Shares: PPS's published split where given, otherwise the school's immersion share and an even split of neighborhood students. Program moves are unchanged.</div></div>`;
  }""")
    rep("""    if (btn.dataset.act === 'reopen') custom.actions = custom.actions.filter(a => a.k !== k);
    else {""",
"""    if (btn.dataset.act === 'reopen') custom.actions = custom.actions.filter(a => a.k !== k);
    else if (btn.dataset.act === 'keep') custom.actions.push({ k, reopen: true });
    else {""")

    # ---------- custom panel list and sliders ----------
    rep("const sliders = (a, i) => a.parts.map(",
        "const sliders = (a, i) => a.reopen ? '' : a.parts.map(")
    rep("h += nA ? `<ol class=\"cplist\">${custom.actions.map((a, i) => `<li><b>${esc(short(byKey[a.k].name))}</b> closes &rarr; ${a.parts.map(",
        "h += nA ? `<ol class=\"cplist\">${custom.actions.map((a, i) => `<li><b>${esc(short(byKey[a.k].name))}</b> ${a.reopen ? `stays open (${LABEL[custom.base]} closes it)` : `closes &rarr; ${a.parts.map(")
    rep(".join(' + ')).join('; ')} <button class=\"cp-del\" data-i=\"${i}\"",
        ".join(' + ')).join('; ')}`} <button class=\"cp-del\" data-i=\"${i}\"")
    rep("Right-click (or long-press) any PPS school on the map to close it and move its students to the nearest open PPS school(s) for the same grades in its region.",
        "Right-click (or long-press) any PPS school on the map to close it and move its students to the nearest open PPS school(s) for the same grades in its region, or, starting from Scenario A or B, to keep open a school that scenario closes.")

    # ---------- headline ----------
    rep("`${custom.name ? custom.name + ': ' : ''}${LABEL[custom.base]} plus ${custom.actions.length} custom closure${custom.actions.length === 1 ? '' : 's'} (this page's model).`;",
        "`${custom.name ? custom.name + ': ' : ''}${LABEL[custom.base]}${((c, r) => [c ? ` plus ${c} custom closure${c === 1 ? '' : 's'}` : '', r ? `${c ? ',' : ''} with ${r} of its closures kept open` : ''].join('') || ' with no changes')(custom.actions.filter(a => !a.reopen).length, custom.actions.filter(a => a.reopen).length)} (this page's model).`;")

    # ---------- method note ----------
    rep("  'Custom scenario: right-click (or long-press) a school to close it.",
        "  'Custom scenario, keeping a school open: starting from Scenario A or B, right-click a school that scenario closes to keep it open. It gets back its Status Quo projection from ' + D.impl_year + ', and those students come back out of its receiving schools: PPS\\'s published split where given; otherwise the immersion receiver takes the school\\'s 2025-26 dual-language share, a K-8\\'s K-5 and 6-8 receivers take the district K-5 share, and the rest come back evenly from the neighborhood receivers. Deaf and Hard of Hearing program moves and other program and grade moves are left as the scenario has them.',\n  'Custom scenario: right-click (or long-press) a school to close it.")

open(PAGE, 'w', encoding='utf-8', newline=NEWLINE).write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
