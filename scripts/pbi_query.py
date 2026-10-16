"""Query a Power BI publish-to-web model. Usage: pbi_q.py '<json spec>'  spec: {"from": {"a": "Table"}, "cols": [["a","Col"]...], "measures": [["a","Measure"]...], "sums": [["a","Col"]...]}"""
import json, sys, gzip, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
K = 'e61e8c9e-d02e-4bad-b8ae-96b8e19015c3'; MODEL = 17440778
URL = 'https://wabi-west-us-api.analysis.windows.net/public/reports/querydata?synchronous=true'

def query(frm, cols=(), measures=(), sums=(), count=30000):
    sel = []
    for s, c in cols: sel.append({'Column': {'Expression': {'SourceRef': {'Source': s}}, 'Property': c}, 'Name': f'{frm[s]}.{c}'})
    for s, c in sums: sel.append({'Aggregation': {'Expression': {'Column': {'Expression': {'SourceRef': {'Source': s}}, 'Property': c}}, 'Function': 0}, 'Name': f'Sum({frm[s]}.{c})'})
    for s, c in measures: sel.append({'Measure': {'Expression': {'SourceRef': {'Source': s}}, 'Property': c}, 'Name': f'{frm[s]}.{c}'})
    q = {'Version': 2, 'From': [{'Name': a, 'Entity': t, 'Type': 0} for a, t in frm.items()], 'Select': sel}
    body = {'version': '1.0.0', 'queries': [{'Query': {'Commands': [{'SemanticQueryDataShapeCommand': {'Query': q,
        'Binding': {'Primary': {'Groupings': [{'Projections': list(range(len(sel)))}]}, 'DataReduction': {'DataVolume': 4, 'Primary': {'Window': {'Count': count}}}, 'Version': 1}}}]},
        'QueryId': ''}], 'cancelQueries': [], 'modelId': MODEL}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={'X-PowerBI-ResourceKey': K, 'Content-Type': 'application/json;charset=UTF-8', 'Accept-Encoding': 'gzip'})
    raw = urllib.request.urlopen(req, timeout=120).read()
    try: raw = gzip.decompress(raw)
    except OSError: pass
    r = json.loads(raw)
    return [x['Name'] for x in sel], decode(r)

def decode(r):
    """Decode the DSR compressed row format into lists of values."""
    res = r['results'][0]['result']['data']
    if 'dsr' not in res: return res
    ds = res['dsr']['DS'][0]; dicts = ds.get('ValueDicts', {}); rows = []
    prev = None
    for ph in ds['PH']:
        for key, dm in ph.items():
            for row in dm:
                if 'S' in row:   # schema
                    schema = row['S']
                vals = []; ci = 0; r_ = row.get('R', 0); n_ = row.get('Ø', 0); cvals = iter(row.get('C', []))
                for i, sc in enumerate(schema):
                    if r_ >> i & 1: v = prev[i] if prev else None
                    elif n_ >> i & 1: v = None
                    else:
                        v = next(cvals, None)
                        if 'DN' in sc and isinstance(v, int): v = dicts[sc['DN']][v]
                    vals.append(v)
                prev = vals; rows.append(vals)
    return rows

if __name__ == '__main__':
    spec = json.loads(sys.argv[1])
    names, rows = query(spec['from'], [tuple(x) for x in spec.get('cols', [])], [tuple(x) for x in spec.get('measures', [])], [tuple(x) for x in spec.get('sums', [])])
    out = spec.get('out')
    if out: json.dump({'names': names, 'rows': rows}, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(names); print(len(rows) if isinstance(rows, list) else rows, 'rows')
    if isinstance(rows, list):
        for r in rows[:spec.get('show', 40)]: print(r)
