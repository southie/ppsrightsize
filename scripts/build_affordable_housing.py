"""Students from new affordable housing, by school and year: PSU's exogenous school-level additions (PPS Enrollment Forecast
2026-27, section 4.2). Developments: Table 2.7 (elementary zone, 2- and 3+-bedroom units, completion month). Yields:
Table 4.1, students per regulated affordable 2+ bedroom unit by school level and years since occupancy (0 .. 5+).
Years since occupancy at each fall count: the fall after completion is year 0 if completed by August, otherwise the
next fall. Middle and high school students go to the zone's Status Quo feeder schools (D.feeders.SQ; K-8 zones keep
their 6-8 students). Also writes the historic K-12 enrollment by grade, fall 2004-2025, from the PSU editions
(2009-10 Table 13 for 2004-08, 2016-17 Table 5 for 2009-15, 2026-27 Table 3.1 for 2016-25) used by the backtest.
Output: source/pps-forecast/affordable-housing.json, source/pps-forecast/historic-grades.json
"""
import json, os, re, sys
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'rightsizing-scenario-explorer.html'), encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
FC = os.path.join(ROOT, 'archive', 'forecasts')

# ---------- Table 2.7 ----------
t = ' '.join(pymupdf.open(os.path.join(FC, 'PPS-enrollment-forecast-2026-27.pdf'))[17].get_text().split())
t = t[t.find('Completion') + 10:]
rows = re.findall(r'(.+?) (\d+) (\d+) (\d+) ([A-Z][A-Za-z.\- ]+?) (\d{4})/(\d{2})', t)
ALIAS = {'Bridger CS': 'Bridger Creative Science', 'MLK Jr': 'MLK Jr', 'Boise-Eliot/Humboldt': 'Boise-Eliot/Humboldt'}
keys = set(D['region_of'])
dev = []
for zn, total, b2, b3, hood, y, m in rows:
    # the zone name is the leading part of the captured text that matches a school key; the rest is the development name
    zn = zn.strip(); zone = None
    for k in sorted(keys | set(ALIAS), key=len, reverse=True):
        if zn.startswith(k + ' '): zone = ALIAS.get(k, k); name = zn[len(k) + 1:]; break
    if not zone: print('unmatched zone:', zn); continue
    dev.append(dict(zone=zone, name=name, units=int(total), br2=int(b2), br3=int(b3), neighborhood=hood, completed=f'{y}-{m}'))
print(len(dev), 'developments,', sum(d['br2'] + d['br3'] for d in dev), 'units with 2+ bedrooms')
# ---------- Table 4.1 ----------
RATE = {'K-5': [0.242, 0.289, 0.303, 0.308, 0.268, 0.265], '6-8': [0.096, 0.118, 0.120, 0.126, 0.110, 0.093], '9-12': [0.082, 0.108, 0.136, 0.149, 0.137, 0.157]}
feed = {}
for es, ms, hs, pg, *_ in D['feeders']['SQ']:
    if es and (not pg or pg.lower() == 'neighborhood'): feed.setdefault(es, (ms or es, hs))
by = {}
for d in dev:
    y, m = map(int, d['completed'].split('-')); first = y if m <= 8 else y + 1     # first fall occupied
    ms, hs = feed.get(d['zone'], (d['zone'], None))
    if D['types']['SQ'].get(d['zone']) == 'K8': ms = d['zone']
    for yi, sy in enumerate(D['years']):
        fall = int(sy[:4]); age = fall - first
        if age < 0: continue
        u = d['br2'] + d['br3']
        for lvl, k in (('K-5', d['zone']), ('6-8', ms), ('9-12', hs)):
            if not k: continue
            by.setdefault(k, [0.0] * len(D['years']))[yi] += u * RATE[lvl][min(age, 5)]
out = dict(source='PPS Enrollment Forecast 2026-27 (PSU PRC): Table 2.7 developments, Table 4.1 yields per 2+ bedroom unit', rates=RATE, developments=dev,
           years=D['years'], students_by_school={k: [round(v, 2) for v in a] for k, a in sorted(by.items())})
