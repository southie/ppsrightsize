// Headless checks for rightsizing-scenario-explorer.html: runs the page script with a stubbed DOM/Leaflet.
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'rightsizing-scenario-explorer.html'), 'utf8');
const full = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
const cut = full.lastIndexOf('renderAll();');
const script = full.slice(0, cut) + full.slice(cut + 'renderAll();'.length);   // skip the initial render
const el = () => ({ innerHTML: '', textContent: '', style: {}, value: '', checked: false, appendChild() {}, querySelectorAll: () => [], querySelector: () => null, addEventListener() {}, setAttribute() {}, getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 300 }), clientWidth: 900, offsetWidth: 100 });
const chain = new Proxy(function () {}, { get: () => chain, apply: () => chain });
Object.assign(global, { window: global, L: chain, innerWidth: 1200, addEventListener() {}, confirm: () => true,
  document: { getElementById: el, querySelectorAll: () => [], createElement: el, createElementNS: el, documentElement: {} },
  getComputedStyle: () => ({ getPropertyValue: () => '#000' }), localStorage: { getItem: () => null, setItem() {} },
  location: { hash: '', pathname: '/x.html', search: '', href: '' }, history: { replaceState() {} } });
const T = new Function(script + `;return { D, P, custom, buildCustom: () => buildCustom(), applyAdjust, ADJ, busScen, busH, alternatives, describeClose, baseState, encodeCustom, decodeCustom, nearestPPS, menuHtml, reopenWeights, renderEndpoints, renderKPIs, setScen: v => { scen = v; }, applyAdjust, k5Of, rpFlow };`)();
const { D } = T;
const ok = (c, msg) => { console.log((c ? 'PASS ' : 'FAIL ') + msg); if (!c) process.exitCode = 1; };

// 1) private alternatives by road for A and B (NCES PSS private-school list, 2019-20 to 2023-24: 59 / 50)
for (const sc of ['A', 'B']) {
  let n = 0, schools = 0;
  for (const s of D.schools) { const a = T.alternatives(s, sc); if (a) { schools++; n += a.within.length; } }
  console.log(`  ${sc}: ${n} alternatives for ${schools} affected schools`);
  ok(n === (sc === 'A' ? 59 : 50), `${sc} alternative count matches the NCES private-school list`);
}
const sel = T.alternatives(D.schools.find(s => s.key === 'Sellwood'), 'A');
ok(Math.abs(sel.r.d - 4.41) < 0.01 && sel.r.driving, `Sellwood relocation by road: ${sel.r.d} mi / ${sel.r.min} min to ${sel.r.to.key}`);

// 2) custom closure: nearest by road, then a 70/30 slider split
T.custom.base = 'SQ'; T.custom.actions = [];
const parts = T.describeClose(T.baseState('SQ'), 'Woodstock', 2);
console.log('  Woodstock 2 nearest by road:', parts[0].c.map(c => `${c.k} ${c.d} mi/${c.min} min`).join(', '));
T.custom.actions.push({ k: 'Woodstock', parts: parts.map(p => ({ band: p.band, to: p.c.map(c => c.k), sh: [0.7, 0.3] })) });
T.buildCustom();
const y = D.years.indexOf('2031-32'), w = D.series.SQ.Woodstock[y];
const [r1, r2] = parts[0].c.map(c => c.k);
const g1 = D.series.C[r1][y] - D.series.SQ[r1][y], g2 = D.series.C[r2][y] - D.series.SQ[r2][y];
ok(Math.abs(g1 - 0.7 * w) < 0.01 && Math.abs(g2 - 0.3 * w) < 0.01, `70/30 split moves ${g1.toFixed(1)} / ${g2.toFixed(1)} of Woodstock's ${w}`);
const tot = s => Object.values(D.series[s]).reduce((a, v) => a + (v[y] || 0), 0);
ok(Math.abs(tot('SQ') - tot('C')) < 0.01, `district 2031-32 total conserved (${Math.round(tot('C'))})`);
const recv = D.flows.C.receivers.filter(r => r.from_key === 'Woodstock').map(r => r.share);
ok(recv.length === 2 && Math.abs(recv[0] - 0.7) < 1e-9, `flow shares recorded: ${recv.join(', ')}`);

// 3) link round trip keeps the shares
const back = T.decodeCustom(T.encodeCustom());
ok(JSON.stringify(back.actions[0].parts[0].sh) === JSON.stringify([0.7, 0.3]), 'link round trip keeps 70/30');

// 4) 0% share: receiver gets nothing and no flow line
T.custom.actions[0].parts[0].sh = [1, 0]; T.buildCustom();
ok(Math.abs(D.series.C[r2][y] - D.series.SQ[r2][y]) < 1e-9 && D.flows.C.receivers.filter(r => r.from_key === 'Woodstock').length === 1, '100/0 split: second school unchanged, one flow line');

