"""Add annual cost (2026-27 dollars) to the staffing estimate, using General Fund salary and FTE by employee type
from the PPS 2026-27 Proposed Budget, Vol. 1, p. 100 (General Fund requirements by major object, $ thousands)."""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()
if 'staffCost(' in html: sys.exit('already patched')

# ---- rates from the budget (General Fund, 2026-27 proposed) ----
GF = dict(licensed=(276175, 2718.10), classified=(65416, 1255.72), nonrep=(35185, 307.62), admin=(33957, 199.90), other_salaries=24531, payroll=245251)
salaries = GF['licensed'][0] + GF['classified'][0] + GF['nonrep'][0] + GF['admin'][0] + GF['other_salaries']
load = GF['payroll'] / salaries                         # benefits + payroll taxes per salary dollar
rate = lambda k: GF[k][0] * 1000 / GF[k][1] * (1 + load)
COSTS = dict(
    source='PPS 2026-27 Proposed Budget, Vol. 1, p. 100: General Fund salaries and budgeted FTE by employee type; associated payroll costs spread over all salaries',
    payroll_load=round(load, 4),
    licensed=round(rate('licensed')),          # teachers, counselors, specialists, discretionary (licensed-equivalent FTE)
    administrator=round(rate('admin')),        # principals, assistant / vice principals
    classified=round(rate('classified')),      # administrative assistants: 1 licensed-equivalent = 2 classified FTE
    slide7_check=159500,                       # PPS board deck slide 7 implies ~$159.5k per formula FTE
)
print(json.dumps(COSTS, indent=1))

m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1)); D['staff']['costs'] = COSTS
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# cost of a set of formula positions: administrators at the administrator rate, office support as classified staff
# (2 classified FTE per licensed-equivalent), everything else at the licensed rate
rep("function staffAgg(keys, sc, yi) {",
"""const SC = D.staff.costs;
function staffCost(a) {
  return (a.principal + a.ap) * SC.administrator + a.office * 2 * SC.classified
    + (a.homeroom + a.specialists + a.support + a.t68 + a.t912) * SC.licensed;
}
const usdM = v => (v < 0 ? '&minus;' : '') + '$' + (Math.abs(v) / 1e6).toFixed(1) + 'M';
function staffAgg(keys, sc, yi) {""")
rep("  ['t68', '6-8 teachers'], ['t912', '9-12 teachers'], ['total', 'Total']];",
    "  ['t68', '6-8 teachers'], ['t912', '9-12 teachers'], ['total', 'Total FTE']];")
# header + cells
rep("<th>Buildings closed</th>${STAFF_COLS.map(([, l]) => `<th>${l}</th>`).join('')}</tr></thead><tbody>`;",
    "<th>Buildings closed</th>${STAFF_COLS.map(([, l]) => `<th>${l}</th>`).join('')}<th>Annual cost (2026-27 $)</th></tr></thead><tbody>`;")
rep("""        : `<td><span class="main">${fte1(d)}</span><span class="muted" style="display:block;font-size:11px">of ${sq[c].toFixed(c === 'principal' || c === 'ap' ? 0 : 1)}</span></td>`;
    }
    h += '</tr>';""",
"""        : `<td><span class="main">${fte1(d)}</span><span class="muted" style="display:block;font-size:11px">of ${sq[c].toFixed(c === 'principal' || c === 'ap' ? 0 : 1)}</span></td>`;
    }
    const cs = staffCost(sq), cc = staffCost(cur);
    h += isSQ ? `<td>${usdM(cs)}</td>` : `<td><span class="main">${usdM(cc - cs)}</span><span class="muted" style="display:block;font-size:11px">of ${usdM(cs)}</span></td>`;
    h += '</tr>';""")
rep("""          STAFF_COLS.map(([c]) => isSQ ? `<td>${a[c].toFixed(c === 'principal' || c === 'ap' ? 0 : 1)}</td>` : `<td>${fte1((b ? b[c] : 0) - a[c])}</td>`).join('') + '</tr>';""",
"""          STAFF_COLS.map(([c]) => isSQ ? `<td>${a[c].toFixed(c === 'principal' || c === 'ap' ? 0 : 1)}</td>` : `<td>${fte1((b ? b[c] : 0) - a[c])}</td>`).join('') +
          (isSQ ? `<td>${usdM(staffCost(a))}</td>` : `<td>${usdM((b ? staffCost(b) : 0) - staffCost(a))}</td>`) + '</tr>';""")
# summary sentence: add the dollar figure
rep("""    : `${LABEL[scen]} in ${staffYear}, compared with Status Quo the same year: about <b>${(dsq.total - dist.total).toFixed(0)}</b> fewer formula positions""",
"""    : `${LABEL[scen]} in ${staffYear}, compared with Status Quo the same year: about <b>${usdM(staffCost(dsq) - staffCost(dist)).replace('&minus;', '')}</b> a year in formula staffing (2026-27 dollars, salary plus benefits), from about <b>${(dsq.total - dist.total).toFixed(0)}</b> fewer formula positions""")
rep("Whether reductions become layoffs, reassignments or attrition is PPS's decision.</p>",
    "Whether reductions become layoffs, reassignments or attrition is PPS's decision. Costs use 2026-27 General Fund salary per budgeted FTE by employee type plus associated payroll costs (pension, FICA, health and other benefits, about 56% of salaries; Proposed Budget p. 100): about $159k per licensed FTE (matching the roughly $159.5k per formula FTE implied by PPS's October 6 board slide 7), $265k per principal or assistant/vice principal, and $81k per administrative assistant. They are averages in 2026-27 dollars, without raises or cost escalation, and exclude custodial, utilities and other building operating costs.</p>")
open(PAGE, 'w', encoding='utf-8').write(html)

# keep scripts/staffing.js in sync with the page's staffing block
src = os.path.join(ROOT, 'scripts', 'staffing.js')
blk = html[html.index('// ---------- staffing estimate'):html.index('function renderAll()')]
open(src, 'w', encoding='utf-8').write(blk)
print('patched')
