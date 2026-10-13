"""Southeast enrollment and program balancing, Phase 2 (the Southeast Guiding Coalition, SEGC): the changes PPS made
for each school in fall 2023, as notes on the explorer.
  - school report: a "Southeast enrollment balancing" panel listing the school's Phase 2 changes (and Phase 1 context),
    with PPS's planning estimate of its enrollment against actual 2025-26 enrollment
  - "Projected enrollment by school": a collapsible list of all Phase 2 schools, the changes in the enrollment
    charts' hover tips, and an "SEGC Phase 2" tag in the forecast accuracy table
Sources (archive/):
  Resolution 6513 - SE Enrollment and Program Balancing Phase 2.pdf (adopted May 2022; the changes, effective 2023-24)
  Implementation impacts by school program and year.pdf (school-by-school impact analysis of proposal F-3 amended:
    2021 enrollment and 2025 forecast, before and "if in place", students in each boundary change area)
  H_SEGC Phase 2 Final Report.pdf; 5_10_22_ Staff Report; PSU 2023-24 forecast, p22 (program relocations as made)
Data: D.segc. Safe to rerun: data is refreshed; page code is added once. Runs after patch_forecast_accuracy.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))

# per school: Phase 2 changes (Resolution 6513, with the impact analysis's counts of students enrolled in 2021-22 in
# each moved area); est = [2021-22 enrollment, 2025 forecast without the changes, 2021-22 if in place, 2025 forecast
# with the changes] from the impact analysis (proposal F-3 amended, which the board adopted)
S = {
 'Arleta': dict(p2=[
   'Area north of SE Holgate Blvd and west of SE 60th Ave/SE Foster Rd reassigned to Creston ES and Hosford MS (7 students)',
   'Area east of SE 72nd Ave/north of SE Boise St reassigned to Marysville ES (14 students)',
   'Area south of SE Woodstock Blvd reassigned to Woodmere ES and Lane MS (7 students)',
   'Area south of SE Holgate Blvd and west of SE 60th Ave reassigned to Woodstock ES and Lane MS (23 students)',
   'Gains the area north of SE Powell Blvd, east of SE 67th Ave, south of SE Woodward St and west of SE 82nd Ave from Bridger (11 students; includes the Kellogg MS site)',
   'Gains an area west of SE 72nd Ave between SE Holgate Blvd and SE Foster Rd from Marysville (6 students)'],
   p1='Phase 1 (2021-22): converted from K-8 to K-5; middle school students assigned to the new Kellogg MS.', est=[269, 290, 250, 277]),
 'Atkinson': dict(p2=[
   'Gains the area north of SE Woodward St, east of SE 67th Ave, south of SE Division St and west of SE 82nd Ave from Bridger (52 students)',
   'Neighborhood middle school changes from Mt. Tabor to Harrison Park MS (94 middle school students in 2021-22)',
   'Spanish immersion students continue at Kellogg MS, where Mt. Tabor\'s Spanish immersion program moved'], est=[342, 354, 388, 396]),
 'Bridger Creative Science': dict(p2=[
   'Creative Science School (K-8 focus option) moved from the Clark building to Bridger, which became Bridger-Creative Science K-8; Bridger English-program and future neighborhood students are assigned to it automatically and may opt out to Clark ES and Harrison Park MS',
   'Bridger\'s Spanish immersion program (two strands, K-5) moved to Lent',
   'Area north of SE Powell Blvd between SE 67th and 82nd Aves, south of SE Woodward St, reassigned to Arleta ES and Kellogg MS (11 students)',
   'Area north of SE Woodward St between SE 67th and 82nd Aves, south of SE Division St, reassigned to Atkinson ES and Harrison Park MS (52 students)'],
   p1='Phase 1 (2021-22): converted from K-8 to K-5, with middle school students assigned to Harrison Park (transfer preference to Kellogg).'),
 'Clark': dict(p2=[
   'Reopened as a neighborhood K-5 in the Clark building (Creative Science School\'s home since 2008), for the whole former Harrison Park K-8 attendance area',
   'Harrison Park\'s K-5 Chinese immersion program moved here; Clark feeds Harrison Park MS'], est=[None, None, 349, 372]),
 'Creston': dict(p2=[
   'Gains the area north of SE Holgate Blvd and west of SE 60th Ave/SE Foster Rd from Arleta (7 students)',
   'Middle school changes from Kellogg to Hosford MS (98 middle school students in 2021-22)'],
   p1='Phase 1 (2021-22): converted from K-8 to K-5; middle school students assigned to Kellogg MS.', est=[250, 225, 265, 254]),
 'Glencoe': dict(p2=['Area north of E. Burnside St and east of NE 60th Ave reassigned to Vestal ES and Harrison Park MS (41 students)'], est=[373, 375, 348, 364]),
 'Harrison Park': dict(p2=[
   'Converted from K-8 to a middle school (6-8): its K-5 students and K-5 Chinese immersion moved to the reopened Clark ES',
   'New feeder schools: Clark, Atkinson (from Mt. Tabor) and Vestal (from Roseway Heights), plus the area north of E. Burnside St/east of NE 60th Ave from Mt. Tabor',
   'Hosford\'s middle school Chinese immersion program (Woodstock\'s immersion feeder, 116 students) moved here',
   'Area south of SE Woodward St between SE 67th and 82nd Aves reassigned to Kellogg MS (10 middle school students)'], est=[529, 560, 558, 588]),
 'Hosford': dict(p2=[
   'Chinese immersion program (grades 6-8, 116 students) moved to Harrison Park MS',
   'Woodstock neighborhood now feeds Lane MS (82 middle school students in 2021-22)',
   'Creston neighborhood now feeds Hosford, from Kellogg (98 middle school students)',
   'The area of Arleta reassigned to Creston ES now feeds Hosford'], est=[629, 619, 536, 479]),
 'Kellogg': dict(p2=[
   'Creston neighborhood moved to Hosford MS (98 middle school students in 2021-22)',
   'Areas on its southern edge (from Arleta and Marysville, reassigned to Woodmere and Woodstock) moved to Lane MS (10 students)',
   'Mt. Tabor\'s Spanish immersion program (grades 6-8, Atkinson\'s immersion feeder, 69 students) moved here; Kellogg now hosts all southeast middle school Spanish immersion',
   'Gains the Bridger area reassigned to Arleta, which includes the Kellogg site'],
   p1='Phase 1 (2021-22): opened as a middle school for Arleta, Creston, Lent and Marysville, plus Spanish immersion from Bridger and Lent.', est=[684, 727, 659, 694]),
 'Lane': dict(p2=[
   'Woodstock neighborhood now feeds Lane, from Hosford (82 middle school students in 2021-22)',
   'Gains areas from Kellogg (the Arleta and Marysville areas reassigned to Woodmere and Woodstock; 10 students) and from Sellwood (the Lewis area reassigned to Whitman; 32 students)',
   'The Woodstock area reassigned to Woodmere continues to Lane'], est=[363, 363, 513, 598]),
 'Lent': dict(p2=[
   'Bridger\'s Spanish immersion program (two strands, K-5) moved here, making Lent a whole-school Spanish immersion K-5; Lent neighborhood students are guaranteed a place',
   'Lent\'s English (neighborhood) program moved to Marysville: current English-program students and future neighborhood students who opt out of immersion may enroll there, with bus service',
   'Kellogg remains the middle school for Lent neighborhood students'],
   p1='Phase 1 (2021-22): converted from K-8 to K-5; middle school students assigned to Kellogg MS.', est=[277, 277, 553, 527]),
 'Lewis': dict(p2=['An area at its eastern edge (described as west of SE 52nd Ave and east of SE 57th Ave) reassigned to Whitman ES and Lane MS (54 students)'], est=[337, 358, 286, 281]),
 'Marysville': dict(p2=[
   'Gains the area east of SE 72nd Ave/north of SE Boise St from Arleta (14 students)',
   'Area west of SE 72nd Ave between SE Holgate Blvd and SE Foster Rd reassigned to Arleta (6 students)',
   'Area east of SE 82nd Ave and south of SE Foster Rd reassigned to Woodmere ES and Lane MS (6 students)',
   'Receives Lent\'s English (neighborhood) program: Lent students who opt out of Spanish immersion (not in the estimate below)'],
   p1='Phase 1 (2021-22): converted from K-8 to K-5; middle school students assigned to Kellogg MS.', est=[248, 246, 260, 281]),
 'Mt Tabor': dict(p2=[
   'Atkinson neighborhood now feeds Harrison Park MS (94 middle school students in 2021-22)',
   'Area north of E. Burnside St and east of NE 60th Ave (reassigned from Glencoe to Vestal) moved to Harrison Park MS (17 students)',
   'Spanish immersion program (grades 6-8, 69 students) moved to Kellogg MS'], est=[645, 660, 479, 456]),
 'Roseway Heights': dict(p2=['Vestal neighborhood now feeds Harrison Park MS (119 middle school students in 2021-22)'], est=[604, 642, 524, 551]),
 'Sellwood': dict(p2=['The Lewis area reassigned to Whitman ES now feeds Lane MS instead of Sellwood (32 middle school students in 2021-22)']),
 'Vestal': dict(p2=[
   'Gains the area north of E. Burnside St and east of NE 60th Ave from Glencoe (41 students)',
   'Middle school changes from Roseway Heights to Harrison Park MS (119 middle school students in 2021-22)'], est=[207, 205, 271, 274]),
 'Whitman': dict(p2=[
   'Gains an area from Lewis (54 students)',
   'Gains the area south of SE Duke St and east of SE 57th Ave from Woodmere (51 students)'], est=[152, 189, 261, 303]),
 'Woodmere': dict(p2=[
   'Gains the area south of SE Woodstock Blvd from Arleta (7 students), east of SE 82nd Ave/south of SE Foster Rd from Marysville (6), and south of SE Woodstock Blvd/east of SE 52nd Ave from Woodstock (40)',
   'Area south of SE Duke St and east of SE 57th Ave reassigned to Whitman (51 students)'], est=[253, 247, 263, 298]),
 'Woodstock': dict(p2=[
   'Gains the area south of SE Holgate Blvd and west of SE 60th Ave from Arleta (23 students)',
   'Area south of SE Woodstock Blvd and east of SE 52nd Ave reassigned to Woodmere (40 students)',
   'Neighborhood middle school changes from Hosford to Lane MS (69 middle school students in 2021-22)',
   'Chinese immersion students now continue to Harrison Park MS instead of Hosford (116 students)'], est=[479, 515, 482, 502]),
}
missing = [k for k in S if k not in D['region_of']]
assert not missing, missing
D['segc'] = dict(
  sch=S, title='Southeast enrollment and program balancing, Phase 2',
  summary=('PPS Board Resolution 6513 (May 2022), from the Southeast Guiding Coalition (SEGC) process, effective fall 2023 (2023-24): '
           'Harrison Park K-8 became a middle school and Clark reopened as its K-5; Creative Science School moved to Bridger; immersion programs consolidated '
           '(Bridger Spanish to Lent, Mt. Tabor Spanish to Kellogg, Harrison Park K-5 Chinese to Clark, Hosford Chinese to Harrison Park); Atkinson and Vestal '
           'now feed Harrison Park, Creston feeds Hosford and Woodstock feeds Lane; and boundary changes among Arleta, Atkinson, Bridger, Creston, Glencoe, '
           'Lewis, Marysville, Vestal, Whitman, Woodmere and Woodstock.'),
  phase_in=('Boundary changes started with incoming kindergarten and 6th-grade students and other new students; current students could stay (legacy rights, '
            'with sibling transfers guaranteed), so their effect builds up through 2028-29 for K-5 and 2025-26 for middle schools. Program moves happened '
            'for all grades at once in 2023-24.'),
  est_note=('PPS\'s planning estimate (school-by-school impact analysis, proposal F-3 amended, April 2022): the school\'s enrollment forecast for 2025 '
            'with the changes, from PSU\'s March 2021 forecast.'),
  sources=[['Resolution 6513, SE Enrollment and Program Balancing Phase 2', 'https://www.pps.net/Page/13615'],
           ['SEGC Phase 2 school-by-school impact analysis and final report', 'https://www.pps.net/Page/13615']])
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + html[m.end(1):]
print(len(S), 'schools')

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function segcList' not in html:
    # projections section: the list of Phase 2 schools, under the section's description
    rep("""    <p class="sub" id="linesub"></p>
