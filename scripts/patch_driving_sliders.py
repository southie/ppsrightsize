"""Switch rightsizing-scenario-explorer.html to driving distance (source/osrm/osrm-matrix.json)
and add proportional split sliders for custom-scenario closures."""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
MAT = os.path.join(ROOT, 'source', 'osrm', 'osrm-matrix.json')
html = open(PAGE, encoding='utf-8').read()

# ---------- data: driving matrix aligned to D.schools and D.private ----------
m = re.search(r'const D = (\{.*?\});\nconst esc', html, re.S)
D = json.loads(m.group(1))
M = json.load(open(MAT, encoding='utf-8'))
assert [s['key'] for s in M['pps']] == [s['key'] for s in D['schools']], 'school order differs'
col = {(p['name'], round(p['lat'], 5), round(p['lng'], 5)): j for j, p in enumerate(M['private'])}
pmap = [col.get((x['name'], round(x['lat'], 5), round(x['lng'], 5))) for x in D['private']]
print('private schools with routes:', sum(c is not None for c in pmap), 'of', len(pmap))
D['drive'] = dict(source=M['source'], units=M['units'], pp=M['pps_to_pps'],
                  pv=[[row[c] if c is not None else None for c in pmap] for row in M['pps_to_private']])
D.pop('routes', None)
html = html[:m.start(1)] + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + html[m.end(1):]

def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# ---------- helpers ----------
rep("function nearestPrivate(s, t, k = 3) {",
"""// driving distance [miles, minutes] from the OSRM matrix (PPS -> PPS, PPS -> private)
const SI = Object.fromEntries(D.schools.map((s, i) => [s.key, i]));
P.forEach((x, i) => { x.pi = i; });
const drv = (a, b) => a === b ? [0, 0] : D.drive.pp[SI[a]][SI[b]];
const drvP = (a, pi) => D.drive.pv[SI[a]][pi];
function nearestPrivate(s, t, k = 3) {""")

rep("""function nearestPPS(x) {
  return D.schools.map(s => ({ s, d: miles([s.lat, s.lng], [x.lat, x.lng]) })).sort((a, b) => a.d - b.d)[0];
}""",
"""function nearestPPS(x) {
  const road = D.schools.every(s => drvP(s.key, x.pi));
  return D.schools.map(s => { const v = drvP(s.key, x.pi); return v ? { s, d: v[0], min: v[1], road: true } : { s, d: miles([s.lat, s.lng], [x.lat, x.lng]), road: false }; })
    .sort((a, b) => a.d - b.d)[0];
}""")

# relocation distance by road
rep("    const far = use.map(r => ({ to: byKey[r.to_key], d: miles([s.lat, s.lng], [byKey[r.to_key].lat, byKey[r.to_key].lng]) })).sort((a, b) => b.d - a.d)[0];\n"
    "    return { kind: 'closes', d: far.d, to: far.to,",
    "    const far = use.map(r => { const v = drv(s.key, r.to_key); return { to: byKey[r.to_key], d: v[0], min: v[1] }; }).sort((a, b) => b.d - a.d)[0];\n"
    "    return { kind: 'closes', d: far.d, min: far.min, driving: true, to: far.to,")
rep("    return { kind: 'grades', d: miles([s.lat, s.lng], [to.lat, to.lng]), to, band: 'MS', label: 'grades 6-8' };",
    "    const v = drv(s.key, to.key);\n    return { kind: 'grades', d: v[0], min: v[1], driving: true, to, band: 'MS', label: 'grades 6-8' };")

# alternatives: one road-distance path for every scenario
rep("""  const R = D.routes && D.routes[sc] && D.routes[sc][s.key];
  if (R) {
    const label = R.band === 'MS' ? 'grades 6-8' : R.band === 'HS' ? 'grades 9-12' : R.band === 'K8' ? 'grades K-8' : 'grades K-5';
    const mk = z => z && ({ x: P[z.i], d: z.miles, min: z.minutes });
    return { r: { kind: R.kind, d: R.reloc.miles, min: R.reloc.minutes, to: byKey[R.reloc.to], band: R.band, label, driving: true },
             within: R.within.map(mk), nearest: mk(R.nearest) };
  }
  const r = relocation(s, sc); if (!r) return null;
  const list = P.filter(x => !x.preKOnly && serves(x, r.band)).map(x => ({ x, d: miles([s.lat, s.lng], [x.lat, x.lng]) }))
    .sort((a, b) => a.d - b.d);""",
"""  const r = relocation(s, sc); if (!r) return null;
  const list = P.filter(x => !x.preKOnly && serves(x, r.band) && drvP(s.key, x.pi))
    .map(x => { const v = drvP(s.key, x.pi); return { x, d: v[0], min: v[1] }; }).sort((a, b) => a.d - b.d);""")

