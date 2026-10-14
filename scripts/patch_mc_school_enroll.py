"""Enrollment uncertainty section: projected enrollment by school. The school table gains each school's projected students
in the scenario and year being viewed: the page's value (PSU medium) and the simulated median and 90% range.
District uncertainty: rebuilt exactly from each stored draw's district grade-band totals, as the simulation does
(the school's enrollment net of affordable-housing students, scaled by its band's change net of housing students,
plus the housing students), so the capture-rate filter applies. With school-level forecast error: the same plus a
random school error at PSU's typical miss for the horizon (seeded, the same for a school across scenarios; mean one,
standing in for the simulation's rescaling to district totals). Needs D.mc.house / hband / school_sd (patch_mc_section.py).
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

if 'mcSchoolEnroll' not in html:
    rep("""function renderMCSchools(w, sc) {""", r"""// each school's simulated enrollment in the year and scenario being viewed (scripts/patch_mc_school_enroll.py)
const mcEnrollCache = {};
function mcSchoolEnroll(sc) {
  const ck = [sc, mcYear, mcVar, (mcCap || []).join(), adjOn].join('|'); if (mcEnrollCache[ck]) return mcEnrollCache[ck];
  const M = D.mc, j = M.out_years.indexOf(mcYear), yi = D.years.indexOf(mcYear), fi = +mcYear.slice(0, 4) - 2025, impl = D.years.indexOf(D.impl_year);
  const dv = M.variants.district, [lo, hi] = mcCap || [-1, 9], wd = dv.cap.map(c => c >= lo - 1e-9 && c <= hi + 1e-9 ? 1 : 0);
  const md = M.medium_bands[fi], hb = M.hband[j], sd = M.school_sd[j];
  const R = dv.bands.map(b => { const s = b[fi], r = (i, h) => ((s[i] / md[i]) * md[i] - h) / (md[i] - h); return { k5: r(1, hb[0]), m68: r(2, hb[1]), h912: r(3, hb[2]) }; });
  const out = {};
  M.schools.forEach((k, ki) => {
    const v = D.series[sc]?.[k]?.[yi]; if (v == null) { out[k] = null; return; }
    const t = (yi < impl ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k], f = k5Of(k, mcYear) ?? 0.66, h = Math.min(v, M.house[sc]?.[k]?.[j] || 0);
    let st = (ki + 1) * 2654435761 >>> 0;
    const nrm = () => { const u = () => { st = (st + 0x6D2B79F5) >>> 0; let x = st; x = Math.imul(x ^ (x >>> 15), x | 1); x ^= x + Math.imul(x ^ (x >>> 7), x | 61); return (((x ^ (x >>> 14)) >>> 0) + 0.5) / 4294967297; }; return Math.sqrt(-2 * Math.log(u())) * Math.cos(2 * Math.PI * u()); };
    const vals = R.map(r => { const m = t === 'ES' ? r.k5 : t === 'MS' ? r.m68 : t === 'HS' ? r.h912 : f * r.k5 + (1 - f) * r.m68;
      return (v - h) * m * (mcVar === 'school' ? Math.exp(sd * nrm() - sd * sd / 2) : 1) + h; });
    const [p5, p50, p95] = mcQ(vals, wd, [0.05, 0.5, 0.95]);
    out[k] = { page: v, p5, p50, p95, pb: mcProb(vals, wd, x => x < (D.thresholds[t] ?? 0) - 1e-9) };
  });
  return mcEnrollCache[ck] = out;
}
function renderMCSchools(w, sc) {""")
    # enrollment column in the school table
    rep("""  host.innerHTML = `<table style="min-width:520px"><thead><tr><th style="text-align:left">School</th>${D.mc.scen.map""",
        """  const EN = mcSchoolEnroll(sc), enc = r => { const e = EN[r.k]; return e ? `<td style="text-align:right;white-space:nowrap"><b>${Math.round(e.p50).toLocaleString()}</b> <span class="muted">(${Math.round(e.p5).toLocaleString()}&ndash;${Math.round(e.p95).toLocaleString()})</span><span class="muted" style="display:block;font-size:11px">page ${Math.round(e.page).toLocaleString()}</span></td>` : '<td class="muted" style="text-align:right">closes</td>'; };
  host.innerHTML = `<table style="min-width:640px"><thead><tr><th style="text-align:left">School</th><th style="text-align:right">Projected students, ${esc(sc === 'SQ' ? 'Status Quo' : LABEL[sc])} ${mcYear}<br><span style="font-weight:400">median (90% range)</span></th>${D.mc.scen.map""")
    rep("""<span class="muted">${TYPE_LABEL[typ(sc, r.k)] || ''}</span></td>${D.mc.scen.map(s => cell(r, s)).join('')}""",
        """<span class="muted">${TYPE_LABEL[typ(sc, r.k)] || ''}</span></td>${enc(r)}${D.mc.scen.map(s => cell(r, s)).join('')}""")
    rep("""`</tbody></table><p class="sub" style="margin:6px 0 0">Chance the school is below its size threshold in ${mcYear} (share of simulations).""",
        """`</tbody></table><p class="sub" style="margin:6px 0 0">Projected students: the simulated median and middle 90% for the scenario being viewed, and the page's value (PSU medium forecast); ${mcVar === 'school' ? 'school-level error is added here in the browser, so ranges can differ slightly from the simulation\\u2019s own' : 'rebuilt from each simulation\\u2019s district totals'}. Chance the school is below its size threshold in ${mcYear} (share of simulations).""")
    rep("""<th style="text-align:right">Threshold</th></tr></thead>""", """<th style="text-align:right">Threshold</th></tr></thead>""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
