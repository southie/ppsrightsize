"""Room to grow: births a year as a fertility rate (total fertility rate, children per woman). PSU's August 2026 county
projections put Multnomah County's rate at about 1.0 in 2024; about 3,650 children were born to PPS-area residents in
2025 (ZIP-based estimate). With about the same number of women of childbearing age (PSU's medium projection holds
that group roughly level), births scale with the rate: rate ~= births / 3,650 x 1.0. Added to the scale (a fourth
row), the "what it would take" card, the first-to-fill list and the region table's "Full at" column, with a note
(U.S. about 1.6, replacement 2.1). Code changed once.
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

if 'roomTFR' not in html:
    rep("""  const capNow = 2919 / 4121;   // fall 2025 kindergarten / 2020 births to PPS-area residents""",
        """  const capNow = 2919 / 4121;   // fall 2025 kindergarten / 2020 births to PPS-area residents
  // fertility rate behind a number of births: about 1.0 children per woman in 2024 (PSU, county) for about 3,650 births to
  // PPS-area residents in 2025; with about as many women of childbearing age, births scale with the rate
  const roomTFR = b => (b / 3650 * 1.0).toFixed(2), tfrOf = K => roomTFR(K / capNow);""")
    # card
    rep("""<span class="vt">What it would take to fill them</span></div><div class="l">At today's kindergarten capture (2025: about 3,650 births; 2008 peak 5,802)""",
        """<span class="vt">What it would take to fill them</span></div><div class="l">A fertility rate of about <b>${tfrOf(Kmax)}</b> children per woman (now about 1.0; U.S. about 1.6; replacement 2.1) at today's kindergarten capture (2025: about 3,650 births; 2008 peak 5,802)""")
    # scale: a fourth row
    rep("""<text x="${X(v)}" y="${AX + 46}" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">${n0(v / capNow)}</text>`;""",
        """<text x="${X(v)}" y="${AX + 46}" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">${n0(v / capNow)}</text><text x="${X(v)}" y="${AX + 61}" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">${tfrOf(v)}</text>`;""")
    rep("""<text x="${LM - 22}" y="${AX + 46}" text-anchor="end" font-size="9.5" fill="var(--text-secondary)">Births a year</text>`;""",
        """<text x="${LM - 22}" y="${AX + 46}" text-anchor="end" font-size="9.5" fill="var(--text-secondary)">Births a year</text><text x="${LM - 22}" y="${AX + 61}" text-anchor="end" font-size="9.5" fill="var(--text-secondary)">Fertility rate</text>`;""")
    rep("""<svg viewBox="0 0 ${W} ${AX + 54}" style="width:100%;max-width:${W}px;height:auto" role="img" aria-label="Kindergarten class sizes">""",
        """<svg viewBox="0 0 ${W} ${AX + 68}" style="width:100%;max-width:${W}px;height:auto" role="img" aria-label="Kindergarten class sizes">""")
    rep("""and the births a year it would take at today's capture.""",
        """the births a year it would take at today's capture, and the fertility rate (children per woman) behind those births: about 1.0 in 2024 (PSU, Multnomah County) for about 3,650 births to PPS-area residents in 2025, scaled with the number of births at about today's number of women of childbearing age; for comparison the U.S. rate is about 1.6 and the replacement rate 2.1.""")
    # first-to-fill list and table
    rep("""${age5 ? `, capture ${Math.round(100 * f.K / age5)}%` : ''}, births about ${n0(f.K / capNow)}`;""",
        """${age5 ? `, capture ${Math.round(100 * f.K / age5)}%` : ''}, births about ${n0(f.K / capNow)} (fertility rate about ${tfrOf(f.K)})`;""")
    rep("""Full at<br><span style="font-weight:400">kindergarten / capture / births</span></th>""",
        """Full at<br><span style="font-weight:400">kindergarten / capture / births / fertility</span></th>""")
    rep("""&middot; ${n0(f.K / capNow)} births</td>`)(FILL[k])}""", """&middot; ${n0(f.K / capNow)} births &middot; ${tfrOf(f.K)}</td>`)(FILL[k])}""")
    rep("""/ ${n0(FILL[f1].K / capNow)}` : '&ndash;'}""", """/ ${n0(FILL[f1].K / capNow)} / ${tfrOf(FILL[f1].K)}` : '&ndash;'}""")
    rep("""Births at today's capture: fall 2025 kindergarten (2,919) over 2020 births to PPS-area residents (4,121).`;""",
        """Births at today's capture: fall 2025 kindergarten (2,919) over 2020 births to PPS-area residents (4,121). Fertility rate: births scaled from about 1.0 children per woman in 2024 (PSU's county projections) and about 3,650 births to PPS-area residents in 2025, assuming about today's number of women of childbearing age (PSU's medium projection holds it roughly level); in-migration of families with young children would fill seats without higher fertility.`;""")
open(PAGE, 'w', encoding='utf-8', newline='\n').write(html)
print('patched')
