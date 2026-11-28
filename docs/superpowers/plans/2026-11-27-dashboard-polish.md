# Dashboard polish implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** done on branch `dashboard-polish`, awaiting review. Owner decided on 27 Nov 2026: D1 dark for every viewer, D2 remove the computed columns, D3 stays out. Deviations from the steps below are recorded as rulings in the pull request.

**Goal:** Finish the dark "Keynote Darkroom" dashboard merged in PR #16: put each page's main figure first, stop chart chrome from covering text, fix the labels that get cut off, and fix the workbook-rule breaks that remain. No figure the dashboard shows should change.

**Architecture:** Theme colours stay in `.streamlit/config.toml`, page CSS stays in `layout.inject_css()`, and Plotly styling stays in `theme.py`. One new helper, `layout.show_chart()`, owns every chart's toolbar setting. Page changes reorder what each page already draws. The only new drawing is the tile-free circuit in Task 6, which reuses `pwt.deck.track` (that module has no Streamlit import).

**Tech stack:** Streamlit 1.66.1, Plotly 7.1.0, pytest with `streamlit.testing.v1.AppTest`.

**Spec:** the two second-pass critiques of 27 Nov 2026 (T3 threads "Dashboard re-critique (GPT Sol)" and "Dashboard re-critique (Gemini Neon)"), merged in the chat that produced this plan. Every decision taken from them is written here.

## Decisions for the owner

- **D1: dark for everyone, or follow the viewer's system setting.** `config.toml` defines both `[theme.dark]` and `[theme.light]`. With both defined, Streamlit follows the browser, so a light-mode laptop opens the white version (both critics saw this). The plan assumes dark for everyone: delete `[theme.light]` and keep `theme.LIGHT` for a viewer who switches in the settings menu. If the owner wants the system setting followed, skip Task 1 Step 3.
- **D2: Compare's "Difference" and "Change from left (%)" columns** (`dashboard/views/4_Compare.py:66-84`). Both critics, and `AGENTS.md`, treat them as recomputation on a workbook page. The plan removes them in Task 3 Step 3. If the owner keeps them, skip that step.
- **D3: Hybrid sizing reruns the sweep on page load** (`dashboard/views/7_Sizing.py:48-59`). This is Study A's owner's call and stays out of this plan. Task 5 changes only that page's labels.

## Global constraints

- Branch `dashboard-polish`, in worktree `/home/phred/.t3/worktrees/pwt-co2-simulation/dashboard-polish`, cut from `origin/main` at `5f05792`. Open a pull request into `main` and don't commit to `main` directly.
- Change only `dashboard/`, `.streamlit/`, `tests/`, `dashboard/README.md` and this plan. Don't touch `pwt/` or `data/course-files/`. With `pwt/` unchanged, the Cloud app needs no reboot.
- Workbook pages (Overview, Category view, Trace explorer, Compare, Data) show figures exactly as reported, in the workbook's own units. Axis ticks count as display.
- Study pages keep their owner-review, draft, provisional and feasibility labels where the reader can see them. Report text files aren't edited.
- `tests/test_extract_golden.py` and `tests/test_model_golden.py` stay green.
- The four powertrain colours are reserved for powertrains: petrol `#d09539`, full hybrid `#4fb267`, plug-in hybrid `#b677d5`, battery electric `#3984d0`. No control, accent or neutral trace uses them.
- UI accent: neutral silver `#d1d1d6`. Filled chips and active controls take `#000000` text on it. Inline code: `#c7c7cc` on `#1c1c1e`.
- Font stays Inter. Numbers in metrics and tables use tabular numerals.
- Copy follows `AGENTS.md` "Writing". Cycle names come from `pwt.sweep.CYCLES` and powertrain names from `pwt.catalog.POWERTRAIN_NAMES`. Use "Powertrain", never "Car", as a control label.
- Run everything through `/home/phred/Projects/pwt-co2-simulation/.venv/bin/`.

## Review focus

1. **Phone width (390 px).** Each reordered page must show its main figure, or the control that drives it, on the first screen. Checked in Task 7's screenshot pass against a list of pages.
2. **A viewer who switches to light in the settings menu.** Charts must pick `LIGHT`, and the neutral accent must still clear 4.5:1 on white. Task 1 tests the contrast.
3. **The plug-in hybrid NEDC gap** must keep its "electricity not counted" mark beside the chart and in the cell after the Overview reorder. Task 4 adds a test.
4. **Tests that find widgets by position** (`app.radio[0]`, `app.dataframe[0]`). Any task that moves a widget gives it a `key`, and the tests select it by that key.
5. **A missing value on Compare or Data.** It must show "—", never `None` or `nan`. Task 3 adds a test.

