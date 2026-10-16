"""Receiving schools in PPS's model runs (source/pps-powerbi tables, scripts/fetch_pps_powerbi.py), 2027-28, the year the
changes take effect. Output: source/pps-powerbi/receiving.json
  For each run (A = Seventy Percent, B = Fifty Percent, S60 = Sixty Percent, BAL = Balanced):
  receivers: schools that take students from another school under the run's move rules (a rule with a share above 0
    from another school), open in 2027-28: [page key, PPS type, arriving, enrollment, share new, only receives]
    arriving: each grade and student group's increase over the school's Status Quo projection, summed (2027 Summary);
      a school that gains and loses students in the same grade counts only the net gain, so this is a floor.
    enrollment: PPS's 2027-28 enrollment after changes. share new = arriving / enrollment.
    only receives: no rule sends any of its students to another school (or to neighborhood schools), and its grades,
      program type and immersion language are the same as in Status Quo; it only takes in students from elsewhere.
  totals: arriving students, students at receiving schools, Status Quo 2027-28 students at the schools that close.
  shrink: open schools whose 2027-28 enrollment falls by more than 25% from Status Quo.
"""
import json, os, re, sys, unicodedata, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TB = os.path.join(ROOT, 'source', 'pps-powerbi', 'tables')
html = open(os.path.join(ROOT, 'rightsizing-scenario-explorer.html'), encoding='utf-8').read()
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', html, re.S).group(1))
L = lambda t: (lambda d: [dict(zip(d['cols'], r)) for r in d['rows']])(json.load(open(os.path.join(TB, t + '.json'), encoding='utf-8')))
norm = lambda s: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
OURS = {norm(k): k for k in D['region_of']}
ALIAS = {'Brentwood': 'Lane', 'Sunrise': 'Lee'}
key = lambda s: ALIAS.get(s) or OURS.get(norm(s or ''))
rules, S, U = L('scenarios'), L('2027 Summary'), L('2027 utilization before and after')
num = lambda v: float(v) if v not in (None, '') else 0.0
act = lambda r: str(r['Is_Active_School']) in ('1', '1.0')
RUNS = {'A': 'Seventy Percent', 'B': 'Fifty Percent', 'S60': 'Sixty Percent', 'BAL': 'Balanced'}
U27 = {(r['eval_scenario'], r['school']): r for r in U if r['year'] == '2027'}
out = {'source': 'PPS Rightsizing Scenarios Schools dashboard (Power BI, version 1.0, October 14, 2026), 2027-28', 'runs': {}}
for sc, run in RUNS.items():
    R = [r for r in rules if r['scenario_name'] == run]
    moves = [r for r in R if r['school_to'] not in ('', None) and r['school_to'] != r['school_from'] and num(r['percent_of_projections_to_move']) > 0]
    rec = {r['school_to'] for r in moves if r['school_to'] != 'neighborhood'}
    senders = {r['school_from'] for r in moves}
    arr = collections.Counter()
    for r in S:
        if r['eval_scenario'] == run and r['school'] in rec:
            d = num(r['Difference (M - O)'])
            if d > 0: arr[r['school']] += d
    rows = []
    for s in sorted(rec):
        a, q = U27.get((run, s)), U27.get(('Status Quo', s))
        if not a or not act(a) or num(a['projected enrollment after changes']) <= 0: continue
        e = num(a['projected enrollment after changes'])
        only = s not in senders and q is not None and a['Column1'] == q['Column1'] and a['Future Program Type'] == q['Future Program Type'] and a['Immersion Language'] == q['Immersion Language']
        rows.append([key(s) or s, a['Column1'], round(arr[s]), round(e), round(arr[s] / e, 4), only])
    closing = [s for (rn, s), a in U27.items() if rn == run and not act(a) and ('Status Quo', s) in U27 and act(U27[('Status Quo', s)])]
    out['runs'][sc] = {'run': run, 'receivers': rows, 'arriving': sum(r[2] for r in rows), 'at_receivers': sum(r[3] for r in rows),
                       'closing_students': round(sum(num(U27[('Status Quo', s)]['projected enrollment after changes']) for s in closing)),
                       'only': [r[0] for r in rows if r[5]], 'off_page': [r[0] for r in rows if r[0] not in D['region_of']],
                       # open schools whose 2027-28 enrollment falls by more than 25% from Status Quo: [key, before, after]
                       'shrink': [[key(s) or s, round(num(a['projected enrollment before changes'])), round(num(a['projected enrollment after changes']))]
                                  for (rn, s), a in sorted(U27.items()) if rn == run and act(a) and num(a['projected enrollment before changes']) > 0
                                  and num(a['projected enrollment after changes']) < num(a['projected enrollment before changes']) * 0.75]}
json.dump(out, open(os.path.join(ROOT, 'source', 'pps-powerbi', 'receiving.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
for sc, o in out['runs'].items():
    print(f"{sc}: {len(o['receivers'])} receivers, {o['arriving']:,} arriving, {o['at_receivers']:,} students at them, closing schools {o['closing_students']:,}; only receive {len(o['only'])}: {', '.join(o['only'])}; off page {o['off_page']}")
