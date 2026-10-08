"""School-age residents per 2020 Census block (DHC table P12, sex by age) for the counties the PPS area touches,
from the Census Bureau's bulk Oregon DHC summary file (the Census API now requires a key).

Input:  source/census-dhc/or2020.dhc.zip  (https://www2.census.gov/programs-surveys/decennial/2020/data/
        demographic-and-housing-characteristics-file/Oregon/or2020.dhc.zip)
        Segment 6 holds P10 (71 cells), P11 (73), then P12 (49), after 5 header fields
        (FILEID|STUSAB|CHARITER|CIFSN|LOGRECNO); see table_segments_dhc.csv in 2020_dhc_sas_example.zip.
Output: source/census-dhc/block-ages.csv  GEOID, total, age 5-9, 10-14, 15-17 (male + female)
"""
import csv, io, os, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'source', 'census-dhc')
ZIP = os.path.join(DIR, 'or2020.dhc.zip')
COUNTIES = {'005', '051', '067'}   # Clackamas, Multnomah, Washington
P12 = 5 + 71 + 73                   # column of P12_001N
cell = lambda n: P12 + n - 1        # P12_00nN
z = zipfile.ZipFile(ZIP)

blocks = {}   # LOGRECNO -> GEOID
with z.open('orgeo2020.dhc') as f:
    for line in io.TextIOWrapper(f, encoding='latin-1'):
        v = line.split('|')
        if v[2] == '100' and v[9][2:5] in COUNTIES: blocks[v[7]] = v[9]
print(f'{len(blocks):,} blocks in counties {sorted(COUNTIES)}')

rows = []
with z.open('or000062020.dhc') as f:
    for line in io.TextIOWrapper(f, encoding='latin-1'):
        v = line.rstrip('\n').split('|')
        g = blocks.get(v[4])
        if not g: continue
        n = lambda i: int(v[cell(i)])
        rows.append([g, n(1), n(4) + n(28), n(5) + n(29), n(6) + n(30)])   # 5-9, 10-14, 15-17 (male 004-006, female 028-030)
with open(os.path.join(DIR, 'block-ages.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['GEOID', 'pop', 'age5_9', 'age10_14', 'age15_17']); w.writerows(rows)
tot = [sum(r[i] for r in rows) for i in range(1, 5)]
print(f'{len(rows):,} blocks; population {tot[0]:,}; ages 5-9 {tot[1]:,}, 10-14 {tot[2]:,}, 15-17 {tot[3]:,}')
