// What the "County population (PFA study)" switch changes, for the summary section above the school report
// (scripts/patch_pfa_summary.py). Runs the explorer's own code with the modified enrollment model on, the switch off
// and on, and records: kindergarten paths, scenario measures, schools that fall below or near their size threshold,
// the largest enrollment drops, measures by region and staffing savings.
// Usage: node scripts/build_pfa_impact.js   Output: source/pfa-impact.json
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'rightsizing-scenario-explorer.html'), 'utf8');
const full = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
const cut = full.lastIndexOf('renderAll();');
const script = full.slice(0, cut) + full.slice(cut + 'renderAll();'.length);
const el = () => ({ innerHTML: '', textContent: '', style: {}, value: '', checked: false, options: [], dataset: {}, focus() {}, appendChild() {}, querySelectorAll: () => [], querySelector: () => null, addEventListener() {}, setAttribute() {}, getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 300 }), clientWidth: 900, offsetWidth: 100 });
const chain = new Proxy(function () {}, { get: () => chain, apply: () => chain });
Object.assign(global, { window: global, L: chain, innerWidth: 1200, innerHeight: 900, addEventListener() {}, confirm: () => true,
  document: { getElementById: el, querySelector: () => null, querySelectorAll: () => [], createElement: el, createElementNS: el, documentElement: {}, body: { appendChild() {} }, addEventListener() {}, removeEventListener() {} },
  getComputedStyle: () => ({ getPropertyValue: () => '#000' }), localStorage: { getItem: () => null, setItem() {} },
  location: { hash: '', pathname: '/x.html', search: '', href: '' }, history: { replaceState() {} } });
const T = new Function(script + `;return {
  set: pfa => { pfaOn = pfa; applyAdjust(true); },
  snap: () => {
    const keys = Object.keys(D.region_of), impl = D.years.indexOf(D.impl_year), o = { series: {}, ep: {}, staff: {}, below: {} };
    for (const s of ['SQ', 'A', 'B']) o.series[s] = Object.fromEntries(keys.map(k => [k, D.series[s][k]?.slice()]));
    for (const r of [...D.region_order, 'District']) o.ep[r] = JSON.parse(JSON.stringify(D.endpoints[r]));
    for (const y of ['2031-32', '2035-36']) { const yi = D.years.indexOf(y);
      for (const s of ['SQ', 'A', 'B']) {
        o.staff[y + '|' + s] = { District: staffCost(staffAgg(keys, s, yi)), ...Object.fromEntries(D.region_order.map(r => [r, staffCost(staffAgg(keys.filter(k => D.region_of[k] === r), s, yi))])) };
        o.below[y + '|' + s] = keys.filter(k => { const v = D.series[s][k]?.[yi]; if (v == null) return false; const t = (yi < impl ? D.types.SQ[k] : D.types[s][k]) || D.types.SQ[k]; return v < D.thresholds[t] - 1e-9; }).length;
      } }
    return o; },
  meta: () => ({ years: D.years, impl: D.years.indexOf(D.impl_year), types: D.types, thr: D.thresholds, region: D.region_of, regions: D.region_order, names: Object.fromEntries(D.schools.map(s => [s.key, short(s.name)])), pfa: D.pfa }) };`)();
T.set(false); const A = T.snap(); T.set(true); const B = T.snap(); T.set(false);
const M = T.meta(), yi = y => M.years.indexOf(y), typ = (s, k, i) => (i < M.impl ? M.types.SQ[k] : M.types[s][k]) || M.types.SQ[k];
const isBelow = (v, s, k, i) => v != null && v < M.thr[typ(s, k, i)] - 1e-9;
const out = { generated: new Date().toISOString().slice(0, 10), basis: 'Modified enrollment model on', pfa: { capture: M.pfa.capture, k_psu: M.pfa.k_psu, k_pfa: M.pfa.k_pfa }, scen: {}, schools: {}, regions: {} };
for (const s of ['SQ', 'A', 'B']) {
  const E0 = A.ep.District[s], E1 = B.ep.District[s];
  out.scen[s] = { below: ['2031-32', '2035-36'].map(y => [A.below[y + '|' + s], B.below[y + '|' + s]]), schools_above: [E0.schools_above, E1.schools_above], students_above: [E0.students_above, E1.students_above],
    students: ['2031-32', '2035-36'].map(y => [Object.values(A.series[s]).reduce((t, a) => t + (a?.[yi(y)] || 0), 0), Object.values(B.series[s]).reduce((t, a) => t + (a?.[yi(y)] || 0), 0)]) };
  if (s !== 'SQ') out.scen[s].saved = ['2031-32', '2035-36'].map(y => [A.staff[y + '|SQ'].District - A.staff[y + '|' + s].District, B.staff[y + '|SQ'].District - B.staff[y + '|' + s].District].map(v => Math.round(v / 1e5) / 10));
  for (const y of ['2031-32', '2035-36']) {
    const i = yi(y), rows = Object.keys(M.region).filter(k => A.series[s][k]?.[i] != null).map(k => ({ k, a: A.series[s][k][i], b: B.series[s][k][i], t: typ(s, k, i), th: M.thr[typ(s, k, i)] }));
    out.schools[y + '|' + s] = {
      flips: rows.filter(r => !isBelow(r.a, s, r.k, i) && isBelow(r.b, s, r.k, i)).map(r => [r.k, r.a, r.b, r.th]),
      near: rows.filter(r => !isBelow(r.b, s, r.k, i) && (r.b - r.th) / r.th < 0.03 && r.b < r.a).map(r => [r.k, r.b, r.th]),
      drops: rows.sort((p, q) => (p.b - p.a) - (q.b - q.a)).slice(0, 6).map(r => [r.k, r.a, r.b]) };
  }
}
for (const r of [...M.regions, 'District']) {
  const ch = [];
  for (const s of ['SQ', 'A', 'B']) for (const k of ['schools_above', 'students_above']) { const a = A.ep[r][s][k], b = B.ep[r][s][k]; if (a !== b) ch.push([s, k, a, b]); }
  out.regions[r] = { measures: ch, saved: r === 'District' ? null : Object.fromEntries(['A', 'B'].map(s => [s, ['2031-32', '2035-36'].map(y => [A.staff[y + '|SQ'][r] - A.staff[y + '|' + s][r], B.staff[y + '|SQ'][r] - B.staff[y + '|' + s][r]].map(v => Math.round(v / 1e5) / 10))])) };
}
out.names = M.names;
fs.writeFileSync(path.join(ROOT, 'source', 'pfa-impact.json'), JSON.stringify(out, null, 1));
console.log('wrote source/pfa-impact.json:', Object.entries(out.scen).map(([s, v]) => `${s} below 2031 ${v.below[0].join('->')}, 2035 ${v.below[1].join('->')}`).join('; '));
