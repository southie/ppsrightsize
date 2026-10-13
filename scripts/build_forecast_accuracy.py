"""PPS enrollment forecast accuracy, from PSU Population Research Center's annual forecasts for Portland Public
Schools (11 editions, 2016-17 to 2026-27; PDFs in archive/forecasts/PPS-enrollment-forecast-<first forecast year>.pdf,
from https://pdxscholar.library.pdx.edu/enrollmentforecasts/).

Each edition is named for its first forecast year (its history runs through the year before). Parsed from each:
  district: low / medium (middle) / high forecasts by grade (Tables A1-A3; 2023-24 pp11-13; Tables 5.2-5.4 from
    2024-25), with grade groups K-5, 6-8, 9-12 and K-12 summed from the grades, and the history columns
  schools: medium forecast by school (Tables C1-C5 by grade group in 2016-17 and 2017-18, Table C by school and
    program 2018-19 to 2022-23, the grade-group-by-school table in 2023-24, Table 5.5 from 2024-25); the school's
    Total row (all programs) is kept, with its grade range
Actual enrollment for a year = that year as history in the next edition (PSU's own counting, so forecast and actual
are on the same basis); when a later edition restates it, the next edition's figure is kept and the restatement noted.
Error = forecast - actual; horizon h = years ahead of the edition's base year (h=1 is the edition's first forecast
year). Reported: by edition, by horizon (mean absolute % error, mean % error = bias), whether the actual fell within the
low-high range, for the district, grade groups, and schools (each school, and pooled by horizon and school type); for
all editions, and separately for pre-COVID editions (2016-17 to 2021-22) and post-COVID editions (2022-23 on).
Outputs: source/pps-forecast/forecast-history.json (everything parsed), forecast-accuracy.json, and CSVs
(district-accuracy.csv, school-accuracy.csv).
"""
import csv, json, os, re, statistics, sys
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'archive', 'forecasts')
OUT = os.path.join(ROOT, 'source', 'pps-forecast')
EDS = ['2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26', '2026-27']
# district tables: pages (1-based) of the low / medium / high tables
DPAGES = {'2016-17': [58, 59, 60], '2017-18': [52, 53, 54], '2018-19': [54, 55, 56], '2019-20': [55, 56, 57], '2020-21': [56, 57, 58],
          '2021-22': [70, 71, 72], '2022-23': [68, 69, 70], '2023-24': [11, 12, 13], '2024-25': [35, 36, 37], '2025-26': [34, 35, 36],
          '2026-27': [34, 35, 36]}
GRADES = ['K'] + [str(g) for g in range(1, 13)]
GROUPS = {'K-5': GRADES[:6], '6-8': GRADES[6:9], '9-12': GRADES[9:], 'K-12': GRADES}
YEAR = re.compile(r'^(\d{4})-(\d{2})\d?\*?$')
NUM = re.compile(r'^(-?[\d,]+|--?|—)$')

def yr(i): return f'{i}-{(i + 1) % 100:02d}'
def yi(y): return int(y[:4])
def norm(t): return re.sub(r'[‐‑–—]', '-', t).replace(' ', ' ').strip()

def tokens(page):
    out = []
    for line in page.get_text().split('\n'):
        t = norm(line)
        if not t: continue
        parts = t.split()
        if len(parts) > 1 and all(YEAR.match(p) for p in parts): out += parts
        else: out.append(t)
    return out

def header_years(tk):
    """the table's year columns: the first run of consecutive year tokens"""
    for i, t in enumerate(tk):
        if YEAR.match(t):
            j = i
            while j < len(tk) and YEAR.match(tk[j]): j += 1
            if j - i >= 5: return [yr(int(YEAR.match(t)[1])) for t in tk[i:j]], j
    return None, 0

def val(t): return None if t.startswith('-') and not t[1:2].isdigit() or t == '—' else int(t.replace(',', ''))

