"""School report, "Enrollment and capacity" plot: PSU's low and high projections for the school, and what it would take for
the school to reach its size threshold.
  - Low/high: PSU publishes low, medium and high forecasts for the district by grade band (K-5, 6-8, 9-12), not by
    school. Each year, the school's projection for the scenario viewed is split into grade bands (roomSplit: its type,
    K-8s by their K-5 share) and each band scaled by PSU's district low/medium and high/medium ratio for that fall; drawn as
    a shaded range behind the lines, in the scenario's color, with the range in each dot's tooltip.
  - Note under the plot: in the last year, the district kindergarten class at which the school reaches its threshold
    (roomFill: each grade band at steady state, PSU's grade progression ratios), as the number of 5-year-olds living in
    PPS it would take at today's capture, the capture of the projected 5-year-olds it would take, and the births a year
    and fertility rate (as in Room to grow); or, if the school is at its threshold already, the kindergarten below which
    it would fall short. Whether PSU's high projection gets it there.
Code added once.
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

if 'rpPsuRange' not in html:
    rep(""".rpplot .impl { stroke: var(--axis); stroke-dasharray: 3 3; }""",
        """.rpplot .impl { stroke: var(--axis); stroke-dasharray: 3 3; }
.rpplot path.rng { stroke: none; opacity: .16; } .rpplot path.rng.lsq { fill: var(--none); } .rpplot path.rng.la { fill: var(--change); } .rpplot path.rng.lb { fill: #0f9b78; } .rpplot path.rng.lc { fill: #b0369a; }
.rplegend .k.rng { height: 9px; border: none; opacity: .3; } .rplegend .k.rng.lsq { background: var(--none); } .rplegend .k.rng.la { background: var(--change); } .rplegend .k.rng.lb { background: #0f9b78; } .rplegend .k.rng.lc { background: #b0369a; }""")
    rep("""function rpPlot(k, sc) {""", r"""// PSU's low and high projections for a school: its projection by grade band x PSU's district low/medium, high/medium
// ratio for that band and fall (scripts/patch_rp_psu_range.py)
function rpPsuRange(k, s) {
  const P = D.mc?.psu, v = D.series[s]?.[k]; if (!P || !v) return null;
  const B = { k5: 'K-5', m68: '6-8', h912: '9-12' };
  return D.years.map((yr, i) => {
    const j = P.falls.indexOf(2025 + i); if (v[i] == null || j < 0) return null;
    const sp = roomSplit(k, s, i, v[i]), r = (sc2, b) => P[sc2][B[b]][j] / P.medium[B[b]][j];
    return [Object.keys(sp).reduce((a, b) => a + sp[b] * r('low', b), 0), Object.keys(sp).reduce((a, b) => a + sp[b] * r('high', b), 0)];
  });
}
// what it would take for the school to reach its size threshold in the last year (scripts/patch_rp_psu_range.py)
function rpSustain(k, sc) {
  if (typeof roomFill !== 'function' || !D.pfa) return '';
  const yi = D.years.length - 1, yr = D.years[yi], f = roomFill(sc, yi)[k], dist = roomDist(yi); if (!f || !f.th || !dist) return '';
  const n0 = v => Math.round(v).toLocaleString(), Kproj = dist[0], capt = D.pfa.capture, age5 = (D.pfa.k_pfa[yr] || Object.values(D.pfa.k_pfa).slice(-1)[0]) / capt;
  const capNow = 2919 / 4121, tfr = K => (K / capNow / 3650).toFixed(2), R = rpPsuRange(k, sc)?.[yi], lab = sc === 'SQ' ? 'Status Quo' : LABEL[sc];
  const how = K => `a district kindergarten of about <b>${n0(K)}</b> a year (projected ${n0(Kproj)}, ${K >= Kproj ? '+' : '&minus;'}${Math.abs(Math.round(100 * (K / Kproj - 1)))}%): about <b>${n0(K / capt)}</b> 5-year-olds living in PPS at today's ${Math.round(100 * capt)}% capture (projected ${n0(age5)}), or capture of <b>${Math.round(100 * K / age5)}%</b> of the projected 5-year-olds (today ${Math.round(100 * capt)}%), or about ${n0(K / capNow)} births a year, a fertility rate of about <b>${tfr(K)}</b> children per woman (now about 1.0; U.S. about 1.6; replacement 2.1)`;
  const hi = R ? (R[1] >= f.th ? ` PSU's high projection puts it at about ${n0(R[1])} in ${yr}, at or above the threshold.` : ` Even PSU's high projection (about ${n0(R[1])} in ${yr}) leaves it below the threshold.`) : '';
  return `<p class="rpnote"><b>What would sustain this school:</b> ${f.v >= f.th && f.Kt <= Kproj ?
    `projected at ${n0(f.v)} in ${yr} (${esc(lab)}), at or above its size threshold of ${f.th}. It would fall below the threshold at ${how(f.Kt)}.` : f.v >= f.th ?
    `projected at ${n0(f.v)} in ${yr} (${esc(lab)}), at or above its size threshold of ${f.th}, but it would fall below once today's smaller kindergarten classes reach every grade. Staying at the threshold would take ${how(f.Kt)}.` :
    `projected at ${n0(f.v)} in ${yr} (${esc(lab)}), below its size threshold of ${f.th}. Reaching it would take ${how(f.Kt)}.${hi}`}` +
    ` <span class="muted">Each grade band at steady state (PSU's grade progression ratios), at the school's ${yr} share of the district's students in that band; boundary or program changes would change that share. Fertility rate: births scaled from about 1.0 in 2024 (PSU, Multnomah County) and about 3,650 births to PPS-area residents in 2025.</span></p>`;
}
function rpPlot(k, sc) {""")
    rep("""  const vals = [...cols.flatMap(s => ser[s]), fc, thr].filter(v => v != null);
  const ymax = Math.max(...vals) * 1.12 || 1;""",
        """  const rgS = cols.includes(sc) && (D.series[sc]?.[k] || []).slice(Y.indexOf(D.impl_year)).some(v => v != null) ? sc : 'SQ', RG = rpPsuRange(k, rgS);
  const vals = [...cols.flatMap(s => ser[s]), fc, thr, ...(RG || []).flatMap(r => r ? r : [])].filter(v => v != null);
  const ymax = Math.max(...vals) * 1.12 || 1;""")
    rep("""  const dots = s => ser[s].map((v, i) => v == null || (s !== 'SQ' && i < imp) ? '' :
    `<circle class="d ${RP_LINE[s]}${s === sc ? ' cur' : ''}" cx="${x(i)}" cy="${y(v)}" r="${s === sc ? 3 : 2.2}"><title>${esc(LABEL[s])}, ${Y[i]}: ${Math.round(v)}` +""",
        """  const rgPts = RG ? RG.map((r, i) => r && (rgS === 'SQ' || i >= imp - 1) ? [i, r] : null).filter(Boolean) : [];
  const rng = rgPts.length > 1 ? `<path class="rng ${RP_LINE[rgS]}" d="M${rgPts.map(([i, r]) => x(i).toFixed(1) + ',' + y(r[1]).toFixed(1)).join('L')}L${rgPts.slice().reverse().map(([i, r]) => x(i).toFixed(1) + ',' + y(r[0]).toFixed(1)).join('L')}Z"><title>PSU low to high, ${esc(LABEL[rgS])}</title></path>` : '';
  const dots = s => ser[s].map((v, i) => v == null || (s !== 'SQ' && i < imp) ? '' :
    `<circle class="d ${RP_LINE[s]}${s === sc ? ' cur' : ''}" cx="${x(i)}" cy="${y(v)}" r="${s === sc ? 3 : 2.2}"><title>${esc(LABEL[s])}, ${Y[i]}: ${Math.round(v)}${s === rgS && RG?.[i] ? ` (PSU low ${Math.round(RG[i][0])}, high ${Math.round(RG[i][1])})` : ''}` +""")
    rep("""    `<line class="impl" x1="${x(imp)}" x2="${x(imp)}" y1="${M.t}" y2="${H - M.b}"/>` +
    hline(fc, 'cap',""", """    `<line class="impl" x1="${x(imp)}" x2="${x(imp)}" y1="${M.t}" y2="${H - M.b}"/>` + rng +
    hline(fc, 'cap',""")
    rep("""    `<span><i class="k cap"></i>2021 functional capacity</span><span><i class="k thr"></i>size threshold</span><span><i class="k impl"></i>changes take effect (${D.impl_year})</span></div>` +""",
        """    `${rng ? `<span><i class="k rng ${RP_LINE[rgS]}"></i>PSU low to high, ${esc(LABEL[rgS])}</span>` : ''}<span><i class="k cap"></i>2021 functional capacity</span><span><i class="k thr"></i>size threshold</span><span><i class="k impl"></i>changes take effect (${D.impl_year})</span></div>` +
    (rng ? `<p class="muted rpnote">Shaded: PSU's low and high projections for ${esc(LABEL[rgS])}${RG?.[Y.length - 1] ? ` (${Y[Y.length - 1]}: ${Math.round(RG[Y.length - 1][0])} to ${Math.round(RG[Y.length - 1][1])})` : ''}. PSU publishes its low and high forecasts for the district by grade band, not by school; each year this school's projection in each band is scaled by the district's low/medium and high/medium ratio for that band${pfaOn ? ', applied to this page\\'s projection (district share of county population, PFA study)' : ''}.</p>` : '') + rpSustain(k, sc) +""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
