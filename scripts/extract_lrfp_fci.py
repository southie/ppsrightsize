"""Facility condition index (FCI) and building area per school from the PPS 2021 Long-Range Facility Plan,
Volume 2 (school profiles), written to source/lrfp/lrfp-2021-fci.csv for scripts/build_costs.py.

Each school profile is a two-page spread: the school name heads the first page ("ABERNETHY / ELEMENTARY /
SCHOOL ... Address"), and its FCI sentence ("facility condition index (FCI) score of 0.16") may fall on
either page, so each score is assigned to the most recent school heading.

  python scripts/extract_lrfp_fci.py [path to 2021LRFP-VOL2.pdf]   (default: archive/2021LRFP-VOL2.pdf)
"""
import csv, os, re, sys
import pypdf
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'archive', '2021LRFP-VOL2.pdf')
OUT = os.path.join(ROOT, 'source', 'lrfp', 'lrfp-2021-fci.csv')

rows, cur = [], None
for i, page in enumerate(pypdf.PdfReader(PDF).pages):
    lines = [l.strip() for l in (page.extract_text() or '').split('\n')]
    # a profile's first page: the school name is a few short all-caps lines directly above "Address"
    head = []
    if 'Address' in lines:
        a = lines.index('Address')
        for l in reversed(lines[:a]):   # names are short lines; body text above them is long, bulleted or ends in punctuation
            if re.fullmatch(r'\(.*\)', l): continue   # e.g. "(Anticipated)"
            if not l or l.startswith(('LONG-RANGE', 'PAGE', '', '•')) or len(l) > 30 or l[-1] in '.,;:)' or not re.search(r'[A-Za-z]', l): break
            head.insert(0, l)
    if head:
        area = re.search(r'Bldg Area\s*\|?\s*([\d,]+)\s*SF', ' | '.join(lines).replace(' | SF', ' SF'))
        cur = {'school': ' '.join(head).title(), 'page': i + 1, 'bldg_area_sf': area.group(1).replace(',', '') if area else '', 'fci': ''}
        rows.append(cur)
    m = re.search(r'\(FCI\)\s*score\s*of\s*(0?\.\d+)', ' '.join(lines))
    if m and cur and not cur['fci']:
        cur['fci'] = m.group(1) if m.group(1).startswith('0') else '0' + m.group(1)
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, ['school', 'fci', 'bldg_area_sf', 'page']); w.writeheader(); w.writerows(rows)
print(f'wrote {os.path.relpath(OUT, ROOT)}: {len(rows)} profiles, {sum(1 for r in rows if r["fci"])} with an FCI score')