# ---------------- district ----------------
def scen_of(text):
    m = re.search(r'\b(Low|Middle|Medium|High)\b\s*(Growth|Series|Scenario)', text)
    return {'Middle': 'medium', 'Medium': 'medium', 'Low': 'low', 'High': 'high'}[m[1]]

district = {}
for e in EDS:
    d = pymupdf.open(os.path.join(SRC, f'PPS-enrollment-forecast-{e}.pdf'))
    rec = {}
    for p in DPAGES[e]:
        pg = d[p - 1]; sc = scen_of(pg.get_text()[:400])
        tk = tokens(pg); years, j = header_years(tk)
        rows = {}
        while j < len(tk):
            lab = tk[j].rstrip('*')
            if lab in GRADES + ['Total'] and j + len(years) < len(tk) + 1 and all(NUM.match(x) for x in tk[j + 1:j + 1 + len(years)]):
                rows.setdefault(lab, [val(x) for x in tk[j + 1:j + 1 + len(years)]]); j += 1 + len(years)
            else: j += 1
        assert all(g in rows for g in GRADES), (e, p, sorted(rows))
        for g, gs in GROUPS.items(): rows[g] = [sum(rows[x][i] for x in gs) for i in range(len(years))]
        if 'Total' in rows and rows['Total'] != rows['K-12']: print('  total mismatch', e, sc, rows['Total'][:3], rows['K-12'][:3])
        rows.pop('Total', None)
        rec[sc] = dict(page=p, years=years, rows=rows)
    yrs = rec['medium']['years']; f0 = yrs.index(e)
    district[e] = dict(years=yrs, history=yrs[:f0], forecast=yrs[f0:],
                       actual={g: dict(zip(yrs[:f0], rec['medium']['rows'][g][:f0])) for g in GROUPS},
                       actual_grades={g: dict(zip(yrs[:f0], rec['medium']['rows'][g][:f0])) for g in GRADES},
                       pages={s: rec[s]['page'] for s in rec},
                       **{s: {g: dict(zip(yrs[f0:], rec[s]['rows'][g][f0:])) for g in list(GROUPS) + GRADES} for s in ('low', 'medium', 'high')})
    print(e, 'district: history', yrs[0], '-', yrs[f0 - 1], '| medium K-12', district[e]['medium']['K-12'][e], '| low', district[e]['low']['K-12'][e], '| high', district[e]['high']['K-12'][e])

# ---------------- schools ----------------
PROG = re.compile(r'Program|Immersion|^Total$|^(Spanish|Japanese|Chinese|Mandarin|Russian|Vietnamese|Somali|Ukrainian|Neighborhood|Odyssey|Arabic)\b|DLI', re.I)
GR = re.compile(r'^(PK|KG|K)?-?\d{0,2}-\d{1,2}\d?$|^(KG|K)-\d+$')
TYPE = {'ES', 'MS', 'HS', 'K8', 'K-8', 'N/A'}   # (N/A: a program's grade range once it has closed)
def canon(n):
    n = norm(n)
    n = re.sub(r'(\s+(ES|MS|HS|K-8|K8))?\d*$', '', n).strip()
    return ALIAS.get(n, n)
