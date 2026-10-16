"""Download every table of PPS's Rightsizing Scenarios Schools Power BI dashboard (publish-to-web, report key e61e8c9e...) to
source/pps-powerbi/tables/<table>.json ({cols, rows}). Needs source/pps-powerbi/schema.json (the model's conceptual schema).
Distinct rows only (the query groups by every column)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbi_query import query
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'source', 'pps-powerbi')
sys.stdout.reconfigure(encoding='utf-8')
s = json.load(open(os.path.join(OUT, 'schema.json'), encoding='utf-8'))
os.makedirs(os.path.join(OUT, 'tables'), exist_ok=True)
for e in s['schemas'][0]['schema']['Entities']:
    t = e['Name']
    if t.startswith(('DateTableTemplate', 'LocalDateTable')): continue
    cols = [p['Name'] for p in e['Properties'] if 'Measure' not in p and 'Column' in p or ('Measure' not in p and 'Hierarchy' not in p)]
    cols = [c for c in cols]
    try:
        names, rows = query({'a': t}, [('a', c) for c in cols], count=30000)
        json.dump({'cols': cols, 'rows': rows}, open(os.path.join(OUT, 'tables', f'{t}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'{t}: {len(rows)} rows, {len(cols)} cols')
    except Exception as ex:
        print(f'{t}: ERROR {str(ex)[:200]}')
