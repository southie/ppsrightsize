"""Enrollment forecast accuracy on the explorer, from scripts/build_forecast_accuracy.py (PSU's PPS forecasts,
2016-17 to 2026-27 editions; source/pps-forecast/):
  - school report: under "Enrollment and capacity", each past edition's forecast for the school against its actual
    enrollment, and the average miss and lean by years ahead, post-COVID (2022-23 on) and pre-COVID editions
  - "Projected enrollment by school": a table of forecast accuracy by region (the region's total) with its schools,
    expandable, and the district (PSU's district total), with a Link button (fao = open regions)
Data: D.fcacc. A school-year is left out of the averages when an edition restated the school's history (programs
moving in or out); the chart still draws those forecasts, dashed.
Safe to rerun: data is refreshed; page code is added once. Runs after patch_deeplinks and patch_school_report.
"""
import csv, json, os, re, statistics, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
SRC = os.path.join(ROOT, 'source', 'pps-forecast')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))

H = json.load(open(os.path.join(SRC, 'forecast-history.json'), encoding='utf-8'))
SR = list(csv.DictReader(open(os.path.join(SRC, 'school-accuracy.csv'), encoding='utf-8')))
DR = [r for r in csv.DictReader(open(os.path.join(SRC, 'district-accuracy.csv'), encoding='utf-8')) if r['group'] == 'K-12']
EDS = H['editions']
PRE = [e for e in EDS if int(e[:4]) < 2022]; POST = [e for e in EDS if int(e[:4]) >= 2022]
KEY = {'Bridger': 'Bridger Creative Science', 'Cesar Chavez': 'César Chávez', 'Tubman': 'Harriet Tubman', 'Ida B Wells': 'Ida B Wells-Barnett',
       'King': 'MLK Jr', 'Sunnyside': 'Sunnyside Environmental'}
def key(n): return KEY.get(n, n)
LAST = D['years'][-1]
def yi(y): return int(y[:4])

def stat(rows):
    """[n, mean absolute % error, mean % error] (positive: forecast too high)"""
    if not rows: return None
    p = [float(r['pct']) for r in rows]
    return [len(p), round(statistics.mean(abs(v) for v in p), 1), round(statistics.mean(p), 1)]
def by_h(rows, hs=(1, 2, 3, 4, 5)):
    out = {}
    for era, eds in (('post', POST), ('pre', PRE)):
        out[era] = {h: s for h in hs for s in [stat([r for r in rows if r['edition'] in eds and int(r['h']) == h])] if s}
    return out

ok = [r for r in SR if r['basis'] == 'same']
sch = {}
for e in EDS:
    for n, r in H['schools'][e].items():
        k = key(n)
        if k not in D['region_of']: continue
        s = sch.setdefault(k, dict(a={}, f={}, bc=[]))
        for y, v in r['history'].items(): s['a'].setdefault(y, v)   # first edition reporting the year as history wins
        s['f'][e] = [v for y, v in sorted(r['forecast'].items()) if yi(y) <= yi(LAST)]
for r in SR:
    k = key(r['school'])
    if k in sch and r['basis'] == 'changed' and r['edition'] not in sch[k]['bc']: sch[k]['bc'].append(r['edition'])
# actuals as used in the error rows (the next edition's history), in place of the first-reported value
for r in SR:
    k = key(r['school'])
    if k in sch: sch[k]['a'][r['year']] = int(r['actual'])
for k, s in sch.items():
    s['a'] = dict(sorted(s['a'].items()))
    s['st'] = by_h([r for r in ok if key(r['school']) == k])

# regions: the region's total (its schools' forecasts summed against their actuals, school-years on the same basis)
def total_rows(keys):
    g = {}
    for r in ok:
        if key(r['school']) not in keys: continue
        t = g.setdefault((r['edition'], r['year']), dict(edition=r['edition'], h=r['h'], f=0, a=0))
        t['f'] += int(r['forecast']); t['a'] += int(r['actual'])
    return [dict(edition=t['edition'], h=t['h'], pct=100 * (t['f'] - t['a']) / t['a']) for t in g.values() if t['a']]