---

### Task 1: Lock the theme and neutralise the accent

**Files:** `.streamlit/config.toml`, `dashboard/layout.py` (`inject_css`), `dashboard/theme.py`. Test: `tests/test_theme_and_home.py`.

**Interfaces:** produces `theme.ACCENT = "#d1d1d6"` and `theme.ACCENT_INK = "#000000"`.

- [x] **Step 1: Write the failing tests.**
  - `test_accent_is_not_a_powertrain_colour`: neither `primaryColor` nor `ACCENT` is in `CAR_COLOURS.values()`.
  - `test_config_has_no_light_twin`: `tomllib` finds no `theme.light` table (D1).
  - `test_accent_contrast`: `ACCENT` against `#000000` is at least 4.5:1, and against `LIGHT.surface` it is at least 3:1 for non-text UI. If silver fails on white, the light twin uses `LIGHT.text_primary` as its accent; that case is tested in Task 1 Step 4.
  - `test_css_targets_real_segmented_control`: `inject_css`'s output contains no `segmented_controlActive`, and does contain `.stApp code`.
- [x] **Step 2: Run** `pytest tests/test_theme_and_home.py -q`. Expected: the new tests fail.
- [x] **Step 3: In `config.toml`,** delete `[theme.light]` and `[theme.light.sidebar]`. Set `primaryColor = "#d1d1d6"` in `[theme]` and `[theme.dark]`, and change the header comment to match.
- [x] **Step 4: In `inject_css`,** remove the two dead segmented-control selectors. Style filled multiselect tags (`span[data-baseweb="tag"]`, including its child `span` and `svg`) with `ACCENT` and `ACCENT_INK`. Give `.stApp code` the inline-code colours. Find the active segmented-control button's real selector by inspecting the DOM in the Task 7 setup (start the app once now), and give it `ACCENT` with `ACCENT_INK` text. Record the selector in a comment.
- [x] **Step 5: Run the full suite.** Expected: everything passes. Commit: `Dashboard: dark for every viewer, neutral accent, readable code and active controls`.

### Task 2: Chart chrome and trace colour

**Files:** `dashboard/layout.py` (new `show_chart`, `elevation_strip`), `dashboard/track_charts.py` (`mark_corners`, `metric_strip`), `dashboard/charts.py` (`speed_and_altitude`, `gear_steps`), every `st.plotly_chart` call site in `dashboard/`. Tests: `tests/test_accessibility_charts.py`, `tests/test_charts.py`.

**Interfaces:**
- Produces `layout.show_chart(fig, *, toolbar: bool = False, key: str | None = None) -> None`. It calls `st.plotly_chart(fig, width="stretch", theme=None, key=key, config={"displayModeBar": "hover" if toolbar else False, "displaylogo": False})`.
- Changes `speed_and_altitude`, `gear_steps` and `metric_strip` to take `colour: str`.

- [x] **Step 1: Write the failing tests.**
  - `test_no_direct_plotly_chart_calls`: a scan of the source finds `st.plotly_chart(` only in `layout.py`.
  - `test_corner_labels_clear_the_legend`: after `mark_corners` runs on a figure with `showlegend=True`, `legend.y` is at least 1.14 and `margin.t` at least 76.
  - `test_single_run_traces_use_the_given_colour`: `speed_and_altitude(lap, ..., colour=X)` gives traces whose `line.color` is X, and no trace uses `CAR_COLOURS["bev"]` unless X is that colour.
  - `test_elevation_strip_has_scale_and_neutral_stroke`: both axes are visible, the y tick text includes the trace's rounded min and max altitude in m, and the line colour is `pal.text_secondary`.
- [x] **Step 2: Run them.** Expected: they fail.
- [x] **Step 3: Implement `show_chart`** and replace all 28 call sites. Only the Trace explorer's trace charts, Compare's trace chart and Category view's overlay pass `toolbar=True`. Make the `mark_corners` change exactly as the test pins it.
- [x] **Step 4: Pass the colour in.** Single-run traces take the run's powertrain colour. Car-independent profiles, such as the elevation strip and the cycle speed profile on Model, take `pal.text_secondary`. Give `elevation_strip` visible quiet axes: x in the workbook's distance column, ticks in m, and y ticks at the min and max altitude.
- [x] **Step 5: Run the full suite.** Expected: everything passes. Commit: `Dashboard: one chart helper, legends clear of corner labels, traces in the car's colour`.

### Task 3: Workbook fidelity

