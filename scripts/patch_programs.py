"""School programs and designations under each school's name in the school report: immersion (DLI) programs with
2025-26 enrollment, Title I and ODE support status (CSI / TSI), SUN Community School, and centrally assigned special
education staff (source/pps-programs/school-programs.json, scripts/build_school_programs.py), and what changes in the
scenario being viewed:
  - immersion programs moving in or out, read from PPS's scenario change list (D.fchanges: program moves, and the
    "[Spanish DLI]" destinations of closures)
  - Title I: estimated. The school's 2024-25 Direct Certification share is scaled by the change in this page's low-income
    share for the school between Status Quo and the scenario (D.detail .g.poverty / enrollment); flagged only when that
    crosses PPS's threshold (33% for elementary, middle and K-8 schools, 46.9% for high schools)
  - a closing school's SUN site and special education staff need a new home (PPS and the county have not said where);
    schools receiving students from a closing SUN school are noted
Data: D.progs. Safe to rerun: data refreshed, page code (in scripts/school_report.js) re-embedded by patch_school_report.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
P = json.load(open(os.path.join(ROOT, 'source', 'pps-programs', 'school-programs.json'), encoding='utf-8'))
S = P['schools']
names = {}
for s in D['schools']:
    for n in {s['key'], s['name'], re.sub(r'\s+(Elementary|Middle|High|K-8)\b.*$', '', s['name'])}: names[n.lower()] = s['key']
names.update({'cesar chavez': 'César Chávez', 'mlk jr.': 'MLK Jr', 'mlk jr': 'MLK Jr', 'boise-eliot/humboldt': 'Boise-Eliot/Humboldt'})
def key_of(t):
    t = t.strip().rstrip('.').lower()
    t = re.sub(r'\s+(elementary|middle school|middle|high school|k-8 school|k-8)$', '', t)
    return names.get(t)

chg = {}
for sc in ('A', 'B'):
    out = chg.setdefault(sc, {})
    add = lambda k, txt: k and out.setdefault(k, []).append(txt) if k and txt not in out.get(k, []) else None
    for school, kind, text, *_ in D['fchanges'][sc]:
        # "Spanish DLI: Sitton (and Beach, James John) consolidate at Cesar Chavez" / "Chinese (Mandarin) DLI: MLK Jr. to Boise-Eliot/Humboldt"
        mm = re.match(r'^(.+?) DLI(?: grades ([\d-]+))?: (.+?)(?: \(and ([^)]+)\))? (?:to|consolidate at) (.+)$', text)
        if mm:
            lang, gr, src, more, dst = mm.groups(); lab = f"{lang} immersion{f' (grades {gr})' if gr else ''}"
            for s_ in [src] + (more.split(', ') if more else []):
                add(key_of(s_), f'{lab} moves to {dst.strip()}'); add(key_of(dst), f'Receives {lab} from {s_.strip()}')
            continue
        mm = re.match(r'^(.+?) DLI(?: grades ([\d-]+))? moves? from (.+?) to (.+?)(;|,| so|$)', text)
        if mm:
            lang, gr, src, dst = mm.groups()[:4]; lab = f"{lang} immersion{f' (grades {gr})' if gr else ''}"
            add(key_of(src), f'{lab} moves to {dst.strip()}'); add(key_of(dst), f'Receives {lab} from {src.strip()}')
            continue

    # closures' immersion destinations ("... [Spanish DLI]"), unless a program move already covers them
    for school, kind, text, *_ in D['fchanges'][sc]:
        if kind != 'closure': continue
        for dst, lang in re.findall(r'(?:into |, )([^,\[]+?) \[([^\]]+?) DLI\]', text):
            if not any('immersion' in t for t in out.get(school, [])): add(school, f'{lang} immersion students go to {dst.strip()}')
            dk = key_of(dst)
            if dk and not any(school in t and 'immersion' in t for t in out.get(dk, [])): add(dk, f'Receives {lang} immersion students from {school}')
    # special programs that move with a closure (PPS's receiving list: D.flows), such as Creston's Deaf and Hard of Hearing program
    for r in D['flows'][sc]['receivers']:
        g = r['group']
        if re.search(r'neighborhood|students$|middle school area|immersion', g, re.I): continue
        add(r['from_key'], f"{g} moves to {r['to_key']}"); add(r['to_key'], f"Receives {r['from_key']}'s {g}")
# closing schools: SUN site and special education staff; receivers of a closing SUN school
for sc in ('A', 'B'):
    det = D['detail'][sc]
    for k, v in S.items():
        if not det.get(k, {}).get('closed'): continue
        if v['sun']: chg[sc].setdefault(k, []).append('SUN Community School site closes with the building (Multnomah County decides any new site)')
        sl, sc_ = (v['sped_licensed'] or [None] * 6)[5], (v['sped_classified'] or [None] * 6)[5]
        if sl or sc_: chg[sc].setdefault(k, []).append(f'Special education staff ({sl or 0:g} licensed, {sc_ or 0:g} classified FTE) and any special education classrooms would need a new location; PPS has not said where')
    for school, kind, text, dests in [(c[0], c[1], c[2], c[4] if len(c) > 4 else []) for c in D['fchanges'][sc]]:
        if kind == 'closure' and S.get(school, {}).get('sun'):
            for d_ in dests or []:
                if d_ and d_[0] and not S.get(d_[0], {}).get('sun'): chg[sc].setdefault(d_[0], []).append(f'Receives students from {school}, a SUN Community School (this school is not a SUN site)')
# Title I, estimated: a receiving school's Direct Certification share becomes the enrollment-weighted mix of its own
# students' 2024-25 share and the shares of the closing schools whose students it receives (PPS's receiving list,
# D.flows; a closing school's students split by the listed shares, else evenly among its receivers). Immersion moves
# between open schools are not included (their students' shares are not published).
T1 = {}
for sc in ('A', 'B'):
    det, sq = D['detail'][sc], D['detail']['SQ']
    recv = {}
    for r in D['flows'][sc]['receivers']:
        if det.get(r['from_key'], {}).get('closed'): recv.setdefault(r['from_key'], []).append(r)
    inc = {}
    for j, rs in recv.items():
        dj, ej = S.get(j, {}).get('dc_2425'), sq.get(j, {}).get('e') or 0
        if dj is None or not ej: continue
        known = sum(r['share'] or 0 for r in rs); unk = [r for r in rs if r['share'] is None]
        for r in rs:
            sh = r['share'] if r['share'] is not None else max(0.0, 1 - known) / len(unk)
            inc.setdefault(r['to_key'], []).append((j, ej * sh, dj))
    for k, lst in inc.items():
        v = S.get(k); e0 = sq.get(k, {}).get('e') or 0
        if not v or v['dc_2425'] is None or det.get(k, {}).get('closed') or not e0: continue
        n_in = sum(x[1] for x in lst)
        est = (e0 * v['dc_2425'] + sum(x[1] * x[2] for x in lst)) / (e0 + n_in)
        th = 46.9 if (D['types'][sc].get(k) or D['types']['SQ'].get(k)) == 'HS' else 33.0
        T1.setdefault(sc, {})[k] = [round(est, 1), th, [[j, round(n), d] for j, n, d in lst]]
        # flagged only where the rate explains the status (Title I at or above the threshold, or not Title I below it) and the
        # estimate crosses it; schools that are Title I below the threshold (bridged) are left alone
        now = v['dc_2425'] >= th
        if bool(v['title1']) == now and (est >= th) != now:
            chg[sc].setdefault(k, []).append(f"Title I: may {'qualify' if est >= th else 'no longer qualify'} (est. {est:.0f}% Direct Certification after receiving "
                                             f"{', '.join(j for j, _, _ in lst)} students, against the {th:g}% threshold; {v['dc_2425']:g}% in 2024-25)")
D['progs'] = dict(sch={k: {f: v[f] for f in ('type', 'programs', 'ode', 'title1', 'dc_2425', 'sun')} | dict(
                      sped=[(v['sped_licensed'] or [None] * 6)[5], (v['sped_classified'] or [None] * 6)[5]],
                      dli={p: e.get('2025-26') for p, e in v['enroll_by_program'].items() if 'Immersion' in p and e.get('2025-26')},
                      total=next((e.get('2025-26') for p, e in v['enroll_by_program'].items() if p == 'Total'), None),
                      page=v['budget_page']) for k, v in S.items()},
                  chg=chg, t1=T1, rule=P['title1_rule'], source=P['source'])
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
for sc in chg: print(sc, json.dumps(chg[sc], ensure_ascii=False)[:2500])
