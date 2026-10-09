"""rightsizing-scenario-explorer.html: each K-8 school's own share of K-5 vs 6-8 students, and the
"Modified enrollment model" switch (formerly "Census boundary adjustment").

Shares: ODE fall membership 2025-26 by grade (source/ode/fall_membership_2025_26.xlsx), K-5 / (K-5 + 6-8) per K-8,
moved with the district's year-by-year K-5 share (D.k5_share) so later years follow the forecast. Schools ODE does not
list separately (Odyssey) keep the district share.

With the switch on (default), every K-8 split uses the school's own share (k5Of): K-8s becoming K-5 send their own 6-8
share to the receiving middle school, and custom closures, keep-open returns, the Census boundary adjustment, commute
counts and staffing all split K-8s the same way. Off, the page shows the original model (district-wide share, no
boundary adjustment). Writes source/ode/k8-k5-shares-2025-26.csv. Safe to rerun.
"""
import csv, json, os, re, sys, unicodedata
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
ODE = os.path.join(ROOT, 'source', 'ode', 'fall_membership_2025_26.xlsx')
OUT = os.path.join(ROOT, 'source', 'ode', 'k8-k5-shares-2025-26.csv')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))

# ---------- shares ----------
def norm(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower().replace('.', '')
    n = re.sub(r"\b(elementary|middle|high|school|k-8|k8|k-5|academy|program|of|the|and)\b", ' ', n)
    return re.sub(r'[^a-z0-9]+', ' ', n).strip()

rows = [r for r in openpyxl.load_workbook(ODE, read_only=True)['School 20252026'].iter_rows(values_only=True)
        if r and r[0] == 'Portland SD 1J']
ode = {norm(r[2]): r for r in rows}
D['k8share'], out = {}, []
for k in sorted(k for k, t in D['types']['SQ'].items() if t == 'K8'):
    s = next(x for x in D['schools'] if x['key'] == k)
    cands = [norm(k), norm(s['name'])]
    r = next((ode[c] for c in cands if c in ode), None) or \
        next((v for c in cands for kk, v in ode.items() if c and kk.startswith(c)), None)
    if not r:
        print('no ODE grades for', k, '(keeps the district share)')
        continue
    g = [x or 0 for x in r[21:30]]
    k5, m68 = sum(g[:6]), sum(g[6:9])
    D['k8share'][k] = round(k5 / (k5 + m68), 4)
    out.append([k, r[2].strip(), k5, m68, D['k8share'][k], D['k5_share'][D['years'][0]]])
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['school_key', 'ode_school_name', 'k5_2025_26', 'g68_2025_26', 'k5_share', 'district_k5_share_2025_26'])
    w.writerows(out)
print(f"K-5 shares for {len(D['k8share'])} K-8 schools:", ', '.join(f'{k} {v:.1%}' for k, v in D['k8share'].items()))

# ---------- method notes (data) ----------
SW = '(checkbox beside the scenario buttons, on by default)'
NEW_SW = '(part of the "Modified enrollment model" checkbox beside the scenario buttons, on by default)'
D['assumptions'] = [a.replace('Census boundary adjustment ' + SW, 'Census boundary adjustment ' + NEW_SW) for a in D['assumptions']]
K8NOTE = ('K-8 grade mix ' + NEW_SW + ': each K-8 school is split into K-5 and 6-8 students with its own share from ODE fall '
          '2025 enrollment by grade (for example Sunnyside Environmental 60% K-5, Beverly Cleary 58%, Bridger 69%), moved with '
          'the district K-5 share year by year, instead of the district-wide share (66% in 2025-26). K-8s becoming K-5 send '
          'their own 6-8 share to the receiving middle school; custom closures, keeping a school open, commute counts and '
          'staffing split K-8s the same way. With the checkbox off, the page shows the original model.')
D['assumptions'] = [a for a in D['assumptions'] if not a.startswith('K-8 grade mix ')] + [K8NOTE]
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]


def rep(a, b, n=1):
    global html
    assert html.count(a) == n, (html.count(a), a[:110])
    html = html.replace(a, b)


HELPER = """// K-5 share of a K-8 school's students in a year: its own 2025-26 share (D.k8share) moved with the district trend when
// the "Modified enrollment model" switch is on, otherwise the district-wide share (D.k5_share)
var MODEL_ON = true;
try { MODEL_ON = localStorage.getItem('rsAdj') !== '0'; } catch (e) {}
function k5Of(k, year) {
  const d = D.k5_share[year], s = D.k8share && D.k8share[k];
  if (!MODEL_ON || s == null || d == null) return d;
  return Math.min(0.95, Math.max(0.05, s * d / D.k5_share[D.years[0]]));
}
"""

