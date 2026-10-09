"""rightsizing-scenario-explorer.html: a "School report" card above the map. Search for a school to see, for the
scenario being viewed against Status Quo: feeder and outflow pathways (changes marked), PPS's listed changes,
building costs, a boundary map, staffing under the budget formula and the PAT thresholds, enrollment vs capacity
over time, and students by grade.

Data added: D.feeders (Status Quo, A and B pathways [elementary, middle, high, program, note, changed]) and
D.fchanges (PPS's change list per scenario) from source/feeders/, and school keys for every boundary shape
(D.bounds[*].akeys) and changing area (D.bounds[*].ckeys). Page code: scripts/school_report.js.
Safe to rerun: data is refreshed, page code is replaced with the current scripts/school_report.js.
"""
import json, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
FEED = os.path.join(ROOT, 'source', 'feeders')
JS = os.path.join(ROOT, 'scripts', 'school_report.js')
html = open(PAGE, encoding='utf-8').read()
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
keys = {s['key'] for s in D['schools']}

# ---------- name -> school key ----------
def norm(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower().replace('.', '').replace("'", '')
    n = re.sub(r"\b(elementary|middle|high|school|k-8|k8|k-5|k5|6-8|9-12|academy|program|of|the|and|neighborhood)\b", ' ', n)
    return re.sub(r'[^a-z0-9]+', ' ', n).strip()
ALIAS = {'brentwood': 'Lane', 'sunrise': 'Lee', 'martin luther king jr': 'MLK Jr', 'king': 'MLK Jr', 'mlk jr': 'MLK Jr',
         'boise eliot humboldt': 'Boise-Eliot/Humboldt', 'boise eliot': 'Boise-Eliot/Humboldt', 'wells barnett': 'Ida B Wells-Barnett',
         'ida b wells barnett': 'Ida B Wells-Barnett', 'ida b wells': 'Ida B Wells-Barnett', 'bridger': 'Bridger Creative Science',
         'clark creative science': 'Clark', 'east sylvan': 'Odyssey', 'sunnyside': 'Sunnyside Environmental', 'mt tabor': 'Mt Tabor',
         'mount tabor': 'Mt Tabor', 'cesar chavez': 'César Chávez', 'leodis v mcdaniel': 'McDaniel', 'harrison park': 'Harrison Park'}
BYN = {}
for s in D['schools']:
    for n in (s['key'], s['name']): BYN[norm(n)] = s['key']
def key_of(name):
    """Longest leading run of words that names a school ("Cleveland High School Mandarin Immersion" -> Cleveland)."""
    w = norm(name or '').split()
    for i in range(len(w), 0, -1):
        n = ' '.join(w[:i])
        if n in ALIAS: return ALIAS[n]
        if n in BYN: return BYN[n]
    return None

# ---------- pathways and PPS's change list ----------
D['feeders'], D['fchanges'] = {}, {}
for sc, f in [('SQ', 'pps-feeder-patterns.json'), ('A', 'pps-feeder-patterns-scenario-a.json'), ('B', 'pps-feeder-patterns-scenario-b.json')]:
    d = json.load(open(os.path.join(FEED, f), encoding='utf-8'))
    D['feeders'][sc] = [[p.get('elementary_forecast_name'), p.get('middle_forecast_name'), p.get('high_school_forecast_name'),
                         p.get('program') or '', p.get('note') or '', bool(p.get('changed'))] for p in d['pathways']]
    bad = {x for p in D['feeders'][sc] for x in p[:3] if x and x not in keys}
    if bad: print(f'{sc}: pathway names not explorer keys: {sorted(bad)}')
    if sc != 'SQ':
        D['fchanges'][sc] = [[key_of(c.get('school')), c.get('type', ''), c.get('change', ''), c.get('source', ''),
                              [[key_of(r.get('school')), r.get('share')] for r in c.get('receivers', [])]] for c in d.get('changes', [])]
print('pathways:', {sc: len(v) for sc, v in D['feeders'].items()}, '| PPS changes:', {sc: len(v) for sc, v in D['fchanges'].items()})

# ---------- school keys for boundary shapes ----------
missing = set()
for bk, B in D['bounds'].items():
    B['akeys'] = [key_of(lab) for lab, g in B['areas']]
    B['ckeys'] = [[key_of(f), key_of(t)] for f, t, g in B.get('changed', [])]
    missing |= {lab for (lab, g), k in zip(B['areas'], B['akeys']) if not k}
    missing |= {n for (f, t, g), ks in zip(B.get('changed', []), B['ckeys']) for n, k in zip((f, t), ks) if not k}
print('boundary labels not matched to a school:', sorted(missing) or 'none')
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b, n=1):
    global html
    assert html.count(a) == n, (html.count(a), a[:110])
    html = html.replace(a, b)