// optional: print a sample link (node scripts/test_explorer.js link)
if (process.argv[2] === 'link') {
  T.custom.base = 'A'; T.custom.actions = []; T.custom.name = 'Slider test';
  const p3 = T.describeClose(T.baseState('A'), 'Woodstock', 3);
  T.custom.actions.push({ k: 'Woodstock', parts: p3.map(x => ({ band: x.band, to: x.c.map(c => c.k), sh: [0.6, 0.3, 0.1] })) });
  T.buildCustom();
  console.log('LINK ' + T.encodeCustom());
}

// 5) private popup nearest PPS by road
const pr = T.P.find(x => !x.preKOnly);
const np = T.nearestPPS(pr);
ok(np.road && np.min > 0, `nearest PPS to ${pr.name}: ${np.s.key} ${np.d} mi / ${np.min} min by road`);

// 6) keep open a school the starting scenario closes (checked without the Census boundary adjustment, which moves
// part of Hayhurst's area to Rieke and so caps what Hayhurst can give back)
T.applyAdjust(false);
{
  const Y = D.years.indexOf('2031-32'), sum = sc => Object.values(D.series[sc]).reduce((a, s) => a + (s[Y] || 0), 0);
  T.custom.base = 'A'; T.custom.name = ''; T.custom.actions = [{ k: 'Maplewood', reopen: true }]; T.buildCustom();
  const sq = D.series.SQ.Maplewood[Y];
  ok(Math.abs(D.series.C.Maplewood[Y] - sq) < 0.5,   // projections are whole numbers, so caps can round a fraction off
   `Maplewood kept open in A: 2031-32 back to Status Quo (${sq})`);
  ok(Math.abs((D.series.A.Hayhurst[Y] - D.series.C.Hayhurst[Y]) - 0.7 * sq) < 0.5 && Math.abs((D.series.A.Rieke[Y] - D.series.C.Rieke[Y]) - 0.3 * sq) < 0.5, 'Hayhurst and Rieke give back 70% / 30%');
  ok(Math.abs(sum('A') - sum('C')) < 0.01, `district 2031-32 total unchanged from A (${Math.round(sum('C'))})`);
  ok(D.endpoints.District.C.closures === D.endpoints.District.A.closures - 1, `district closures ${D.endpoints.District.A.closures} -> ${D.endpoints.District.C.closures}`);
  ok(!D.flows.C.receivers.some(r => r.from_key === 'Maplewood') && D.schools.find(s => s.key === 'Maplewood').cat.C === 'other', 'no flow lines from Maplewood; marked as a change');
  const w = T.reopenWeights('Beach', 'A', Y), cc = w.find(r => /Ch.vez/.test(r.to));
  ok(Math.abs(cc.w - D.dli.Beach) < 1e-9 && Math.abs(w.reduce((a, r) => a + r.w, 0) - 1) < 1e-9, `Beach immersion share to ${cc.to}: ${cc.w}`);
  ok(/Keep Beach open/.test(T.menuHtml(D.schools.find(s => s.key === 'Beach'))) && /Close Maplewood again/.test(T.menuHtml(D.schools.find(s => s.key === 'Maplewood'))), 'menu offers keep-open and close-again');
  const rt = T.decodeCustom(T.encodeCustom());
  ok(rt.base === 'A' && rt.actions.length === 1 && rt.actions[0].reopen && rt.actions[0].k === 'Maplewood', 'link round trip keeps the reopen');
  // a later custom closure can send students to the reopened school
  const parts = T.describeClose(T.baseState('A'), 'Hayhurst', 1);
  T.custom.actions.push({ k: 'Hayhurst', parts: parts.map(p => ({ band: p.band, to: ['Maplewood'] })) }); T.buildCustom();
  ok(D.series.C.Hayhurst[Y] == null && D.series.C.Maplewood[Y] > sq && Math.abs(sum('A') - sum('C')) < 0.01, `then closing Hayhurst into Maplewood: ${Math.round(D.series.C.Maplewood[Y])}, total conserved`);
  T.custom.actions = []; T.custom.base = 'SQ';
}

// 7) switching between a custom scenario and the published ones redraws the table and summary cards
//    (building a custom scenario adds a District closing list for C only; switching back to A/B used to throw)
{
  T.custom.base = 'A'; T.custom.name = ''; T.custom.actions = [{ k: 'Maplewood', reopen: true }]; T.buildCustom();
  for (const sc of ['C', 'A', 'B', 'SQ', 'C']) {
    let err = null;
    try { T.setScen(sc); T.renderEndpoints(); T.renderKPIs(); } catch (e) { err = e; }
    ok(!err, `table and summary cards render after switching to ${sc}${err ? ': ' + err.message : ''}`);
  }
  T.setScen('A'); T.custom.actions = []; T.custom.base = 'SQ';
}