**Files:** `dashboard/views/4_Compare.py`, `dashboard/track_charts.py` (`metric_strip` and the live readout at `:189`), `dashboard/labels.py` (`COLUMNS`). Tests: `tests/test_app.py`, `tests/test_data_page.py`, `tests/test_track_map_layout.py`.

**Interfaces:** produces `track_charts.metric_strip(..., distance_unit: Literal["m", "km"] = "km")`. Workbook pages pass `"m"`.

- [x] **Step 1: Write the failing tests.**
  - `test_compare_reports_only_reported_values`: the first dataframe on Compare has exactly the columns `Figure`, Run A's name and Run B's name (D2).
  - `test_compare_parameter_gaps_show_a_dash`: no cell in "Parameter differences" equals `None`, `"None"` or `"nan"`. The battery-energy row for a petrol run reads `—` (Review focus 5).
  - `test_workbook_strip_keeps_metres`: `metric_strip(..., distance_unit="m")` has its x range in m and its readout ending " m".
  - `test_data_column_picker_uses_display_names`: on Data, the column multiselect shows "CO₂ per km", not `co2_g_per_km`.
- [x] **Step 2: Run them.** Expected: they fail.
- [x] **Step 3: On Compare,** remove the two computed columns and their formatting, and format both run columns with `mark_gap_value`. Pass the "Parameter differences" values through `labels.figure`, which already turns a missing value into "—". Keep the run notices.
- [x] **Step 4:** add `distance_unit` and pass `"m"` from every workbook-page call (Overview, Category view, Trace explorer, Compare). Add the four canonical run columns to `labels.COLUMNS` with the names in `layout.CANONICAL_QUANTITIES`.
- [x] **Step 5: Run the full suite.** Expected: everything passes. Commit: `Workbook pages: reported values only, metres as reported, dashes for gaps`.

### Task 4: Main figure first on Home, Overview, Model and Compare

**Files:** `dashboard/views/0_Home.py`, `dashboard/views/1_Overview.py`, `dashboard/views/6_Model.py`, `dashboard/views/4_Compare.py`, `dashboard/Overview.py`. Tests: `tests/test_theme_and_home.py`, `tests/test_app.py`, `tests/test_model_page.py`.

- [x] **Step 1: Write the failing tests.**
  - Home: no element text matches `^0\d$`; no more than three page links are rendered in the main column; and the hero HTML has no `border` rule.
  - Home route: in `Overview.py`, the default page has no `url_path`, so `/` serves Home and nothing claims `/home`.
  - Overview: the first `plotly_chart` comes before the first dataframe and before the warning. `app.radio(key="measure")` is in main, not the sidebar. The NEDC plug-in hybrid cell still ends with `GAP_LABEL` (Review focus 3).
  - Model: the scenario chart comes before both scenario tables. The tables sit inside an expander labelled "Scenario tables".
  - Compare: the trace chart comes before "Parameter differences".
- [x] **Step 2: Run them.** Expected: they fail.
- [x] **Step 3: Home.** Remove the card border around the hero and let the Spa art take a full column (`st.columns([5, 4])`) beside the title. Replace the numbered groups and the ten link cards with three `st.page_link` calls: "See the workbook figures" (Overview), "See what the model computes" (Model) and "Read the studies" (Hybrid sizing). Show the WLTC preview as its bar chart only; drop the four repeated metric cards. Copy WLTC as "the WLTC Class 3 cycle", not "the highway cycle". Keep the provenance badges.
- [x] **Step 4: Overview.** The order is: title with the workbook badge, then a control row with Measure (`horizontal=True`, `key="measure"`) and a "Filter runs" popover, then the chart with a one-line gap note under it, the "Electricity accounting" expander, the matrix, and last the elevation strip inside "What the cycles are". The sidebar keeps only "Reset selections".
- [x] **Step 5: Model.** Lead with the scenario chart, defaulting to `storage losses`. Put both tables in the "Scenario tables" expander, with columns `Powertrain` and `Cycle` and rows in `POWERTRAIN_ORDER`. Move the single-drive controls straight after the chart.
- [x] **Step 6: Compare.** Order: run pickers, reported figures, trace chart, parameter differences.
- [x] **Step 7: Run the full suite.** Expected: everything passes. Commit: `Dashboard: each page opens on its main figure; Home becomes one composed stage`.

### Task 5: Cut-off labels, tables and vocabulary

**Files:** `dashboard/views/6_Model.py`, `7_Sizing.py`, `8_Track_Map.py`, `9_CO2_Sensitivity.py`, `10_Cornering_Speed.py`, `3_Trace_Explorer.py`, `dashboard/layout.py` (CSS). Tests: the matching `tests/test_*_page.py` files.

