"""City of Portland bicycle network (PBOT, portlandmaps.com open data, COP_OpenData_Transportation MapServer layer 75):
built bikeways (Status = ACTIVE) with their facility type, for the low-stress bike routing in
scripts/build_block_access.py.
  Facility  TRL off-street path/trail, PBL protected bike lane, SIR separated in-roadway, BBL buffered bike lane,
            BL bike lane, ABL advisory bike lane, NG neighborhood greenway, ESR enhanced shared roadway
  SCS       streets of citywide significance (MAJBIKEWAY, GREENWAY, OTHERLANE)
Covers the City of Portland only; outside it the routing falls back on OpenStreetMap's bike tags.
Output: source/pbot/bicycle-network.geojson
"""
import json, os, sys, time
import requests
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'source', 'pbot'); os.makedirs(OUT, exist_ok=True)
URL = 'https://www.portlandmaps.com/od/rest/services/COP_OpenData_Transportation/MapServer/75/query'
UA = {'User-Agent': 'pps-rightsizing-analysis/1.0 (personal research, low volume)'}
feats, off, page = [], 0, 1000
while True:
    for i in range(4):
        try:
            r = requests.get(URL, params=dict(where="Status='ACTIVE'", outFields='Facility,SCS,SegmentName,YearBuilt', outSR=4326,
                                              f='geojson', resultOffset=off, resultRecordCount=page, orderByFields='OBJECTID'), headers=UA, timeout=120)
            d = r.json(); break
        except Exception as ex:
            print('retry', ex); time.sleep(5 * (i + 1))
    else: sys.exit('failed')
    fs = d.get('features', [])
    feats += fs; off += len(fs)
    print(f'{off:,} features')
    if not fs or not (d.get('exceededTransferLimit') or d.get('properties', {}).get('exceededTransferLimit')) and len(fs) < page: break
    time.sleep(1)
json.dump(dict(type='FeatureCollection', fetched=time.strftime('%Y-%m-%d'), source=URL.rsplit('/', 1)[0], features=feats),
          open(os.path.join(OUT, 'bicycle-network.geojson'), 'w', encoding='utf-8'), separators=(',', ':'))
from collections import Counter
print(Counter(f['properties']['Facility'] for f in feats))
