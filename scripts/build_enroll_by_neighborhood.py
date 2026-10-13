"""Where each school's students live: PPS "Enrollment Summary, October 2025, by K-12 Students' School and High School
Area" (archive/SchoolProfiles-EnrollByNeighborhood25-26.pdf). For every school and program (neighborhood program, each
immersion program, the school total): students from the school's own neighborhood, students from each high school
area outside it, out of district / undetermined, and the total.
The table prints a zero cell as "0%" alone and any other cell as a count then a percentage.
Output: source/pps-programs/enroll-by-neighborhood.json  {school name: {program: {total, nbhd, nbhd_share, areas, outside}}}
"""
import json, os, re, sys
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, 'archive', 'SchoolProfiles-EnrollByNeighborhood25-26.pdf')
OUT = os.path.join(ROOT, 'source', 'pps-programs', 'enroll-by-neighborhood.json')
AREAS = ['Cleveland', 'Franklin', 'Grant', 'Ida B. Wells-Barnett', 'Jefferson / Grant', 'Jefferson / McDaniel', 'Jefferson / Roosevelt',
         'Lincoln', 'McDaniel', 'Roosevelt', 'Out of District / Undetermined']
HEADER = {'Portland Public Schools', "Students from Outside of School's Neighborhood", 'School that Students Attend', 'School Program',
          'Total', "Students from", "School's", 'Neighborhood', 'Cleveland', 'Franklin', 'Grant', 'Ida B. Wells-', 'Barnett', 'Jefferson /',
          'McDaniel', 'Roosevelt', 'Lincoln', 'Out of', 'District/', 'Undetermin', 'ed'}
toks = []
for p in pymupdf.open(PDF):
    for l in p.get_text().split('\n'):
        l = l.strip()
        if not l or l.startswith('Enrollment Summary') or l in HEADER: continue
        toks.append(l)
NUM = re.compile(r'^[\d,]+$'); PCT = re.compile(r'^\d+%$')
PROG = re.compile(r'Immersion$|^Neighborhood Program$')
out, school, i, name = {}, None, 0, []   # name: the lines of the current label (a school name may wrap)
while i < len(toks):
    t = toks[i]
    if NUM.match(t) or PCT.match(t):
        # a row: 12 cells (own neighborhood, 10 high school areas, out of district) then the total
        cells, j = [], i
        while len(cells) < 12 and j < len(toks):
            if PCT.match(toks[j]): cells.append(0); j += 1
            elif NUM.match(toks[j]) and j + 1 < len(toks) and PCT.match(toks[j + 1]): cells.append(int(toks[j].replace(',', ''))); j += 2
            else: break
        if len(cells) == 12 and j < len(toks) and NUM.match(toks[j]):
            total = int(toks[j].replace(',', '')); j += 1
            label = ' '.join(name)
            if PROG.search(label): prog = label                       # a program of the school named before it
            elif label.endswith(' Total'): school, prog = label[:-6], 'Total'
            else: school, prog = label, 'Total'
            if school and not re.search(r'Schools? Total$|^Total|^District', school):
                out.setdefault(school, {})[prog] = dict(total=total, nbhd=cells[0], nbhd_share=round(cells[0] / total, 4) if total else None,
                                                        areas=dict(zip(AREAS[:-1], cells[1:11])), outside=cells[11])
            name = []; i = j; continue
        name = []; i += 1; continue
    if PROG.search(t):
        if name: school = ' '.join(name)   # "Ainsworth" then "Neighborhood Program": the school is the line before
        name = [t]
    else:
        name = name + [t] if name and not PROG.search(name[0]) else [t]
    i += 1
# a school whose first row is a program: its name is the line before (handled: "Ainsworth" then "Neighborhood Program")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(dict(source='PPS Enrollment Summary, October 2025, by K-12 Students\' School and High School Area (archive/SchoolProfiles-EnrollByNeighborhood25-26.pdf)', schools=out),
          open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'schools')
for k in ['Beach', 'James John', 'Rose City Park', 'Buckman', 'Sitton', 'Atkinson', 'Ainsworth', 'Sunnyside Environmental']:
    print(k, {p: (v['nbhd'], v['total'], v['nbhd_share']) for p, v in out.get(k, {}).items()})
