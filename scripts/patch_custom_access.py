"""Custom scenarios in the getting-to-school table and yellow-bus figures: students moved by a custom closure are
counted where they live (their old school's attendance area), travelling to their new school, using
source/block-access/school-pairs.json (scripts/build_block_access.py: each area's residents to every school in the
region that could take those grades). Also: a school kept open that the starting scenario closes uses its Status Quo
area; moved students whose home area is unknown (from a program school) count as program students; custom closures
prefer neighborhood schools over program schools as receivers; and a negative cost reads as a saving.
Runs after patch_commute / patch_buscost / patch_program_rows / patch_custom_note. Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
PAIRS = os.path.join(ROOT, 'source', 'block-access', 'school-pairs.json')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['commute']['X'] = json.load(open(PAIRS, encoding='utf-8'))['pairs']
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

NEW_AGG = r"""function cmAgg(sc, keys, band) {
  // before the scenarios take effect (D.impl_year) every scenario still has Status Quo's attendance areas
  const pre = D.years.indexOf(cmYear) < D.years.indexOf(D.impl_year);
  const Sc = pre ? 'SQ' : sc === 'C' ? custom.base : sc;
  const S = D.commute.S[Sc] || {}, X = D.commute.X?.[Sc] || {};
  const bands = band === 'all' ? ['k5', '68', '912'] : [band];
  const nb = D.commute.hist_min.length + 1, yi = D.years.indexOf(cmYear);
  const MB = D.buscost?.M?.[Sc] || {}, MBsq = D.buscost?.M?.SQ || {};   // eligible K-8 walking miles per area (bus columns)
  const CM = sc === 'C' && !pre ? CS : null;   // custom: students moved by a closure still live in their old school's area
  const o = { r: 0, beyond: 0, wmi: 0, wmin: 0, bmin: 0, dmin: 0, w15: 0, b15: 0, d15: 0, near: 0, n: 0, bm: 0, bn: 0, pn: 0, pAt: new Set(),
    h: { walk: Array(nb).fill(0), bike: Array(nb).fill(0), drive: Array(nb).fill(0) } };
  // r students living like the residents of an area (v: per-area array; mb: their walking miles beyond bus distance)
  const add = (v, r, mb) => {
    const x = r / v[0];   // students per census resident of the area
    if (mb != null) { o.bm += mb * x; o.bn++; }
    o.n++; o.r += r; o.beyond += r * v[1]; o.wmi += r * v[2]; o.wmin += r * v[3]; o.bmin += r * v[4]; o.dmin += r * v[5];
    o.w15 += r * v[6]; o.b15 += r * v[7]; o.d15 += r * v[8]; o.near += r * v[9];
    ['walk', 'bike', 'drive'].forEach((m, j) => v[10 + j].forEach((y, i) => { o.h[m][i] += y * x; }));
  };
  for (const k of keys) for (const b of bands) {
    let r = cmStu(sc, k, b);
    if (CM) for (const m of CM.moves) {
      if (m.to !== k || m.band !== b) continue;
      const a = m.amt[yi] || 0; if (!a) continue;
      r -= a;
      const pv = X[m.from]?.[b]?.[k];
      if (pv && pv[0]) add(pv, a, b === '912' ? null : pv[13]);
      else { o.pn += a; o.pAt.add(m.from); }   // moved from a school with no area here: home area unknown
    }
    if (r <= 1e-6) continue;
    const kept = CM?.reopened.has(k);   // kept open though the starting scenario closes it: its Status Quo area
    const v = kept ? D.commute.S.SQ[k]?.[b] : S[k]?.[b];
    if (!v || !v[0]) { o.pn += r; o.pAt.add(k); continue; }   // program school: no neighborhood area
    add(v, r, kept ? MBsq[k]?.[b] : MB[k]?.[b]);
  }
  if (o.r) for (const f of ['wmi', 'wmin', 'bmin', 'dmin', 'w15', 'b15', 'd15', 'near']) o[f] /= o.r;
  return o;
}
"""
NEW_PROG = r"""// students in the given grades whose home area is not known (program schools; students moved from them)
function cmProg(sc, keys, band) { const o = cmAgg(sc, keys, band); return { n: o.pn, schools: [...o.pAt] }; }
"""

if 'CS.moves' not in html and 'st.moves' not in html:
    # ---- aggregation: one pass for neighborhood, moved and program students ----
    # replace cmAgg, then cmProg, each up to its own closing brace (other helpers sit between them)
    a = html.index('function cmAgg(sc, keys, band) {'); b = html.index('\n}\n', a) + 3
    c = html.index('function cmProg(sc, keys, band) {'); d = html.index('\n}\n', c) + 3
    html = html[:a] + NEW_AGG + html[b:c] + NEW_PROG + html[d:]


    # ---- custom state records where moved students live ----
    rep("const st = { ser: {}, typ: {}, g: {}, closed: new Set(), reopened: new Set(), moved: 0, notes: {}, receivers: [] };",
        "const st = { ser: {}, typ: {}, g: {}, closed: new Set(), reopened: new Set(), moved: 0, notes: {}, receivers: [], moves: [] };")
    rep("""    const tot = part.sh.reduce((a, b) => a + b, 0) || 1;
    const shares = part.sh.map(v => v / tot);
