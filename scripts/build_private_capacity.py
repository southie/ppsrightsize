"""Private school capacity and enrollment trend by PPS enrollment area, for comparable schools, from five waves of the
NCES Private School Universe Survey (2015-16, 2017-18, 2019-20, 2021-22, 2023-24; source/nces-pss/pss*_pu_csv.zip).

Schools: the private schools on the explorer (source/nces-pss/private-schools-pss.json: inside PPS or within 2 miles,
reported in 2019-20 or later), matched across waves by PPIN. Schools outside PPS (the 2-mile border) count if they are
within BORDER_MI miles by road of a PPS school, or if the explorer lists them as a private alternative for a PPS school
in Scenario A or B (source/nces-pss/private-listed-near-pps.json, from the page). Areas: the PPS high school attendance
area (shared zones assigned to the region of the nearest PPS school by road); border schools go to the region of the
closest PPS school that lists them, otherwise of their nearest PPS school. Comparable: regular schools (PSS typology 1-7: Catholic,
other religious, nonsectarian regular), excluding special program emphasis (8) and special education (9) schools.
Enrollment by grade band (K-5 with transitional K and 1st, 6-8, 9-12; pre-K excluded) from the PSS grade counts
(P160-P180 kindergarten, P190-P300 grades 1-12).

Per school: capacity = its peak total K-12 enrollment in the five waves (demonstrated capacity), split across its grade
bands in proportion to its latest enrollment by band (so a K-8 or K-12 school is not credited with each band's own
peak from different years); a school serving one band keeps that band's peak. Per band: open seats = capacity -
latest enrollment. Per area and band: enrollment in each wave (a school's missing waves between two reports are
filled by straight line; before its first report it counts as not yet open, 0), and the trend: a log-linear fit of
area enrollment on survey year, as an average percent change per year.

Output: source/nces-pss/private-capacity.json
"""
import csv, io, json, math, os, sys, zipfile
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSS = os.path.join(ROOT, 'source', 'nces-pss')
WAVES = [('1516', '2015-16', 2015.75), ('1718', '2017-18', 2017.75), ('1920', '2019-20', 2019.75), ('2122', '2021-22', 2021.75), ('2324', '2023-24', 2023.75)]
BANDS = {'k5': ['P160', 'P170', 'P180', 'P190', 'P200', 'P210', 'P220', 'P230'], '68': ['P240', 'P250', 'P260'], '912': ['P270', 'P280', 'P290', 'P300']}
COMPARABLE = {1, 2, 3, 4, 5, 6, 7}
BORDER_MI = 3.5   # border schools within this many miles by road of a PPS school (Catlin Gabel is 3.1, OES 2.7)
GRADES = [['P160', 'P170', 'P180']] + [[f'P{c}'] for c in range(190, 301, 10)]   # K (with transitional K and 1st), grades 1-12

S = json.load(open(os.path.join(PSS, 'private-schools-pss.json'), encoding='utf-8'))['schools']
L = json.load(open(os.path.join(PSS, 'private-listed-near-pps.json'), encoding='utf-8'))
def place(s):
    # (region, area) for a school, or None for a border school no PPS school lists
    if s.get('pps_hs_area'):
        return (s.get('pps_region') or L['nearest'][s['name']]['region'], s['pps_hs_area'])
    lst, near = L['listed'].get(s['name']), L['nearest'].get(s['name'])
    if lst: return (min(lst, key=lambda x: x['mi'])['region'], 'Near the PPS border')
    if near and near['mi'] <= BORDER_MI: return (near['region'], 'Near the PPS border')
    return None
S = [s for s in S if place(s)]
by_ppin = {s['pss_ppin']: s for s in S if s.get('pss_ppin')}
# merged listings can carry several PPINs ('A, B'); map each to the school
for s in S:
    for p in str(s.get('pss_ppin') or '').replace(';', ',').split(','):
        if p.strip(): by_ppin[p.strip()] = s

data = {}   # school name -> {wave: {band: n}, typology}
for code, label, _ in WAVES:
    z = zipfile.ZipFile(os.path.join(PSS, f'pss{code}_pu_csv.zip'))
    rows = csv.DictReader(io.TextIOWrapper(z.open(f'pss{code}_pu.csv'), encoding='latin-1'))
    for r in rows:
        r = {k.upper(): v for k, v in r.items()}
        s = by_ppin.get(r.get('PPIN'))
        if not s: continue
        num = lambda c: max(0, int(float(r.get(c) or 0))) if (r.get(c) or '').strip() not in ('', '-1') else 0
        d = data.setdefault(s['name'], {'school': s, 'waves': {}, 'typology': None})
        w = d['waves'].setdefault(label, {b: 0 for b in BANDS})
        for b, cols in BANDS.items(): w[b] += sum(num(c) for c in cols)
        gw = d.setdefault('grades', {}).setdefault(label, [0] * 13)
        for i, cols in enumerate(GRADES): gw[i] += sum(num(c) for c in cols)
        d['typology'] = int(float(r.get('TYPOLOGY') or 0)) or d['typology']   # newest wave read last wins