# private popup: nearest PPS school by road
rep("    `<div class=\"row\">Nearest PPS school: ${esc(short(n.s.name))}, ${n.d.toFixed(1)} mi straight-line${fate}</div>` +",
    "    `<div class=\"row\">Nearest PPS school: ${esc(short(n.s.name))}, ${n.road ? `${n.d.toFixed(1)} mi / ${Math.round(n.min)} min by road` : `${n.d.toFixed(1)} mi straight-line`}${fate}</div>` +")

# custom candidates by road
rep("""// open schools in the same region that take this grade band, nearest first (straight-line)
function candidates(state, k, band) {
  const s = byKey[k];
  return D.schools.filter(o => o.key !== k && D.region_of[o.key] === D.region_of[k] && !state.closed.has(o.key) && ACCEPTS[band].includes(state.typ[o.key]))
    .map(o => ({ k: o.key, d: miles([s.lat, s.lng], [o.lat, o.lng]) })).sort((a, b) => a.d - b.d);
}""",
"""// open schools in the same region that take this grade band, nearest first by driving distance
function candidates(state, k, band) {
  return D.schools.filter(o => o.key !== k && D.region_of[o.key] === D.region_of[k] && !state.closed.has(o.key) && ACCEPTS[band].includes(state.typ[o.key]))
    .map(o => { const v = drv(k, o.key); return { k: o.key, d: v[0], min: v[1] }; }).sort((a, b) => a.d - b.d);
}""")
rep("p.c.map(c => `${short(byKey[c.k].name)} (${c.d.toFixed(1)} mi)`)",
    "p.c.map(c => `${short(byKey[c.k].name)} (${c.d.toFixed(1)} mi, ${Math.round(c.min)} min)`)")
rep("Same region, same grades, straight-line distance. Applies from ${D.impl_year}.",
    "Same region, same grades, nearest by driving distance. Adjust the split with the sliders in the custom panel. Applies from ${D.impl_year}.")

# ---------- proportional shares ----------
rep("""    if (!to.length) continue;
    part.to = to;
    const sh = 1 / to.length;""",
"""    if (!to.length) continue;
    if (to.join() !== part.to.join() || !part.sh || part.sh.length !== to.length) part.sh = to.map(() => 1 / to.length);
    part.to = to;
    const tot = part.sh.reduce((a, b) => a + b, 0) || 1;
    const shares = part.sh.map(v => v / tot);""")
rep("      for (const r of to) if (st.ser[r][i] != null) st.ser[r][i] += amt * sh;",
    "      to.forEach((r, j) => { if (st.ser[r][i] != null) st.ser[r][i] += amt * shares[j]; });")
rep("""    for (const r of to) {
      for (const g of GRP) {
        const src = st.g[x][g]; if (src == null) continue;
        st.g[r][g] = (st.g[r][g] || 0) + src * f31 * sh;
      }
      st.receivers.push({ from: byKey[x].name, to: byKey[r].name, from_key: x, to_key: r, share: to.length > 1 ? sh : null,""",
"""    to.forEach((r, j) => {
      const sh = shares[j];
      if (sh <= 0) return;
      for (const g of GRP) {
        const src = st.g[x][g]; if (src == null) continue;
        st.g[r][g] = (st.g[r][g] || 0) + src * f31 * sh;
      }
      st.receivers.push({ from: byKey[x].name, to: byKey[r].name, from_key: x, to_key: r, share: to.length > 1 ? sh : null,""")
rep("""      (st.notes[r] ||= []).push(`Custom: receives ${BAND_LABEL[part.band]} students from ${short(byKey[x].name)}`);
    }
  }""",
"""      (st.notes[r] ||= []).push(`Custom: receives ${BAND_LABEL[part.band]} students from ${short(byKey[x].name)}${to.length > 1 ? ` (${Math.round(100 * sh)}%)` : ''}`);
    });
  }""")

# link: shares as whole percents
rep("a: custom.actions.map(a => [SIDX[a.k], a.parts.map(p => [p.band, p.to.map(r => SIDX[r])])]) };",
    "a: custom.actions.map(a => [SIDX[a.k], a.parts.map(p => p.to.length > 1 && p.sh ? [p.band, p.to.map(r => SIDX[r]), p.sh.map(v => Math.round(v * 100))] : [p.band, p.to.map(r => SIDX[r])])]) };")
rep("parts: parts.map(([band, to]) => ({ band, to: to.map(j => D.schools[j].key) })) })) };",
    "parts: parts.map(([band, to, sh]) => ({ band, to: to.map(j => D.schools[j].key), ...(sh && sh.length === to.length ? { sh: sh.map(v => v / 100) } : {}) })) })) };")

