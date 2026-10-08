"""Marker shape = grade range (K-5 circle, 6-8 square, 9-12 hexagon, combined diamond) for PPS and private schools.
Color keeps its meaning: scenario role for PPS schools, violet for private schools."""
import os, sys, shutil
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
shutil.copy(PAGE, os.path.join(ROOT, 'source', 'rightsizing-scenario-explorer.backup-before-shapes.html'))
html = open(PAGE, encoding='utf-8').read()
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# ---------- shape helpers ----------
rep("const ll = s => L.latLng(s.lat, s.lng);",
r"""const ll = s => L.latLng(s.lat, s.lng);
// marker shape encodes grade range; color encodes role (PPS) or private
const SHAPE = { ES: 'circle', MS: 'square', HS: 'hex', K8: 'diamond' };
const SHAPE_LABEL = { ES: 'K-5 elementary', MS: '6-8 middle', HS: '9-12 high', K8: 'Combined range (K-8, K-12, 6-12)' };
function shapeEl(shape, attrs) {
  const a = Object.entries(attrs).map(([k, v]) => `${k}="${v}"`).join(' ') + ' vector-effect="non-scaling-stroke"';
  if (shape === 'circle') return `<circle cx="10" cy="10" r="8" ${a}/>`;
  if (shape === 'square') return `<rect x="2.9" y="2.9" width="14.2" height="14.2" rx="1.2" ${a}/>`;
  if (shape === 'hex') { const p = [0, 1, 2, 3, 4, 5].map(i => { const t = Math.PI / 180 * (60 * i - 90); return `${(10 + 8.8 * Math.cos(t)).toFixed(2)},${(10 + 8.8 * Math.sin(t)).toFixed(2)}`; }).join(' '); return `<polygon points="${p}" ${a}/>`; }
  return `<polygon points="10,0.6 19.4,10 10,19.4 0.6,10" ${a}/>`;   // diamond
}
let hatchN = 0;
function shapeIcon(shape, sz, o) {
  const id = o.hatch ? `hx${++hatchN}` : '';
  const defs = o.hatch ? `<defs><pattern id="${id}" patternUnits="userSpaceOnUse" width="3.2" height="3.2" patternTransform="rotate(45)"><rect width="3.2" height="3.2" fill="${o.fill}"/><line x1="0" y1="0" x2="0" y2="3.2" stroke="#ffffff" stroke-width="1.4"/></pattern></defs>` : '';
  const halo = o.halo ? shapeEl(shape, { fill: 'none', stroke: '#0d1117', 'stroke-width': 4.5, 'stroke-linejoin': 'round' }) : '';
  const body = shapeEl(shape, { fill: o.hatch ? `url(#${id})` : o.fill, 'fill-opacity': o.opacity ?? .95, stroke: o.stroke, 'stroke-width': o.sw, 'stroke-linejoin': 'round' });
  return L.divIcon({ className: 'shape-icon', iconSize: [sz, sz], iconAnchor: [sz / 2, sz / 2],
    html: `<svg width="${sz}" height="${sz}" viewBox="0 0 20 20" style="overflow:visible;display:block">${defs}${halo}${body}</svg>` });
}
function gradeCat(g) {
  const v = [...g].filter(k => k >= 0); if (!v.length) return 'ES';
  const lo = Math.min(...v), hi = Math.max(...v);
  if (hi <= 5) return 'ES'; if (lo >= 6 && hi <= 8) return 'MS'; if (lo >= 9) return 'HS'; return 'K8';
}
function shapeSwatch(shape, fill = 'var(--text-secondary)') {
  return `<svg width="13" height="13" viewBox="0 0 20 20" style="vertical-align:-2px;margin-right:5px;overflow:visible">${shapeEl(shape, { fill, stroke: 'var(--surface-1)', 'stroke-width': 1 })}</svg>`;
}""")

