"""A "County population (PFA study)" switch beside "Modified enrollment model": rebuilds the page's enrollment projections
on PSU's August 2026 Multnomah County single-year-of-age projections (prepared for Preschool for All; Census Vintage
2025 base; source/demographics/psu-multnomah-ages-0-9.json), instead of the population behind PSU's May 2026 PPS
forecast.
  Kindergarten, fall 2026-2035 = the county's projected 5-year-olds (medium scenario, July 1) x PPS's share of the
  county's children (age 5-9: 56.7% in 2020 to 53.9% in 2030 from PSU's PPS Table 5.1, held after 2030) x one capture
  rate, set so the 2031-2035 average equals PSU's own kindergarten forecast (PSU's long-run level is kept; the
  year-to-year path follows the newer birth and migration data, e.g. the small 2021 and 2023 birth cohorts).
  The change in each kindergarten class is carried up the grades with PSU's medium grade progression ratios; each
  grade band's (K-5, 6-8, 9-12) change relative to PSU's medium forecast scales every school's enrollment in that band
  (K-8s by their K-5 share), in Status Quo, A and B (custom scenarios build on them), from 2026-27 on. The 2031-32
  school details (enrollment, threshold, use of capacity, student groups) and the measures by region follow.
Off by default; remembered in the browser; carried by links (pfa=1). Works with the modified enrollment model (applied
after it). The enrollment uncertainty section's simulations stay on PSU's medium forecast.
Data: D.pfa (refreshed on rerun); code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
CTY = {int(a): {int(y): v for y, v in d.items()} for a, d in json.load(open(os.path.join(ROOT, 'source', 'demographics', 'psu-multnomah-ages-0-9.json')))['medium'].items()}
MED = json.load(open(os.path.join(ROOT, 'source', 'pps-forecast', 'table-5.2-medium.json')))
GR = ['K'] + [str(i) for i in range(1, 13)]
lab = lambda y: f'{y}-{str((y + 1) % 100).zfill(2)}'
med = lambda g, y: MED['grades'][GR[g]][MED['years'].index(lab(y))]
s20 = 23620 / sum(CTY[a][2020] for a in range(5, 10)); s30 = 17664 / sum(CTY[a][2030] for a in range(5, 10))
share = lambda y: s20 + (s30 - s20) * min(y - 2020, 10) / 10
P5 = {y: CTY[5][y] * share(y) for y in range(2021, 2037)}
cap = sum(med(0, y) / P5[y] for y in range(2031, 2036)) / 5
KP = {y: cap * P5[y] for y in range(2026, 2036)}
dK = {y: KP[y] - med(0, y) for y in KP}
# carry each class's change up the grades with PSU's medium grade progression ratios
delta = {}   # (grade, fall) -> change
for y0, d in dK.items():
    v = d; delta[(0, y0)] = v
    for g in range(1, 13):
        y = y0 + g
        if y > 2035: break
        v = v * med(g, y) / med(g - 1, y - 1); delta[(g, y)] = v
ratio = []
for sy in D['years']:
    y = int(sy[:4]); r = {}
    for b, (a, z) in {'k5': (0, 5), 'm68': (6, 8), 'h912': (9, 12)}.items():
        base = sum(med(g, y) for g in range(a, z + 1)) if y >= 2021 else 1
        r[b] = round(1 + sum(delta.get((g, y), 0) for g in range(a, z + 1)) / base, 5) if y >= 2026 else 1
    ratio.append(r)
D['pfa'] = dict(source='PSU Population Research Center, Multnomah County Population Projections 2026-2036 (Aug 11, 2026; prepared for Preschool for All), medium scenario',
                capture=round(cap, 4), share_2020=round(s20, 4), share_2030=round(s30, 4),
                k_pfa={lab(y): round(v) for y, v in KP.items()}, k_psu={lab(y): med(0, y) for y in KP}, ratio=ratio)
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
print(f'capture {cap:.3f}; K PFA vs PSU:', {y: f'{KP[y]:.0f}/{med(0, y)}' for y in KP})
print('band ratios:', {D['years'][i]: r for i, r in enumerate(ratio) if i in (1, 2, 3, 6, 10)})

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

JS = r'''// ---------- county population (Preschool for All study) switch (scripts/patch_pfa_population.py) ----------
let pfaOn = false;
try { pfaOn = localStorage.getItem('rsPfa') === '1'; } catch (e) {}
const PFA_BASE = { series: clone(D.series.SQ), detail: clone(D.detail.SQ), e2031: Object.fromEntries(D.schools.map(s => [s.key, s.e2031.SQ])) };
const PFA = { diff: {} };
function applyPFA(on) {   // runs after applyAdjust, which has just reset (and adjusted) A and B
  pfaOn = on; PFA.diff = {};
  D.series.SQ = clone(PFA_BASE.series); D.detail.SQ = clone(PFA_BASE.detail); for (const s of D.schools) s.e2031.SQ = PFA_BASE.e2031[s.key];
  if (!on || !D.pfa) return;
  for (const sc of ['SQ', 'A', 'B']) {
    const ser = D.series[sc], det = D.detail[sc], before = clone(det);
    for (const k of Object.keys(ser)) ser[k] = ser[k].map((v, i) => {
      if (v == null) return v;
      const r = D.pfa.ratio[i] || { k5: 1, m68: 1, h912: 1 }, t = (i < IMPL_I ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k], f = k5Of(k, CY[i]) ?? 0.66;
      const mm = t === 'ES' ? r.k5 : t === 'MS' ? r.m68 : t === 'HS' ? r.h912 : f * r.k5 + (1 - f) * r.m68;
      return Math.round(v * mm);
    });
    for (const n of Object.keys(det)) {
      const d = det[n], e = ser[n]?.[Y31_I]; if (d.closed || e == null) continue;
      const k = d.e ? e / d.e : 1;
      for (const g of GRP) if (d.g[g] != null) d.g[g] = rndh(d.g[g] * k);
      d.e = e; d.above = e >= d.thr - 1e-9; d.util = d.fc ? rndh(100 * e / d.fc) : null;
      if (byKey[n]) byKey[n].e2031[sc] = e;
    }
    for (const rn of [...D.region_order, 'District']) {
      const names = Object.keys(D.region_of).filter(n => rn === 'District' || D.region_of[n] === rn);
      const b0 = metricsOf(before, names), b1 = metricsOf(det, names), E = D.endpoints[rn]?.[sc], R = D.recreated[sc]?.[rn];
      if (!E) continue;
      for (const k of ['schools_above', 'students_above', ...GRP]) {
        const dd = (b1[k] ?? 0) - (b0[k] ?? 0); if (!dd) continue;
        ((PFA.diff[rn] ||= {})[sc] ||= {})[k] = dd; E[k] += dd; if (R && R[k] != null) R[k] += dd;
      }
    }
  }
}
function applyAdjust(on) {   // every change to the enrollment models re-applies both, from Status Quo as published
  D.series.SQ = clone(PFA_BASE.series); D.detail.SQ = clone(PFA_BASE.detail); for (const s of D.schools) s.e2031.SQ = PFA_BASE.e2031[s.key];
  applyAdjust0(on); applyPFA(pfaOn);
}
function applyAdjust0(on) {'''

if 'applyPFA' not in html:
    rep("function applyAdjust(on) {", JS)
    rep("""id="adjtog"> Modified enrollment model</label>""",
        """id="adjtog"> Modified enrollment model</label><label class="adjtog" id="pfatogl" title="Rebuilds enrollment on PSU's August 2026 Multnomah County population projections, prepared for Preschool for All (Census 2025 base: smaller 2021 and 2023 birth cohorts, continued out-migration of young children). Kindergarten = the county's projected 5-year-olds x PPS's share of the county's children x one capture rate that keeps PSU's long-run kindergarten level (about 2,700); the change in each class is carried up the grades and scales every school's enrollment by grade band, from 2026-27, in every scenario. Off: PSU's May 2026 PPS forecast. The enrollment uncertainty section stays on PSU's forecast."><input type="checkbox" id="pfatog"> County population (PFA study)</label>""")
    rep("""adjBox.onchange = () => { try { localStorage.setItem('rsAdj', adjBox.checked ? '1' : '0'); } catch (e) {} applyAdjust(adjBox.checked); if (CS || scen === 'C') buildCustom(); renderAll(); };""",
        """adjBox.onchange = () => { try { localStorage.setItem('rsAdj', adjBox.checked ? '1' : '0'); } catch (e) {} applyAdjust(adjBox.checked); if (CS || scen === 'C') buildCustom(); renderAll(); };
