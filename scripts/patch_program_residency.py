"""Where a closing school's immersion students go, by where they live: part of the "Modified enrollment model" switch.
PPS's scenarios send a closing school's immersion (DLI) program to a new site and its neighborhood students to a
neighborhood receiver; the model sent all of the school's immersion share (D.dli) to the new site. PPS's October 2025
enrollment by neighborhood (source/pps-programs/enroll-by-neighborhood.json, scripts/build_enroll_by_neighborhood.py)
says how many of each immersion program's students live in the school's own neighborhood. With the switch on, those
students go to the closing school's neighborhood receiver(s) instead, and the rest follow the program to its new site.
Affects Beach and James John (Spanish, to Cesar Chavez; their neighborhoods to Chief Joseph and Sitton) and, in
Scenario A, Rose City Park (Vietnamese, to Vestal; neighborhood to Scott). Focus schools that close without their
focus moving (Buckman, arts) already send their students to the neighborhood receivers, so they are unchanged.
The same split drives custom scenarios that keep such a school open (the students returned from each receiver) and the
closures' staffing figures. Data: D.progres {school: {imm: [program, share living in the school's neighborhood,
program students, school total], nb: whole school's share}}. Runs after patch_k8_shares / patch_boundary_adjust.
Data refreshed on rerun; code added once.
"""
import json, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
R = json.load(open(os.path.join(ROOT, 'source', 'pps-programs', 'enroll-by-neighborhood.json'), encoding='utf-8'))['schools']
n = lambda s: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
RN = {n(k): k for k in R}
P = {}
for k in D['region_of']:
    r = R.get(RN.get(n(k)))
    if not r: continue
    e = {'nb': r['Total']['nbhd_share']} if r.get('Total') else {}
    imm = [(p, v) for p, v in r.items() if 'Immersion' in p and v['total']]
    if len(imm) == 1:
        p, v = imm[0]; e['imm'] = [p.replace(' Immersion', ''), v['nbhd_share'], v['total'], r['Total']['total']]
    P[k] = e
D['progres'] = P
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
print(len(P), 'schools;', sum('imm' in v for v in P.values()), 'with one immersion program')

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'immersion students who live in a closing school' not in html:
    rep("""    for (const n of touched) {
      const d = det[n], e = ser[n][Y31_I];""", """    // immersion students who live in a closing school's own neighborhood go to its neighborhood receiver(s), not the
    // program's new site (PPS enrollment by neighborhood, October 2025; scripts/patch_program_residency.py)
    for (const j of Object.keys(D.progres || {})) {
      const pr = D.progres[j].imm; if (!pr || !ADJ_BASE.detail[sc][j]?.closed || !D.series.SQ[j]) continue;
      const rs = ADJ_BASE.recv[sc].filter(r => r.from_key === j && byKey[r.to_key]);
      const Pk = rs.find(r => /immersion/i.test(r.group))?.to_key, N = rs.filter(r => !/immersion|Hearing/i.test(r.group)).map(r => r.to_key).filter(t => ser[t]);
      if (!Pk || !ser[Pk] || !N.length || det[Pk]?.closed) continue;
      const frac = (D.dli[j] || 0) * pr[1];
      const amt = CY.map((_, i) => {
        if (i < IMPL_I || D.series.SQ[j][i] == null || ser[Pk][i] == null) return 0;
        const v = Math.min(Math.round(D.series.SQ[j][i] * frac), ser[Pk][i]); ser[Pk][i] -= v;
        let left = v; N.forEach((t, q) => { const part = q === N.length - 1 ? left : Math.round(v / N.length); left -= part; if (ser[t][i] != null) ser[t][i] += part; });
        return v;
      });
      const n31 = amt[Y31_I]; if (!n31) continue;
      const src = D.detail.SQ[j], kk = src.e ? n31 / src.e : 0;
      for (const g of GRP) if (src.g[g] != null) {
        if (det[Pk].g[g] != null) det[Pk].g[g] = Math.max(0, det[Pk].g[g] - src.g[g] * kk);
        for (const t of N) if (det[t].g[g] != null) det[t].g[g] += src.g[g] * kk / N.length;
      }
      touched.add(Pk); N.forEach(t => touched.add(t));
      ADJ.moves[sc].push({ f: Pk, t: N[0], band: 'k5', n: n31, prog: j, lang: pr[0], live: pr[1] });
      D.flows[sc].receivers.push({ from: byKey[j].name, to: byKey[N[0]].name, from_key: j, to_key: N[0], share: null, adj: true,
        group: `${pr[0]} immersion students living in ${short(byKey[j].name)}'s neighborhood (${Math.round(100 * pr[1])}%, PPS enrollment by neighborhood, Oct 2025)` });
    }
    for (const n of touched) {
      const d = det[n], e = ser[n][Y31_I];""")
    # tooltips list the move
    rep("""const adjMoveTxt = x => x.k8 ?""", """const adjMoveTxt = x => x.prog ? `${short(byKey[x.prog].name)}'s ${x.lang} immersion students who live in its neighborhood (${Math.round(100 * x.live)}%): ${x.n} go to ${short(byKey[x.t].name)} instead of ${short(byKey[x.f].name)}` : x.k8 ?""")
    # the receivers' split for custom scenarios and closures' staffing: the same shares; the adjustment's own rows are not receivers
    rep("""  const rs = D.flows[base].receivers.filter(r => r.from_key === x && byKey[r.to_key]);
  const t = D.types.SQ[x], k5 = k5Of(x, CY[yi]);
  const w = rs.map(r => r.share != null ? r.share : /immersion/i.test(r.group) ? (D.dli[x] || 0) :""",
        """  const rs = D.flows[base].receivers.filter(r => r.from_key === x && byKey[r.to_key] && !r.adj);
  const t = D.types.SQ[x], k5 = k5Of(x, CY[yi]);
  const live = adjOn && D.progres?.[x]?.imm ? D.progres[x].imm[1] : 0;   // immersion students living in the school's neighborhood stay with it
  const w = rs.map(r => r.share != null ? r.share : /immersion/i.test(r.group) ? (D.dli[x] || 0) * (1 - live) :""")
    rep("""enrollment model does not move (such as Duniway&#39;s southern area to Llewellyn), estimated from 2020 Census residents. Marked figures""",
        """enrollment model does not move (such as Duniway&#39;s southern area to Llewellyn), estimated from 2020 Census residents, and sends the immersion students of a closing school who live in its own neighborhood to its neighborhood school rather than the program&#39;s new site (PPS enrollment by neighborhood, October 2025). Marked figures""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
