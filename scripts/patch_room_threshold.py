"""Room to grow: the conditions at which each school would reach its size threshold (ES 360, K-8 and MS 500, HS 1,100).
  Same method as the capacity fill (scripts/patch_room_fill.py): each open school's enrollment in the chosen year, each
  grade band scaled to the steady state of a district kindergarten class K, reaches its threshold at
  K_thr = threshold / that enrollment per kindergartner; shown as the kindergarten class, the capture of the district's
  5-year-olds, the births a year and the fertility rate.
  - scale: markers where half and 9 in 10 of the open schools are at or above their threshold;
  - below the scale: schools at threshold at the projection, the kindergarten at which half, 3 in 4, 9 in 10 and all
    reach it, and the schools that need the largest kindergarten;
  - region table: an "At threshold" column (each school's conditions or "at threshold now"; each region: schools
    below, and the kindergarten at which all of them reach it).
Runs after patch_room_fill and patch_room_tfr. Code added once.
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

if 'roomThrQ' not in html:
    # each school's kindergarten at its threshold
    rep("""    const v = D.series[s]?.[k]?.[yi], fc = byKey[k]?.fc; if (v == null || !fc) continue;
    const sp = roomSplit(k, s, yi, 1), per = Object.entries(sp).filter(([, w]) => w).reduce((a, [b, w]) => a + v * w * M[b] / dist[idx[b]], 0);
    if (per > 0) out[k] = { K: fc / per, v, fc };""",
        """    const v = D.series[s]?.[k]?.[yi], fc = byKey[k]?.fc; if (v == null || !fc) continue;
    const sp = roomSplit(k, s, yi, 1), per = Object.entries(sp).filter(([, w]) => w).reduce((a, [b, w]) => a + v * w * M[b] / dist[idx[b]], 0);
    const t = (yi < D.years.indexOf(D.impl_year) ? D.types.SQ[k] : D.types[s]?.[k]) || D.types.SQ[k], th = D.thresholds[t] || 0;   // patch_room_threshold
    if (per > 0) out[k] = { K: fc / per, v, fc, th, Kt: th / per };""")
    # quantiles and scale markers
    rep("""  const marks = [...(firstUp ? [[firstUp[1].K,""",
        """  const KT = Object.values(FILL).map(f => f.Kt).sort((a, b) => a - b), roomThrQ = p => KT.length ? KT[Math.max(0, Math.ceil(p * KT.length) - 1)] : null;
  const thrMarks = [[0.5, 'Half of schools at threshold'], [0.9, '9 in 10 schools at threshold']].map(([p, l]) => [roomThrQ(p), l, '#7c3aed']).filter(m => m[0] && (!Kproj || m[0] > Kproj));
  const marks = [...thrMarks, ...(firstUp ? [[firstUp[1].K,""")
    # block below the scale
    rep("""  // region table
  const rows = [...D.region_order, 'District'];""",
        """  // when schools would reach their size threshold
  const thrNow = KT.filter(K => Kproj && K <= Kproj).length, TK = Object.entries(FILL).sort((a, b) => b[1].Kt - a[1].Kt);
  const condT = K => `kindergarten <b>${n0(K)}</b>${Kproj ? ` (${K >= Kproj ? '+' : '&minus;'}${Math.abs(Math.round(100 * (K / Kproj - 1)))}%)` : ''}${age5 ? `, capture ${Math.round(100 * K / age5)}%` : ''}, births about ${n0(K / capNow)}, fertility rate about ${tfrOf(K)}`;
  document.getElementById('roomscale').innerHTML += `<div class="sub" style="margin-top:8px"><b>When schools would reach their size threshold</b> (${esc(lab)}, ${roomYear}; ES ${D.thresholds.ES}, K-8 and middle ${D.thresholds.K8}, high ${D.thresholds.HS} students): ` +
    `${thrNow} of ${KT.length} open schools are at or above it at the projection${Kproj ? ` (kindergarten ${n0(Kproj)})` : ''}.` +
    `<ul style="margin:4px 0 4px 18px;padding:0">${[[0.5, 'Half of the schools'], [0.75, '3 in 4'], [0.9, '9 in 10'], [1, 'Every school']].map(([p, l]) => { const K = roomThrQ(p); return !K ? '' : `<li>${l}: ${Kproj && K <= Kproj ? 'already at the projection' : condT(K)}</li>`; }).join('')}</ul>` +
    `Needing the largest kindergarten: ${TK.slice(0, 5).map(([k, f]) => `<b>${esc(short(byKey[k]?.name || k))}</b> <span class="muted">(${n0(f.v)} of ${n0(f.th)})</span> ${n0(f.Kt)} / fertility ${tfrOf(f.Kt)}`).join('; ')}. ` +
    `Schools at or above threshold as kindergarten grows: ${[3000, 3300, 3600, 4000, 4500].map(th => `${n0(th)}: ${KT.filter(K => K <= th).length}`).join(' &middot; ')} (of ${KT.length}). A school's own growth is modeled by its grade band at today's share of each band; boundary changes could move students between schools.</div>`;
  // region table
  const rows = [...D.region_order, 'District'];""")
    # region table column
    rep("""Full at<br><span style="font-weight:400">kindergarten / capture / births / fertility</span></th></tr></thead><tbody>`;""",
        """Full at<br><span style="font-weight:400">kindergarten / capture / births / fertility</span></th><th title="The district kindergarten class at which the school reaches its size threshold (each grade band at steady state), with the matching capture, births a year and fertility rate">At threshold<br><span style="font-weight:400">kindergarten / capture / births / fertility</span></th></tr></thead><tbody>`;""")
    rep("""${over ? `<span class="muted" style="display:block">${over} over capacity now</span>` : ''}</td>`; })()}</tr>`;""",
        """${over ? `<span class="muted" style="display:block">${over} over capacity now</span>` : ''}</td>`; })()}${(() => { const fs = keys.filter(k => FILL[k]), below = fs.filter(k => !Kproj || FILL[k].Kt > Kproj), Ka = fs.length ? Math.max(...fs.map(k => FILL[k].Kt)) : null;
      return `<td style="text-align:left;font-size:12px">${!fs.length ? '&ndash;' : !below.length ? 'all at threshold now' : `${below.length} of ${fs.length} below; all at ${n0(Ka)}${age5 ? ` / ${Math.round(100 * Ka / age5)}%` : ''} / ${n0(Ka / capNow)} / ${tfrOf(Ka)}`}</td>`; })()}</tr>`;""")
    rep("""(v == null ? `<td colspan="6" class="muted" style="text-align:left">closed in ${esc(lab)}</td>` :""",
        """(v == null ? `<td colspan="7" class="muted" style="text-align:left">closed in ${esc(lab)}</td>` :""")
    rep("""&middot; ${n0(f.K / capNow)} births &middot; ${tfrOf(f.K)}</td>`)(FILL[k])}`) + '</tr>';""",
        """&middot; ${n0(f.K / capNow)} births &middot; ${tfrOf(f.K)}</td>`)(FILL[k])}${(f => !f || !f.th ? '<td></td>' : Kproj && f.Kt <= Kproj ? '<td style="text-align:left;font-size:12px;color:var(--up)">at threshold now</td>' :
          `<td style="text-align:left;font-size:12px">K ${n0(f.Kt)}${Kproj ? ` (+${Math.round(100 * (f.Kt / Kproj - 1))}%)` : ''}${age5 ? ` &middot; ${Math.round(100 * f.Kt / age5)}%` : ''} &middot; ${n0(f.Kt / capNow)} births &middot; ${tfrOf(f.Kt)}</td>`)(FILL[k])}`) + '</tr>';""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
