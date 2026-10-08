"""Car button next to each point-to-point drive time in the school and private-school panes: requests the Mapbox
Directions API (mapbox/driving-traffic) drive time on the next Tuesday (slowest weekday in a test), leaving 30 minutes before the start time of
the PPS school in the trip (PPS 2026-27 start times by level), and shows it in line, with Mapbox / OpenStreetMap
attribution. Results are cached for the page visit.
The page embeds a URL-restricted public token; local test servers read mapbox-token.local.json (git-ignored).
Safe to rerun: added once.
"""
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
TOKEN = 'pk.eyJ1IjoibXNvdXRod29ydGgiLCJhIjoiY211end3czdkMDBmbzJ3cHN0NWluZnRrdCJ9.-cxIWvBRaLVGM8UnexvslA'   # URL-restricted public token (rightsizepdx.com, southie.github.io)
html = open(PAGE, encoding='utf-8').read()
if 'function mbLink' in html: sys.exit('already patched')
def rep(a, b):
    global html
    assert html.count(a) == 1, (html.count(a), a[:100])
    html = html.replace(a, b)

# ---- buttons next to each drive time ----
rep("""${dm(a.r.d, a.r.min)} to ${esc(short(a.r.to.name))}${a.r.kind === 'grades' ? ' (grades 6-8)' : ''}, ${a.r.driving ? 'by road' : 'straight-line'}</span></div>`;""",
    """${dm(a.r.d, a.r.min)} to ${esc(short(a.r.to.name))}${a.r.kind === 'grades' ? ' (grades 6-8)' : ''}, ${a.r.driving ? 'by road' : 'straight-line'}</span>${a.r.driving ? mbLink(s, a.r.to) : ''}</div>`;""")
rep("""Nearest: ${esc(a.nearest.x.name)}, ${dm(a.nearest.d, a.nearest.min)}` : ''}</div>`;""",
    """Nearest: ${esc(a.nearest.x.name)}, ${dm(a.nearest.d, a.nearest.min)}${mbLink(s, a.nearest.x)}` : ''}</div>`;""")
rep("""${dm(n.d, n.min)} &middot; ${esc(n.x.grades_served || '')}${n.x.pps_hs_area ? '' : ' &middot; outside PPS'}</span></div>`)""",
    """${dm(n.d, n.min)} &middot; ${esc(n.x.grades_served || '')}${n.x.pps_hs_area ? '' : ' &middot; outside PPS'}</span>${mbLink(s, n.x)}</div>`)""")
rep("""${n.road ? `${n.d.toFixed(1)} mi / ${Math.round(n.min)} min by road` : `${n.d.toFixed(1)} mi straight-line`}${fate}</div>`""",
    """${n.road ? `${n.d.toFixed(1)} mi / ${Math.round(n.min)} min by road` : `${n.d.toFixed(1)} mi straight-line`}${fate}${n.road ? mbLink(n.s, x) : ''}</div>`""")