ALIAS = {'MLK Jr': 'King', 'Martin Luther King Jr': 'King', 'Dr. MLK Jr': 'King', 'Dr MLK Jr': 'King', 'Ida B. Wells-Barnett': 'Ida B Wells', 'Ida B. Wells': 'Ida B Wells',
         'Wilson': 'Ida B Wells', 'Madison': 'McDaniel', 'Leodis V. McDaniel': 'McDaniel', 'Rose City Park': 'Rose City Park', 'Harriet Tubman': 'Tubman',
         'Bridger Creative Science': 'Bridger', 'Creative Science': 'Creative Science', 'Boise-Eliot': 'Boise-Eliot/Humboldt', 'Boise Eliot/Humboldt': 'Boise-Eliot/Humboldt',
         'Metropolitan Learning Center': 'MLC', 'Sabin': 'Sabin', 'Beverly Cleary': 'Beverly Cleary', 'Mt. Tabor': 'Mt Tabor', 'Mount Tabor': 'Mt Tabor',
         'Lane': 'Lane', 'Faubion': 'Faubion', 'Hosford': 'Hosford', 'Kellogg': 'Kellogg', 'Roseway Heights': 'Roseway Heights', 'César Chávez': 'Cesar Chavez', 'Cesar Chavez': 'Cesar Chavez',
         'da Vinci': 'da Vinci', 'Da Vinci': 'da Vinci', 'Harrison Park': 'Harrison Park',
         'Benson Polytechnic': 'Benson', 'Boise-Eliot-Humboldt': 'Boise-Eliot/Humboldt', 'Ida B Wells-Barnett': 'Ida B Wells', 'ML King Jr': 'King',
         'Metro. Learning Center': 'MLC', 'Metro. Learning Ctr. K-': 'MLC', 'Online Learning Academy': 'OLA', 'Sunnyside Environm.': 'Sunnyside',
         'Sunnyside Environmental': 'Sunnyside', 'Sylvan': 'West Sylvan', 'Hayhurst-Odyssey': 'Hayhurst'}
SKIP = re.compile(r'Schools$|Total|Subtotal|District|Other|Charter|Community|Special|Focus|Alternative|continued|Population Research|^Name$|^School|^Grades?$|^Range|^Program$|^Type$|Historic|Forecast|^Table|^Source|Enrollment', re.I)

def school_page_kind(e, text):
    text = norm(text)
    if e in ('2016-17', '2017-18'):
        m = re.search(r'Table C([1-5])', text[:120]); return m and {'1': 'K-2', '2': '3-5', '3': '6-8', '4': '9-12', '5': 'total'}[m[1]]
    if e in ('2018-19', '2019-20', '2020-21', '2021-22', '2022-23'): return 'total' if re.search(r'Table C\.? K-12 Enrollment by School', norm(text[:200])) else None
    if e == '2023-24': return 'total' if 'by Grade Group and School' in text[:200] else None
    return 'total' if re.search(r'Table 5\.5', text[:200]) else None

schools = {}
for e in EDS:
    d = pymupdf.open(os.path.join(SRC, f'PPS-enrollment-forecast-{e}.pdf'))
    out, name = {}, None
    for p in range(len(d)):
        kind = school_page_kind(e, d[p].get_text())
        if not kind: continue
        tk = tokens(d[p]); years, j = header_years(tk)
        if not years or e not in years: continue
        labs = []
        while j < len(tk):
            run = tk[j:j + len(years)]
            if len(run) == len(years) and all(NUM.match(x) for x in run) and labs:
                vals = [val(x) for x in run]; j += len(years)
                grades = next((l for l in labs if GR.match(l)), None)
                L = [l for l in labs if not GR.match(l) and l not in TYPE]
                labs = []
                if not L: continue
                if len(L) >= 2: name, prog = L[0], L[1]
                elif PROG.search(L[0]) and name: prog = L[0]
                else: name, prog = L[0], 'Total'
                if re.search(r'Subtotal|District|Total$', name) and name != 'Total' or SKIP.search(name) and prog == 'Total' and not GR.match(name or ''):
                    if re.search(r'Subtotal|District Total|^Total', name): continue
                if prog != 'Total' and kind == 'total': continue
                k = canon(name)
                if SKIP.search(k): continue
                r = out.setdefault(k, dict(name=norm(name)))
                if grades: r['grades'] = grades.replace('KG', 'K')
                r[kind] = dict(zip(years, vals))
            else:
                t = tk[j]
                if NUM.match(t) or YEAR.match(t): labs = []
                else: labs.append(t)
                j += 1
    # 2016-17 / 2017-18: K-12 total from C5; 2018+: Total rows only (a single-program school's only row is its total)
    for k, r in out.items():
        r['history'] = {y: v for y, v in (r.get('total') or {}).items() if yi(y) < yi(e) and v is not None}
        r['forecast'] = {y: v for y, v in (r.get('total') or {}).items() if yi(y) >= yi(e) and v is not None}
        if 'grades' not in r and any(g in r for g in ('K-2', '3-5', '6-8', '9-12')):   # 2016-17 / 2017-18: from the grade-group tables
            has = [g for g in ('K-2', '3-5', '6-8', '9-12') if (r.get(g) or {}).get(e)]
            if has: r['grades'] = ('K' if has[0] in ('K-2', '3-5') else has[0].split('-')[0]) + '-' + has[-1].split('-')[1]
    out = {k: r for k, r in out.items() if r['history'] or r['forecast']}
    schools[e] = out
    print(e, 'schools:', len(out))