print(f'{len(data)} of {len(S)} private schools (inside PPS, or border schools near a PPS school) found in the PSS files')

labels = [w[1] for w in WAVES]; years = np.array([w[2] for w in WAVES])
def series(d, b):
    """enrollment in each wave: interpolate gaps between reports; 0 before the first report; carry the last forward"""
    have = [i for i, l in enumerate(labels) if l in d['waves']]
    v = [None] * len(labels)
    for i in have: v[i] = d['waves'][labels[i]][b]
    for i in range(len(labels)):
        if v[i] is not None: continue
        prev = max((j for j in have if j < i), default=None); nxt = min((j for j in have if j > i), default=None)
        v[i] = 0 if prev is None else v[prev] if nxt is None else v[prev] + (v[nxt] - v[prev]) * (i - prev) / (nxt - prev)
    return v

def trend(tot):
    """average annual percent change: log-linear fit of enrollment on survey year (waves with enrollment > 0)"""
    ok = [i for i, x in enumerate(tot) if x > 0]
    if len(ok) < 3: return None
    k = np.polyfit(years[ok], np.log(np.array(tot)[ok]), 1)[0]
    return round(100 * (math.exp(k) - 1), 1)

areas = {}
for name, d in data.items():
    s = d['school']; comp = d['typology'] in COMPARABLE
    region, area = place(s)
    for b in BANDS:
        v = series(d, b)
        if max(v) <= 0: continue
        latest_label = max(l for l in labels if l in d['waves'])
        latest = d['waves'][latest_label][b]
        a = areas.setdefault((region, area), {}).setdefault(b, {'schools': [], 'series': [0.0] * len(labels), 'cap': 0, 'latest': 0, 'excluded': 0})
        if not comp: a['excluded'] += 1; continue
        # capacity: the school's peak total enrollment, split by its latest enrollment by band
        tot_latest = sum(d['waves'][latest_label].values())
        peak_total = max(sum(w.values()) for w in d['waves'].values())
        cap = round(peak_total * latest / tot_latest) if tot_latest else max(d['waves'][l][b] for l in d['waves'])
        a['schools'].append(dict(name=name, latest=latest, latest_wave=latest_label, peak=cap, open=max(0, cap - latest),
                                 series=[round(x) for x in v], trend=trend(v), typology=d['typology']))
        a['series'] = [x + y for x, y in zip(a['series'], v)]; a['cap'] += cap; a['latest'] += latest

# per school and grade, for the explorer's drill-down table (comparable schools only)
def gseries(d, i):
    have = [j for j, l in enumerate(labels) if l in d['grades']]
    v = [None] * len(labels)
    for j in have: v[j] = d['grades'][labels[j]][i]
    for j in range(len(labels)):
        if v[j] is not None: continue
        prev = max((x for x in have if x < j), default=None); nxt = min((x for x in have if x > j), default=None)
        v[j] = 0 if prev is None else v[prev] if nxt is None else v[prev] + (v[nxt] - v[prev]) * (j - prev) / (nxt - prev)
    return [round(x, 1) for x in v]
SCHOOLS = []
for name, d in sorted(data.items()):
    if d['typology'] not in COMPARABLE: continue
    s = d['school']; region, area = place(s)
    latest_label = max(l for l in labels if l in d['waves'])
    lg = d['grades'][latest_label]; lt = sum(lg)
    peak_total = max(sum(g) for g in d['grades'].values())
    SCHOOLS.append(dict(name=name, region=region, area=area, character=s.get('character'), grades_served=s.get('grades_served'),
                        latest_wave=latest_label, peak_total=peak_total, latest=lg,
                        capacity=[round(peak_total * x / lt, 1) if lt else 0 for x in lg],
                        series=[gseries(d, i) for i in range(13)], typology=d['typology']))

out = []
for (region, area), bands in sorted(areas.items()):
    row = dict(region=region, area=area, bands={})
    for b, a in bands.items():
        row['bands'][b] = dict(schools=len(a['schools']), excluded_noncomparable=a['excluded'], latest=a['latest'], capacity=a['cap'],
                               open_seats=a['cap'] - a['latest'], series=[round(x) for x in a['series']], trend_pct_per_year=trend(a['series']),
                               detail=sorted(a['schools'], key=lambda x: -x['latest']))
    out.append(row)
json.dump(dict(source='NCES Private School Universe Survey, 2015-16 to 2023-24 (five waves)', waves=labels,
               rule=__doc__.split('Output')[0].strip(), areas=out, schools=SCHOOLS),
          open(os.path.join(PSS, 'private-capacity.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

# summary
for b, lab in [('k5', 'K-5'), ('68', '6-8'), ('912', '9-12')]:
    print(f'\n{lab}: area | comparable schools | latest | capacity (peak) | open seats | trend %/yr | enrollment by wave')
    for r in out:
        x = r['bands'].get(b)
        if x and x['schools']: print(f"  {r['region'][:22]:22s} {r['area'][:28]:28s} {x['schools']:3d} {x['latest']:6d} {x['capacity']:6d} {x['open_seats']:5d} {str(x['trend_pct_per_year']):>6s}  {x['series']}")