# panel: sliders under each split closure
rep("""    h += nA ? `<ol class="cplist">${custom.actions.map((a, i) => `<li><b>${esc(short(byKey[a.k].name))}</b> closes &rarr; ${a.parts.map(p => (a.parts.length > 1 ? BAND_LABEL[p.band] + ': ' : '') + p.to.map(r => esc(short(byKey[r].name))).join(' + ')).join('; ')} <button class="cp-del" data-i="${i}" title="Remove this change">&times;</button></li>`).join('')}</ol>`""",
"""    const sliders = (a, i) => a.parts.map((p, j) => p.to.length < 2 ? '' :
      `<div class="cpsplit">${a.parts.length > 1 ? `<span class="cpband">${BAND_LABEL[p.band]}</span>` : ''}${p.to.map((r, k) => {
        const pct = Math.round(100 * (p.sh ? p.sh[k] / p.sh.reduce((x, y) => x + y, 0) : 1 / p.to.length));
        const v = drv(a.k, r);
        return `<label class="cpslider"><span class="cpname">${esc(short(byKey[r].name))} <span class="muted">${v[0].toFixed(1)} mi / ${Math.round(v[1])} min</span></span>` +
          `<input type="range" min="0" max="100" step="1" value="${pct}" data-a="${i}" data-p="${j}" data-r="${k}" aria-label="Share of ${esc(short(byKey[a.k].name))} students to ${esc(short(byKey[r].name))}"><b class="cppct">${pct}%</b></label>`;
      }).join('')}</div>`).join('');
    h += nA ? `<ol class="cplist">${custom.actions.map((a, i) => `<li><b>${esc(short(byKey[a.k].name))}</b> closes &rarr; ${a.parts.map(p => (a.parts.length > 1 ? BAND_LABEL[p.band] + ': ' : '') + p.to.map(r => esc(short(byKey[r].name))).join(' + ')).join('; ')} <button class="cp-del" data-i="${i}" title="Remove this change">&times;</button>${sliders(a, i)}</li>`).join('')}</ol>`""")
rep("  el.querySelectorAll('.cp-del').forEach(b => b.onclick = () => { custom.actions.splice(+b.dataset.i, 1); redo(); });",
"""  el.querySelectorAll('.cp-del').forEach(b => b.onclick = () => { custom.actions.splice(+b.dataset.i, 1); redo(); });
  // moving one slider rescales the others in the same split proportionally so the total stays 100%
  el.querySelectorAll('.cpsplit').forEach(group => {
    const inputs = [...group.querySelectorAll('input[type=range]')];
    const show = () => inputs.forEach(x => { x.parentElement.querySelector('.cppct').textContent = x.value + '%'; });
    inputs.forEach(inp => {
      inp.oninput = () => {
        const v = +inp.value, others = inputs.filter(x => x !== inp);
        const rest = others.reduce((a, x) => a + +x.value, 0);
        let left = 100 - v;
        others.forEach((x, idx) => {
          const nv = idx === others.length - 1 ? left : Math.round(rest > 0 ? (100 - v) * +x.value / rest : (100 - v) / others.length);
          x.value = Math.max(0, Math.min(100, nv)); left -= +x.value;
        });
        show();
      };
      inp.onchange = () => {
        const a = custom.actions[+inp.dataset.a], p = a.parts[+inp.dataset.p];
        p.sh = inputs.map(x => +x.value / 100);
        if (p.sh.every(v => v === 0)) p.sh = p.to.map(() => 1 / p.to.length);
        redo();
      };
    });
  });""")

# styles
rep("#custompanel button[disabled] { opacity: .5; cursor: default; }",
"""#custompanel button[disabled] { opacity: .5; cursor: default; }
.cpsplit { display: grid; grid-template-columns: 1fr; gap: 4px; margin: 6px 0 4px; padding: 8px 10px; background: var(--surface-2); border-radius: 8px; max-width: 640px; }
.cpband { font-size: 11.5px; font-weight: 700; color: var(--text-secondary); letter-spacing: .04em; }
.cpslider { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(120px, 2fr) 44px; gap: 10px; align-items: center; font-size: 12.5px; }
.cpslider input[type=range] { width: 100%; accent-color: var(--change); }
.cppct { text-align: right; font-variant-numeric: tabular-nums; }
@media (max-width: 600px) { .cpslider { grid-template-columns: 1fr 44px; } .cpslider .cpname { grid-column: 1 / -1; } }""")

# notes
rep("(straight-line distance; a K-8 sends K-5 and 6-8 students separately), split evenly when you choose 2 or 3, from ",
    "(driving distance; a K-8 sends K-5 and 6-8 students separately), split evenly when you choose 2 or 3 and adjustable with sliders, from ")
rep("precomputed and cached; the nearest-PPS-school distance in private school popups is straight-line.",
    "precomputed for every PPS-to-PPS and PPS-to-private pair (source/osrm/osrm-matrix.json); only preschool/kindergarten-only sites, which are never alternatives, fall back to straight-line in their popups.")
open(PAGE, 'w', encoding='utf-8').write(html)
print('page patched;', round(len(html.encode('utf-8')) / 1024), 'KB')
