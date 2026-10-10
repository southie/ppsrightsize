"""Outstanding repairs instead of full modernization: the building costs table, the building-cost summary card and the
method note now total the outstanding maintenance and repair needs (deferred maintenance + remaining seismic retrofit,
the 2021 plan's "must-fix"), shown as a total and its two parts. Full modernization (replacement value) is no longer
presented as a cost: it stays only as a reference note (hover tips, school detail lines, the summary card, the
school report). Runs after patch_building_table and patch_bond. Code changed once. (The school report's building
costs panel is changed the same way in scripts/school_report.js.)
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
html = open(PAGE, encoding='utf-8').read()

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

if 'Outstanding repairs<br>' not in html:
    # ---- table: total, deferred maintenance, seismic retrofit (replacement value only as a note) ----
    rep("  const amt = (v, tot) => isSQ ? `<span class=\"main\">${usdM(v)}</span>`",
        "  // sum of a cost field over schools (closed buildings only, under a scenario)\n"
        "  const sumC = (keys, f, closedOnly) => keys.reduce((s, k) => s + (!closedOnly || det[k]?.closed ? (C[k]?.[f] || 0) : 0), 0);\n"
        "  const amt = (v, tot) => isSQ ? `<span class=\"main\">${usdM(v)}</span>`")
    rep("""<th>Must-fix<br><span style="font-weight:400">${isSQ ? 'all buildings' : 'avoided by closures'} (deferred maintenance + seismic)</span></th>` +""",
        """<th>Outstanding repairs<br><span style="font-weight:400">${isSQ ? 'all buildings' : 'avoided by closures'}: total</span></th>` +""")
    rep("""    `<th>Full modernization<br><span style="font-weight:400">${isSQ ? 'all buildings' : 'avoided by closures'}</span></th><th>Operating cost""",
        """    `<th>Deferred maintenance<br><span style="font-weight:400">2021 condition (FCI) &times; replacement value</span></th><th>Seismic retrofit<br><span style="font-weight:400">remaining, incl. masonry</span></th><th>Operating cost""")
    rep("""      `<td>${amt(isSQ ? t.mf : a.mf, t.mf)}</td><td>${amt(isSQ ? t.mod : a.mod, t.mod)}</td>` +""",
        """      `<td title="${esc(`Replacement value of ${isSQ ? 'all these buildings' : 'the closed buildings'}, for reference (not a cost): ${usdM(isSQ ? t.mod : a.mod)}`)}">${amt(isSQ ? t.mf : a.mf, t.mf)}</td>` +
      `<td>${amt(sumC(keys, 'dm', !isSQ), sumC(keys, 'dm', false))}</td><td>${amt(sumC(keys, 'se', !isSQ), sumC(keys, 'se', false))}</td>` +""")
    rep("""        (c ? cell(c.mf) + cell(c.mod) : '<td class="muted">&mdash;</td><td class="muted">&mdash;</td>') +""",
        """        (c ? cell(c.mf) + cell(c.dm) + cell(c.se) : '<td class="muted">&mdash;</td><td class="muted">&mdash;</td><td class="muted">&mdash;</td>') +""")
    rep("""      const tip = c ? `Deferred maintenance ${c.dm == null ? 'n/a' : usdM(c.dm)} + seismic retrofit ${c.se == null ? 'n/a' : usdM(c.se)}${c.urm ? ` (URM part ${usdM(c.urm)})` : ''}` : '';""",
        """      const tip = c ? `Deferred maintenance ${c.dm == null ? 'n/a' : usdM(c.dm)} + seismic retrofit ${c.se == null ? 'n/a' : usdM(c.se)}${c.urm ? ` (URM part ${usdM(c.urm)})` : ''}. Replacement value, for reference (not a cost): ${c.mod == null ? 'n/a' : usdM(c.mod)}` : '';""")
    rep("""${c?.sf ? `${c?.fci != null ? ' &middot; ' : ''}${c.sf.toLocaleString()} sq ft` : ''}</span></td>` +""",
        """${c?.sf ? `${c?.fci != null ? ' &middot; ' : ''}${c.sf.toLocaleString()} sq ft` : ''}${c?.mod ? ` &middot; replacement value ${usdM(c.mod)} (reference)` : ''}</span></td>` +""")
    rep("""from the 2021 Long-Range Facility Plan: <b>must-fix</b> = deferred maintenance + seismic retrofit; <b>modernize</b> = full modernization. Under Status Quo every building stays open; under a scenario, the costs of the buildings it closes are avoided (shown against the Status Quo total).""",
        """from the 2021 Long-Range Facility Plan: <b>outstanding repairs</b> = deferred maintenance (the 2021 facility condition index &times; replacement value) + the remaining seismic retrofit (Holmes 2024, including unreinforced-masonry work). Under Status Quo every building stays open; under a scenario, the repairs of the buildings it closes are avoided (shown against the Status Quo total). Replacement value (building area &times; the plan's cost per square foot) is shown only for reference in the school rows and tooltips: it is what a new building would cost, not money owed.""")
    # ---- summary card ----
    rep("""      ? `<div class="kpi"><div class="v">${usdM(t.mf)}</div><div class="l">Must-fix building costs, all buildings (deferred maintenance + seismic retrofit, 2026 $)</div>` +
        `<div class="s">Full modernization, all buildings: <b>${usdM(t.mod)}</b></div></div>`""",
        """      ? `<div class="kpi"><div class="v">${usdM(t.mf)}</div><div class="l">Outstanding building repairs, all buildings (deferred maintenance + seismic retrofit, 2026 $)</div>` +
        ((ks) => `<div class="s">Deferred maintenance: <b>${usdM(ks.reduce((s, k) => s + (D.costs[k]?.dm || 0), 0))}</b><br>Seismic retrofit: <b>${usdM(ks.reduce((s, k) => s + (D.costs[k]?.se || 0), 0))}</b><br><span class="pcs">Replacement value, for reference (not a cost): ${usdM(t.mod)}</span></div></div>`)(Object.keys(D.costs || {}))""")
    rep("""        `<div class="l">Must-fix building costs avoided by closures, of ${usdM(t.mf)} under Status Quo (deferred maintenance + seismic retrofit, 2026 $)</div>` +
        `<div class="s">Full modernization avoided: <b>${usdM(a.mod)}</b> (${pctOf(-a.mod, t.mod)} of ${usdM(t.mod)})${a.n ? ` &middot; ${a.n} building${a.n === 1 ? '' : 's'}` : ''}</div>` +""",
        """        `<div class="l">Outstanding building repairs avoided by closures, of ${usdM(t.mf)} under Status Quo (deferred maintenance + seismic retrofit, 2026 $)</div>` +
        ((ks) => `<div class="s">Deferred maintenance: <b>${usdM(ks.reduce((s, k) => s + (D.costs[k]?.dm || 0), 0))}</b> &middot; seismic retrofit: <b>${usdM(ks.reduce((s, k) => s + (D.costs[k]?.se || 0), 0))}</b>${a.n ? ` &middot; ${a.n} building${a.n === 1 ? '' : 's'}` : ''}<br><span class="pcs">Replacement value of the closed buildings, for reference (not a cost): ${usdM(a.mod)}</span></div>`)(Object.keys(D.costs || {}).filter(k => D.detail[scen]?.[k]?.closed)) +""")
    # ---- method note ----
    rep("""'Building costs (2026 dollars): must-fix = deferred maintenance + remaining seismic retrofit; full modernization = replacement value. Replacement value is""",
        """'Building costs (2026 dollars): outstanding repairs = deferred maintenance + remaining seismic retrofit (the plan\\'s must-fix); replacement value (full modernization) is shown only for reference, not as a cost. Replacement value is""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
