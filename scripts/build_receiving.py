"""Receiving schools in PPS's model runs (source/pps-powerbi tables, scripts/fetch_pps_powerbi.py): the impact of each
wave of changes, summed. Most changes take effect in 2027-28; Sellwood's and Marysville's students move in 2028-29.
Output: source/pps-powerbi/receiving.json
  For each run (A = Seventy Percent, B = Fifty Percent, S60 = Sixty Percent, BAL = Balanced):
  waves: the 2027-28 changes and the 2028-29 changes, each from its own enrollment changes:
    2027-28: each grade and student group's change from the school's Status Quo projection (2027 Summary, PPS's
      grade-level results): increases are students arriving, decreases students leaving. A school that gains and loses
      students in the same grade counts only the net change, so these are floors.
    2028-29: PPS's move rules that take effect in 2028 (scenarios table, share of projections moved above 0) x the moved
      group's grades in PPS's 2028-29 Status Quo projection (projections table): students arriving at the receiving
      school, leaving the sending school.
  receivers: schools that take students from another school under the run's move rules, open after the changes:
    [page key, PPS type, arriving (both waves), enrollment after both waves, share new, only receives, arriving 2027-28,
     arriving 2028-29]
    enrollment after both waves: its 2027-28 enrollment after changes + 2028-29 arrivals - 2028-29 departures.
    only receives: no rule sends any of its students to another school (or to neighborhood schools), and its grades,
      program type and immersion language are the same as in Status Quo.
  totals by wave and summed: arriving students; students at schools that close (their Status Quo enrollment in the year
  they close); students at receiving schools (after both waves).
  shrink: open schools whose enrollment after both waves is more than 20% below their 2027-28 Status Quo enrollment:
    [key, Status Quo, after].
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
rules, S, U, P = L('scenarios'), L('2027 Summary'), L('2027 utilization before and after'), L('projections (2)')
num = lambda v: float(v) if v not in (None, '') else 0.0
act = lambda r: str(r['Is_Active_School']) in ('1', '1.0')
RUNS = {'A': 'Seventy Percent', 'B': 'Fifty Percent', 'S60': 'Sixty Percent', 'BAL': 'Balanced'}
U27 = {(r['eval_scenario'], r['school']): r for r in U if r['year'] == '2027'}
U28 = {(r['eval_scenario'], r['school']): r for r in U if r['year'] == '2028'}
# Status Quo projection by school, group and grade, 2028-29 (the students a 2028 rule moves)
P28 = collections.defaultdict(float)
for r in P:
    if str(r['year']) == '2028' and r['count'] not in (None, ''): P28[(r['school'], r['group'], int(r['grade']))] += num(r['count'])
grade = lambda g: 0 if str(g) in ('0', 'K', '') else int(g)
out = {'source': 'PPS Rightsizing Scenarios Schools dashboard (Power BI, version 1.0, October 14, 2026)', 'waves': ['2027-28', '2028-29'], 'runs': {}}
for sc, run in RUNS.items():
    R = [r for r in rules if r['scenario_name'] == run]
    moves = [r for r in R if r['school_to'] not in ('', None) and r['school_to'] != r['school_from'] and num(r['percent_of_projections_to_move']) > 0]
    rec = {r['school_to'] for r in moves if r['school_to'] != 'neighborhood'}
    senders = {r['school_from'] for r in moves}
    # wave 1: 2027-28, PPS's grade-level results
    arr27, out27, aft27 = collections.Counter(), collections.Counter(), collections.Counter()
    for r in S:
        if r['eval_scenario'] != run: continue
        d = num(r['Difference (M - O)']); aft27[r['school']] += num(r['Modeled'])
        if d > 0: arr27[r['school']] += d
        else: out27[r['school']] += -d
    # wave 2: 2028-29, the rules that take effect in 2028 x the moved students
    arr28, out28 = collections.Counter(), collections.Counter()
    for r in moves:
        if str(r['year_of_change']) != '2028': continue
        g0, g1 = grade(r['grade']), grade(r['up_to_grade'])
        n = num(r['percent_of_projections_to_move']) * sum(P28[(r['school_from'], r['group_from'], g)] for g in range(g0, g1 + 1))
        out28[r['school_from']] += n
        if r['school_to'] != 'neighborhood': arr28[r['school_to']] += n
    rows = []
    for s in sorted(rec):
        a = U28.get((run, s)) or U27.get((run, s)); q = U27.get(('Status Quo', s))
        e = aft27[s] + arr28[s] - out28[s]
        if not a or e <= 0 or (not act(a) and num(a['projected enrollment after changes']) <= 0): continue
        only = s not in senders and q is not None and a['Column1'] == q['Column1'] and a['Future Program Type'] == q['Future Program Type'] and a['Immersion Language'] == q['Immersion Language']
        tot = arr27[s] + arr28[s]
        rows.append([key(s) or s, a['Column1'], round(tot), round(e), round(tot / e, 4), only, round(arr27[s]), round(arr28[s])])
    sq_act = lambda Uy, s: ('Status Quo', s) in Uy and act(Uy[('Status Quo', s)])
    closed27 = [s for (rn, s), a in U27.items() if rn == run and not act(a) and num(a['projected enrollment after changes']) <= 0 and sq_act(U27, s)]
    closed28 = [s for (rn, s), a in U28.items() if rn == run and not act(a) and num(a['projected enrollment after changes']) <= 0 and s not in closed27 and sq_act(U28, s)]
    c27 = round(sum(num(U27[('Status Quo', s)]['projected enrollment after changes']) for s in closed27))
    c28 = round(sum(num(U28[('Status Quo', s)]['projected enrollment after changes']) for s in closed28))
    shrink = []
    for (rn, s), q in sorted(U27.items()):
        if rn != 'Status Quo' or s in rec or s in closed27 or s in closed28 or s not in aft27: continue
        b0 = num(q['projected enrollment after changes']); e = aft27[s] + arr28[s] - out28[s]
        if b0 > 0 and 0 < e < 0.8 * b0: shrink.append([key(s) or s, round(b0), round(e)])
    out['runs'][sc] = {'run': run, 'receivers': rows,
                       'arriving_waves': [sum(r[6] for r in rows), sum(r[7] for r in rows)], 'arriving': sum(r[2] for r in rows),
                       'closing_waves': [c27, c28], 'closing_students': c27 + c28, 'closing_schools': [[key(s) or s for s in closed27], [key(s) or s for s in closed28]],
                       'at_receivers': sum(r[3] for r in rows), 'only': [r[0] for r in rows if r[5]],
                       'off_page': [r[0] for r in rows if r[0] not in D['region_of']], 'shrink': shrink}
json.dump(out, open(os.path.join(ROOT, 'source', 'pps-powerbi', 'receiving.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
for sc, o in out['runs'].items():
    print(f"{sc}: {len(o['receivers'])} receivers; arriving {o['arriving_waves'][0]:,} (2027-28) + {o['arriving_waves'][1]:,} (2028-29) = {o['arriving']:,}; "
          f"closing {o['closing_waves'][0]:,} + {o['closing_waves'][1]:,} ({', '.join(o['closing_schools'][1])}); at receivers {o['at_receivers']:,}; only {len(o['only'])}; shrink {o['shrink']}")