""", """    <p class="sub" id="linesub"></p>
    <details id="segcwrap" class="lineswrap"><summary>Southeast enrollment balancing (SEGC Phase 2, fall 2023): changes by school</summary><div id="segclist"></div></details>
""")
    rep("// ---------- enrollment forecast accuracy by region and school (scripts/patch_forecast_accuracy.py) ----------", r"""// ---------- SEGC Phase 2 notes (scripts/patch_segc.py) ----------
const segcOf = k => D.segc?.sch?.[k];
const segcTip = k => { const s = segcOf(k); return s ? `SEGC Phase 2 (fall 2023): ${s.p2.join('; ')}.` : ''; };
// PPS's 2025 planning estimate with the changes against actual 2025-26 enrollment
function segcEst(k) {
  const s = segcOf(k), a = D.series.SQ[k]?.[0];
  if (!s?.est?.[3] || a == null) return '';
  const d = a - s.est[3];
  return `PPS's planning estimate for 2025 with the changes: <b>${s.est[3]}</b>; actual ${D.years[0]}: <b>${Math.round(a)}</b> (${d >= 0 ? '+' : '&minus;'}${Math.abs(Math.round(d))})` +
    (s.est[0] != null ? `. In 2021-22 it enrolled ${s.est[0]}; without the changes PPS forecast ${s.est[1]} for 2025.` : '.');
}
function segcList() {
  const host = document.getElementById('segclist'); if (!host || !D.segc) return;
  const keys = Object.keys(D.segc.sch).sort((a, b) => short(byKey[a]?.name || a).localeCompare(short(byKey[b]?.name || b)));
  host.innerHTML = `<p class="sub" style="margin:8px 0">${esc(D.segc.summary)} ${esc(D.segc.phase_in)} PSU's forecasts from 2023-24 on include these changes; earlier editions did not, which is part of why older forecasts for these schools missed (see the forecast accuracy table below). Estimates: ${esc(D.segc.est_note)} Sources: ${D.segc.sources.map(s => `<a href="${esc(s[1])}">${esc(s[0])}</a>`).join('; ')} (copies in archive/).</p>` +
    '<div class="tablewrap"><table class="segctable"><thead><tr><th>School</th><th>Phase 2 changes (student counts: enrolled in 2021-22 in the area or program moved)</th><th>Enrollment: PPS 2025 estimate vs actual ' + D.years[0] + '</th></tr></thead><tbody>' +
    keys.map(k => { const s = D.segc.sch[k], a = D.series.SQ[k]?.[0];
      return `<tr><td><span class="nm">${typeof rpLink === 'function' ? rpLink(k, short(byKey[k]?.name || k)) : esc(short(byKey[k]?.name || k))}</span><span class="ty">${TYPE_LABEL[D.types.SQ[k]] || ''}</span></td>` +
        `<td style="text-align:left"><ul class="segcul">${s.p2.map(t => `<li>${esc(t)}</li>`).join('')}</ul>${s.p1 ? `<span class="muted" style="font-size:11.5px">${esc(s.p1)}</span>` : ''}</td>` +
        `<td>${s.est?.[3] ? `<span class="main">${s.est[3]} vs ${a == null ? '&mdash;' : Math.round(a)}</span><span class="muted" style="display:block;font-size:11px">${a == null ? '' : (a >= s.est[3] ? '+' : '&minus;') + Math.abs(Math.round(a - s.est[3]))}</span>` : '<span class="muted">&mdash;</span>'}</td></tr>`; }).join('') +
    '</tbody></table></div>';
}
// ---------- enrollment forecast accuracy by region and school (scripts/patch_forecast_accuracy.py) ----------""")
    rep("function renderAll() { renderReport(); renderFcAcc(); ", "function renderAll() { renderReport(); renderFcAcc(); segcList(); ")
    # enrollment chart hover tips
    rep("""        (capOf(best) ? `<br>${v > capOf(best) ? '<span class="tri"></span><b>Over capacity:</b> ' : '<span class="k">Utilization:</span> '}${Math.round(100 * v / capOf(best))}% of ${capOf(best).toLocaleString()} seats (2021)` : ''));""",
        """        (capOf(best) ? `<br>${v > capOf(best) ? '<span class="tri"></span><b>Over capacity:</b> ' : '<span class="k">Utilization:</span> '}${Math.round(100 * v / capOf(best))}% of ${capOf(best).toLocaleString()} seats (2021)` : '') +
        (segcOf(best) ? `<br><span class="k"><b>SEGC Phase 2 (fall 2023):</b> ${segcOf(best).p2.map(esc).join('; ')}</span>` : ''));""")
    # forecast accuracy table: a tag on Phase 2 schools
    rep("""<span class="ty">${TYPE_LABEL[D.types.SQ[k]] || ''}</span>` +
        `${scen !== 'SQ' && closed""", """<span class="ty">${TYPE_LABEL[D.types.SQ[k]] || ''}</span>` +
        `${segcOf(k) ? `<span class="muted" style="display:block;font-size:11px"><span class="segctag" title="${esc(segcTip(k) + ' Forecasts made before 2023-24 did not include these changes.')}">SEGC Phase 2</span></span>` : ''}` +
        `${scen !== 'SQ' && closed""")
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
.segctable { min-width: 760px; } .segctable td { vertical-align: top; } .segcul { margin: 0; padding-left: 18px; font-size: 12.5px; } .segcul li { margin: 2px 0; }
.segctag { display: inline-block; font-size: 10.5px; padding: 0 6px; border-radius: 999px; border: 1px solid var(--change); color: var(--change); cursor: help; }
.rpsegc ul { margin: 4px 0 6px; padding-left: 18px; } .rpsegc li { margin: 3px 0; }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