CSS = """
/* school report */
#reportcard .controls input[type=search] { width: 300px; max-width: 100%; }
#reportcard .controls button { font: inherit; font-size: 13px; padding: 4px 10px; border-radius: 6px; border: 1px solid var(--line); background: var(--surface-1); color: var(--text-primary); cursor: pointer; }
.rphead { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 6px 0 10px; }
.rphead h3 { margin: 0; font-size: 18px; }
.rpkpis { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.rpkpis > div { background: var(--surface-2); border-radius: 10px; padding: 8px 12px; min-width: 130px; }
.rpkpis b { display: block; font-size: 20px; } .rpkpis span { font-size: 12px; color: var(--text-secondary); }
.rpgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 900px) { .rpgrid { grid-template-columns: 1fr; } }
.rppanel { background: var(--surface-2); border-radius: 10px; padding: 12px 14px; min-width: 0; }
.rppanel.rpwide { grid-column: 1 / -1; }
.rppanel h3 { margin: 0 0 8px; font-size: 14px; }
.rppanel h4 { margin: 12px 0 4px; font-size: 12px; color: var(--text-secondary); font-weight: 600; }
.rppanel table, .rptable { min-width: 0; width: auto; font-size: 12.5px; }
.rptable { min-width: min(100%, 420px); } .rptable.full { width: 100%; }
.rptable th, .rptable td { padding: 3px 6px; text-align: right; } .rptable th:first-child, .rptable td:first-child { text-align: left; }
.rptable tr.tot td { font-weight: 600; } .rptable td.over { color: var(--down); font-weight: 600; }
.rptable .sq { display: block; font-size: 10.5px; color: var(--text-muted); }
.rptable.sm { margin-top: 6px; font-size: 12px; }
.rpflow { display: flex; align-items: flex-start; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.rpcol { flex: 1 1 0; min-width: 170px; display: flex; flex-direction: column; gap: 6px; }
.rpcol h4 { margin: 0 0 2px; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted); }
.rparrow { align-self: center; font-size: 22px; color: var(--text-muted); padding-top: 14px; }
.rpbox { border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px; font-size: 12.5px; background: var(--surface-1); }
.rpbox .n { font-size: 11px; color: var(--text-muted); } .rpbox .nt { display: block; font-size: 11.5px; color: var(--text-secondary); margin-top: 2px; }
.rpbox.add { box-shadow: inset 4px 0 0 var(--up); } .rpbox.rem { opacity: .65; box-shadow: inset 4px 0 0 var(--down); } .rpbox.rem b { text-decoration: line-through; }
.rplink { color: inherit; text-decoration: underline dotted; text-underline-offset: 2px; cursor: pointer; } .rplink:hover { color: var(--change); text-decoration-style: solid; }
.rpbox.self { border-width: 2px; border-color: var(--text-primary); } .rpbox.none { color: var(--text-muted); }
.rpmoves { display: block; margin-top: 6px; font-weight: 400; } .rpmoves .h { display: block; font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .03em; }
.rpmoves .mv { display: block; margin-top: 4px; font-size: 12.5px; } .rpmoves .why { display: block; font-size: 11.5px; color: var(--text-secondary); padding-left: 12px; }
.rpbadge { display: inline-block; margin-left: 6px; font-size: 10.5px; padding: 0 6px; border-radius: 9px; border: 1px solid currentColor; }
.rpbadge.add { color: var(--up); } .rpbadge.rem { color: var(--down); } .rpbadge.cl { color: #fff; background: var(--close); border-color: var(--close); }
.rplist { margin: 4px 0 0; padding-left: 18px; font-size: 12.5px; } .rpline { margin: 4px 0; font-size: 12.5px; }
.rpnote { font-size: 11.5px; margin: 6px 0 0; }
#rpmap { height: 300px; border-radius: 8px; }
.rpplot { width: 100%; max-width: 760px; height: auto; display: block; }
.rpplot .grid { stroke: var(--grid); } .rpplot .ax { font-size: 10px; fill: var(--text-muted); } .rpplot .lab { font-size: 10px; }
.rpplot path.lsq, .rpplot path.la, .rpplot path.lb, .rpplot path.lc { fill: none; stroke-width: 1.8; opacity: .85; } .rpplot path.cur { stroke-width: 3.2; opacity: 1; }
.rpplot .lsq { stroke: var(--none); } .rpplot .la { stroke: var(--change); } .rpplot .lb { stroke: #0f9b78; } .rpplot .lc { stroke: #b0369a; }
.rpplot circle.lsq { fill: var(--none); } .rpplot circle.la { fill: var(--change); } .rpplot circle.lb { fill: #0f9b78; } .rpplot circle.lc { fill: #b0369a; } .rpplot circle { stroke: none; }
.rptable th.cur, .rptable td.cur { background: color-mix(in srgb, var(--change) 10%, transparent); } .rpline.cur { font-weight: 600; } .rplegend .cur { font-weight: 600; color: var(--text-primary); }
.rpplot line.cap { stroke: var(--down); stroke-dasharray: 6 4; } .rpplot text.cap { fill: var(--down); }
.rpplot line.thr { stroke: var(--text-secondary); stroke-dasharray: 2 4; } .rpplot text.thr { fill: var(--text-secondary); }
.rpplot .impl { stroke: var(--axis); stroke-dasharray: 3 3; }
.rplegend { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 11.5px; color: var(--text-secondary); margin-top: 4px; }
.rplegend .k { display: inline-block; width: 16px; height: 0; border-top: 2.5px solid; vertical-align: 3px; margin-right: 5px; }
.rplegend .k.lsq { border-color: var(--none); } .rplegend .k.la { border-color: var(--change); } .rplegend .k.lb { border-color: #0f9b78; } .rplegend .k.lc { border-color: #b0369a; } .rplegend .k.cap { border-top-style: dashed; border-color: var(--down); }
.rplegend .k.thr { border-top-style: dotted; border-color: var(--text-secondary); } .rplegend .k.impl { border-top-style: dashed; border-color: var(--axis); }
.rplegend .k.sqa { height: 10px; border: 2px dashed #33312c; width: 12px; vertical-align: -1px; } .rplegend .k.sca { height: 10px; border: 0; background: var(--change); opacity: .5; width: 14px; vertical-align: -1px; }
.rplegend .k.chg { height: 10px; border: 0; background: #d4a017; opacity: .8; width: 14px; vertical-align: -1px; }
/* end school report */"""
SECTION = """  <section class="card" id="reportcard">
    <h2>School report</h2>
    <p class="sub">Search for a school to see what the selected scenario does to it, compared with Status Quo: where its students come from and go, building costs, its attendance area, staffing, enrollment against capacity, and students by grade.</p>
    <div class="controls"><label>School <input type="search" id="rpfind" list="rplist" placeholder="e.g. Sunnyside Environmental" autocomplete="off"></label><datalist id="rplist"></datalist>
      <label>Staffing year <select id="rpyear"></select></label><button type="button" id="rpclear">Clear</button><button type="button" id="rpcopy">Copy link</button><span id="rpcopied" class="muted"></span></div>
    <div id="report"></div>
  </section>

"""
js = open(JS, encoding='utf-8').read().rstrip() + '\n'
START, END = '// ---------- school report: search above the map', '// ---------- end school report ----------\n'
if START in html:   # replace the injected code with the current file
    i = html.index(START); j = html.index(END, i) + len(END)
    html = html[:i] + js + END + html[j:]
    cs, ce = '\n/* school report */', '/* end school report */'
    if ce in html:   # and the styles
        i = html.index(cs); j = html.index(ce, i) + len(ce)
        html = html[:i] + CSS + html[j:]
    else:
        i = html.index(cs); j = html.index('\n.rplegend .k.chg', i); j = html.index('\n', j + 1)
        html = html[:i] + CSS + html[j:]
    print('report code and styles refreshed')
else:
    rep('.legend label { cursor: pointer; }', '.legend label { cursor: pointer; }' + CSS)
    i = html.index('  <section class="card">\n    <h2>Map: closures, receiving schools and moves</h2>')
    html = html[:i] + SECTION + html[i:]
    rep('function renderAll() { renderKPIs();', js + END + 'function renderAll() { renderReport(); renderKPIs();')
    print('report card added')

open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print(f'wrote {os.path.basename(PAGE)} ({len(html.encode()) / 1e6:.2f} MB)')
