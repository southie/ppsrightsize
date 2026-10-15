"""Room to grow: the conditions at which each school would reach its capacity.
  For each open school: its enrollment in the chosen year, each grade band scaled to the steady state of a district
  kindergarten class K (band students per kindergartner, PSU's grade progression ratios, over the district's band in
  that year), reaches the building's 2021 functional capacity at K_full = capacity / that enrollment per kindergartner.
  Shown as the kindergarten class, the capture of the district's 5-year-olds and the births a year (at today's capture).
  - the "what would fill the buildings" scale marks the first school at capacity (schools already over it are counted
    separately);
  - below the scale, the first schools to fill, with their conditions;
  - the region table gets a "Full at" column: each school's conditions (or "over capacity now"), and each region's
    first school.
Runs after patch_room_to_grow. Code added once.
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

if 'roomFill' not in html:
    rep("""function renderRoom() {""", r"""// the district kindergarten class at which each open school reaches its capacity (scripts/patch_room_fill.py)
function roomFill(s, yi) {
  const M = roomMult(), dist = roomDist(yi), idx = { k5: 1, m68: 2, h912: 3 }, out = {};
  if (!dist) return out;
  for (const k of Object.keys(D.region_of)) {
    const v = D.series[s]?.[k]?.[yi], fc = byKey[k]?.fc; if (v == null || !fc) continue;
    const sp = roomSplit(k, s, yi, 1), per = Object.entries(sp).filter(([, w]) => w).reduce((a, [b, w]) => a + v * w * M[b] / dist[idx[b]], 0);
    if (per > 0) out[k] = { K: fc / per, v, fc };
  }
  return out;
}
function renderRoom() {""")
    # scale marker and the first-to-fill list
    rep("""  const marks = [[Kthr, 'Schools average their size threshold', 'var(--down)'],""",
        """  const FILL = roomFill(sc, yi), FK = Object.entries(FILL).sort((a, b) => a[1].K - b[1].K), overNow = FK.filter(([, f]) => Kproj && f.K <= Kproj), firstUp = FK.find(([, f]) => !Kproj || f.K > Kproj);
  const marks = [...(firstUp ? [[firstUp[1].K, `First school full (${short(byKey[firstUp[0]]?.name || firstUp[0])})`, '#b45309']] : []), [Kthr, 'Schools average their size threshold', 'var(--down)'],""")
    rep("""  // region table
  const rows = [...D.region_order, 'District'];""",
        """  // the first schools to fill and the conditions
  const cond = f => `kindergarten <b>${n0(f.K)}</b>${Kproj ? ` (${f.K >= Kproj ? '+' : '&minus;'}${Math.abs(Math.round(100 * (f.K / Kproj - 1)))}%)` : ''}${age5 ? `, capture ${Math.round(100 * f.K / age5)}%` : ''}, births about ${n0(f.K / capNow)}`;
  const nAt = th => FK.filter(([, f]) => f.K <= th).length;
  document.getElementById('roomscale').innerHTML += `<div class="sub" style="margin-top:6px"><b>When schools would reach capacity</b> (${esc(lab)}, ${roomYear}): ` +
    (overNow.length ? `${overNow.map(([k, f]) => `${esc(short(byKey[k]?.name || k))} (${n0(f.v)} of ${n0(f.fc)} seats)`).join(', ')} ${overNow.length === 1 ? 'is' : 'are'} over capacity at the projection already. ` : '') +
    `<ol style="margin:4px 0 4px 18px;padding:0">${FK.filter(([, f]) => !Kproj || f.K > Kproj).slice(0, 6).map(([k, f]) => `<li><b>${esc(short(byKey[k]?.name || k))}</b> <span class="muted">${TYPE_LABEL[(D.types[sc] || {})[k] || D.types.SQ[k]] || ''}, ${n0(f.v)} of ${n0(f.fc)} seats (${pc(f.v, f.fc)})</span>: full at ${cond(f)}</li>`).join('')}</ol>` +
    `Schools at or over capacity as kindergarten grows: ${[3000, 3300, 3600, 4000, 4500].map(th => `${n0(th)}: ${nAt(th)}`).join(' &middot; ')} (of ${FK.length}). A school's own growth is modeled by its grade band; boundary changes could spread students to buildings with room.</div>`;
  // region table
  const rows = [...D.region_order, 'District'];""")
    rep("""<th>K-12</th></tr></thead><tbody>`;""",
        """<th>K-12</th><th title="The district kindergarten class at which the school reaches its capacity (each grade band at steady state), with the matching capture of the district's 5-year-olds and births a year at today's capture">Full at<br><span style="font-weight:400">kindergarten / capture / births</span></th></tr></thead><tbody>`;""")
    rep("""${ROOM_B.map(([b]) => cell(o, b)).join('')}${cell(o, 'all')}</tr>`;""",
        """${ROOM_B.map(([b]) => cell(o, b)).join('')}${cell(o, 'all')}${(() => { const fs = keys.filter(k => FILL[k]).sort((a, b) => FILL[a].K - FILL[b].K); const f1 = fs.find(k => !Kproj || FILL[k].K > Kproj); const over = fs.filter(k => Kproj && FILL[k].K <= Kproj).length;
      return `<td style="text-align:left;font-size:12px">${f1 ? `first: <b>${esc(short(byKey[f1]?.name || f1))}</b> at ${n0(FILL[f1].K)}${age5 ? ` / ${Math.round(100 * FILL[f1].K / age5)}%` : ''} / ${n0(FILL[f1].K / capNow)}` : '&ndash;'}${over ? `<span class="muted" style="display:block">${over} over capacity now</span>` : ''}</td>`; })()}</tr>`;""")
    rep("""(v == null ? `<td colspan="5" class="muted" style="text-align:left">closed in ${esc(lab)}</td>` :""",
        """(v == null ? `<td colspan="6" class="muted" style="text-align:left">closed in ${esc(lab)}</td>` :""")
    rep("""<span class="muted" style="display:block;font-size:11px">${pc(v, fc)} full</span></td>`) + '</tr>';""",
        """<span class="muted" style="display:block;font-size:11px">${pc(v, fc)} full</span></td>${(f => !f ? '<td></td>' : Kproj && f.K <= Kproj ? '<td style="text-align:left;font-size:12px;color:var(--down);font-weight:600">over capacity now</td>' :
          `<td style="text-align:left;font-size:12px;${Kproj && f.K < Kproj * 1.1 ? 'color:#b45309;font-weight:600' : ''}">K ${n0(f.K)}${Kproj ? ` (+${Math.round(100 * (f.K / Kproj - 1))}%)` : ''}${age5 ? ` &middot; ${Math.round(100 * f.K / age5)}%` : ''} &middot; ${n0(f.K / capNow)} births</td>`)(FILL[k])}`) + '</tr>';""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
