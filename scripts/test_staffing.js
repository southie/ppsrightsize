// Staffing-formula checks: calibration against PPS board deck slide 7, and scenario estimates.
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'rightsizing-scenario-explorer.html'), 'utf8');
const full = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
const cut = full.lastIndexOf('renderAll();');
const script = full.slice(0, cut) + full.slice(cut + 'renderAll();'.length);
const el = () => ({ innerHTML: '', textContent: '', style: {}, value: '', checked: false, dataset: {}, appendChild() {}, querySelectorAll: () => [], querySelector: () => null, addEventListener() {}, setAttribute() {}, getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 300 }), clientWidth: 900, offsetWidth: 100 });
const chain = new Proxy(function () {}, { get: () => chain, apply: () => chain });
Object.assign(global, { window: global, L: chain, innerWidth: 1200, addEventListener() {}, confirm: () => true, fetch: () => new Promise(() => {}),
  document: { getElementById: el, querySelectorAll: () => [], createElement: el, createElementNS: el, documentElement: {} },
  getComputedStyle: () => ({ getPropertyValue: () => '#000' }), localStorage: { getItem: () => null, setItem() {} },
  location: { hash: '', pathname: '/x.html', search: '', href: '' }, history: { replaceState() {} } });
const T = new Function(script + ';return { D, schoolFTE, staffAgg, staffCost, setCaps: c => { caps = c; }, SF };')();
const { D } = T;

// 1) slide 7: PPS General Fund FTE (core staffing formulas) at PPS's projected enrollment
const slide7 = [['Rosa Parks', 161, 13.0], ['Whitman', 196, 15.0], ['Creston', 198, 13.0], ['Rieke', 255, 17.2], ['Beach', 286, 20.0],
  ['Woodstock', 351, 22.2], ['Atkinson', 358, 22.0], ['Kelly', 412, 24.6], ['Ainsworth', 554, 32.0], ['Richmond', 505, 26.0]];
console.log('Calibration vs PPS slide 7 (K-5, General Fund core formula FTE):');
let sumDiff = 0;
for (const [k, e, pps] of slide7) {
  const r = T.schoolFTE(k, 'SQ', 0, e, 'ES');
  sumDiff += pps - r.total;
  console.log(`  ${k.padEnd(11)} ${String(e).padStart(4)} students  PPS ${pps.toFixed(1).padStart(5)}  formula ${r.total.toFixed(1).padStart(5)}  (homerooms ${r.homeroom}, specialists ${r.specialists.toFixed(1)}, admin ${(r.principal + r.ap + r.office).toFixed(2)}, support ${r.support.toFixed(1)})  gap ${(pps - r.total).toFixed(1)}`);
}
console.log(`  mean gap ${(sumDiff / slide7.length).toFixed(2)} FTE per school (PPS higher)`);

// 2) scenario estimates
const keys = Object.keys(D.region_of);
const sum = (sc, yi) => T.staffAgg(keys, sc, yi);
for (const preset of ['caps_budget', 'caps_contract']) {
  T.setCaps(JSON.parse(JSON.stringify(T.SF[preset])));
  for (const y of ['2027-28', '2031-32']) {
    const yi = D.years.indexOf(y), sq = sum('SQ', yi);
    for (const sc of ['A', 'B']) {
      const s = sum(sc, yi), d = c => (sq[c] - s[c]);
      console.log(`${preset.padEnd(13)} ${y} ${sc}: closed ${s.closed} | principals ${d('principal').toFixed(0)} AP/VP ${d('ap').toFixed(0)} office ${d('office').toFixed(2)} | homerooms ${d('homeroom').toFixed(0)} specialists ${d('specialists').toFixed(1)} support ${d('support').toFixed(1)} 6-8 ${d('t68').toFixed(1)} 9-12 ${d('t912').toFixed(1)} | TOTAL ${d('total').toFixed(1)} of ${sq.total.toFixed(0)} | $${((T.staffCost(sq) - T.staffCost(s)) / 1e6).toFixed(1)}M/yr (admin $${(((sq.principal - s.principal) + (sq.ap - s.ap)) * T.D.staff.costs.administrator / 1e6 + (sq.office - s.office) * 2 * T.D.staff.costs.classified / 1e6).toFixed(1)}M) of $${(T.staffCost(sq) / 1e6).toFixed(0)}M`);
    }
  }
}
