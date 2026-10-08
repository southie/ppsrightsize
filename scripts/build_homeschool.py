"""Homeschool registrations for the Portland School District and Multnomah County, 2020-21 on, from Multnomah ESD
(which registers homeschooling families in the county; ORS 339.010, OAR 581-021-0026):
  - new registrations by district and school year: the "full detailed report" spreadsheet linked from the
    November 2025 Homeschool Data Brief (archive/homeschool/mesd-detail-2025.csv; 2025-26 is July-October only)
  - students registered by district on November 1: the 2023, 2024 and 2025 November Homeschool Data Briefs
  - county total of about 3,700 on June 1, 2022: the 2022 Homeschool Report (no district breakdown published)
Families must notify MESD when they start homeschooling but not when they stop, so registered totals can overcount
(and records cleanups can make them drop sharply); families unaware of the rule are not counted.
Output: source/homeschool/mesd-homeschool.json
"""
import csv, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'archive', 'homeschool', 'mesd-detail-2025.csv')
OUT = os.path.join(ROOT, 'source', 'homeschool'); os.makedirs(OUT, exist_ok=True)
rows = list(csv.reader(open(SRC, encoding='utf-8')))
i = next(j for j, r in enumerate(rows) if r and r[0].startswith('New Registrations by District'))
years = [y for y in rows[i + 1][1:] if y and y[0].isdigit()]
new = {}
for r in rows[i + 2:]:
    if not r or not r[0] or r[0] == 'Grand Total': break
    new[r[0].replace(' School District', '')] = {y: int(v) if v else 0 for y, v in zip(years, r[1:1 + len(years)])}
county_new = {y: sum(d[y] for d in new.values()) for y in years}
# students registered on November 1, by district (MESD November Homeschool Data Briefs 2023, 2024, 2025)
REG = {d: dict(zip(['2023', '2024', '2025'], v)) for d, v in {
    'Centennial': (205, 213, 183), 'Corbett': (64, 66, 62), 'David Douglas': (271, 274, 240), 'Gresham Barlow': (564, 525, 451),
    'Parkrose': (89, 81, 91), 'Portland': (1585, 1414, 787), 'Reynolds': (338, 303, 287), 'Riverdale': (1, 0, 1)}.items()}
J = dict(
    source='Multnomah Education Service District homeschool registrations: Homeschool Data Briefs (November 2023, 2024, 2025), '
           'the detailed registration spreadsheet linked from the November 2025 brief, and the 2022 Homeschool Report',
    note=__doc__.split('Output')[0].strip(),
    new_registrations={'Portland': {y: new['Portland'][y] for y in years if y >= '2020-21'},
                       'Multnomah County': {y: county_new[y] for y in years if y >= '2020-21'}},
    new_registrations_partial_year='2025-26 (July to October)',
    registered_nov1={'Portland': {'2023': 1585, '2024': 1414, '2025': 787},
                     'Multnomah County': {'2023': 3117, '2024': 2876, '2025': 2102}},
    registered_county_jun1_2022=3700,
    pre_2020_portland_new_registrations={y: new['Portland'][y] for y in years if y < '2020-21'},
    # every MESD component district: new registrations by school year (all years) and registered on November 1
    years=years,
    by_district={d: dict(new=new[d], registered_nov1=REG.get(d, {})) for d in new})
json.dump(J, open(os.path.join(OUT, 'mesd-homeschool.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps({k: J[k] for k in ('new_registrations', 'registered_nov1', 'pre_2020_portland_new_registrations')}, indent=1))