# ---- request, cache, display ----
rep("function altSection(s) {", r"""// ---------- Mapbox drive time in traffic (weekday 7:30 am) ----------
// The listed drive times are free-flow (OSRM, no traffic). The car button asks the Mapbox Directions API
// (driving-traffic profile, depart_at = the next Tuesday before school starts, Portland time, i.e. typical traffic then) for the same
// trip and shows the result in line with Mapbox / OpenStreetMap attribution.
// Published pages use a Mapbox token restricted to this site's URLs. A restricted token cannot allow localhost, so on a
// local test server the page uses the token in mapbox-token.local.json ({"token": "pk..."}), which is git-ignored.
let MAPBOX_TOKEN = '""" + TOKEN + r"""';
if (['localhost', '127.0.0.1', '[::1]'].includes(location.hostname))
  fetch('mapbox-token.local.json').then(r => r.ok ? r.json() : null).then(j => { if (j?.token) MAPBOX_TOKEN = j.token; }).catch(() => {});
const MB_CACHE = new Map();
const MB_CAR = '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="currentColor" d="M5 11l1.6-4.4A2 2 0 0 1 8.5 5.3h7a2 2 0 0 1 1.9 1.3L19 11a2 2 0 0 1 2 2v4a1 1 0 0 1-1 1h-1a2 2 0 0 1-4 0H9a2 2 0 0 1-4 0H4a1 1 0 0 1-1-1v-4a2 2 0 0 1 2-2zm1.2 0h11.6l-1.3-3.6a.7.7 0 0 0-.6-.4H8.1a.7.7 0 0 0-.6.4zM6.5 13.5a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 0 0 0-2.4zm11 0a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 0 0 0-2.4z"/></svg>';
// PPS 2026-27 start times by school level (PPS communications via PDX Parent, Aug 12, 2026; the last morning bus on
// PPS's posted routes reaches every elementary, K-8 and middle school 10 minutes before these). Trips depart 30
// minutes before the start time of the PPS school in the trip: the destination when it is a PPS school, otherwise the
// origin (private schools' start times are not published). A school's level follows the selected scenario.
const MB_START = { ES: 8 * 60, K8: 8 * 60 + 45, MS: 9 * 60 + 15, HS: 8 * 60 + 30 }, MB_LEAD = 30;
const mbClock = m => `${(Math.floor(m / 60) + 11) % 12 + 1}:${String(m % 60).padStart(2, '0')} ${m < 720 ? 'am' : 'pm'}`;
function mbPlan(a, b) {
  const pps = [b, a].find(x => x?.key && byKey[x.key]); if (!pps) return null;
  const t = D.types[scen]?.[pps.key] || D.types.SQ[pps.key], start = MB_START[t]; if (start == null) return null;
  return { dep: start - MB_LEAD, start, school: short(pps.name), dest: pps === b };
}
// Tuesday: in a test of 23 closure-to-receiver trips on each weekday (Oct 12-16, 2026), Tuesday was the slowest
// for 19 of them (about 0.5% above the weekday average; Friday the fastest; the weekdays differ by about 2%)
const MB_DAY = 2, MB_DAY_NAME = 'Tuesday';
// the next Tuesday whose departure time is still ahead, Portland time, as Mapbox's local depart_at (YYYY-MM-DDThh:mm)
function mbDepart(dep) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: 'America/Los_Angeles', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
    .formatToParts(new Date()).map(x => [x.type, x.value]));
  const d = new Date(Date.UTC(+p.year, +p.month - 1, +p.day));
  if (+p.hour * 60 + +p.minute >= dep - 5) d.setUTCDate(d.getUTCDate() + 1);   // leave a few minutes: must be in the future
  while (d.getUTCDay() !== MB_DAY) d.setUTCDate(d.getUTCDate() + 1);
  return { at: `${d.toISOString().slice(0, 10)}T${String(Math.floor(dep / 60)).padStart(2, '0')}:${String(dep % 60).padStart(2, '0')}`,
    day: d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }) };
}
const MB_ATTR = '<span class="mbattr">&copy; <a href="https://www.mapbox.com/about/maps/" target="_blank" rel="noopener">Mapbox</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a></span>';
const mbCoords = (a, b) => `${a.lng.toFixed(5)},${a.lat.toFixed(5)};${b.lng.toFixed(5)},${b.lat.toFixed(5)}`;
function mbResult(r) {
  if (!r) return '';
  if (r.err) return `<span class="mbres err">Mapbox traffic time unavailable (${esc(r.err)})</span>`;
  return `<span class="mbres">In traffic, leaving ${esc(r.day)} ${mbClock(r.dep)}: <b>${Math.round(r.min)} min</b> (${r.mi.toFixed(1)} mi)` +
    `<span class="mbwhy">${r.dep === undefined ? '' : `${MB_LEAD} min before ${esc(r.school)}'s ${mbClock(r.start)} start${r.dest ? '' : ' (private start times not published)'}`}</span> ${MB_ATTR}</span>`;
}
function mbLink(a, b) {
  if (!a || !b || a.lat == null || b.lat == null) return '';
  const pl = mbPlan(a, b); if (!pl) return '';
  const c = mbCoords(a, b), k = `${c}@${pl.dep}`, r = MB_CACHE.get(k);
  const tt = `Drive time in typical ${MB_DAY_NAME} traffic, leaving ${mbClock(pl.dep)} (${MB_LEAD} min before ${pl.school}'s ${mbClock(pl.start)} start; Mapbox)`;
  return ` <button type="button" class="mbx" data-k="${k}" data-c="${c}" data-dep="${pl.dep}" data-start="${pl.start}" data-school="${esc(pl.school)}" data-dest="${pl.dest ? 1 : ''}" title="${esc(tt)}" aria-label="${esc(tt)}">${MB_CAR}</button>${r && !r.pending ? mbResult(r) : ''}`;
}
async function mbFetch(btn) {
  const k = btn.dataset.k, dep = +btn.dataset.dep, when = mbDepart(dep);
  const meta = { dep, start: +btn.dataset.start, school: btn.dataset.school, dest: !!btn.dataset.dest, day: when.day };
  MB_CACHE.set(k, { pending: true });
  try {
    const u = `https://api.mapbox.com/directions/v5/mapbox/driving-traffic/${btn.dataset.c}?depart_at=${when.at}&overview=false&access_token=${MAPBOX_TOKEN}`;
    const res = await fetch(u), j = await res.json();
    if (!res.ok || j.code !== 'Ok' || !j.routes?.length) throw new Error(j.message || j.code || res.status);
    MB_CACHE.set(k, { ...meta, min: j.routes[0].duration / 60, mi: j.routes[0].distance / 1609.344 });
  } catch (e) { MB_CACHE.set(k, { err: String(e.message || e).slice(0, 60) }); }
  return MB_CACHE.get(k);
}
document.getElementById('dockbody').addEventListener('click', async e => {
  const btn = e.target.closest('.mbx'); if (!btn) return;
  e.preventDefault();
  const k = btn.dataset.k, done = MB_CACHE.get(k);
  const put = (b, h) => { b.nextElementSibling?.classList.contains('mbres') && b.nextElementSibling.remove(); b.insertAdjacentHTML('afterend', h); };
  if (done && !done.pending && !done.err) return put(btn, mbResult(done));
  put(btn, '<span class="mbres">loading&hellip;</span>'); btn.disabled = true;
  const r = await mbFetch(btn);
  btn.disabled = false;
  document.querySelectorAll('#dockbody .mbx').forEach(b => { if (b.dataset.k === k) put(b, mbResult(r)); });
});
function altSection(s) {""")

