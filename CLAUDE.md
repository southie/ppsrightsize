# Right Size Portland

Independent explorer of Portland Public Schools' rightsizing scenarios. The site is one page,
`rightsizing-scenario-explorer.html`; its data is embedded as `const D = {...};` followed by `const esc`.
Not affiliated with PPS: keep the disclaimer at the top of the page.

## Making changes

- Change the page through idempotent patch scripts in `scripts/` (`patch_*.py`); build data with `build_*.py`.
  - Each patch guards against being applied twice and uses an exact-match `rep(a, b)` that asserts one match.
  - Data a patch embeds in `D` is refreshed on every rerun; code is added once.
  - When a later change edits code a patch added, edit the page and the patch script the same way, so a rerun on an
    older page gives the same result.
- Run `node scripts/test_explorer.js` after every change; all checks must pass.
  - Its stub storage runs the regression checks on the reconstruction: PSU forecast (`rsPfa` 0), PPS model results off
    (`rsPps` 0), modified enrollment model on (`rsAdj` 1).
- The user runs git. Don't run `git add`, `commit` or `push`; give the command to run, prefixed with `!`.
- Don't modify `source/pta/cache/` (intentionally uncommitted).

## Page rules

### Switching scenarios must not move the page

Switching scenarios (or a switch beside the scenario buttons) must change values, not layout. A reader scrolled
anywhere on the page must stay at the same place.

- Never return `''` for a card, row or block in some scenarios and content in others. Render a placeholder of the same
  kind instead (for example a summary card showing "&ndash;" and one line saying why), so the number and order of
  elements is the same in every scenario.
- Summary cards (`#kpis .kpi`) are matched to `KPI_TARGETS` by position. A card that should link somewhere without a
  fixed position carries `data-go="<target>"` and is handled in `goTo`.
- Wrap every new section's render function with `stableLayout(fn, hostId, [extra block ids], itemSelector)` beside the
  existing wrappers (after `renderMap = stableLayout(...)`). It renders every scenario in `STABLE_SCENS()` once and
  keeps each row's and block's tallest height. Every block whose text length varies by scenario (subtitles, notes,
  legends) goes in the extra ids.
- Every function that runs for each scenario in `STABLE_SCENS()` must render without errors for all of them,
  including custom scenarios started from each.
- Check it: render each scenario headlessly and compare the count of cards and rows; screenshot the page with
  headless Chrome before and after a switch when a section is new.

### New sections get links

- Add every new section to `LINK_TABLES` (`['key', 'element id']`), so it gets a "Link" button and deep link.
- If its state matters in a link (open regions, chosen year), add it to `linkParams` and restore it in `applyLink`.
- If a summary card summarizes it, make the card link to it (`data-go` and `goTo`).

### Style

- New charts follow the page's existing charts: the travel-time histograms (`cmPaneHtml`) for histograms. Grey bars
  (`var(--text-secondary)`, darker for the highlighted bands), `var(--line)` grid, small value labels above bars,
  muted axis labels, dashed marker lines, `.cmleg` legend swatches, hover detail in `<title>`.
- Draw an SVG at about its display size so text sizes match the rest of the page.
- Use sentence case with proper capitalization in chart titles, axis titles, legends and markers.
- Colors come from the page's CSS variables, never literals that only work in one theme.

## Data notes

- Scenarios: `SQ`, `A`, `B`, `C` (custom). PPS's other model runs `S60` (Sixty Percent) and `BAL` (Balanced) are in
  the data but not offered (`SCENS`).
- "PPS model results" switch (default on): A and B use PPS's own school-by-year enrollment from its Power BI dashboard
  (`source/pps-powerbi/`, `scripts/fetch_pps_powerbi.py`, `scripts/build_pps_model.py`); off uses this page's
  reconstruction. A = PPS run "Seventy Percent", B = "Fifty Percent".
- "District share of county population (PFA study)" switch: on by default. "Modified enrollment model": off by default
  and has no effect while PPS model results are on.
- PPS's "well-resourced" and "sustainable" are both enrollment at or above the size threshold (K-5 360, K-8 and 6-8
  500, 9-12 1,100).
- PPS's affordable-housing students are redistributed within its fixed district total, not added to it.
