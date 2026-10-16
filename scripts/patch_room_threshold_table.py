"""Room to grow, "When schools would reach their size threshold": a table instead of the list (patch_room_threshold.py).
Rows: the projection, then the district kindergarten at which half, 3 in 4, 9 in 10 and every open school reach their
threshold. Columns: schools at or above threshold, the district kindergarten class (vs projected), and for a low and a
high kindergarten capture rate the district's 5-year-olds that class takes and the fertility rate behind them.
  Capture = kindergartners / 5-year-olds living in PPS (D.pfa.capture today). Low and high: today's x the post-COVID
  average and pre-COVID high / fall 2025 kindergarten capture of births (Monte Carlo inputs, D.mc.params.capture).
  Fertility rate: 5-year-olds x (today's capture of 5-year-olds / capture of births: births five years earlier per
  5-year-old) over about 3,650 births at a rate of about 1.0 (PSU, Multnomah County 2024).
Code changed once.
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

if 'roomThrTable' not in html:
    rep("""    `<ul style="margin:4px 0 4px 18px;padding:0">${[[0.5, 'Half of the schools'], [0.75, '3 in 4'], [0.9, '9 in 10'], [1, 'Every school']].map(([p, l]) => { const K = roomThrQ(p); return !K ? '' : `<li>${l}: ${Kproj && K <= Kproj ? 'already at the projection' : condT(K)}</li>`; }).join('')}</ul>` +""",
        r"""    roomThrTable() +""")
    rep("""  // when schools would reach their size threshold
