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
const T = new Function(script + `;return { D, P, custom, buildCustom: () => buildCustom(), alternatives, describeClose, baseState, encodeCustom, decodeCustom, nearestPPS, menuHtml, reopenWeights, renderEndpoints, renderKPIs, setScen: v => { scen = v; } };`)();
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

// 6) keep open a school the starting scenario closes
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