const pfaBox = document.getElementById('pfatog');
if (pfaBox) { pfaBox.checked = pfaOn; pfaBox.onchange = () => { pfaOn = pfaBox.checked; try { localStorage.setItem('rsPfa', pfaOn ? '1' : '0'); } catch (e) {} applyAdjust(adjOn); if (CS || scen === 'C') buildCustom(); renderAll(); }; }""")
    # links carry the switch
    rep("""  if (!adjOn) p.set('adj', '0');""", """  if (!adjOn) p.set('adj', '0');
  if (pfaOn) p.set('pfa', '1');""")
    rep("""  if (q.get('adj') === '0' && adjOn) { applyAdjust(false); const b = document.getElementById('adjtog'); if (b) b.checked = false; }""",
        """  if (q.get('adj') === '0' && adjOn) { applyAdjust(false); const b = document.getElementById('adjtog'); if (b) b.checked = false; }
  if (q.has('pfa') && (q.get('pfa') === '1') !== pfaOn) { pfaOn = q.get('pfa') === '1'; applyAdjust(adjOn); const b = document.getElementById('pfatog'); if (b) b.checked = pfaOn; }""")
    # the uncertainty section says which basis it shows when the switch is on
    rep("Ranges are the middle 90% of the simulations (5th to 95th percentile).`;",
        "Ranges are the middle 90% of the simulations (5th to 95th percentile).${pfaOn ? ' <b>County population (PFA study) is on:</b> the summary cards, district chart and ranges stay on the simulations around PSU\u2019s forecast; the school table and school charts are centered on this page\u2019s figures with the switch applied.' : ''}`;")
    # uncertainty-section caches depend on the switch too
    html = html.replace("adjOn].join('|')", "adjOn, pfaOn].join('|')")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
