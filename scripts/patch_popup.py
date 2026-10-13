"""Main map school popup (the panel that opens on the left): enrollment now, in the year scenarios take effect and in
2031-32 (each against the school's size threshold, highlighted when above it; 2031-32 with the school's typical 5-year
forecast miss from PSU's past forecasts, D.fcacc), the 2026-27 General Fund staffing spending per student (PPS budget
school report, D.staff_actual), the formula staffing cost in the selected staffing year (and, for a closing school, the
net change after its receiving schools add staff), an "Open school report" button, and the private-school alternatives
collapsed under a heading. Code added once.
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

if 'function popFacts' not in html:
    rep("""    altSection(s) +
    `<h4>Enrollment</h4><div class="row">2025-26: ${s.enroll_2526}</div>` +
    (s.fc ? `<div class="row">2021 functional capacity: ${s.fc.toLocaleString()}${e != null ? ` · 2031-32 utilization ${Math.round(100 * e / s.fc)}%` : ''}</div>` : '') +
    (s.fc_note ? `<div class="row" style="color:#57606a;font-size:11.5px">${esc(s.fc_note)}</div>` : '') +
    (e == null ? `<div class="row">2031-32: closed</div>` : `<div class="row">2031-32 projected (${LABEL[scen]}): <b style="display:inline">${e}</b> · threshold ${t} · ${e >= t ? 'above' : 'below'}</div>`) + '</div>';""",
        """    popFacts(s) +
    (s.fc ? `<div class="row">2021 functional capacity: ${s.fc.toLocaleString()}${e != null ? ` · 2031-32 utilization ${Math.round(100 * e / s.fc)}%` : ''}</div>` : '') +
    (s.fc_note ? `<div class="row" style="color:#57606a;font-size:11.5px">${esc(s.fc_note)}</div>` : '') +
    (altSection(s) ? `<details class="popalt"><summary>Private school alternatives</summary>${altSection(s)}</details>` : '') + '</div>';""")
    rep("""  return `<div class="pop"><b>${esc(s.name)}</b><span class="tag ${rl}">${tg}</span> <span style="color:#57606a">${esc(s.region)}</span>` +""",
        """  return `<div class="pop"><b>${esc(s.name)}</b><span class="tag ${rl}">${tg}</span> <span style="color:#57606a">${esc(s.region)}</span>` +
    `<div class="row"><button type="button" class="popreport" data-k="${esc(s.key)}">Open school report &rarr;</button></div>` +""")
    rep("""function privPopup(x) {""", r"""// enrollment against the threshold, the forecast's typical miss, budget per student and staffing cost (scripts/patch_popup.py)
function popFacts(s) {
  const k = s.key, Y = D.years, sc = scen, base = sc === 'C' ? custom.base : sc;
  const yImp = Y.indexOf(D.impl_year), y31 = Y.indexOf('2031-32');
  const typ = i => (i >= yImp ? (D.types[sc] || {})[k] : null) || D.types.SQ[k];
  const thr = i => D.thresholds[typ(i)];
  const val = (i, sc_) => (D.series[sc_] || {})[k]?.[i];
  const vs = (v, t) => v == null ? '<span class="muted">closed</span>' : `<b style="display:inline">${Math.round(v).toLocaleString()}</b> ` +
    (v >= t ? `<span class="popabove" title="At or above the size threshold for this school type (${t})">above threshold ${t}</span>` : `<span class="muted">below threshold ${t}</span>`);
  // the school's typical 5-year forecast miss (PSU's past forecasts, both eras), else the typical school's
  const st = D.fcacc?.sch?.[k]?.st, F = D.fcacc;
  const pool = [st?.post?.[5], st?.pre?.[5]].filter(Boolean);
  let miss = pool.length ? pool.reduce((a, x) => a + x[1] * x[0], 0) / pool.reduce((a, x) => a + x[0], 0) : null, own = pool.length > 0;
  if (miss == null && F) { const t5 = [F.dist.typ.post?.[5], F.dist.typ.pre?.[5]].filter(Boolean); if (t5.length) miss = t5.reduce((a, x) => a + x[1] * x[0], 0) / t5.reduce((a, x) => a + x[0], 0); }
  const e31 = val(y31, sc), eImp = val(yImp, sc);
  let h = `<h4>Enrollment</h4><div class="row">2025-26 (actual): <b style="display:inline">${s.enroll_2526.toLocaleString()}</b></div>`;
  h += `<div class="row">${D.impl_year} projected, ${esc(LABEL[sc])}: ${vs(eImp, thr(yImp))}</div>`;
  h += `<div class="row">2031-32 projected, ${esc(LABEL[sc])}: ${vs(e31, thr(y31))}` +
    (e31 != null && miss != null ? ` <span class="muted" title="${esc(own ? "This school's average miss five years ahead in PSU's past forecasts (2016-17 to 2021-22 editions; post-COVID editions do not reach five years yet)" : "The typical PPS school's average miss five years ahead in PSU's past forecasts")}">(&plusmn;${Math.round(e31 * miss / 100).toLocaleString()}, ${Math.round(miss)}% typical 5-year forecast miss${own ? '' : ', all schools'})</span>` : '') + '</div>';
  // General Fund staffing spending per student, 2026-27 budget (PPS budget school report)
  const sa = D.staff_actual?.schools?.[k], SY = D.staff_actual?.years || [];
  h += '<h4>Cost</h4>';
  if (sa?.salaries) {
    const i = SY.indexOf('2026-27'), all = sa.salaries[i] == null ? null : sa.salaries[i] + (sa.payroll?.[i] || 0);
    const gf = all != null && sa.alloc_fte?.[i] ? all * sa.gf_fte[i] / sa.alloc_fte[i] : null, en = val(Y.indexOf('2026-27'), 'SQ');
    if (gf != null && en) h += `<div class="row" title="Salaries and payroll costs of the school-allocated staff paid from the General Fund (estimated by its share of the school's FTE), PPS 2026-27 Proposed Budget, Vol. 2, over projected 2026-27 enrollment">General Fund staffing per student, 2026-27 budget: <b style="display:inline">$${Math.round(gf / en).toLocaleString()}</b> <span class="muted">(all school-allocated funds $${Math.round(all / en).toLocaleString()})</span></div>`;
  }
  // formula staffing cost in the selected staffing year; for a closing school, the net change after receivers add staff
  const yi = Y.indexOf(staffYear), closed = (D.detail[sc] || {})[k]?.closed;
  const fte = typeof schoolFTE === 'function' ? schoolFTE(k, closed ? 'SQ' : sc, yi) : null;
  if (fte) {
    const cost = staffCost(fte), net = closed && typeof closureStaffNet === 'function' ? closureStaffNet(k, base, yi) : null;
    h += `<div class="row" title="This page's estimate from PPS's 2026-27 staffing formula at average salaries and payroll costs (see Staffing impact)">Estimated staffing cost, ${staffYear}${closed ? ' (Status Quo)' : `, ${esc(LABEL[sc])}`}: <b style="display:inline">${usdM1(cost)}</b> a year` +
      (net ? ` <span class="${net.usd < 0 ? 'popsave' : 'muted'}">(net ${net.usd < 0 ? '&minus;' : '+'}${usdM1(Math.abs(net.usd))} a year if it closes, after the receiving schools add staff)</span>` : '') + '</div>';
  }
  return h;
}
function privPopup(x) {""")
    # the report button: close the panel and open the school report
    rep("""document.getElementById('dockbody').addEventListener('click', async e => {""",
        """document.getElementById('dockbody').addEventListener('click', e => {
  const b = e.target.closest('.popreport'); if (!b) return;
  e.preventDefault(); closeDock(); if (typeof rpOpen === 'function') rpOpen(b.dataset.k);
});
document.getElementById('dockbody').addEventListener('click', async e => {""")
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
.popreport { margin: 6px 0 2px; font: inherit; font-size: 12.5px; font-weight: 600; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--change); background: var(--surface-1); color: var(--change); cursor: pointer; }
.popreport:hover { background: var(--change); color: #fff; }
.popabove { font-weight: 700; color: #17803a; } .popsave { font-weight: 600; color: #17803a; }
details.popalt { margin-top: 8px; } details.popalt > summary { cursor: pointer; font-weight: 600; font-size: 12.5px; margin: 4px 0; }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
