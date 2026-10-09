"""Private school share chart, in its own card above "Private school capacity": the share of PPS-area residents
enrolled in grades K-12 who attend private school, by grade group, 2019 and 2024, with the 90% margin of error.
From the PPS Enrollment Forecast 2026-27, Table 3.2 (Census Bureau American Community Survey, 2019 and 2024 1-year
estimates; archive/PPS_Forecast_2026_27.pdf, page 20). Writes source/pps-forecast/table-3.2.json. The table's Total
row does not equal the sum of its grade rows; the chart shows the published figures and notes the difference.
Data refreshed on rerun; code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
# (estimate, MOE) for 2019 and 2024: enrolled, public, private, private share (%)
T = {'K': dict(enrolled=((9469, 1822), (7111, 1699)), public=((6450, 1479), (4848, 1176)), private=((3019, 1159), (2263, 1073)), share=((31.9, 10.6), (31.8, 13.0))),
     '1-4': dict(enrolled=((20316, 2102), (17345, 2557)), public=((17313, 2074), (14419, 2356)), private=((3003, 1064), (2926, 1122)), share=((14.8, 5.0), (16.9, 6.0))),
     '5-8': dict(enrolled=((19976, 2463), (19413, 2507)), public=((17008, 2341), (15018, 2425)), private=((2968, 964), (4395, 1606)), share=((14.9, 4.5), (22.6, 7.7))),
     '9-12': dict(enrolled=((17816, 1925), (17948, 2022)), public=((14884, 1962), (14955, 1992)), private=((2932, 680), (2993, 909)), share=((16.5, 3.4), (16.7, 4.7))),
     'Total': dict(enrolled=((27809, 2940), (25101, 2955)), public=((21727, 2471), (17489, 2389)), private=((6082, 1726), (7612, 1556)), share=((21.9, 5.8), (30.3, 5.1)))}
J = dict(source='PPS Enrollment Forecast 2026-27, Table 3.2: School Enrollment by Type of School, PPS District Residents, 2019 and 2024 '
                '(American Community Survey 2019 and 2024 1-year estimates; MOE = margin of error at 90% confidence)',
         years=['2019', '2024'],
         groups={g: {k: {y: dict(est=v[i][0], moe=v[i][1]) for i, y in enumerate(['2019', '2024'])} for k, v in d.items()} for g, d in T.items()})
os.makedirs(os.path.join(ROOT, 'source', 'pps-forecast'), exist_ok=True)
json.dump(J, open(os.path.join(ROOT, 'source', 'pps-forecast', 'table-3.2.json'), 'w', encoding='utf-8', newline='\n'), indent=1)

html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
D['privshare'] = J
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderPrivShare' not in html:
    rep("""  <section class="card">
    <h2>Private school capacity: comparable schools by region</h2>""", """  <section class="card">
    <h2>Private school share of PPS-area students</h2>
    <p class="sub">Share of PPS-area residents enrolled in school who attend a private school, by grade group, from the Census Bureau's American Community Survey (PPS Enrollment Forecast 2026-27, Table 3.2). Whiskers show the margin of error (MOE) at 90% confidence: the survey is a sample, so there is about a 90% chance the true share lies within that range. Overlapping ranges mean a change may not be real.</p>
    <div id="privshare"></div>
  </section>

  <section class="card">
    <h2>Private school capacity: comparable schools by region</h2>""")
    rep("function renderAll() {", r"""// ---------- private school share, ACS (D.privshare, forecast Table 3.2) ----------