CONVERSIONS = """    const ser = D.series[sc], det = D.detail[sc], touched = new Set();
    // K-8s becoming K-5 send their own 6-8 share (k5Of) rather than the district-wide share the model used
    const k8done = new Set();
    for (const mv of D.flows[sc].moves || []) {
      const k = mv.from_key, to = mv.to_key;
      if (mv.kind !== 'grade' || k8done.has(k) || !k || !to || k === to || D.types.SQ[k] !== 'K8' || D.types[sc][k] !== 'ES' ||
          D.k8share?.[k] == null || !ser[k] || !ser[to] || det[k]?.closed || det[to]?.closed) continue;
      k8done.add(k);
      const amt = CY.map((_, i) => {
        if (i < IMPL_I || ser[k][i] == null || ser[to][i] == null || D.series.SQ[k][i] == null) return 0;
        const v = Math.round(D.series.SQ[k][i] * (D.k5_share[CY[i]] - k5Of(k, CY[i])));
        ser[k][i] -= v; ser[to][i] += v; return v;
      });
      const n31 = amt[Y31_I]; if (!n31) continue;
      const src = D.detail.SQ[k], r = src.e ? n31 / src.e : 0;
      for (const g of GRP) if (src.g[g] != null) {
        if (det[k].g[g] != null) det[k].g[g] = Math.max(0, det[k].g[g] - src.g[g] * r);
        if (det[to].g[g] != null) det[to].g[g] = Math.max(0, det[to].g[g] + src.g[g] * r);
      }
      touched.add(k); touched.add(to);
      ADJ.moves[sc].push({ f: k, t: to, band: '68', n: n31, k8: true });
    }
"""

LABEL = ('<label class="adjtog" id="adjtogl" title="Uses each K-8 school&#39;s own share of K-5 and 6-8 students (ODE fall 2025 '
         'enrollment by grade) instead of the district-wide share, and adds the attendance-area changes PPS drew but its '
         'enrollment model does not move (such as Duniway&#39;s southern area to Llewellyn), estimated from 2020 Census '
         'residents. Marked figures differ from PPS&#39;s published values. Uncheck for the original model.">'
         '<input type="checkbox" id="adjtog"> Modified enrollment model</label>')

if 'function k5Of' not in html:
    # helper goes after the esc line, before any code that calls it: other scripts find the data as
    # "const D = {...};" followed directly by "const esc", so nothing may go between them
    i = html.index('\nconst esc =', m.start()) + 1
    j = html.index('\n', i) + 1
    html = html[:j] + HELPER + html[j:]
    # every K-8 split goes through it
    rep("const t = (pre ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k], f = D.k5_share[cmYear];",
        "const t = (pre ? D.types.SQ[k] : D.types[sc]?.[k]) || D.types.SQ[k], f = k5Of(k, cmYear);")
    rep("function fracOf(t, band, yi) {\n  if (t !== 'K8') return 1;\n  const k5 = D.k5_share[CY[yi]];",
        "function fracOf(t, band, yi, k) {\n  if (t !== 'K8') return 1;\n  const k5 = k5Of(k, CY[yi]);")
    rep("st.ser[x][i] * fracOf(t, part.band, i) -", "st.ser[x][i] * fracOf(t, part.band, i, x) -")
    rep("const amt = v * fracOf(t, part.band, i);", "const amt = v * fracOf(t, part.band, i, x);")
    rep("const f31 = fracOf(t, part.band, Y31_I),", "const f31 = fracOf(t, part.band, Y31_I, x),")
    rep("const t = D.types.SQ[x], k5 = D.k5_share[CY[yi]];", "const t = D.types.SQ[x], k5 = k5Of(x, CY[yi]);")
    rep("band === 'k5' ? D.k5_share[CY[i]] : band === '68' ? 1 - D.k5_share[CY[i]] : 0;",
        "band === 'k5' ? k5Of(f, CY[i]) : band === '68' ? 1 - k5Of(f, CY[i]) : 0;")
    rep("D.k5_share[D.years[yi]] ?? K8_AVG_FRAC", "k5Of(k, D.years[yi]) ?? K8_AVG_FRAC", n=2)
    # the switch drives both corrections; conversions send each K-8's own 6-8 share
    rep("function applyAdjust(on) {\n  adjOn = on;", "function applyAdjust(on) {\n  adjOn = on; MODEL_ON = on;")
    rep("    const ser = D.series[sc], det = D.detail[sc], touched = new Set();\n", CONVERSIONS)
    rep("const adjMoveTxt = x => `",
        "const adjMoveTxt = x => x.k8 ? `${short(byKey[x.f].name)}'s own grade mix: ${Math.abs(x.n)} ${x.n > 0 ? 'more' : 'fewer'} "
        "6-8 students to ${short(byKey[x.t].name)}` : `")
    rep("mv.map(x => x.f === k ?", "mv.map(x => x.k8 ? adjMoveTxt(x) : x.f === k ?")
    # wording: one switch, two corrections
    rep("const t = `Census boundary adjustment, 2031-32: ", "const t = `Modified enrollment model, 2031-32: ")
    rep("(estimated from 2020 Census residents of the redrawn area). This differs",
        "(K-8 grade mix from ODE fall 2025 enrollment; boundary changes estimated from 2020 Census residents of the redrawn area). This differs")
    rep('aria-label="Census boundary adjustment">&#9670;', 'aria-label="Modified enrollment model">&#9670;')
    rep("""const ADJ_OFF = 'Uncheck "Census boundary adjustment" beside the scenario buttons to see the figures without it.';""",
        """const ADJ_OFF = 'Uncheck "Modified enrollment model" beside the scenario buttons to see the original model.';""")
    rep("with this page's Census estimate of boundary changes PPS drew but its enrollment figures may not move",
        "with this page's modified enrollment model (each K-8's own grade mix, and Census estimates of boundary changes PPS drew "
        "but its enrollment figures may not move)")
    i = html.index('<label class="adjtog" id="adjtogl" title="')
    j = html.index('</label>', i) + len('</label>')
    html = html[:i] + LABEL + html[j:]
    print('page code updated')

open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
