"""Enrollment uncertainty section, school fan pop-up: two more charts under the school's own, for its grade segment
district-wide (K-5, 6-8, 9-12; K-8 schools: K-8) and for district K-12, all PPS: actual history from fall 2016, PSU's
low / medium / high forecasts and the simulated median and 50% / 90% ranges (the district draws, with the section's
capture filter; school-level error does not change district totals). Code added once.
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

HELPER = r'''// a district-wide fan chart for the school pop-up (scripts/patch_mc_fan_district.py): band 'K-5', '6-8', '9-12', 'K-8' or 'K-12'
function mcBandFan(band) {
  const pick = { 'K-5': [1], '6-8': [2], '9-12': [3], 'K-8': [1, 2], 'K-12': [1, 2, 3] }[band], hb = { 1: 'K-5', 2: '6-8', 3: '9-12' };
  const val = a => pick.reduce((t, i) => t + a[i], 0);
  const H_ = D.mc.hist, hv = f => { const i = H_.falls.indexOf(f); return i < 0 ? null : pick.reduce((t, i2) => t + H_.bands[hb[i2]][i], 0); };
  const PS = D.mc.psu, pv = (s, f) => { const i = PS.falls.indexOf(f); return i < 0 ? null : pick.reduce((t, i2) => t + PS[s][hb[i2]][i], 0); };
  const wd = mcDW(), sims = D.mc.variants.district.bands, F = D.years.map((_, i) => 2025 + i);
  const Q = F.map((f, j) => mcQ(sims.map(s => val(s[j])), wd, [0.05, 0.25, 0.5, 0.75, 0.95]));
  const x0 = 2016, x1 = 2035, W = 360, Hh = 200, L = 50, R = 8, T = 10, B = 24;
  const pts = [...Q.flatMap(q => [q[0], q[4]]), ...Array.from({ length: 10 }, (_, i) => hv(2016 + i)), ...F.flatMap(f => ['low', 'medium', 'high'].map(s => pv(s, f)))].filter(v => v != null && isFinite(v));
  const ylo = Math.min(...pts) * 0.97, yhi = Math.max(...pts) * 1.02;
  const x = f => L + (W - L - R) * (f - x0) / (x1 - x0), y = v => T + (Hh - T - B) * (1 - (v - ylo) / ((yhi - ylo) || 1));
  let s = '';
  const span = yhi - ylo, step = span > 16000 ? 4000 : span > 8000 ? 2000 : span > 3000 ? 1000 : span > 1200 ? 500 : 250;
  for (let v = Math.ceil(ylo / step) * step; v <= yhi; v += step) s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 5}" y="${y(v) + 3.5}" text-anchor="end" font-size="9.5" fill="var(--text-muted)">${v.toLocaleString()}</text>`;
  for (let f = x0; f <= x1; f += 4) s += `<text x="${x(f)}" y="${Hh - B + 13}" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">${f}</text>`;
  s += `<line x1="${x(2025.5)}" x2="${x(2025.5)}" y1="${T}" y2="${Hh - B}" stroke="var(--line)" stroke-dasharray="3 3"/>`;
  const poly = (a, b) => F.map((f, j) => `${x(f)},${y(Q[j][b])}`).join(' ') + ' ' + F.map((f, j) => `${x(f)},${y(Q[j][a])}`).reverse().join(' ');
  s += `<polygon points="${poly(0, 4)}" fill="var(--change)" opacity=".14"/><polygon points="${poly(1, 3)}" fill="var(--change)" opacity=".26"/>`;
  s += `<polyline points="${F.map((f, j) => `${x(f)},${y(Q[j][2])}`).join(' ')}" fill="none" stroke="var(--change)" stroke-width="2"/>`;
  for (const [sn, dash, wdt] of [['medium', '', 1.6], ['low', '5 4', 1.1], ['high', '5 4', 1.1]])
    s += `<polyline points="${F.map(f => [f, pv(sn, f)]).filter(p => p[1] != null).map(p => `${x(p[0])},${y(p[1])}`).join(' ')}" fill="none" stroke="var(--text-primary)" stroke-width="${wdt}" ${dash ? `stroke-dasharray="${dash}"` : ''} opacity=".8"><title>PSU ${sn} forecast</title></polyline>`;
  const hp = Array.from({ length: 10 }, (_, i) => [2016 + i, hv(2016 + i)]).filter(p => p[1] != null);
  s += `<polyline points="${hp.map(p => `${x(p[0])},${y(p[1])}`).join(' ')}" fill="none" stroke="var(--text-primary)" stroke-width="2.4"/>` + hp.map(p => `<circle cx="${x(p[0])}" cy="${y(p[1])}" r="2.2" fill="var(--text-primary)"><title>Fall ${p[0]}: ${p[1].toLocaleString()} actual</title></circle>`).join('');
  F.forEach((f, j) => { s += `<rect x="${x(f) - 7}" y="${T}" width="14" height="${Hh - T - B}" fill="transparent"><title>${D.years[j]}: simulated median ${Math.round(Q[j][2]).toLocaleString()}; 90% range ${Math.round(Q[j][0]).toLocaleString()}-${Math.round(Q[j][4]).toLocaleString()}; PSU medium ${(pv('medium', f) ?? 0).toLocaleString()}</title></rect>`; });
  const j31 = D.years.indexOf('2031-32');
  return `<div><div style="font-size:13px;font-weight:600">District ${band === 'K-12' ? 'K-12' : band + ' grades'}, all PPS</div>` +
    `<div class="muted" style="font-size:11.5px">2031-32: median ${Math.round(Q[j31][2]).toLocaleString()} (90% range ${Math.round(Q[j31][0]).toLocaleString()}&ndash;${Math.round(Q[j31][4]).toLocaleString()}); PSU medium ${(pv('medium', 2031) ?? 0).toLocaleString()}</div>` +
    `<svg viewBox="0 0 ${W} ${Hh}" style="width:100%;height:auto" role="img" aria-label="District ${band} enrollment">${s}</svg></div>`;
}
function mcSchoolFan(k, sc) {'''

if 'mcBandFan' not in html:
    rep("function mcSchoolFan(k, sc) {", HELPER)
    rep("""<span><i class="k" style="border-top:1.6px dashed var(--down);width:18px"></i>size threshold</span></div>` + tbl + `</div>`;""",
        """<span><i class="k" style="border-top:1.6px dashed var(--down);width:18px"></i>size threshold</span></div>` + tbl +
    ((t => `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:12px">${mcBandFan(t)}${mcBandFan('K-12')}</div>` +
      `<div class="rplegend"><span><i class="k" style="border-top:2.4px solid var(--text-primary);width:18px"></i>actual</span><span><i class="k" style="border-top:1.6px solid var(--text-primary);width:18px"></i>PSU medium</span><span><i class="k" style="border-top:1.6px dashed var(--text-primary);width:18px"></i>PSU low / high</span><span><i class="k" style="height:10px;width:16px;background:var(--change);opacity:.35"></i>simulated 50% / 90% and median</span><span class="muted">District totals include every PPS school and program, not only those on this page; school-level error does not change them.</span></div>`)
     ({ ES: 'K-5', MS: '6-8', HS: '9-12', K8: 'K-8' }[(D.types[sc] || {})[k] || D.types.SQ[k]] || 'K-5')) + `</div>`;""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