# ---------- PPS markers ----------
rep("""    if (rl === 'closes' || rl === 'receives') L.circleMarker(ll(s), { radius: r + 2, stroke: false, fillColor: '#0d1117', fillOpacity: .9, interactive: false }).addTo(layer);
    L.circleMarker(ll(s), {
      radius: r, color: rl === 'closes' || rl === 'receives' ? '#ffffff' : css('--change'), weight: rl === 'closes' || rl === 'receives' ? 1.8 : 1,
      fillColor: rl === 'closes' ? css('--close') : rl === 'other' ? 'url(#hatch)' : css('--change'), fillOpacity: .95,
    }).on('contextmenu',""",
"""    const ring = rl === 'closes' || rl === 'receives';
    const icon = shapeIcon(SHAPE[s.type[scen]] || 'circle', Math.round(2 * r + 2), {
      fill: rl === 'closes' ? css('--close') : css('--change'), hatch: rl === 'other',
      stroke: ring ? '#ffffff' : css('--change'), sw: ring ? 1.8 : 1, halo: ring });
    L.marker(ll(s), { icon, keyboard: false, zIndexOffset: { closes: 300, receives: 200, other: 100, none: 100 }[rl] }).on('contextmenu',""")

# ---------- private markers ----------
rep("""    L.marker([x.lat, x.lng], { keyboard: false, zIndexOffset: -500, icon: L.divIcon({ className: 'priv-icon', iconSize: [sz, sz], iconAnchor: [sz / 2, sz / 2],
      html: `<svg width="${sz}" height="${sz}" viewBox="0 0 20 20"><path d="M10 1 L19 10 L10 19 L1 10 Z" fill="${col}" fill-opacity="${x.pps_hs_area ? .92 : .7}" stroke="#ffffff" stroke-width="1.6"/></svg>` }) })""",
"""    L.marker([x.lat, x.lng], { keyboard: false, zIndexOffset: -500,
      icon: shapeIcon(SHAPE[gradeCat(x.g)], sz, { fill: col, opacity: x.pps_hs_area ? .92 : .7, stroke: '#ffffff', sw: 1.4 }) })""")

# ---------- legends and text ----------
rep("<span class=\"dia\"></span>Private schools (${P.length}:",
    "<span class=\"sw\" style=\"background:var(--priv)\"></span>Private schools, violet (${P.length}:")
shape_key = ("<span class=\"shapekey\"><b>Shape = grades:</b> ${['ES', 'MS', 'HS', 'K8'].map(k => `<span>${shapeSwatch(SHAPE[k])}${SHAPE_LABEL[k]}</span>`).join('')}</span>")
rep("""    ? `<span><span class="sw" style="background:var(--change)"></span>Open school</span><span>Circle size: 2025-26 enrollment</span>` + privLegend()""",
    "    ? `" + shape_key + """<span><span class="sw" style="background:var(--change)"></span>Open PPS school</span><span>Size: 2025-26 enrollment</span>` + privLegend()""")
rep("""    : `<span><span class="sw" style="background:var(--close);box-shadow:0 0 0 2px #fff,0 0 0 3.5px #0d1117"></span>Closes</span>""",
    "    : `" + shape_key + """<span><span class="sw" style="background:var(--close);box-shadow:0 0 0 2px #fff,0 0 0 3.5px #0d1117"></span>Closes</span>""")
rep("Show other program and grade moves <span class=\"ln moves\"></span></label><span>Circle size: 2025-26 enrollment</span>` + privLegend();",
    "Show other program and grade moves <span class=\"ln moves\"></span></label><span>Size: 2025-26 enrollment</span>` + privLegend();")
rep("Circle size is 2025-26 enrollment. Violet diamonds are private schools, sized by enrollment; zoom out to see those outside the district.",
    "Shape shows grades (circle K-5, square 6-8, hexagon 9-12, diamond combined range); size is 2025-26 enrollment. Violet markers are private schools; zoom out to see those outside the district.")
rep("Lines are drawn straight for clarity. Violet diamonds are private schools; zoom out to see those outside the district.`;",
    "Lines are drawn straight for clarity. Shape shows grades (circle K-5, square 6-8, hexagon 9-12, diamond combined range); violet markers are private schools.`;")
rep(".priv-icon { background: none; border: 0; }",
    ".priv-icon, .shape-icon { background: none; border: 0; }\n"
    ".legend .shapekey { display: inline-flex; flex-wrap: wrap; gap: 4px 12px; align-items: center; width: 100%; }\n"
    ".legend .shapekey > span { display: inline-flex; align-items: center; }")
open(PAGE, 'w', encoding='utf-8').write(html)
print('patched')