These are layout and label changes only. Tell each study's owner when the pull request opens.

- [x] **Step 1: Write the failing tests.**
  - Every `st.metric` label on these pages is at most 28 characters long. Metric values carry no unit longer than 4 characters; longer units go in the label, for example "Fuel (l/100 km)".
  - Model scenario headers are at most 20 characters long. When a generated lap is selected, the scenario readout says "4 · Assignment vehicles", matching what `steps()` runs.
  - The Study B and C tables round to 1 decimal place, or to 2 for elasticities, and no header is cut to fewer than 4 characters at 1440 px. Set the widths with `column_config`.
  - Each page renders exactly one `h1`. `render_report` demotes every heading by one level before rendering.
  - No control label is "Car". Every mention of the generated lap equals `CYCLES["franco_sport_generated"]`. Trace explorer's X-axis select sits in main, beside Run.
- [x] **Step 2: Run them.** Expected: they fail.
- [x] **Step 3: Implement.** Add CSS so `stMetricLabel` wraps (`white-space: normal`). Shorten labels as pinned above; for example, Sizing's tile becomes "Best full hybrid, sport lap". The Model headers are `1 · Workbook vehicles`, `2 · Harmonised`, `3 · Hybrid control`, `4 · Assignment`, `5 · Storage losses`; check each against `SCENARIO_LABELS` and keep the full wording in the methods expander. Use the same lap name everywhere.
- [x] **Step 4: Run the full suite.** Expected: everything passes. Commit: `Dashboard: no cut-off labels, one lap name, one heading per page`.

### Task 6: Track map without tiles

**Files:** `dashboard/track_charts.py` (`lap_map`, `lap_section`), `dashboard/views/8_Track_Map.py`. Tests: `tests/test_track_map_layout.py`, `tests/test_track_map.py`.

**Interfaces:**
- Consumes `pwt.deck.track.lap()`, `relief()` and `CORNERS`.
- Produces `track_charts.lap_map(..., basemap: Literal["relief", "tiles"] = "relief")`. `lap_section` gains `width_px: int | None`, and callers pass 390 on the compact layout.

- [x] **Step 1: Write the failing tests.**
  - `test_relief_map_has_no_tiles`: the default `lap_map` figure has no `Scattermap` traces and no `layout.map.style`, and its y-axis has `scaleanchor == "x"`.
  - `test_relief_map_draws_contours_below_the_lap`: the contour traces come before the lap trace and use `pal.grid`.
  - `test_compact_labels_are_used`: with `width_px=390`, the rendered corner names are a subset of `COMPACT_LANDMARKS`.
  - `test_track_map_controls_precede_map_on_phone`: on Track map, Play and the scrubber come before the map in element order, and the four lap figures sit in one `st.caption` line, not four `st.metric`s.
- [x] **Step 2: Run them.** Expected: they fail.
- [x] **Step 3: Implement the relief basemap** in Cartesian Plotly, with equal aspect: contours, then the painted lap, then the cursor. Place corner labels outward from the track with `pwt.deck.track.label_spot`. Keep the outline credit in a muted caption under the map. Keep `"tiles"` as an option so nothing that depends on it breaks. Wire `width_px` through.
- [x] **Step 4: Run the full suite.** Expected: everything passes. Commit: `Track map: deck relief instead of street tiles, labels clear of the track, controls first`.

### Task 7: Study chart ergonomics, screenshots, docs and pull request

**Files:** `dashboard/cornering_charts.py`, `dashboard/views/10_Cornering_Speed.py`, `dashboard/sizing_charts.py`, `dashboard/README.md`, this plan.

- [x] **Step 1: Write the failing tests.** Cornering's two responses are one figure with 2 rows sharing x, with a vertical line at x = 1.0 (the baseline). The PHEV legend in Sizing has 2 entries, the same as the panel beside it.
- [x] **Step 2: Implement** both. Keep the hollow provisional markers and the owner-review captions.
- [x] **Step 3: Screenshot pass.** Start the app on port 8661. Wait for each page to finish rendering, then capture all 11 pages at 1440 × 1000, and Home, Overview, Model and Track map at 390 × 844, into the session scratchpad. Check each against the Review focus list. Fix anything that fails with a test first.
- [x] **Step 4:** run the full suite, update `dashboard/README.md` (accent rule, `show_chart`, relief map) and this plan's Status, and commit.
- [x] **Step 5: Push and open a pull request** into `main` with before and after screenshots of Home, Overview and Track map. List D3 as open, and name the study pages Tasks 5 and 7 touched.