function renderPrivShare() {
  const host = document.getElementById('privshare'); if (!host || host.dataset.done) return;
  const P = D.privshare, G = Object.keys(P.groups), Y = P.years, LBL = { K: 'Kindergarten', '1-4': 'Grades 1-4', '5-8': 'Grades 5-8', '9-12': 'Grades 9-12', Total: 'K-12 total' };
  const W = 760, H = 300, L = 44, R = 10, T = 16, B = 46, top = 50, gw = (W - L - R) / G.length, bw = Math.min(46, gw / 3);
  const y = v => T + (H - T - B) * (1 - v / top), col = ['color-mix(in srgb, var(--priv) 45%, transparent)', 'var(--priv)'];
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Private school share by grade group, 2019 and 2024" style="width:100%;max-width:${W}px;display:block">`;
  for (let v = 0; v <= top; v += 10) s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="var(--text-muted)">${v}%</text>`;
  G.forEach((g, gi) => {
    const cx = L + gw * gi + gw / 2;
    if (g === 'Total') s += `<line x1="${L + gw * gi}" x2="${L + gw * gi}" y1="${T}" y2="${H - B}" stroke="var(--line)" stroke-dasharray="3 3"/>`;
    Y.forEach((yr, i) => {
      const d = P.groups[g].share[yr], pv = P.groups[g].private[yr], en = P.groups[g].enrolled[yr], x = cx + (i - 1) * (bw + 4) + 2;
      const lo = Math.max(0, d.est - d.moe), hi = Math.min(top, d.est + d.moe), wx = x + bw / 2;
      s += `<g><title>${esc(`${LBL[g]}, ${yr}: ${d.est}% private (±${d.moe} points, so ${lo.toFixed(1)}% to ${(d.est + d.moe).toFixed(1)}%). ${pv.est.toLocaleString()} private of ${en.est.toLocaleString()} enrolled.`)}</title>` +
        `<rect x="${x}" y="${y(d.est)}" width="${bw}" height="${y(0) - y(d.est)}" fill="${col[i]}" rx="2"/>` +
        `<line x1="${wx}" x2="${wx}" y1="${y(hi)}" y2="${y(lo)}" stroke="var(--text-primary)" stroke-width="1.2"/>` +
        `<line x1="${wx - 5}" x2="${wx + 5}" y1="${y(hi)}" y2="${y(hi)}" stroke="var(--text-primary)" stroke-width="1.2"/><line x1="${wx - 5}" x2="${wx + 5}" y1="${y(lo)}" y2="${y(lo)}" stroke="var(--text-primary)" stroke-width="1.2"/>` +
        `<text x="${wx}" y="${y(0) + 13}" text-anchor="middle" font-size="10.5" fill="var(--text-muted)">${yr}</text>` +
        `<text x="${wx}" y="${y(hi) - 5}" text-anchor="middle" font-size="11" font-weight="600" fill="var(--text-primary)">${d.est}%</text></g>`;
    });
    s += `<text x="${cx}" y="${H - B + 30}" text-anchor="middle" font-size="12.5" font-weight="600" fill="var(--text-secondary)">${LBL[g]}</text>`;
  });
  s += '</svg>';
  const sum = yr => { const pv = G.filter(g => g !== 'Total').reduce((a, g) => a + P.groups[g].private[yr].est, 0), en = G.filter(g => g !== 'Total').reduce((a, g) => a + P.groups[g].enrolled[yr].est, 0); return (100 * pv / en).toFixed(1); };
  host.innerHTML = s + `<p class="sub" style="margin-top:6px"><span class="psleg" style="background:${col[0]}"></span>2019 <span class="psleg" style="background:${col[1]};margin-left:12px"></span>2024 &middot; ` +
    `Note: the table's K-12 total (${P.groups.Total.enrolled['2019'].est.toLocaleString()} enrolled in 2019) does not equal the sum of its grade groups (${G.filter(g => g !== 'Total').reduce((a, g) => a + P.groups[g].enrolled['2019'].est, 0).toLocaleString()}). ` +
    `Adding up the grade groups gives a private share of ${sum('2019')}% in 2019 and ${sum('2024')}% in 2024, lower than the published ${P.groups.Total.share['2019'].est}% and ${P.groups.Total.share['2024'].est}%. The grade groups in the table also differ from PPS's (K-5, 6-8, 9-12).</p>`;
  host.dataset.done = '1';
}
function renderAll() {""")
    rep("renderPrivCap(); renderHomeschool();", "renderPrivShare(); renderPrivCap(); renderHomeschool();")
    rep(".hstable { min-width: 640px; }", ".hstable { min-width: 640px; }\n.psleg { display: inline-block; width: 11px; height: 11px; border-radius: 2px; vertical-align: -1px; margin-right: 4px; }")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