""", r"""  // when schools would reach their size threshold
  // as a table: district kindergarten, and the 5-year-olds and fertility rate behind it at a low and a high capture (scripts/patch_room_threshold_table.py)
  const roomThrTable = () => {
    const C = D.mc?.params?.capture, c0 = D.pfa?.capture; if (!C || !c0) return '';
    const caps = [['Low', c0 * C.post_covid_mean / C.fall_2025, 'the post-COVID average'], ['High', c0 * C.tri.b / C.fall_2025, 'the pre-COVID high']];
    const popG = K => { const b = K / (2919 / 4121), g = b / 3650 - 1; return `<b>${g >= 0 ? '+' : '&minus;'}${Math.abs(Math.round(100 * g))}%</b><span class="muted" style="display:block;font-size:11px">${b >= 3650 ? '+' : '&minus;'}${Math.round(Math.abs(b - 3650)).toLocaleString()} births a year</span>`; };   // population growth needed at today's fertility and capture
    const tf = pop5 => (pop5 * c0 / capNow / 3650).toFixed(2), G1 = 'border-left:2px solid var(--line)', G2 = G1 + ';background:var(--surface-2)', bg = ';background:var(--surface-2)';
    // elementary (K-5) schools on their own: the smallest schools, with the highest cost per student
    const tyOf = k => (yi < D.years.indexOf(D.impl_year) ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k];
    const KE = Object.entries(FILL).filter(([k]) => tyOf(k) === 'ES').map(([, f]) => f.Kt).sort((a, b) => a - b), qE = p => KE.length ? KE[Math.max(0, Math.ceil(p * KE.length) - 1)] : null;
    const rowsT = [['At the projection', Kproj, KT], ['Half of the schools', roomThrQ(0.5), KT], ['3 in 4', roomThrQ(0.75), KT], ['9 in 10', roomThrQ(0.9), KT], ['Every school', roomThrQ(1), KT],
      ...(KE.length ? [['Elementary (K-5) schools', null, KE], ['At the projection', Kproj, KE, 'es'], ['Half of the elementary schools', qE(0.5), KE, 'es'], ['3 in 4', qE(0.75), KE, 'es'], ['9 in 10', qE(0.9), KE, 'es']] : [])].filter(r => r[1] || r[1] === null);
    return `<div class="tablewrap" style="margin:6px 0"><table style="min-width:0"><thead><tr><th style="text-align:left" rowspan="2"></th><th rowspan="2">Schools at or above threshold</th><th rowspan="2">District kindergarten class</th><th rowspan="2" title="With fertility (about 1.0) and kindergarten capture held at today's levels, births grow only with the number of residents of childbearing age: the births a year this kindergarten class takes, over about 3,650 births to PPS-area residents in 2025">Population growth needed<br><span style="font-weight:400">at today's fertility and capture</span></th>` +
      caps.map(([l, c, why], i) => `<th colspan="2" style="text-align:center;${i ? G2 : G1};border-bottom:1px solid var(--line)" title="${Math.round(100 * c)}% of 5-year-olds living in PPS: today's ${Math.round(100 * c0)}% scaled by ${why}">${l} capture, ${Math.round(100 * c)}%</th>`).join('') + `</tr><tr>` +
      caps.map((_, i) => `<th style="${i ? G2 : G1};font-weight:400">5-year-olds in PPS</th><th style="font-weight:400${i ? bg : ''}">Fertility rate</th>`).join('') + `</tr></thead><tbody>` +
      rowsT.map(([l, K, S, g]) => { if (K === null) return `<tr><td colspan="8" style="text-align:left;font-weight:600;padding-top:10px;border-top:2px solid var(--line)">${l} <span class="muted" style="font-weight:400">(the smallest schools, with the highest cost per student; K-8s not included)</span></td></tr>`;
        const nAtK = S.filter(x => x <= K + 1e-6).length, reached = Kproj && K <= Kproj && l !== 'At the projection';
        return `<tr${l === 'At the projection' ? ' class="dist"' : ''}><td style="text-align:left${g ? ';padding-left:14px' : ''}">${l}${reached ? ' <span class="muted">(already at the projection)</span>' : ''}</td><td style="text-align:right">${nAtK} of ${S.length}${g ? ' elementary' : ''}</td>` +
          `<td style="text-align:right"><b>${n0(K)}</b>${Kproj && l !== 'At the projection' ? ` <span class="muted">(${K >= Kproj ? '+' : '&minus;'}${Math.abs(Math.round(100 * (K / Kproj - 1)))}%)</span>` : ''}</td><td style="text-align:right">${popG(K)}</td>` +
          caps.map(([, c], i) => `<td style="text-align:right;${i ? G2 : G1}">${n0(K / c)}</td><td style="text-align:right${i ? bg : ''}">${tf(K / c)}</td>`).join('') + `</tr>`; }).join('') +
      `</tbody></table></div><p class="muted" style="font-size:12px;margin:0 0 4px">Each row at steady state (every grade grown from that kindergarten class; PSU's grade progression ratios), each school at its ${esc(roomYear)} share of the district's students in its grade band. Capture: kindergartners as a share of the 5-year-olds living in PPS (today ${Math.round(100 * c0)}%); low and high scale today's by the post-COVID average (${Math.round(100 * C.post_covid_mean)}% of births five years earlier) and the pre-COVID high (${Math.round(100 * C.tri.b)}%) against fall 2025 (${Math.round(100 * C.fall_2025)}%). Fertility rate (children per woman, district-wide): the births behind those 5-year-olds, scaled from about 1.0 in 2024 (PSU, Multnomah County) for about 3,650 births to PPS-area residents in 2025; U.S. about 1.6, replacement 2.1. A higher capture rate takes fewer 5-year-olds, and so a lower fertility rate, for the same class. Population growth needed: with fertility (about 1.0) and capture held at today's levels, births rise only with the number of residents of childbearing age, so the growth shown (the births a year the class takes at today's capture, over about 3,650 births in 2025) is the growth in families with young children the district would need, from in-migration or new housing. The projection itself is about ${Math.round(100 * (Kproj / (2919 / 4121) / 3650 - 1))}% above that base (PSU expects capture to recover).</p>`;
  };
""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