reg = {}
for rn in D['region_order']:
    keys = {k for k, v in D['region_of'].items() if v == rn}
    reg[rn] = dict(tot=by_h(total_rows(keys)), typ=by_h([r for r in ok if key(r['school']) in keys]))
LATE = POST[-2]   # the latest edition with an actual to check
dist = dict(tot=by_h(DR), typ=by_h(ok), latest=next([int(r['forecast']), int(r['actual'])] for r in DR if r['edition'] == LATE and r['year'] == LATE),
            band={era: {h: [sum(r['band'] == 'within' for r in x), len(x)] for h in (1, 2, 3, 4, 5)
                        for x in [[r for r in DR if r['edition'] in eds and int(r['h']) == h]] if x} for era, eds in (('post', POST), ('pre', PRE))})
D['fcacc'] = dict(eds=EDS, pre=PRE, post=POST, sch=sch, reg=reg, dist=dist,
                  source='PSU Population Research Center enrollment forecasts for PPS, 2016-17 to 2026-27 editions')
print(len(sch), 'schools;', 'no forecast history:', [k for k in D['region_of'] if k not in sch])
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'function renderFcAcc' not in html:
    rep("""    <div class="panels" id="panels"></div>
    </details>
""", """    <div class="panels" id="panels"></div>
    </details>
    <h3 class="cshead" id="fahead">How accurate have past enrollment forecasts been?</h3>
    <p class="sub">PPS's projections come from Portland State University's Population Research Center, which forecasts every year. This compares each edition's forecast for a school (its medium forecast; the district's is the medium scenario) with the enrollment PSU reported the next year. <b>Average miss</b> is the typical size of the error, either way; <b>lean</b> is the average signed error: positive means the forecasts were too high. Editions from 2022-23 on were made after the pandemic enrollment drop; the six before it (2016-17 to 2021-22) forecast straight into it, so they are shown apart. Regions are the region's total (its schools' forecasts summed), with the typical school's miss below; the district row is PSU's district total. Post-COVID results rest on four editions, so four- and five-year results are not available yet. School-years where an edition restated a school's past enrollment (a program moving in or out) are left out. Click a region to see its schools, and a school for its report, which charts every past forecast. Source: <a href="https://pdxscholar.library.pdx.edu/enrollmentforecasts/">PSU enrollment forecasts, 2016-17 to 2026-27</a>.</p>
    <div class="controls tabletools"><button id="fa-expand">Expand all regions</button></div>
    <div class="tablewrap" id="fcacc"></div>
""")
    rep("// ---------- links into tables (scripts/patch_deeplinks.py) ----------", r"""// ---------- enrollment forecast accuracy by region and school (scripts/patch_forecast_accuracy.py) ----------
const faOpen = new Set();
// average miss with its lean below; s = [n, mean absolute % error, mean % error]
function faCell(s, sub = '', tip = '') {
  if (!s) return '<td class="muted">&mdash;</td>';
  const [n, mape, bias] = s, lean = Math.abs(bias) < 1 ? 'no clear lean' : `leans ${bias > 0 ? 'high' : 'low'} ${bias > 0 ? '+' : '&minus;'}${Math.abs(bias).toFixed(1)}%`;
  return `<td title="${esc(`${tip}${n} forecast${n === 1 ? '' : 's'}: average miss ${mape.toFixed(1)}%, average signed error ${bias > 0 ? '+' : ''}${bias.toFixed(1)}% (positive: forecast too high)`)}">` +
    `<span class="main${mape >= 10 ? ' fa-big' : ''}">${mape.toFixed(1)}%</span><span class="muted" style="display:block;font-size:11px">${lean}${sub}</span></td>`;
}
const FA_COLS = [['post', 1], ['post', 2], ['post', 3], ['pre', 1], ['pre', 3], ['pre', 5]];
function renderFcAcc() {
  const host = document.getElementById('fcacc'), F = D.fcacc; if (!host || !F) return;
  const det = D.detail[scen] || {}, rng = e => `${e[0]} to ${e[e.length - 1]}`;
  const yrs = h => `${h} year${h === 1 ? '' : 's'} ahead`;
  let h = '<table class="fatable"><thead><tr><th rowspan="2">Region / school</th>' +
    `<th colspan="3" class="fa-era">Post-COVID editions<br><span style="font-weight:400">${rng(F.post.slice(0, -1))} (actuals so far)</span></th>` +
    `<th colspan="3" class="fa-era">Pre-COVID editions<br><span style="font-weight:400">${rng(F.pre)}</span></th>` +
    `<th rowspan="2">Latest check<br><span style="font-weight:400">${F.post[F.post.length - 2]} forecast vs actual</span></th></tr><tr>` +
    FA_COLS.map(([, n]) => `<th>${yrs(n)}</th>`).join('') + '</tr></thead><tbody>';
  const typSub = (s) => s ? ` &middot; typical school ${s[1].toFixed(1)}%` : '';
  const latest = k => {
    const s = F.sch[k], e = F.post[F.post.length - 2], f = s?.f[e]?.[0], a = s?.a[e];
    if (f == null || a == null) return '<td class="muted">&mdash;</td>';
    const p = 100 * (f - a) / a;
    return `<td title="${esc(`${e} edition forecast for ${e}: ${f}; actual ${a}`)}"><span class="main">${f.toLocaleString()} vs ${a.toLocaleString()}</span><span class="muted" style="display:block;font-size:11px">${p > 0 ? '+' : p < 0 ? '&minus;' : ''}${Math.abs(p).toFixed(1)}%</span></td>`;
  };
  for (const rn of [...D.region_order, 'District']) {
    const isReg = rn !== 'District', R = isReg ? F.reg[rn] : F.dist, open = faOpen.has(rn);
    const band = (era, n) => !isReg && F.dist.band[era]?.[n] ? ` &middot; ${F.dist.band[era][n][0]} of ${F.dist.band[era][n][1]} within low-high` : '';
    h += `<tr class="${isReg ? '' : 'dist'}"><td>${isReg ? `<button class="xbtn fa-x" data-r="${esc(rn)}" aria-expanded="${open}"><span class="car">&#9656;</span><span>${esc(rn)}</span></button>` : 'District (PSU district total)'}</td>` +
      FA_COLS.map(([era, n]) => faCell(R.tot[era]?.[n], typSub(R.typ[era]?.[n]) + band(era, n), `${isReg ? rn + ' total' : 'District total'}, ${era === 'post' ? 'post' : 'pre'}-COVID editions, ${yrs(n)}: `)).join('') +
      (isReg ? '<td></td>' : `<td><span class="main">${F.dist.latest[0].toLocaleString()} vs ${F.dist.latest[1].toLocaleString()}</span><span class="muted" style="display:block;font-size:11px">${(100 * (F.dist.latest[0] - F.dist.latest[1]) / F.dist.latest[1]).toFixed(1)}%</span></td>`) + '</tr>';
    if (!isReg || !open) continue;
    const keys = Object.keys(D.region_of).filter(k => D.region_of[k] === rn).sort((a, b) => short(byKey[a]?.name || a).localeCompare(short(byKey[b]?.name || b)));
    for (const k of keys) {
      const s = F.sch[k], closed = det[k]?.closed;
      h += `<tr class="srow${closed ? ' closed' : ''}"><td><span class="nm">${typeof rpLink === 'function' ? rpLink(k, short(byKey[k]?.name || k)) : esc(short(byKey[k]?.name || k))}</span><span class="ty">${TYPE_LABEL[D.types.SQ[k]] || ''}</span>` +
        `${scen !== 'SQ' && closed ? '<span class="muted" style="display:block;font-size:11px"><span class="stag closes">Closes</span></span>' : ''}${s?.bc?.length ? `<span class="muted" style="display:block;font-size:11px" title="${esc(`Editions ${s.bc.join(', ')}: a later edition restated this school's past enrollment, so those forecasts are not compared`)}">restated: ${s.bc.length} edition${s.bc.length === 1 ? '' : 's'} left out</span>` : ''}</td>` +
        (s ? FA_COLS.map(([era, n]) => faCell(s.st[era]?.[n], '', `${short(byKey[k]?.name || k)}, ${era}-COVID editions, ${yrs(n)}: `)).join('') + latest(k)
           : `<td colspan="7" class="muted" style="text-align:left">No PSU school forecast history (new school or not forecast separately)</td>`) + '</tr>';
    }
  }
  host.innerHTML = h + '</tbody></table>';
  host.querySelectorAll('.fa-x').forEach(b => b.onclick = () => { const r = b.dataset.r; faOpen.has(r) ? faOpen.delete(r) : faOpen.add(r); renderFcAcc(); });
  const ex = document.getElementById('fa-expand');
  if (ex) { ex.textContent = faOpen.size === D.region_order.length ? 'Collapse all regions' : 'Expand all regions';
    ex.onclick = () => { if (faOpen.size === D.region_order.length) faOpen.clear(); else D.region_order.forEach(r => faOpen.add(r)); renderFcAcc(); }; }
}
// ---------- links into tables (scripts/patch_deeplinks.py) ----------""")
    rep("function renderAll() { renderReport(); ", "function renderAll() { renderReport(); renderFcAcc(); ")
    rep("['privcap', 'privcap'], ['homeschool', 'homeschool'], ['virtual', 'virtual']];", "['privcap', 'privcap'], ['homeschool', 'homeschool'], ['virtual', 'virtual'], ['fcacc', 'fcacc']];")
    rep("  if (key === 'classsize') p.set('csy', csYear);", "  if (key === 'classsize') p.set('csy', csYear);\n  if (key === 'fcacc' && faOpen.size) p.set('fao', rIdx(faOpen));")
    rep("  if (q.get('pco')) rSet(q.get('pco'), pcOpen);", "  if (q.get('pco')) rSet(q.get('pco'), pcOpen);\n  if (q.get('fao')) rSet(q.get('fao'), faOpen);")
    rep(".tablewrap { overflow-x: auto; }", """.tablewrap { overflow-x: auto; }
.fatable { min-width: 860px; } .fatable th.fa-era { text-align: center; border-bottom: 1px solid var(--line); } .fatable .fa-big { color: var(--down); } .fatable td .main { white-space: nowrap; }
.rpplot path.fa-pre { fill: none; stroke: #c27c0e; stroke-width: 1.2; opacity: .75; } .rpplot path.fa-post { fill: none; stroke: var(--change); stroke-width: 1.5; opacity: .9; }
.rpplot path.fa-cur { fill: none; stroke: var(--change); stroke-width: 3; } .rpplot path.fa-act { fill: none; stroke: var(--text-primary); stroke-width: 2.4; }
.rpplot path.fa-rs { stroke-dasharray: 3 3; } .rpplot circle.fa-act { fill: var(--text-primary); } .rpplot path.fa-pre:hover, .rpplot path.fa-post:hover { stroke-width: 3; opacity: 1; }
.rplegend .k.fa-pre { border-color: #c27c0e; } .rplegend .k.fa-post { border-color: var(--change); border-top-width: 1.5px; } .rplegend .k.fa-cur { border-color: var(--change); border-top-width: 3px; } .rplegend .k.fa-act { border-color: var(--text-primary); }""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