# ---------------- actuals ----------------
def actual_for(series_of, y):
    """the year as history in the first edition that has it (the next edition, normally); also the later restatements"""
    vals = [(e, series_of(e).get(y)) for e in EDS if yi(e) > yi(y)]
    vals = [(e, v) for e, v in vals if v is not None]
    return (vals[0][1], vals[0][0], vals) if vals else (None, None, [])

restated = []
dist_actual = {}
for g in list(GROUPS) + GRADES:
    dist_actual[g] = {}
    for y in sorted({y for e in EDS for y in district[e]['history']}):
        src = (lambda e: district[e]['actual'][g]) if g in GROUPS else (lambda e: district[e]['actual_grades'][g])
        a, e0, allv = actual_for(src, y)
        if a is None: continue
        dist_actual[g][y] = dict(value=a, edition=e0)
        if g == 'K-12' and len({v for _, v in allv}) > 1: restated.append(dict(year=y, values={e: v for e, v in allv}))

all_keys = sorted({k for e in EDS for k in schools[e]})
sch_actual = {}
for k in all_keys:
    sch_actual[k] = {}
    for y in sorted({y for e in EDS for y in (schools[e].get(k, {}).get('history') or {})}):
        a, e0, _ = actual_for(lambda e: schools[e].get(k, {}).get('history', {}), y)
        if a is not None: sch_actual[k][y] = dict(value=a, edition=e0)

# ---------------- errors ----------------
def mean(x): return round(statistics.mean(x), 2) if x else None
def med(x): return round(statistics.median(x), 2) if x else None

drows = []
for e in EDS:
    for g in GROUPS:
        for y, f in district[e]['medium'][g].items():
            a = dist_actual[g].get(y)
            if not a or f is None: continue
            lo, hi = district[e]['low'][g].get(y), district[e]['high'][g].get(y)
            drows.append(dict(edition=e, group=g, year=y, h=yi(y) - yi(e) + 1, forecast=f, low=lo, high=hi, actual=a['value'], actual_from=a['edition'],
                              err=f - a['value'], pct=round(100 * (f - a['value']) / a['value'], 2),
                              band='below low' if a['value'] < min(lo, hi) else 'above high' if a['value'] > max(lo, hi) else 'within'))
def basis(k, e, e0, y):
    """'changed' when an edition between the forecast's and the one the actual comes from restates the school's history
    (a program moved in or out, a boundary or grade-range change) by more than 3% and 10 students, checked edition to
    edition over the years both report; or when the school's grade configuration changed between the forecast's edition
    and the target year"""
    chain = [x for x in EDS[EDS.index(e):EDS.index(e0) + 1] if k in schools[x]]   # skipping editions without the school
    for e1, e2 in zip(chain, chain[1:]):
        h1, h2 = schools[e1].get(k, {}).get('history', {}), schools[e2].get(k, {}).get('history', {})
        if any(abs(h1[y] - h2[y]) > max(10, 0.03 * h1[y]) for y in h1 if y in h2 and h1[y] and h2[y]): return 'changed'
    # a grade reconfiguration between the forecast's edition and the target year (a K-8 becoming a K-5, say)
    l0, l1 = level(grades_at(k, e)), level(grades_at(k, y))
    if l0 and l1 and l0 != l1: return 'changed'
    return 'same'
