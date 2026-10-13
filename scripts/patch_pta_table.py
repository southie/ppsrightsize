"""Parent-group fundraising by school, from IRS Form 990 filings (scripts/fetch_pta_990.py: ProPublica Nonprofit Explorer),
as a card above "Private school share of PPS-area students": a table by region (expand for schools) of each group type's
revenue in its latest filing with dollar figures: PTA / PTO (incl. PTSA), school foundations and "friends of" groups,
booster clubs, alumni associations; the total, and PTA / PTO revenue per student (2025-26 enrollment). Region and
district rows are sums. School rows list each group with its filing year and a link to its filings. Groups that file
only the 990-N e-Postcard (gross receipts normally $50,000 or less) have no dollar figures and are counted separately.
"Recent filings only" (default on) leaves out filings for tax years before 2022. Schools closing in the scenario being
viewed are tagged. Data: D.pta (refreshed on rerun); code added once.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
P = json.load(open(os.path.join(ROOT, 'source', 'pta', 'pta-990.json'), encoding='utf-8'))

def cat(o):
    k, nm = o['kind'], f"{o.get('name') or ''} {o.get('sub_name') or ''}"
    if k == 'PTA/PTO': return 'pta'
    if k == 'booster' or re.search(r'boost', nm, re.I): return 'boost'
    if k == 'alumni': return 'alum'
    return 'fdn'
def label(o):
    s = o.get('sub_name') or o.get('name') or ''
    s = re.sub(r'^Pta Oregon Congress\s*', '', s, flags=re.I).strip() or (o.get('name') or '')
    s = re.sub(r'\bPta\b', 'PTA', re.sub(r'\bPtsa\b', 'PTSA', re.sub(r'\bPto\b', 'PTO', s)))
    return s.replace('Booste R', 'Booster')

out = {}
for k, orgs in P['schools'].items():
    if k not in D['region_of']: continue
    rows = []
    for o in orgs:
        f = max(o['filings'], key=lambda f: f['year'] or 0) if o['filings'] else None
        rows.append([o['ein'], cat(o), label(o), f['year'] if f else None, f['form'] if f else '990-N',
                     f['revenue'] if f else None, f['contributions'] if f else None, f['net_assets'] if f else None])
    out[k] = rows
D['pta'] = {'fetched': P.get('fetched'), 'source': P.get('source'), 'schools': out}
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
print(len(out), 'schools;', sum(len(v) for v in out.values()), 'groups')

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'renderPTA' not in html:
    rep("""  <section class="card">
    <h2>Private school share of PPS-area students</h2>""",
        """  <section class="card">
    <h2>Parent-group fundraising by school (IRS filings)</h2>
    <p class="sub" id="ptasub"></p>
    <div class="controls tabletools"><button id="pta-expand">Expand all regions</button><label><input type="checkbox" id="pta-recent"> Recent filings only (tax year 2022 or later)</label></div>
    <div class="tablewrap" id="ptatable"></div>
  </section>

  <section class="card">
    <h2>Private school share of PPS-area students</h2>""")
    rep("""#overlist table th:first-child, #overlist table td:first-child,""",
        """#overlist table th:first-child, #overlist table td:first-child,
.ptatable th:first-child, .ptatable td:first-child,""")
    rep("""function renderAll() {""", """// ---------- parent-group fundraising, IRS Form 990 (scripts/patch_pta_table.py) ----------
const PTA_CATS = [['pta', 'PTA / PTO'], ['fdn', 'Foundations'], ['boost', 'Booster clubs'], ['alum', 'Alumni']];
const ptaOpen = new Set();
let ptaRecent = true;
try { ptaRecent = localStorage.getItem('rsPtaRecent') !== '0'; } catch (e) {}
function ptaSchool(k) {   // sums by group type for one school: latest filing with dollar figures
  const s = { pta: 0, fdn: 0, boost: 0, alum: 0, tot: 0, filed: 0, old: 0, n990: 0, groups: [] };
  for (const [ein, c, nm, yr, form, rev] of D.pta?.schools?.[k] || []) {
    const g = { ein, c, nm, yr, form, rev, used: false };
    if (rev == null) s.n990++;
    else if (ptaRecent && yr < 2022) s.old++;
    else { s[c] += rev; s.tot += rev; s.filed++; g.used = true; }
    s.groups.push(g);
  }
  return s;
}
function renderPTA() {
  const host = document.getElementById('ptatable'); if (!host || !D.pta) return;
  const cb = document.getElementById('pta-recent');
  if (cb) { cb.checked = ptaRecent; cb.onchange = () => { ptaRecent = cb.checked; try { localStorage.setItem('rsPtaRecent', ptaRecent ? '1' : '0'); } catch (e) {} renderPTA(); }; }
  const keysOf = rn => Object.keys(D.region_of).filter(k => rn === 'District' || D.region_of[k] === rn);
  const usd = v => v >= 1e6 ? '$' + (v / 1e6).toFixed(2) + 'M' : '$' + Math.round(v / 1e3).toLocaleString() + 'k';
  const cell = v => v > 0 ? usd(v) : '<span class="muted">&mdash;</span>';
  const stu = k => D.series.SQ[k]?.[0] || 0;
  const agg = keys => { const a = { pta: 0, fdn: 0, boost: 0, alum: 0, tot: 0, schools: 0, ptaSchools: 0, n990: 0, stu: 0, ptaStu: 0 };
    for (const k of keys) { const s = ptaSchool(k); for (const [c] of PTA_CATS) a[c] += s[c]; a.tot += s.tot; a.stu += stu(k);
      if (s.filed) a.schools++; if (s.pta > 0) { a.ptaSchools++; a.ptaStu += stu(k); } if (!s.filed && s.n990) a.n990++; }
    return a; };
  const perStu = (v, n) => n ? '$' + Math.round(v / n).toLocaleString() : '<span class="muted">&mdash;</span>';
  const cl = k => (D.detail[scen] || {})[k]?.closed;
  let h = `<table class="ptatable"><thead><tr><th style="text-align:left">Region</th><th>Schools with dollar filings</th>${PTA_CATS.map(([, l]) => `<th>${l}</th>`).join('')}<th>Total</th>` +
    `<th title="PTA / PTO revenue over the 2025-26 enrollment of the schools whose PTA or PTO filed with dollar figures">PTA / PTO per student<br><span style="font-weight:400">(schools with a PTA filing)</span></th></tr></thead><tbody>`;
  for (const rn of [...D.region_order, 'District']) {
    const keys = keysOf(rn), a = agg(keys), isReg = rn !== 'District', open = ptaOpen.has(rn);
    h += `<tr class="${isReg ? '' : 'dist'}"><td style="text-align:left">${isReg ? `<button class="xbtn pta-x" data-r="${esc(rn)}" aria-expanded="${open}"><span class="car">&#9656;</span><span>${esc(rn)}</span></button>` : 'District'}</td>` +
      `<td style="text-align:right">${a.schools} of ${keys.length}${a.n990 ? `<span class="muted" style="display:block;font-size:11px">+${a.n990} 990-N only</span>` : ''}</td>` +
      PTA_CATS.map(([c]) => `<td style="text-align:right">${cell(a[c])}</td>`).join('') +
      `<td style="text-align:right"><b>${cell(a.tot)}</b></td><td style="text-align:right">${perStu(a.pta, a.ptaStu)}</td></tr>`;
    if (isReg && open) for (const k of keys.sort((x, y) => short(byKey[x]?.name || x).localeCompare(short(byKey[y]?.name || y)))) {
      const s = ptaSchool(k);
      const gl = s.groups.map(g => `<a href="https://projects.propublica.org/nonprofits/organizations/${g.ein}" target="_blank" rel="noopener" title="IRS filings on ProPublica Nonprofit Explorer (EIN ${g.ein})">${esc(g.nm)}</a> <span class="muted">${esc(PTA_CATS.find(c => c[0] === g.c)[1].replace(/s$/, ''))}, ${g.rev == null ? '990-N only: no dollar figures' : `${g.form} ${g.yr}: ${usd(g.rev)}${g.used ? '' : ' (before 2022, not counted)'}`}</span>`).join('<br>');
      h += `<tr class="srow${cl(k) ? ' closed' : ''}"><td style="text-align:left;white-space:normal;min-width:260px"><span class="nm">${esc(short(byKey[k]?.name || k))}</span><span class="ty">${TYPE_LABEL[D.types.SQ[k]] || ''}</span>${cl(k) ? ` <span class="stag closes">closes in ${esc(LABEL[scen])}</span>` : ''}` +
        `<span class="muted" style="display:block;font-size:11px;line-height:1.45;margin-top:2px">${gl || 'No parent group found in IRS filings'}</span></td>` +
        `<td style="text-align:right">${Math.round(stu(k)).toLocaleString()} students</td>` +
        PTA_CATS.map(([c]) => `<td style="text-align:right">${cell(s[c])}</td>`).join('') +
        `<td style="text-align:right"><b>${cell(s.tot)}</b></td><td style="text-align:right">${s.pta > 0 ? perStu(s.pta, stu(k)) : '<span class="muted">&mdash;</span>'}</td></tr>`;
    }
  }
  host.innerHTML = h + '</tbody></table>';
  host.querySelectorAll('.pta-x').forEach(b => b.onclick = () => { const r = b.dataset.r; ptaOpen.has(r) ? ptaOpen.delete(r) : ptaOpen.add(r); renderPTA(); });
  const ex = document.getElementById('pta-expand');
  if (ex) { const all = D.region_order.every(r => ptaOpen.has(r)); ex.textContent = all ? 'Collapse all regions' : 'Expand all regions';
    ex.onclick = () => { if (D.region_order.every(r => ptaOpen.has(r))) ptaOpen.clear(); else D.region_order.forEach(r => ptaOpen.add(r)); renderPTA(); }; }
  const d = agg(keysOf('District'));
  document.getElementById('ptasub').innerHTML = `Revenue reported to the IRS by each school's parent groups, from their latest return with dollar figures (Form 990 or 990-EZ; for the newest year often only the IRS exempt-organization master file's summary, marked “IRS summary”: total revenue, no detail)${ptaRecent ? ' (tax year 2022 or later)' : ''}: <b>${usd(d.tot)}</b> across ${d.schools} of ${keysOf('District').length} schools, of which PTAs and PTOs <b>${usd(d.pta)}</b>, foundations and "friends of" groups ${usd(d.fdn)}, booster clubs ${usd(d.boost)} and alumni associations ${usd(d.alum)}. ` +
    `Revenue is the group's total for its fiscal year (fundraising events net of their direct costs on the 990-EZ), not what it gave the school; groups' years differ, and some report a year that ends in June. ` +
    `Groups that file only the 990-N e-Postcard (gross receipts normally $50,000 or less) report no dollar figures; ${d.n990} schools have only those. Most Oregon PTAs file as chapters of "PTA Oregon Congress". Groups were matched by name and city and may miss or mislabel some; click a group for its filings and PDFs. ` +
    `Source: IRS e-filed returns via <a href="https://projects.propublica.org/nonprofits/" target="_blank" rel="noopener">ProPublica Nonprofit Explorer</a>, fetched ${esc(D.pta.fetched || '')}.`;
}
function renderAll() {""")
    rep("""renderLines(); renderSplitFeeders();""", """renderLines(); renderSplitFeeders(); renderPTA();""")
    rep("""['hstrends', 'hsdistrict'], ['splitfeed', 'sftable']];""", """['hstrends', 'hsdistrict'], ['splitfeed', 'sftable'], ['pta', 'ptatable']];""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