json.dump(out, open(os.path.join(ROOT, 'source', 'pps-forecast', 'affordable-housing.json'), 'w', encoding='utf-8'), indent=1)
for yi in (2, 6, 10): print(f"  {D['years'][yi]}: {sum(a[yi] for a in by.values()):.0f} students at {sum(1 for a in by.values() if a[yi] > 0)} schools")

# ---------- historic grades, fall 2004-2025 ----------
def grab(f, page, first):
    t = ' '.join(pymupdf.open(os.path.join(FC, f))[page].get_text().split())
    i = t.find('Grade ' + first); seg = t[i:]
    g = {}
    for gr in ['K'] + [str(n) for n in range(1, 13)]:
        m = re.search(r'(?:^|\s)' + gr + r' ((?:[\d,]+ ){10}[\d,]+)', seg); g[gr] = [int(x.replace(',', '')) for x in m.group(1).split()]
    return g
a = grab('pps_enroll_forecast_2009-10.pdf', 44, '1998-99')            # fall 1998-2008
b = grab('PPS-enrollment-forecast-2016-17.pdf', 24, '2005‐06')         # fall 2005-2015
H = {}
for gr in a:
    H[gr] = {**{1998 + i: v for i, v in enumerate(a[gr])}, **{2005 + i: v for i, v in enumerate(b[gr])}}
c = {'K': [4073, 3948, 3899, 3874, 3244, 3195, 3152, 2995, 2837, 2919], '1': [4141, 4106, 3916, 3930, 3696, 3282, 3376, 3213, 3070, 2950], '2': [4211, 4070, 4040, 3861, 3738, 3476, 3319, 3360, 3207, 3078],
     '3': [4160, 4133, 4011, 3971, 3646, 3486, 3502, 3320, 3365, 3158], '4': [4128, 4137, 4051, 3961, 3747, 3388, 3485, 3464, 3296, 3351], '5': [3916, 4087, 4036, 3963, 3764, 3497, 3358, 3461, 3410, 3239],
     '6': [3568, 3704, 3844, 3797, 3614, 3375, 3405, 3205, 3270, 3305], '7': [3605, 3523, 3619, 3811, 3665, 3420, 3355, 3334, 3200, 3233], '8': [3523, 3553, 3500, 3524, 3738, 3550, 3457, 3285, 3336, 3215],
     '9': [3240, 3344, 3500, 3463, 3442, 3652, 3601, 3439, 3394, 3480], '10': [3203, 3228, 3354, 3472, 3473, 3474, 3621, 3593, 3434, 3401], '11': [3102, 3220, 3234, 3299, 3439, 3379, 3381, 3558, 3546, 3364],
     '12': [3439, 3631, 3704, 3726, 3730, 3831, 3786, 3778, 4010, 3929]}
for gr, v in c.items(): H[gr].update({2016 + i: x for i, x in enumerate(v)})
overlap = [(gr, y, a[gr][y - 1998], b[gr][y - 2005]) for gr in a for y in range(2005, 2009) if a[gr][y - 1998] != b[gr][y - 2005]]
print('overlap mismatches 2005-08:', overlap[:5] or 'none')
yrs = list(range(2004, 2026))
json.dump(dict(source='PSU PPS enrollment forecasts: 2009-10 Table 13 (fall 1998-2008; before 2004 many students were ungraded), 2016-17 Table 5 (2005-2015), 2026-27 Table 3.1 (2016-2025)',
               falls=yrs, grades={gr: [H[gr][y] for y in yrs] for gr in H}), open(os.path.join(ROOT, 'source', 'pps-forecast', 'historic-grades.json'), 'w'), indent=1)
print('historic grades fall', yrs[0], '-', yrs[-1], '| K-12 2004:', sum(H[g][2004] for g in H), '2025:', sum(H[g][2025] for g in H))