def grades_at(k, y):
    """the school's grade range in year y: from the edition whose base year is y, or the latest one before it"""
    for e in reversed(EDS):
        if yi(e) <= yi(y) and schools[e].get(k, {}).get('grades'): return schools[e][k]['grades']
    return None
def level(g):
    """K-4 and K-5 are the same level; K-8, 6-8, 9-12 differ"""
    m = re.match(r'(K|\d+)-(\d+)', g or '')
    if not m: return None
    lo = 'K' if m[1] == 'K' or int(m[1]) <= 2 else m[1]
    return (lo, 'elem' if int(m[2]) <= 5 else m[2])
srows = []
for e in EDS:
    for k, r in schools[e].items():
        for y, f in r['forecast'].items():
            a = sch_actual.get(k, {}).get(y)
            if not a or not a['value'] or f is None: continue
            srows.append(dict(edition=e, school=k, grades=r.get('grades', ''), year=y, h=yi(y) - yi(e) + 1, forecast=f, actual=a['value'], actual_from=a['edition'],
                              err=f - a['value'], pct=round(100 * (f - a['value']) / a['value'], 2), basis=basis(k, e, a['edition'], y)))

def _keep(rows): return [r for r in rows if r['basis'] == 'same']

def stype(g):
    g = g or ''
    return {'K-5': 'ES', 'K-4': 'ES', 'K-3': 'ES', 'K-2': 'ES', '6-8': 'MS', '9-12': 'HS', 'K-8': 'K-8', '3-5': 'ES', 'K-6': 'ES'}.get(g, 'other')
latest_grades = {k: next((schools[e][k].get('grades') for e in reversed(EDS) if k in schools[e] and schools[e][k].get('grades')), '') for k in all_keys}
for r in srows: r['type'] = stype(r['grades'] or latest_grades[r['school']])

def summarize(drows, srows, eds):
    summary = dict(editions=eds, district={}, schools={})
    for g in GROUPS:
        R = [r for r in drows if r['group'] == g]
        summary['district'][g] = dict(
            by_horizon={h: dict(n=len(x), mape=mean([abs(r['pct']) for r in x]), bias=mean([r['pct'] for r in x]),
                                within=sum(r['band'] == 'within' for r in x), below=sum(r['band'] == 'below low' for r in x), above=sum(r['band'] == 'above high' for r in x))
                        for h in sorted({r['h'] for r in R}) for x in [[r for r in R if r['h'] == h]]},
            by_edition={e: [dict(year=r['year'], h=r['h'], forecast=r['forecast'], low=r['low'], high=r['high'], actual=r['actual'], pct=r['pct'], band=r['band'])
                            for r in R if r['edition'] == e] for e in eds})
    summary['schools']['by_horizon'] = {h: dict(n=len(x), mape=mean([abs(r['pct']) for r in x]), median_ape=med([abs(r['pct']) for r in x]), bias=mean([r['pct'] for r in x]),
                                                weighted_ape=round(100 * sum(abs(r['err']) for r in x) / sum(r['actual'] for r in x), 2),
                                                share_within_5pct=round(100 * sum(abs(r['pct']) <= 5 for r in x) / len(x), 1),
                                                share_over_10pct=round(100 * sum(abs(r['pct']) > 10 for r in x) / len(x), 1))
                                        for h in sorted({r['h'] for r in _keep(srows)}) for x in [[r for r in _keep(srows) if r['h'] == h]]}
    summary['schools']['by_type_horizon'] = {t: {h: dict(n=len(x), mape=mean([abs(r['pct']) for r in x]), bias=mean([r['pct'] for r in x]))
                                                 for h in (1, 3, 5) for x in [[r for r in _keep(srows) if r['type'] == t and r['h'] == h]] if x}
                                             for t in ('ES', 'K-8', 'MS', 'HS')}
    summary['schools']['by_edition_h1'] = {e: dict(n=len(x), mape=mean([abs(r['pct']) for r in x]), bias=mean([r['pct'] for r in x])) for e in eds
                                           for x in [[r for r in _keep(srows) if r['edition'] == e and r['h'] == 1]] if x}
    per_school = {}
    for k in all_keys:
        x = [r for r in _keep(srows) if r['school'] == k]
        if not x: continue
        per_school[k] = dict(grades=latest_grades[k], type=stype(latest_grades[k]), n=len(x),
                             **{f'h{h}': dict(n=len(y), mape=mean([abs(r['pct']) for r in y]), bias=mean([r['pct'] for r in y])) for h in (1, 3, 5) for y in [[r for r in x if r['h'] == h]] if y},
                             latest_actual=sch_actual[k][max(sch_actual[k])] | dict(year=max(sch_actual[k])))
    summary['schools']['per_school'] = per_school
    return summary