# ---- styles ----
rep(".dock[hidden] { display: none; }", """.dock[hidden] { display: none; }
.dock .mbx { display: inline-flex; align-items: center; vertical-align: -3px; margin-left: 4px; padding: 1px 3px; border: 1px solid var(--line); border-radius: 5px; background: var(--surface-1); color: var(--text-secondary); cursor: pointer; }
.dock .mbx:hover, .dock .mbx:focus-visible { color: var(--text-primary); border-color: var(--text-secondary); } .dock .mbx:disabled { opacity: .5; cursor: progress; }
.dock .mbres { display: block; margin: 2px 0 2px 2px; font-size: 12px; color: var(--text-primary); } .dock .mbres .mbwhy { display: block; font-size: 11px; color: var(--text-muted); } .dock .pop .mbres b { display: inline; font-size: inherit; margin: 0; } .dock .mbres.err { color: var(--text-muted); }
.dock .mbattr { font-size: 10.5px; color: var(--text-muted); margin-left: 4px; white-space: nowrap; } .dock .mbattr a { color: inherit; }""")

# ---- method note ----
rep("  'Travel time:", "  " + json.dumps(
    "Traffic drive times: the drive times listed in the school panes are free-flow (OSRM, no traffic). The car button next "
    "to each asks the Mapbox Directions API (driving-traffic profile) for the same trip on the next Tuesday (the slowest "
    "weekday in a test of 23 trips, though weekdays differ by only about 2%), leaving 30 "
    "minutes before the start time of the PPS school in the trip (the destination when it is a PPS school, otherwise the "
    "origin; PPS 2026-27 start times: elementary 8:00, K-8 8:45, middle 9:15, high 8:30, as reported by PDX Parent from "
    "PPS, Aug 12, 2026), which reflects typical traffic for that time; results are shown with Mapbox and OpenStreetMap "
    "attribution and kept for the visit. Added by scripts/patch_mapbox_drive.py.") + ",\n  'Travel time:")
rep("  ['Map, boundaries and travel time', ['Map:', 'Attendance boundaries', 'Getting to school', 'Travel time']],",
    "  ['Map, boundaries and travel time', ['Map:', 'Attendance boundaries', 'Getting to school', 'Travel time', 'Traffic drive times']],")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
