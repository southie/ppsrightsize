"""Room to grow, "What would fill the buildings" scale: labels that do not collide. A left margin holds the row names
(Kindergarten / Capture / Births a year) clear of the first tick; marker labels are placed on up to four rows above the
axis, each on the lowest row where its text does not overlap another label and no other marker's leader line passes
through it (and its own line does not cross a label below it); labels are kept inside the chart. Code changed once.
"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = [os.path.join(ROOT, 'rightsizing-scenario-explorer.html'), os.path.join(ROOT, 'scripts', 'patch_room_to_grow.py')]

NEW = r"""  const lo = 2000, hi = Math.max(5000, ...marks.map(m => m[0])) * 1.04, W = 760, AX = 104, LM = 92, RM = 24, X = v => LM + (W - LM - RM) * (v - lo) / (hi - lo);   // room-scale-labels
  let g = `<line x1="${X(lo)}" x2="${X(hi)}" y1="${AX}" y2="${AX}" stroke="var(--text-secondary)" stroke-width="1.5"/>`;
  for (let v = 2000; v <= hi; v += 500) g += `<line x1="${X(v)}" x2="${X(v)}" y1="${AX - 4}" y2="${AX + 4}" stroke="var(--text-secondary)"/><text x="${X(v)}" y="${AX + 16}" text-anchor="middle" font-size="10" fill="var(--text-muted)">${v.toLocaleString()}</text>` +
    (age5 ? `<text x="${X(v)}" y="${AX + 31}" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">${Math.round(100 * v / age5)}%</text>` : '') + `<text x="${X(v)}" y="${AX + 46}" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">${n0(v / capNow)}</text>`;
  g += `<text x="${LM - 22}" y="${AX + 16}" text-anchor="end" font-size="10" fill="var(--text-secondary)">Kindergarten</text>${age5 ? `<text x="${LM - 22}" y="${AX + 31}" text-anchor="end" font-size="9.5" fill="var(--text-secondary)">Capture</text>` : ''}<text x="${LM - 22}" y="${AX + 46}" text-anchor="end" font-size="9.5" fill="var(--text-secondary)">Births a year</text>`;
  // labels: rows above the axis (0 = closest). Each label sits centered on, right of or left of its marker; a placement is
  // valid when no two labels on a row overlap, no marker's line (axis up to its own label) passes through another label,
  // and labels stay inside the chart.
  const ROWS = [0, 1, 2, 3, 4, 5].map(r => AX - 14 - r * 16), items = marks.map(([v, l, c]) => ({ v, l, c, cx: X(v), txt: `${l} ${n0(v)}`, w: `${l} ${n0(v)}`.length * 6 + 4 }));
  const boxAt = (it, a) => a === 'm' ? [it.cx - it.w / 2, it.cx + it.w / 2] : a === 's' ? [it.cx + 5, it.cx + 5 + it.w] : [it.cx - 5 - it.w, it.cx - 5];
  const fits = (it, r, b, placed) => b[0] >= 2 && b[1] <= W - 2 && placed.every(p =>
    !(p.r === r && !(b[1] < p.b[0] - 6 || b[0] > p.b[1] + 6)) &&            // overlap on the same row
    !(p.r < r && it.cx > p.b[0] - 3 && it.cx < p.b[1] + 3) &&               // this line would cross a lower label
    !(p.r > r && p.cx > b[0] - 3 && p.cx < b[1] + 3));                      // a higher label's line would cross this one
  // backtracking over every label's row and anchor (left to right), keeping the layout with the fewest rows
  items.sort((a, b) => a.cx - b.cx);
  let best = null;
  const dfs = (i, placed, top) => {
    if (best && top >= best.top) return;
    if (i === items.length) { best = { top, placed: placed.slice() }; return; }
    const it = items[i];
    for (let r = 0; r < ROWS.length; r++) for (const a of ['m', 's', 'e']) { const b = boxAt(it, a); if (fits(it, r, b, placed)) { placed.push({ ...it, r, b, a }); dfs(i + 1, placed, Math.max(top, r)); placed.pop(); } }
  };
  dfs(0, [], 0);
  const lay = best ? best.placed : items.map((it, i) => ({ ...it, r: i, b: boxAt(it, 'm') }));
  for (const p of lay) {
    const ty = ROWS[p.r];
    g += `<line x1="${p.cx}" x2="${p.cx}" y1="${ty + 3}" y2="${AX}" stroke="${p.c}" stroke-width="1.6"/><circle cx="${p.cx}" cy="${AX}" r="4.5" fill="${p.c}"/>` +
      `<text x="${(p.b[0] + p.b[1]) / 2}" y="${ty}" text-anchor="middle" font-size="10.5" font-weight="600" fill="${p.c}">${esc(p.txt)}</text>`;
  }
  document.getElementById('roomscale').innerHTML = `<svg viewBox="0 0 ${W} ${AX + 54}" style="width:100%;max-width:${W}px;height:auto" role="img" aria-label="Kindergarten class sizes">${g}</svg>` +"""

for f in FILES:
    s = open(f, encoding='utf-8').read()
    if 'room-scale-labels' in s: print(os.path.basename(f), 'already'); continue
    m = re.search(r"  const lo = 2000, hi = Math\.max\(5000, \.\.\.marks\.map\(m => m\[0\]\)\) \* 1\.04, W = 760, X = v => 30 \+ \(W - 60\) \* \(v - lo\) / \(hi - lo\);\n.*?  document\.getElementById\('roomscale'\)\.innerHTML = `<svg viewBox=\"0 0 \$\{W\} 124\" style=\"width:100%;max-width:\$\{W\}px;height:auto\" role=\"img\" aria-label=\"Kindergarten class sizes\">\$\{g\}</svg>` \+", s, re.S)
    assert m, f
    s = s[:m.start()] + NEW + s[m.end():]
    open(f, 'w', encoding='utf-8', newline='\n').write(s); print(os.path.basename(f), 'patched')