// 8) keeping Sellwood open in A: receivers give back at most what they gained over Status Quo
{
  const Y = D.years.indexOf('2031-32'), sum = sc => Object.values(D.series[sc]).reduce((a, s) => a + (s[Y] || 0), 0);
  const gained = ['Hosford', 'Lane'].reduce((a, k) => a + D.series.A[k][Y] - D.series.SQ[k][Y], 0);
  T.custom.base = 'A'; T.custom.actions = [{ k: 'Sellwood', reopen: true }]; T.buildCustom();
  const back = D.series.C.Sellwood[Y];
  ok(!D.detail.C.Sellwood.closed && D.endpoints.District.C.closures === D.endpoints.District.A.closures - 1, `Sellwood kept open in A: open, district closures ${D.endpoints.District.C.closures}`);
  ok(Math.abs(back - Math.min(D.series.SQ.Sellwood[Y], gained)) < 0.5, `Sellwood gets back ${Math.round(back)} (Status Quo ${D.series.SQ.Sellwood[Y]}; Hosford and Brentwood gained ${gained})`);
  ok(['Hosford', 'Lane'].every(k => D.series.C[k][Y] >= D.series.SQ[k][Y] - 0.5), `no receiver drops below Status Quo (Hosford ${Math.round(D.series.C.Hosford[Y])} vs ${D.series.SQ.Hosford[Y]}, Brentwood ${Math.round(D.series.C.Lane[Y])} vs ${D.series.SQ.Lane[Y]})`);
  ok(Math.abs(sum('A') - sum('C')) < 0.01, `district 2031-32 total unchanged from A (${Math.round(sum('C'))})`);
  T.custom.actions = []; T.custom.base = 'SQ';
}

// 7) Census boundary adjustment: moves conserve students, Llewellyn gains from Duniway, published measures shift and restore
{
  const Y = D.years.indexOf('2031-32'), sum = sc => Object.values(D.series[sc]).reduce((a, s) => a + (s[Y] || 0), 0);
  T.applyAdjust(false); const a0 = sum('A'), b0 = sum('B');
  T.applyAdjust(true);
  const dl = D.series.A.Llewellyn[Y] - 312, dd = 546 - D.series.A.Duniway[Y];
  ok(dl > 80 && dl === dd, `A: Duniway -> Llewellyn moves ${dl} students in 2031-32 (Llewellyn ${D.series.A.Llewellyn[Y]}, Duniway ${D.series.A.Duniway[Y]})`);
  ok(Math.abs(sum('A') - a0) < 0.01 && Math.abs(sum('B') - b0) < 0.01, `adjusted A and B keep their district 2031-32 totals (${a0}, ${b0})`);
  ok(D.detail.A.Llewellyn.above && D.endpoints['Cleveland / Franklin'].A.schools_above === 76 && T.ADJ.diff['Cleveland / Franklin'].A.schools_above.pub === 71,
     `Cleveland / Franklin A: schools above ${D.endpoints['Cleveland / Franklin'].A.schools_above}% (PPS published 71%)`);
  ok(D.series.B.Lewis[Y] > 201, `B: Whitman -> Lewis (Lewis ${D.series.B.Lewis[Y]})`);
  T.applyAdjust(false);
  ok(D.series.A.Llewellyn[Y] === 312 && D.endpoints['Cleveland / Franklin'].A.schools_above === 71 && !Object.keys(T.ADJ.diff).length, 'turning it off restores the published figures');
  T.applyAdjust(true);
}

// 9) Modified enrollment model: each K-8's own K-5 share (ODE fall 2025 by grade) instead of the district-wide share
{
  const I = D.years.indexOf(D.impl_year), Y = D.years.indexOf('2031-32'), yr = D.impl_year, d0 = D.k5_share[yr];
  const sum = sc => Object.values(D.series[sc]).reduce((a, s) => a + (s[Y] || 0), 0);
  T.applyAdjust(false);
  ok(Math.abs(T.k5Of('Sunnyside Environmental', '2025-26') - D.k5_share['2025-26']) < 1e-9, 'switch off: K-8 splits use the district-wide share');
  const off = { lau: D.series.A.Laurelhurst[I], tab: D.series.A['Mt Tabor'][I], tot: sum('A') };
  T.applyAdjust(true);
  ok(Math.abs(T.k5Of('Sunnyside Environmental', '2025-26') - 0.6021) < 0.001, `switch on: Sunnyside's own K-5 share ${(100 * T.k5Of('Sunnyside Environmental', '2025-26')).toFixed(1)}% (district ${(100 * D.k5_share['2025-26']).toFixed(1)}%)`);
  const sq = D.series.SQ.Laurelhurst[I], own = T.k5Of('Laurelhurst', yr), shift = Math.round(sq * (d0 - own));
  ok(Math.abs(D.series.A.Laurelhurst[I] - sq * own) <= 1, `Laurelhurst becoming K-5 keeps its own K-5 share in ${yr}: ${D.series.A.Laurelhurst[I]} of ${sq} (${(100 * own).toFixed(1)}%; the district share would keep ${off.lau})`);
  ok(D.series.A['Mt Tabor'][I] - off.tab === shift, `Mt Tabor gains the ${shift} extra 6-8 students`);
  ok(Math.abs(sum('A') - off.tot) < 0.01, `district 2031-32 total unchanged by the K-8 shares (${Math.round(sum('A'))})`);
  T.applyAdjust(false);
  ok(D.series.A.Laurelhurst[I] === off.lau && D.series.A['Mt Tabor'][I] === off.tab, 'switching off restores the original model');
  T.applyAdjust(true);
}