# COVID split: editions made before 2022-23 (2016-17 to 2021-22) forecast into or through the pandemic enrollment drop;
# 2022-23 on were made after it. Each era is summarized on its own, plus all editions together.
PRE = [e for e in EDS if yi(e) < 2022]; POST = [e for e in EDS if yi(e) >= 2022]
for r in drows + srows: r['era'] = 'pre_covid' if r['edition'] in PRE else 'post_covid'
summary = summarize(drows, srows, EDS)
summary['eras'] = {era: summarize([r for r in drows if r['era'] == era], [r for r in srows if r['era'] == era], eds)
                   for era, eds in (('pre_covid', PRE), ('post_covid', POST))}

os.makedirs(OUT, exist_ok=True)
SOURCE = 'PSU Population Research Center, Portland Public Schools enrollment forecasts, 2016-17 to 2026-27 (https://pdxscholar.library.pdx.edu/enrollmentforecasts/); archive/forecasts'
json.dump(dict(source=SOURCE, editions=EDS, district=district, schools=schools), open(os.path.join(OUT, 'forecast-history.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
json.dump(dict(source=SOURCE, method=__doc__.split('Actual enrollment')[1].split('Outputs:')[0].strip(), restated_k12=restated,
               district_actual=dist_actual, summary=summary), open(os.path.join(OUT, 'forecast-accuracy.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
for fn, rows in (('district-accuracy.csv', drows), ('school-accuracy.csv', srows)):
    with open(os.path.join(OUT, fn), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# ---------------- report ----------------
print('\nK-12 restated history:', restated)
print('\nDistrict K-12, medium forecast vs actual (pct error), by edition and horizon:')
for e in EDS:
    print(' ', e, ' '.join(f"h{r['h']}:{r['pct']:+.1f}%{'' if r['band'] == 'within' else '(' + r['band'] + ')'}" for r in summary['district']['K-12']['by_edition'][e]))
for era, S in [('all', summary)] + list(summary['eras'].items()):
    print(f'\n== {era} ({S["editions"][0]} to {S["editions"][-1]}) ==')
    for g in GROUPS:
        print(g, {h: (v['n'], v['mape'], v['bias'], f"{v['within']}/{v['n']} in band") for h, v in S['district'][g]['by_horizon'].items()})
    print('schools by horizon:', {h: (v['n'], v['mape'], v['median_ape'], v['bias'], v['share_within_5pct'], v['share_over_10pct']) for h, v in S['schools']['by_horizon'].items()})
    print('schools by type:', json.dumps(S['schools']['by_type_horizon']))
print('school rows:', len(srows), {b: sum(r['basis'] == b for r in srows) for b in ('same', 'changed', 'unchecked')}, sorted({(r['school'], r['edition'], r['actual_from']) for r in srows if r['basis'] == 'changed'}))
print('schools h1 by edition:', json.dumps(summary['schools']['by_edition_h1']))
# names seen in only one edition (alias candidates)
cnt = {k: sum(k in schools[e] for e in EDS) for k in all_keys}
print('\nschools in <=2 editions:', sorted((k, [e for e in EDS if k in schools[e]]) for k in all_keys if cnt[k] <= 2))