""", """    const tot = part.sh.reduce((a, b) => a + b, 0) || 1;
    const shares = part.sh.map(v => v / tot);
    // where the moved students live (getting-to-school table): x's own students in x's area; students x received from
    // an earlier custom closure still live in their original school's area, so those moves continue to x's receivers
    const bk = { K5: 'k5', M68: '68', HS: '912' }[part.band];
    const inbound = st.moves.filter(m => m.to === x && m.band === bk);
    const own = CY.map((_, i) => i < IMPL_I || st.ser[x][i] == null ? 0
      : Math.max(0, st.ser[x][i] * fracOf(t, part.band, i) - inbound.reduce((a, m) => a + (m.amt[i] || 0), 0)));
    st.moves = st.moves.filter(m => !inbound.includes(m));
    to.forEach((r, j) => {
      st.moves.push({ from: x, to: r, band: bk, amt: own.map(v => v * shares[j]) });
      for (const m of inbound) st.moves.push({ from: m.from, to: r, band: bk, amt: m.amt.map(v => (v || 0) * shares[j]) });
    });
""")

    # ---- receivers: neighborhood schools before program schools ----
    rep("""function candidates(state, k, band) {
  return D.schools.filter(""", """function candidates(state, k, band) {
  // prefer neighborhood schools (an attendance area for these grades in the starting scenario) over focus-option and
  // immersion-only programs, which draw students from across the district
  const bk = { K5: 'k5', M68: '68', HS: '912' }[band], A = D.commute?.S?.[custom.base] || {};
  const all = candidatesAll(state, k, band), nbh = all.filter(c => A[c.k]?.[bk]?.[0]);
  return nbh.length ? nbh : all;
}
function candidatesAll(state, k, band) {
  return D.schools.filter(""")

    # ---- negative cost reads as a saving ----
    rep("const bcRange = (a, b) =>", "const bcMoney = (lo, hi) => hi < 0 ? `${bcRange(-hi, -lo)} less` : lo < 0 ? `&minus;${bcM(lo)} to +${bcM(hi)}` : bcRange(lo, hi);\nconst bcRange = (a, b) =>")
    rep("let h = `<br>Added yellow-bus cost in ${D.impl_year}, the first year: <b>${bcRange(s.lo, s.hi)}</b> a year (est.;",
        "let h = `<br>${s.hi < 0 ? 'Yellow-bus cost' : 'Added yellow-bus cost'} in ${D.impl_year}, the first year: <b>${bcMoney(s.lo, s.hi)}</b> a year (est.;")
    rep("h += `<br><span class=\"pcs\">${cmYear}: ${bcRange(t.lo, t.hi)} a year</span>`;",
        "h += `<br><span class=\"pcs\">${cmYear}: ${bcMoney(t.lo, t.hi)} a year</span>`;")
    rep("<b>${n(s.d_elig)}</b> ${s.d_elig >= 0 ? 'more' : 'fewer'} K-8 students",
        "<b>${n(Math.abs(s.d_elig))}</b> ${s.d_elig >= 0 ? 'more' : 'fewer'} K-8 students")
    rep("That adds about <b>${n(s.d_sm)}</b> student-miles a school day on the bus (central ridership) and, at ${bcD(Math.min(...BC.cases.central.psm))}&ndash;${bcD(Math.max(...BC.cases.central.psm))} a year per daily student-mile, about <b>${bcRange(s.lo, s.hi)}</b> a year in general yellow-bus cost. `",
        "That ${s.d_sm >= 0 ? 'adds' : 'removes'} about <b>${n(Math.abs(s.d_sm))}</b> student-miles a school day on the bus (central ridership) and, at ${bcD(Math.min(...BC.cases.central.psm))}&ndash;${bcD(Math.max(...BC.cases.central.psm))} a year per daily student-mile, ${s.hi < 0 ? 'saves' : 'costs'} about <b>${bcMoney(s.lo, s.hi).replace(' less', '')}</b> a year in general yellow-bus cost. `")
    rep("At today's cost per bus (${bcKRange(...perBus)} a year), that is the cost of roughly <b>${Math.round(s.mid / (perBus[0] + perBus[1]) * 2)}</b> more buses, if the extra riders cannot fit on existing runs (see caveats).</p>`",
        "` + (s.mid > 0 ? `At today's cost per bus (${bcKRange(...perBus)} a year), that is the cost of roughly <b>${Math.round(s.mid / (perBus[0] + perBus[1]) * 2)}</b> more buses, if the extra riders cannot fit on existing runs (see caveats).` : '') + `</p>`")

    # ---- custom note: what is handled now, and what remains weaker ----
    a = html.index("    li('Getting to school (and the yellow-bus cost).',"); b = html.index("    li('Staffing impact.',", a)
    html = html[:a] + r"""    li('Getting to school (and the yellow-bus cost).', `Uses your scenario's enrollment with ${b}'s attendance areas. Students moved by your closures are counted where they live (their old school's area), travelling to their new school.${fromAB ? ` A school you keep open that ${b} closes uses its Status Quo area.` : ''}`,
      `the receiving schools' own areas are still ${b}'s, so they include territory your closures would normally redraw; ` +
      (fromAB ? `when you keep a school open, the schools that would have taken its students still have ${b}'s larger areas; ` : '') +
      `students moved from a program school (no neighborhood area) have no known home area and are left out of the distance and bus figures; ridership is assumed the same as today's.`) +
""" + html[b:]

open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched' if 'CS.moves' in html or 'st.moves' in html else 'data only')