// 10) school report: pathways and flows for one school
{
  const has = (m, k, side) => m.has(k) && m.get(k)[side];
  const sw = T.rpFlow('Sellwood', 'A');
  ok(has(sw.next, 'Hosford', 'sc') && has(sw.next, 'Lane', 'sc'), 'report: Sellwood (closes in A) sends its students to Hosford and Brentwood');
  ok(['Duniway', 'Lewis', 'Llewellyn'].every(k => has(sw.inn, k, 'sq') && !has(sw.inn, k, 'sc')), 'report: Sellwood loses its three elementary feeders in A');
  const sun = T.rpFlow('Sunnyside Environmental', 'A');
  ok(has(sun.high, 'Cleveland', 'sc') && !has(sun.high, 'Cleveland', 'sq') && has(sun.high, 'Franklin', 'sq') && !has(sun.high, 'Franklin', 'sc'),
     'report: Sunnyside moves from the Franklin to the Cleveland high-school pathway in A');
  ok((has(sun.next, 'Hosford', 'sc') || sun.out.has('Hosford')) && has(sun.inn, 'Buckman', 'sc'), 'report: Sunnyside sends 6-8 to Hosford and takes Buckman students in A');
  const sq = T.rpFlow('Sunnyside Environmental', 'SQ');
  ok([...sq.inn.values(), ...sq.next.values(), ...sq.high.values()].every(e => e.sq === e.sc), 'report: Status Quo view shows no changes');
}

// 11) school report: relocations to a same-level school are listed under This school, with the mechanism
{
  const lane = T.rpFlow('Lane', 'A');
  const hp = lane.out.get('Harrison Park');
  ok(hp && hp.sc && hp.notes.some(n => /Boundary change/.test(n)) && !lane.next.has('Harrison Park'),
     'report: part of Brentwood\'s area moving to Harrison Park is a boundary-change relocation, not a next school');
  const sun = T.rpFlow('Sunnyside Environmental', 'A');
  ok(sun.out.has('Hosford') && sun.out.get('Hosford').notes.some(n => /Grade change/.test(n)), 'report: Sunnyside\'s 6-8 grades moving to Hosford are listed as a grade change');
  const sw = T.rpFlow('Sellwood', 'A');
  ok(sw.next.has('Hosford') && sw.next.has('Lane') && !sw.out.has('Hosford'), 'report: a closing school\'s receivers stay under Students go to');
}

// 9) bus cost from the generated-route heuristic: A and B add bus time, and a custom closure is priced too
{
  T.applyAdjust(false);
  const keys = Object.keys(D.region_of);
  T.setScen('A'); const a = T.busScen(); T.setScen('B'); const b = T.busScen();
  ok(a.d_pct > 0.03 && a.d_pct < 0.15 && b.d_pct > 0.03 && b.d_pct < 0.15 && isFinite(a.mid) && a.lo <= a.hi,
     `bus cost: A ${(100 * a.d_pct).toFixed(1)}% bus-minutes (+$${(a.mid / 1e6).toFixed(2)}M), B ${(100 * b.d_pct).toFixed(1)}%`);
  T.custom.base = 'SQ'; T.custom.name = ''; T.custom.actions = [];
  const parts = T.describeClose(T.baseState('SQ'), 'Woodstock', 2);
  T.custom.actions.push({ k: 'Woodstock', parts: parts.map(p => ({ band: p.band, to: p.c.map(c => c.k) })) });
  T.buildCustom(); T.setScen('C'); const c = T.busScen();
  const hq = T.busH('SQ', keys).h, hc = T.busH('C', keys).h;
  ok(isFinite(c.mid) && Math.abs(hc - hq - c.d_h) < 1e-6 && Math.abs(c.d_elig) < 5000, `bus cost: custom (close Woodstock) ${c.d_h >= 0 ? '+' : ''}${Math.round(c.d_h)} bus-minutes a day, $${(c.mid / 1e3).toFixed(0)}k a year`);
  T.setScen('A'); T.applyAdjust(true);
}
