"""Staffing impact: positions no longer needed: the General Fund estimate beside the formula's annual cost. Each school's
formula staffing cost is scaled by its General Fund-to-formula ratio: its actual 2026-27 General Fund staffing (budget
school report; gfOf) over the formula's Status Quo 2026-27 staffing cost (the ratio the closures chart uses). Schools
with no budget report use the ratio of all schools that have one. A closing school's General Fund cost goes to zero;
receiving schools add their own ratio times their added formula cost. Shown in the table (region, district and school
rows), the summary line and the summary card. Code added once.
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

if 'staffGF' not in html:
    rep("""function renderStaffing() {""", """// General Fund estimate (scripts/patch_staff_gf.py): formula cost x the school's General Fund-to-formula ratio
let SGF_CACHE = { key: '', r: {} };
function staffGFRatio(k) {
  const key = JSON.stringify(caps);
  if (SGF_CACHE.key !== key) {
    const y0 = D.years.indexOf('2026-27'), r = {}; let g = 0, f = 0;
    for (const t of Object.keys(D.region_of)) { const gf = gfOf(t), fs = schoolFTE(t, 'SQ', y0), c = fs ? staffCost(fs) : 0;
      if (gf != null && c) { r[t] = gf / c; g += gf; f += c; } }
    r.__all = f ? g / f : 1; SGF_CACHE = { key, r };
  }
  return SGF_CACHE.r[k] ?? SGF_CACHE.r.__all;
}
function staffGF(keys, s, yi) { return keys.reduce((a, k) => { const f = schoolFTE(k, s, yi); return a + (f ? staffCost(f) * staffGFRatio(k) : 0); }, 0); }
const sgfTip = 'General Fund estimate: each school\\u2019s formula staffing cost times its own ratio of actual 2026-27 General Fund staffing (budget school report) to the formula\\u2019s 2026-27 staffing; schools without a budget report use the all-school ratio';
function renderStaffing() {""")
    # region / district rows
    rep("""    const cs = staffCost(sq), cc = staffCost(cur);
    h += isSQ ? `<td>${staffUSD(cs)}</td>` : `<td><span class="main">${staffUSD(cc - cs)}</span><span class="muted" style="display:block;font-size:11px">of ${staffUSD(cs)}</span></td>`;""",
        """    const cs = staffCost(sq), cc = staffCost(cur), gs = staffGF(keys, 'SQ', yi), gc = isSQ ? gs : staffGF(keys, scen, yi);
    h += isSQ ? `<td>${staffUSD(cs)}<span class="muted" style="display:block;font-size:11px" title="${sgfTip}">General Fund ${staffUSD(gs)}</span></td>`
      : `<td><span class="main">${staffUSD(cc - cs)}</span><span class="muted" style="display:block;font-size:11px">of ${staffUSD(cs)}</span>` +
        `<span style="display:block;font-size:12px;margin-top:2px" title="${sgfTip}">General Fund <b>${staffUSD(gc - gs)}</b> <span class="muted" style="font-size:11px">of ${staffUSD(gs)}</span></span></td>`;""")
    # school rows
    rep("""          (isSQ ? `<td>${staffUSD(staffCost(a))}</td>` : `<td>${staffUSD((b ? staffCost(b) : 0) - staffCost(a))}</td>`) + '</tr>';""",
        """          (isSQ ? `<td>${staffUSD(staffCost(a))}<span class="muted" style="display:block;font-size:11px" title="${sgfTip}">GF ${staffUSD(staffCost(a) * staffGFRatio(k))}</span></td>`
            : `<td>${staffUSD((b ? staffCost(b) : 0) - staffCost(a))}<span class="muted" style="display:block;font-size:11px" title="${esc(`${sgfTip}. This school: ${staffGFRatio(k).toFixed(2)}`)}">GF ${staffUSD(((b ? staffCost(b) : 0) - staffCost(a)) * staffGFRatio(k))}</span></td>`) + '</tr>';""")
    rep("""<th>Annual cost (2026-27 $)</th></tr></thead>""",
        """<th>Annual cost (2026-27 $)<br><span style="font-weight:400" title="${sgfTip}">formula; General Fund est.</span></th></tr></thead>""")
    # summary line
    rep("""a year in salary plus benefits (2026-27 dollars): <b>""",
        """a year in salary plus benefits (2026-27 dollars; about <b>${staffUSD(staffGF(keysOf('District'), 'SQ', yi) - staffGF(keysOf('District'), scen, yi)).replace('&minus;', '')}</b> at each school's actual General Fund staffing rate): <b>""")
    rep("""Status Quo in ${staffYear}: the formula allocates <b>${dsq.total.toFixed(0)}</b> licensed-equivalent FTE to these ${dsq.open} schools.""",
        """Status Quo in ${staffYear}: the formula allocates <b>${dsq.total.toFixed(0)}</b> licensed-equivalent FTE to these ${dsq.open} schools, about ${staffUSD(staffCost(dsq))} a year (about ${staffUSD(staffGF(keysOf('District'), 'SQ', yi))} at each school's actual General Fund staffing rate).""")
    # summary card
    rep("""    `Cost: about <b>${pos(s.usd)}</b> a year${pcS(s.usd, s.base.usd)} (salary + benefits, 2026-27 $)</div></div>`;""",
        """    `Cost: about <b>${pos(s.usd)}</b> a year${pcS(s.usd, s.base.usd)} (salary + benefits, 2026-27 $)` +
    ((ks, yi) => { const g0 = staffGF(ks, 'SQ', yi), g1 = staffGF(ks, scen, yi); return `<br><span title="${sgfTip}">General Fund est.: about <b>${pos(g1 - g0)}</b> a year${pcS(g1 - g0, g0)}</span>`; })(D.schools.map(x => x.key), D.years.indexOf(staffYear)) + `</div></div>`;""")
    rep("""      `Cost: <b>${pos(s.base.usd)}</b> a year (salary + benefits, 2026-27 $)` +""",
        """      `Cost: <b>${pos(s.base.usd)}</b> a year (salary + benefits, 2026-27 $)` +
      `<br><span title="${sgfTip}">General Fund est.: <b>${pos(staffGF(D.schools.map(x => x.key), 'SQ', D.years.indexOf(staffYear)))}</b> a year</span>` +""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
