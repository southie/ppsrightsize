function applyReopen(st, a) {
  const x = a.k, base = custom.base;
  if (base === 'SQ' || !st.closed.has(x) || !D.detail[base][x]?.closed) return false;
  // Each receiving school gives back its share of the school's Status Quo students, but never more than it gained
  // over Status Quo in the starting scenario (some of a closed school's students go elsewhere under the scenario's
  // boundaries). The school gets back what is returned: at most its Status Quo enrollment.
  const back = {};
  for (let i = IMPL_I; i < CY.length; i++) {
    const v = D.series.SQ[x][i]; if (v == null) continue;
    let got = 0; back[i] = [];
    for (const { to, w } of reopenWeights(x, base, i)) {
      if (w <= 0 || st.ser[to][i] == null) continue;
      const gain = Math.max(0, (D.series[base][to]?.[i] ?? 0) - (D.series.SQ[to]?.[i] ?? 0));
      const amt = Math.min(v * w, gain, st.ser[to][i]);
      st.ser[to][i] -= amt; got += amt; back[i].push({ to, amt });
    }
    st.ser[x][i] = got;
  }
  const v31 = D.series.SQ[x][Y31_I] || 0, got31 = st.ser[x][Y31_I] || 0, f = v31 ? got31 / v31 : 0;
  st.typ[x] = D.types.SQ[x];
  st.g[x] = Object.fromEntries(GRP.map(g => [g, D.detail.SQ[x].g[g] == null ? null : D.detail.SQ[x].g[g] * f]));
  for (const { to, amt } of back[Y31_I] || []) {
    const share = v31 ? amt / v31 : 0;
    for (const g of GRP) { const src = D.detail.SQ[x].g[g]; if (src != null && st.g[to][g] != null) st.g[to][g] = Math.max(0, st.g[to][g] - src * share); }
    if (amt > 0) (st.notes[to] ||= []).push(`Custom: returns ${Math.round(amt)} students to ${short(byKey[x].name)} (${short(byKey[x].name)} stays open)`);
  }
  st.moved -= got31;
  st.closed.delete(x); st.reopened.add(x);
  (st.notes[x] ||= []).push(`Custom: stays open (${LABEL[base]} closes it)` +
    (got31 < v31 - 0.5 ? `; gets back ${Math.round(got31)} of its ${Math.round(v31)} Status Quo students in 2031-32, what its receiving schools gained in ${LABEL[base]}` : ''));
  return true;
}
