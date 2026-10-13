"""Census split of a closing school's neighborhood students among its receivers, where PPS gives no shares: part of the
"Modified enrollment model" switch. The model split such students evenly; this uses, for each receiver, the 2020 Census
residents of the closing school's grade-band ages in its Status Quo attendance area that the scenario assigns to it
(D.commute.R, scripts/build_closure_access.py). Applies where a closure has two or more neighborhood receivers and no
published shares: Sellwood (6-8: Hosford for the Llewellyn area, Lane for the Duniway and Lewis areas; about 50/50 in
Scenario A, 37/63 in Scenario B). The same split drives custom scenarios that keep such a school open and the closures'
staffing figures (reopenWeights). Runs after patch_program_residency. Code added once.
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

if 'function censusSplit' not in html:
    rep("""function reopenWeights(x, base, yi) {""", """// Census split of a closing school's neighborhood students among receivers PPS gave no shares for: each receiver's share
// of the closing school's Status Quo-area residents of its grade band (D.commute.R); null when it does not apply
function censusSplit(x, base, rs) {
  const N = rs.filter(r => r.share == null && !/immersion|Hearing|K-5|middle|6-8/i.test(r.group)).map(r => r.to_key);
  if (N.length < 2) return null;
  const band = { ES: 'k5', MS: '68', HS: '912' }[D.types.SQ[x]], R = D.commute?.R?.[base === 'C' ? custom.base : base]?.[x]?.[band];
  if (!R) return null;
  const v = N.map(t => R[t]?.[0] || 0), tot = v.reduce((a, b) => a + b, 0);
  return tot > 0 ? Object.fromEntries(N.map((t, i) => [t, v[i] / tot])) : null;
}
function reopenWeights(x, base, yi) {""")
    # receivers' weights: the neighborhood remainder split by the Census rather than evenly (switch on)
    rep("""  const fixed = w.reduce((a, v) => a + (v || 0), 0), nb = w.filter(v => v === null).length;
  return rs.map((r, i) => ({ to: r.to_key, w: w[i] !== null ? w[i] : Math.max(0, 1 - fixed) / nb }));""",
        """  const fixed = w.reduce((a, v) => a + (v || 0), 0), nb = w.filter(v => v === null).length;
  const cs = adjOn ? censusSplit(x, base, rs) : null;
  return rs.map((r, i) => ({ to: r.to_key, w: w[i] !== null ? w[i] : Math.max(0, 1 - fixed) * (cs && cs[r.to_key] != null ? cs[r.to_key] : 1 / nb) }));""")
    # scenario enrollment: move the difference between the even split and the Census split
    rep("""    for (const n of touched) {
      const d = det[n], e = ser[n][Y31_I];""", """    // where PPS gives no shares, a closing school's neighborhood students split among its receivers by the Census rather
    // than evenly (scripts/patch_census_split.py)
    for (const j of Object.keys(D.region_of)) {
      if (!ADJ_BASE.detail[sc][j]?.closed || !D.series.SQ[j]) continue;
      const rs = ADJ_BASE.recv[sc].filter(r => r.from_key === j && byKey[r.to_key]);
      const cs = censusSplit(j, sc, rs); if (!cs) continue;
      const N = Object.keys(cs).filter(t => ser[t] && !det[t]?.closed); if (N.length < 2) continue;
      const fixed = rs.reduce((a, r) => a + (r.share || 0), 0) + (rs.some(r => /immersion/i.test(r.group)) ? (D.dli[j] || 0) : 0);
      const nbp = Math.max(0, 1 - fixed);
      const d31 = {};
      CY.forEach((_, i) => {
        if (i < IMPL_I || D.series.SQ[j][i] == null) return;
        const v = D.series.SQ[j][i] * nbp;
        for (const t of N) { const dv = Math.round(v * (cs[t] - 1 / N.length)); if (ser[t][i] != null) { ser[t][i] = Math.max(0, ser[t][i] + dv); if (i === Y31_I) d31[t] = dv; } }
      });
      const src = D.detail.SQ[j];
      for (const t of N) {
        const dv = d31[t] || 0; if (!dv) continue;
        const kk = src.e ? dv / src.e : 0;
        for (const g of GRP) if (src.g[g] != null && det[t].g[g] != null) det[t].g[g] = Math.max(0, det[t].g[g] + src.g[g] * kk);
        touched.add(t);
      }
      const up = N.filter(t => (d31[t] || 0) > 0), dn = N.filter(t => (d31[t] || 0) < 0);
      if (up.length && dn.length) ADJ.moves[sc].push({ f: dn[0], t: up[0], band: { ES: 'k5', MS: '68', HS: '912' }[D.types.SQ[j]], n: d31[up[0]], census: j, split: N.map(t => [t, cs[t]]) });
    }
    for (const n of touched) {
      const d = det[n], e = ser[n][Y31_I];""")
    rep("""const adjMoveTxt = x => x.prog ?""", """const adjMoveTxt = x => x.census ? `${short(byKey[x.census].name)}'s neighborhood students split by where they live (Census: ${x.split.map(([t, s]) => `${short(byKey[t].name)} ${Math.round(100 * s)}%`).join(', ')}) rather than evenly: ${x.n} more to ${short(byKey[x.t].name)}, fewer to ${short(byKey[x.f].name)}` : x.prog ?""")
    rep("""and sends the immersion students of a closing school who live in its own neighborhood""",
        """splits a closing school&#39;s neighborhood students among its receivers by where they live (Census) where PPS gives no shares, and sends the immersion students of a closing school who live in its own neighborhood""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
