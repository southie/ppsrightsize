"""PPS's own scenario model results (Power BI "Rightsizing Scenarios Schools", v1.0, October 14, 2026; tables downloaded by
scripts/fetch_pps_powerbi.py to source/pps-powerbi/tables) in the page's shapes. Output: source/pps-powerbi/pps-model.json
  scen: {A: 'Seventy Percent', B: 'Fifty Percent', S60: 'Sixty Percent', BAL: 'Balanced'} (PPS's run names; A and B are
        PPS's names for its published scenarios, Scenario Norming table)
  For each: series (2025-26, 2026-27 = Status Quo; 2027-28 .. 2035-36 = PPS "projected enrollment after changes"; null
  once closed), types (PPS's 2031-32 school type; closed: Status Quo type), detail (as D.detail: 2031-32 enrollment,
  threshold, above, capacity, utilization, student groups), e2031, recreated measures by region (this page's method,
  metricsOf), closing lists, change (% of K-8 students who change schools: PPS's Demographic_Moves_Summary; Balanced
  is not in it: estimated from the enrollment changes, scaled to match the other runs), cat / detail text and receivers
  from PPS's move rules (scenarios table: notes, percent of projections moved).
  Student groups: PPS's group counts are defined differently from this page's (roster rates); each school's 2031-32
  Status Quo count for a group is scaled by its enrollment and by PPS's change in that group's share at the school
  (scenario share / Status Quo share), so the page's definitions carry PPS's change in each school's mix.
School names: PPS's 'Brentwood' = Lane, 'Sunrise' = Lee; PPS's other sites (ACCESS, Benson, MLC, da Vinci, charters, out
of district) are not on the page.
"""
import json, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TB = os.path.join(ROOT, 'source', 'pps-powerbi', 'tables')
html = open(os.path.join(ROOT, 'rightsizing-scenario-explorer.html'), encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
L = lambda t: (lambda d: [dict(zip(d['cols'], r)) for r in d['rows']])(json.load(open(os.path.join(TB, t + '.json'), encoding='utf-8')))
RUNS = {'A': 'Seventy Percent', 'B': 'Fifty Percent', 'S60': 'Sixty Percent', 'BAL': 'Balanced'}
GRP = ['poverty', 'underserved', 'sped', 'ml']
PCOL = {'poverty': 'Count_Free_by_DC', 'underserved': 'Count_Underserved_Race', 'sped': 'Count_IEP', 'ml': 'Count_LEP'}
YEARS = D['years']; Y31 = YEARS.index('2031-32')
rndh = lambda v: int(v + 0.5) if v >= 0 else -int(-v + 0.5)
norm = lambda s: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
OURS = {norm(k): k for k in D['region_of']}
ALIAS = {'Brentwood': 'Lane', 'Sunrise': 'Lee'}
key = lambda s: ALIAS.get(s) or OURS.get(norm(s or ''))

NUM = ('projected enrollment after changes', 'Is_Active_School', *['Count_Free_by_DC', 'Count_Underserved_Race', 'Count_IEP', 'Count_LEP'])
U = L('2027 utilization before and after')
for r in U:
    for c in NUM:
        if isinstance(r.get(c), str): r[c] = float(r[c]) if r[c] not in ('', None) else 0.0
by = {}
for r in U:
    k = key(r['school'])
    if k: by[(r['eval_scenario'], k, int(r['year']))] = r

def metrics(det, names):
    op = [n for n in names if det.get(n) and not det[n].get('closed')]
    ab = [n for n in op if det[n]['above']]; tot = sum(det[n]['e'] for n in op)
    m = {'schools_above': rndh(100 * len(ab) / len(op)) if op else None, 'students_above': rndh(100 * sum(det[n]['e'] for n in ab) / tot) if tot else None}
    for g in GRP:
        num = den = 0
        for n in op:
            v = det[n]['g'].get(g)
            if v is None: continue
            den += v; num += v if det[n]['above'] else 0
        m[g] = rndh(100 * num / den) if den else None
    return m

# PPS's share of K-8 students who change schools, by run
moved = {}
for r in L('Demographic_Moves_Summary'):
    if r['Demographic / Grade Band Segment'] == 'All Students (K-8 Total)' and r['Metric Category'] == 'Direct Certification':
        moved[r['Scenario']] = 100 * float(r['% Moved'])
rules = L('scenarios')
out = {'source': "PPS Rightsizing Scenarios Schools dashboard (Power BI, version 1.0, last updated October 14, 2026)", 'runs': RUNS, 'scen': {}}
sq_det = D['detail']['SQ']
for sc, run in RUNS.items():
    ser, typ, det, cat, txt = {}, {}, {}, {}, {}
    for k in D['region_of']:
        base = D['series']['SQ'][k]
        row = [base[0], base[1]]; closed = False
        for y in range(2027, 2036):
            r = by.get((run, k, y))
            if r is None: row.append(base[YEARS.index(f'{y}-{(y + 1) % 100:02d}')]); continue
            if not r['Is_Active_School'] or r['Column1'] == 'School Closed': row.append(None); closed = True
            else: row.append(float(r['projected enrollment after changes']))
        ser[k] = row
        r31 = by.get((run, k, 2031)); s31 = by.get(('Status Quo', k, 2031))
        typ[k] = r31['Column1'] if r31 and r31['Column1'] in ('ES', 'MS', 'K8', 'HS') else D['types']['SQ'][k]
        if row[Y31] is None: det[k] = {'closed': True}; continue
        e = rndh(row[Y31]); t = typ[k]; fc = (D['detail']['SQ'][k] or {}).get('fc'); thr = D['thresholds'][t]
        g = {}
        for gname in GRP:
            q = sq_det[k]['g'].get(gname)
            if q is None or not sq_det[k].get('e'): g[gname] = None; continue
            rate = q / sq_det[k]['e']
            if r31 and s31 and s31[PCOL[gname]] and s31['projected enrollment after changes'] and r31['projected enrollment after changes']:
                rate *= (r31[PCOL[gname]] / r31['projected enrollment after changes']) / (s31[PCOL[gname]] / s31['projected enrollment after changes'])
            g[gname] = rndh(rate * e)
        det[k] = {'e': e, 'type': t, 'thr': thr, 'above': row[Y31] >= thr - 1e-9, 'fc': fc, 'util': rndh(100 * e / fc) if fc else None, 'g': g}
    # move rules: notes per school, receivers of closing schools
    R = [r for r in rules if r['scenario_name'] == run]
    notes = {}
    recv = []
    for r in R:
        f, t = key(r['school_from']), key(r['school_to'])
        for x in (f, t):
            if x and r['note']: notes.setdefault(x, []).append(r['note'].strip())
        if f and t and f != t and det.get(f, {}).get('closed'):
            grp = f"{r['group_from'].replace('Residents Attending Neighborhood Program', 'Neighborhood students').replace('Non-residents Attending Neighborhood Program', 'Transfer students')}, grades {'K' if r['grade'] in ('0', 0) else r['grade']}-{r['up_to_grade']}"
            recv.append({'from': f, 'to': t, 'share': None if r['percent_of_projections_to_move'] is None else float(r['percent_of_projections_to_move']), 'group': grp, 'from_key': f, 'to_key': t})
    # one receiver row per pair and group
    seen = set(); recv = [x for x in recv if not ((x['from_key'], x['to_key'], x['group']) in seen or seen.add((x['from_key'], x['to_key'], x['group'])))]
    for k in D['region_of']:
        nt = list(dict.fromkeys(notes.get(k, [])))
        if det[k].get('closed'): cat[k] = 'closes'
        elif nt or typ[k] != D['types']['SQ'][k] or (ser[k][Y31] is not None and abs(ser[k][Y31] - D['series']['SQ'][k][Y31]) >= 10):
            cat[k] = 'program_change' if any(re.search(r'immersion|program|focus|option', n, re.I) for n in nt) else 'boundary'
        else: cat[k] = 'none'
        txt[k] = '; '.join((['Closes'] if det[k].get('closed') else []) + nt)
    rec = {}
    for rn in [*D['region_order'], 'District']:
        names = [n for n in D['region_of'] if rn == 'District' or D['region_of'][n] == rn]
        rec[rn] = {'n': len([n for n in names if not det[n].get('closed')]), 'closures': len([n for n in names if det[n].get('closed')]), **metrics(det, names)}
    closing = {rn: [n for n in D['region_of'] if (rn == 'District' or D['region_of'][n] == rn) and det[n].get('closed')] for rn in [*D['region_order'], 'District']}
    out['scen'][sc] = {'run': run, 'series': ser, 'types': typ, 'detail': det, 'cat': cat, 'text': txt, 'receivers': recv, 'recreated': rec, 'closing': closing,
                       'change': rndh(moved[run]) if run in moved else None}

# Balanced: not in PPS's moves summary; estimate from the 2031-32 enrollment changes (half the sum of absolute changes
# over the district), scaled by PPS's moved share / that estimate for the other runs
def est(sc):
    s = out['scen'][sc]['series']
    return sum(abs((s[k][Y31] or 0) - D['series']['SQ'][k][Y31]) for k in D['region_of']) / 2 / sum(D['series']['SQ'][k][Y31] for k in D['region_of'])
cal = [out['scen'][sc]['change'] / (100 * est(sc)) for sc in ('A', 'B', 'S60') if out['scen'][sc]['change']]
f = sum(cal) / len(cal)
for sc in RUNS:
    out['scen'][sc]['change_est'] = rndh(100 * est(sc) * f)
    if out['scen'][sc]['change'] is None: out['scen'][sc]['change'] = out['scen'][sc]['change_est']; out['scen'][sc]['change_estimated'] = True
json.dump(out, open(os.path.join(ROOT, 'source', 'pps-powerbi', 'pps-model.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
for sc, s in out['scen'].items():
    cl = s['closing']['District']; d = s['recreated']['District']
    print(sc, s['run'], 'closures', len(cl), 'change', s['change'], '(est', s['change_est'], ')', {k: d[k] for k in ('schools_above', 'students_above', 'poverty', 'underserved', 'sped', 'ml')})
    if sc in ('A', 'B'):
        ours = {k for k, v in D['detail'][sc].items() if v.get('closed')}
        print('   closed vs reconstruction: only PPS', sorted(set(cl) - ours), 'only ours', sorted(ours - set(cl)), '| page measures (reconstruction):', {k: D['recreated'][sc]['District'][k] for k in ('schools_above', 'students_above')}, 'published', {k: D['endpoints']['District'][sc][k] for k in ('schools_above', 'students_above', 'change')})
    else: print('   closes:', ', '.join(cl))
print('calibration', [round(x, 2) for x in cal])
