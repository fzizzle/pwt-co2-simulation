# Accessibility and Responsive Behaviour Audit

**Scope:** All ten pages of `dashboard/` (`Overview.py`, `theme.py`, `layout.py`, `loaders.py`, `*_charts.py`, `views/1_*.py`–`10_*.py`) and `.streamlit/config.toml`.
**Method:** Headless Chromium (158.0) against `http://localhost:8501` at **1920×1080**, **1366×768**, and **390×844** px; exact WCAG 2.1 contrast math; Machado (2009) and Viénot (1999) deuteranopia/protanopia simulation with CIELAB ΔE2000; cold-start loader timing via `.venv/bin/python`.
**Constraint respected:** Every recommendation preserves reported workbook figures unchanged (`AGENTS.md`).

---

## Severity Summary

| Severity | Count | Core issues |
|---|---|---|
| **Critical** | 4 | Cropped Spa map and overlapping controls across all widths (unusable slider at 390 px); keyboard-inaccessible animation/slider controls; sidebar covering 77% of phone viewports; unreadable mobile charts (Study B 2×2 panels, Overview gap label, Sizing annotations). |
| **High** | 5 | WCAG AA text and non-text contrast failures (active segmented controls, multiselect tags, caption links, tornado bars, dark map/heatmap stops); deuteranopia/protanopia collisions (BEV vs PHEV when filtered/compared, Compare same-powertrain identical lines, Study C embedded PNGs); colour-only track map encoding; 9–18.5 s cold-start blocks with missing/hidden loading feedback. |
| **Medium** | 5 | Sub-12 px chart fonts and crowded/rotated ticks across 6+ pages; Plotly modebar overlapping legends, corner labels, and mobile titles; 1366 px widget/metric truncation (`Track map`, `Hybrid sizing`, `CO₂ sensitivity`, `Model`); `8_Track_Map.py` omitting `style_axes`; animation reduced-motion / keyboard-stop gaps. |
| **Low** | 3 | Skipped `<h2>` heading levels and duplicate `<h1>` in report tabs; orphaned sidebar `Run`/`Runs` headings on `Trace Explorer` and `Compare`; high-glare white static PNGs and terse alt text inside report expanders. |

---

## Critical Findings

### C1. Spa-Francorchamps track map is cropped at every width, and its controls overlap both the map and each other
- **Where:** `dashboard/track_charts.py:20, 83-84, 95-97, 150-174` (rendered on **6 pages**: `1_Overview.py:70`, `2_Category_View.py:218`, `3_Trace_Explorer.py:86`, `4_Compare.py:175`, `6_Model.py:132`, `8_Track_Map.py:54`).
- **Map cropping (1920, 1366, 390 px):** `lap_map()` fixes `MAP_HEIGHT = 560` (`track_charts.py:20`), `row_heights=[0.76, 0.24]` (`track_charts.py:84`), `zoom=13.2` (`track_charts.py:152`), and `center=(all_lat.mean(), all_lon.mean())` (`track_charts.py:150`). In MapLibre GL (512 px tile scale), the Spa outline spans **389.5 px tall** (`-241.6 px` north to `+147.9 px` south of `mean()`, because `mean()` skews south of the bounding-box midpoint `50.43695°`), while the map pane is only **331 px tall** (`±165.5 px`). **La Source** is cut off at the top (~76 px overflow) and **Bruxelles** is cut off at the bottom at **1920, 1366, and 390 px**. At **390 px**, the colorbar (`x=0.99`, 46 px wide, `track_charts.py:96`) also covers **Kemmel straight** and **Les Combes**.
- **Control overlap (1920, 1366, 390 px):** `updatemenus` (`y=0.25, yanchor="bottom"`, `track_charts.py:159`) renders at `y=350..383` and `sliders` (`x=0.2, y=0.25, yanchor="bottom"`, `track_charts.py:170`) renders at `y=357..386`. Both overlap the bottom of the map canvas (`y=38..369`) and the Carto/OSM attribution pill at all three widths.
- **Mobile slider buried (390 px):** At 390 px (`358 px` plot width), the Play/Pause group spans `x=48..189` (`141 px`) while the slider starts at `x=107` (`x=0.2` of plot width + 44 px left margin). They **overlap by 82 px**, hiding the slider grip underneath `❚❚ Pause` and making scrubbing unusable on a phone.
- **Fix:** Compute map `center` from `(min+max)/2` of lat/lon and reduce `zoom` (or use `bounds`) to fit the full circuit inside the pane height with padding; raise `MAP_HEIGHT` or separate the speed strip into its own chart; move Play/Pause and the scrubber out of Plotly SVG overlays into native Streamlit controls (see C2).

### C2. Custom map playback and slider controls are completely inaccessible to keyboard and screen-reader users
- **Where:** `dashboard/track_charts.py:158-174` (all 6 pages with `lap_section`), plus Plotly legend toggles across all charts.
- **Measured DOM state:** Headless Chromium inspection of `.js-plotly-plot` on `Track map` shows `.updatemenu-button` (`▶ Play`, `❚❚ Pause`) are SVG `<g>` elements with `tabindex=null`, `role=null`, `aria-label=null`. The slider grip (`.slider-grip-rect`) is an SVG `<rect>` with `tabindex=null`, `role=null`, `aria-label=null`. Only the MapLibre canvas, two attribution links, and the eight `.modebar-btn` buttons receive keyboard focus.
- **Impact:** Violates WCAG 2.1 SC 2.1.1 (Keyboard) and SC 4.1.2 (Name, Role, Value). Keyboard users cannot start, pause, or scrub the lap animation, and cannot toggle series visibility in Plotly legends.
- **Fix:** Replace Plotly `updatemenus`/`sliders` with native Streamlit controls (`st.slider` for lap position or corner step, plus a keyboard-focusable play/stop toggle or step buttons), or add a non-animated corner-position selector beside the map.

### C3. Sidebar opens expanded on mobile and blocks 77% of the 390 px viewport on every page
- **Where:** `dashboard/layout.py:155` (`initial_sidebar_state="expanded"`, called by all 10 pages via `configure()`).
- **Measured state at 390×844 px:** Every page loads with the 300 px sidebar drawer open over the 390 px screen, covering titles, filters, and charts until manually dismissed.
- **Fix:** Change `initial_sidebar_state="expanded"` to `initial_sidebar_state="auto"` in `dashboard/layout.py:155` (expanded on desktop, collapsed on mobile).

### C4. Multiple charts become unreadable or lose data at 390 px phone width
- **Study B 2×2 elasticity panels (`dashboard/sensitivity_charts.py:82-83, 122`; `dashboard/views/9_CO2_Sensitivity.py:143, 145`):** `make_subplots(rows=2, cols=2, horizontal_spacing=0.20)` squeezes two columns into 358 px. Column 2's y-axis labels (`Car mass` … `Peak engine efficiency`) print directly on top of Column 1's bars; subplot titles `"Francorchamps eco, generated"` and `"Francorchamps sport, generated"` smash together and clip right (`+64 px`); x-ticks rotate 90° vertical; the top row of the legend (`y=1.13`) clips off the top of the SVG.
- **Overview and Category view gap label (`dashboard/charts.py:29, 96-101`; `1_Overview.py:125`, `2_Category_View.py:126`):** `GAP_LABEL = "electricity not counted"` uses `textposition="outside"` inside grouped bars. At 390 px (~18 px bar width), Plotly auto-shrinks the 23-character label to an illegible ~1.5–2 px smear above the NEDC PHEV slot.
- **Hybrid sizing charts (`dashboard/sizing_charts.py:66-70, 90, 102-104`; `7_Sizing.py:83, 103, 114`):** At 390 px:
  - `efficiency_lines`: `"They cross near 91 %"` overlaps the `g CO₂/km` y-axis title, and `"Sheets' rule 128"` clips past the right edge (`+3 px`).
  - `petrol_gap`: `"-26 %"` and `"-18 %"` clip behind the y-axis (`"26 %"`, `"8 %"` — losing the minus sign and leading digit), and `"Level with petrol"` clips right (`+44 px`, reading `"Level wi"`).
  - `size_heatmap`: `7_Sizing.py:114` passes `show_scale=False` to the WLTC heatmap. When `st.columns(2)` stacks vertically on 390 px, the WLTC heatmap has no colour scale visible on screen.
- **Study B tornado (`dashboard/sensitivity_charts.py:193-208`; `9_CO2_Sensitivity.py:114`):** At 390 px, the x-axis title clips right (`+8 px`, reading `"(g/kn"`), and narrow-span markers (`Gear ratios`, `Rolling resistance`) collide with each other and the zero line.
- **Corner annotations (`dashboard/track_charts.py:193-201`; 6 pages):** Ten staggered `10 px` corner names collapse into 3–6 overlapping text pairs at 390 px across `Category view`, `Trace Explorer`, `Compare`, `Model`, and `Track map`.

---

## High Findings

### H1. WCAG 2.1 AA colour contrast failures on dark theme text, links, and chart marks
Measured contrast ratios against main surface `#1a1a19`, secondary surface `#242422`, and `#000000` track casing (WCAG AA requires **≥4.5:1** for normal text <18 pt, **≥3.0:1** for large text and graphical/UI components):

| Element | Location | Foreground | Background | Ratio | WCAG AA |
|---|---|---|---|---|---|
| Multiselect tags (`Petrol ×`, etc.) | `.streamlit/config.toml:5` (`primaryColor`) | `#ffffff` (14 px) | `#3987e5` | **3.64:1** | **Fail** (text <4.5) |
| Active `st.segmented_control` text | `.streamlit/config.toml:5`, `7_Sizing.py:80`, `8_Track_Map.py:41`, `track_charts.py:215,220` | `#3987e5` (14 px) | `rgba(57,135,229,0.1)` over `#1a1a19` | **4.26:1** | **Fail** (text <4.5) |
| Caption hyperlink (`bacinger/f1-circuits`) | `track_charts.py:237` (inside `stCaptionContainer` `opacity: 0.6`) | `#3d9df3` @ `0.6` (14 px) | `#1a1a19` | **3.00:1** | **Fail** (text <4.5) |
| Study B tornado bars (`opacity=0.6`) | `sensitivity_charts.py:187` | Petrol `#2d5b93`, BEV `#8d4021`, Hybrid `#19694d`, PHEV `#835a0a` | `#1a1a19` | **2.40–2.85:1** | **Fail** (graphic <3.0) |
| Track map `SEQUENTIAL` low stop | `track_charts.py:21` | `#104281` | `#000000` / `#1a1a19` | **2.12:1** / **1.76:1** | **Fail** (graphic <3.0) |
| Track map landmark text & car dot over bright track | `track_charts.py:21, 109, 115` | `#ffffff` (12 px / 17 px dot) | `#86b6ef` / `#e6f0fc` | **2.11:1** / **1.15:1** | **Fail** (text & graphic) |
| Track map `DIVERGING` midpoint | `track_charts.py:23` | `#383835` | `#000000` / `#1a1a19` | **1.79:1** / **1.48:1** | **Fail** (graphic <3.0) |
| Sizing heatmap dark stops (`0.6`, `1.0`) | `sizing_charts.py:16-17` | `#1c5cab`, `#0d366b` | `#1a1a19` (unbuildable bg) | **2.63:1**, **1.46:1** | **Fail** (graphic <3.0) |
| Dumbbell connector stems (`pal.axis`) | `theme.py:70`, `sizing_charts.py:85` | `#52514e` | `#1a1a19` | **2.19:1** | **Fail** (graphic <3.0) |
| Muted text/ticks on secondary bg (e.g. `8_Track_Map.py` bottom chart) | `theme.py:68`, `8_Track_Map.py:57` | `#8a8880` (10–12 px) | `#242422` | **4.38:1** | **Fail** (text <4.5) |
| Passing tokens (for reference) | `theme.py:66-71` | `#ffffff` (17.42:1), `#c3c2b7` (9.72:1), `#8a8880` on `#1a1a19` (4.90:1), `series` on `#1a1a19` (4.48–5.67:1), captions `#fff@0.6` (6.90:1), warnings (9.21:1) | `#1a1a19` | **4.48–17.42:1** | Pass (≥3.0 marks / ≥4.5 text) |

- **Note on `primaryColor`:** Choosing `#3987e5` in `.streamlit/config.toml:5` fails in both directions—white text on it is `3.64:1`, and `#3987e5` text on its own 10%-tinted active button is `4.26:1`. Using a lighter link/active accent on dark or custom CSS for active pills/buttons resolves both.
- **Note on `tornado` bars:** Removing `opacity=0.6` (or raising to `≥0.8` with a lighter stroke) brings all four powertrains above `3.3:1` against `#1a1a19`.

### H2. Colour-blind (deuteranopia and protanopia) collisions and broken non-adjacent assumptions
- **Categorical powertrain palette (`dashboard/theme.py:71`):** `DARK.series = ("#3987e5", "#d95926", "#199e70", "#c98500")`.
  - Pairwise CIELAB ΔE2000 (Machado 2009 / Viénot 1999):
    - Adjacent pairs pass: Petrol–BEV (`57.1 / 65.0` deut, `53.3 / 57.6` prot); BEV–Hybrid (`17.6 / 18.1` deut, `16.3 / 16.5` prot); Hybrid–PHEV (`20.8 / 20.7` deut, `14.6 / 14.8` prot).
    - **Non-adjacent collision — BEV (`#d95926`) vs PHEV (`#c98500`):** **ΔE2000 = 5.4 (Machado) / 5.0 (Viénot) under deuteranopia** (virtually indistinguishable), `11.5 / 13.0` under protanopia.
  - `theme.py:8-11` documents that the palette only passes when series stay in fixed adjacent order. **Four interactive flows break that guarantee:**
    1. **`1_Overview.py:74` & `2_Category_View.py:143`:** Unchecking `Full hybrid` places `BEV` and `PHEV` directly side-by-side with no pattern/dash difference.
    2. **`4_Compare.py:45-46, 145-148` & `charts.py:277-291`:** `compare_traces()` calls `overlay_traces()` with `dashes=None`. Comparing **BEV vs PHEV** draws two solid lines at ΔE = 5.0–5.4 under deuteranopia. Worse, comparing **two runs of the same powertrain** (e.g., Petrol eco vs Petrol sport) draws **two identical-colour solid lines**, making the series indistinguishable even with normal colour vision.
    3. **`3_Trace_Explorer.py:122-127` (`charts.py:114-137`):** `trace_lines()` plots arbitrary user-selected columns using `pal.series[index % 4]` with solid lines and identical circle markers. Selecting 4 columns collides slot 1 (`#d95926`) and slot 3 (`#c98500`); selecting 5+ columns recycles exact colours.
    4. **`10_Cornering_Speed.py:48` (`docs/study-c-co2.png`, `docs/study-c-lap-time.png`):** Embedded Matplotlib figures use default `tab10` (`#1f77b4`, `#ff7f0e`, `#2ca02c`, `#d62728`) with identical solid lines and circle markers. **Protanopia** collapses BEV vs Full hybrid to **ΔE2000 = 1.4**; **deuteranopia** collapses Full hybrid vs PHEV to **ΔE2000 = 4.8**.
- **Sequential palettes (`track_charts.py:21`, `sizing_charts.py:16-17`):** Both are single-hue blue monotonic luminance ramps (`L* = 28→94` and `89→23`), so ordering survives deuteranopia and protanopia (step ΔE 13.1–21.5).
- **Diverging palette (`track_charts.py:23`):** `#2a78d6` → `#383835` → `#e0483d` stays separable end-to-end (`ΔE 46.6–62.6`), but under **protanopia** red darkens (`#73693b`, contrast vs `#1a1a19` drops from `4.28:1` to `3.16:1`, and ΔE from grey midpoint drops from `38.0` to `21.7–22.8`).

### H3. Places where colour alone carries meaning (track map, heatmaps, multi-series lines)
- **Track map painted metric (`dashboard/track_charts.py:90-105`):** Colour along the 8 px markers is the **sole non-hover encoding** for Speed, Power demand (positive vs regenerative/coasting), CO₂ emitted, Altitude, and Battery charge. When switching away from Speed, the strip chart underneath (`track_charts.py:121-125`) still plots **Speed only**, not the selected painted metric, leaving touch and keyboard users with no non-colour readout of the painted quantity.
- **Unbuildable cells in sizing heatmaps (`dashboard/sizing_charts.py:118-120, 148-149`):** Unbuildable `(battery, motor)` pairs are encoded only as missing colour (`#1a1a19` background) with one floating text note in the bottom-right corner and `hoverongaps=False`. Because the darkest valid cells (`#0d366b`) have only `1.46:1` contrast against `#1a1a19`, the buildable boundary is ambiguous.
- **Force breakdown (`dashboard/charts.py:211-237`, `3_Trace_Explorer.py:107`):** Three overlaid signed curves use `mode="lines"` with solid strokes and no dashes or markers; colour alone distinguishes them.
- **Feasibility flags (mostly good, one legend bug):** Study B (`sensitivity_charts.py:26, 100, 108, 188, 200`) and Study C (`cornering_charts.py:50`) commendably pair hollow markers (`-open`), bar hatching (`/`), `†` text suffixes, table columns, and `st.warning` banners—not colour alone. However, when the first plotted row is provisional, Plotly renders the **legend swatch itself** hatched or hollow (`9_CO2_Sensitivity.py`, `tornado` and `elasticity_panels`), conflicting with the caption explaining hollow/hatched marks as provisional.

### H4. Slow cold-start pages (9–18.5 s) with blank screens or hidden spinners
Measured cold execution (without `data/processed/*.parquet`, matching a fresh clone and Streamlit Cloud):
- **`6_Model.py` (~18.5 s cold):**
  - `comparison()` (`6_Model.py:59, 93`) takes **13.02 s** (shows spinner `"Running the model…"`).
  - `laps()` (`6_Model.py:65, 168`) takes **5.33 s**, called **unconditionally inside a collapsed `st.expander("How the generated laps are built")`**. Because Streamlit always executes expander bodies, every cold visitor waits an extra 5.3 s while the `"Generating the laps…"` spinner is hidden inside the collapsed expander.
- **`7_Sizing.py` (9.26 s cold):**
  - `sizes()` (`7_Sizing.py:35, 45`, **7.33 s**) and `storage()` (`7_Sizing.py:40, 46`, **1.93 s**) both run **before `st.title("Hybrid sizing")` (`7_Sizing.py:53`)**. For 9.3 seconds, visitors see a blank page with only a spinner and no page heading or explanation of what is computing.
- **`9_CO2_Sensitivity.py` (`81, 143-145`):** Runs `swings(results, grid)` uncached on every rerun and builds both 850 px 2×2 `elasticity_panels` figures eagerly inside the inactive `Compare elasticities` tab on every widget interaction.
- **Workbook pages (`1_Overview`–`5_Data`):** Fast (~0.5 s cold total with `show_spinner="Reading workbooks…"` in `loaders.py:35, 43`).
- **Fix:** Move `st.title()` and intro copy above `sizes()`/`storage()` in `7_Sizing.py`; lazy-load `laps()` in `6_Model.py` behind a `st.toggle` (matching `7_Sizing.py:142` and `8_Track_Map.py:61`) or precompute saved tables; show a fallback notice if map tiles fail to load.

---

## Medium Findings

### M1. Sub-12 px chart fonts, tick-label crowding, and rotated labels
- **`10 px` SVG text:** `track_charts.py:172` (slider font), `track_charts.py:179` (speed-strip corner names, hardcoded `tickangle=-30`), `track_charts.py:199` (`mark_corners` annotations).
- **`11 px` SVG text:** `charts.py:101, 107` (bar value labels—also duplicates `textfont=dict(..., size=11)` and `textfont_size=11`), `track_charts.py:97` (map colorbar ticks), `sizing_charts.py:130, 149` (heatmap colorbar ticks and unbuildable note).
- **Tick crowding & forced rotation at 390 px:**
  - `lap_map` speed strip: **10 overlapping corner tick pairs** at `-30°` (`track_charts.py:179`) on all 6 lap pages.
  - `grouped_totals` (`1_Overview.py`, `2_Category_View.py`): Plotly auto-rotates `"Francorchamps — eco"`, `"Francorchamps — sport"`, `"NEDC"` to `+30°` with **2 overlapping pairs** at 390 px.
  - `elasticity_panels` (`9_CO2_Sensitivity.py`): x-ticks rotate **90° vertical** at 390 px.
- **Fix:** Raise minimum chart font size to **12 px** (`11 px` minimum for dense secondary labels only); abbreviate or thin corner ticks on narrow widths; avoid horizontal multi-column subplots on narrow screens.

### M2. Plotly modebar overlaps legends, corner annotations, and live titles
- **Where:** Every page except `1_Overview.py:64` (elevation strip) leaves Plotly's floating top-right modebar enabled (`displayModeBar` unset).
- **Measured collisions:**
  - Covers **`Blanchimont`** and **`Bus Stop`** corner annotations on `Trace Explorer`, `Model`, `Track map`, `Compare`, and `Category view` at 1366, 1920, and 390 px (`track_charts.py:197-201`).
  - Covers **`Parameter +10%`** tornado legend (`9_CO2_Sensitivity.py`, 1366 px), **`1 · 77.82 g CO₂/km`** ranking label (`9_CO2_Sensitivity.py`, 1366 px), **`Free storage`** legend (`7_Sizing.py`, 390 px), **`Battery electric`** legend (`1_Overview.py`, 390 px), and the live telemetry title `km/h` (`3_Trace_Explorer.py`, 390 px).
- **Fix:** Increase top margin when top legends/annotations are present, or pass `config={"displayModeBar": "hover"}` / strip unneeded modebar tools on static charts so the toolbar never rests permanently over chart labels.

### M3. Clipping and horizontal overflow of controls, metrics, and tables at 1366 px and 390 px
- **`8_Track_Map.py:40-44` (1366 px & 390 px):** `st.columns([1, 2])` gives `Lap` ~290 px at 1366 px, clipping `"Francorchamps — eco"` mid-word (`"Francorchamps —"`). At 390 px, segmented-control buttons extend to `417 px` (`> 390 px`).
- **`7_Sizing.py:61-70` (1366 px):** `st.columns(4)` (212 px each) truncates metric label `"Best full hybrid, Francorchamps ..."`.
- **`9_CO2_Sensitivity.py:93-96` (1366 px):** `st.columns(3)` truncates metric value `"Peak engine effic..."`.
- **`9_CO2_Sensitivity.py:88` (390 px):** Four tabs extend to `534 px` (`> 390 px`), pushing `"Full report & downloads"` off-screen in a horizontally scrolled tab strip.
- **`6_Model.py:94` (1366 px):** The 5-scenario dataframe overflows horizontally inside its container (`1071 px`), hiding `"5 · With storage losses"` off the right edge.

### M4. `8_Track_Map.py` omits `style_axes()`, causing contrast drop and missing x-axis label
- **Where:** `dashboard/views/8_Track_Map.py:57-59` (`speed_and_altitude(steps, "distance_m", pal)` rendered with `theme=None` and no `style_axes()` call).
- **Measured effect:** Unlike `3_Trace_Explorer.py:78` and `6_Model.py:140`, this chart renders with a `#242422` solid plot box instead of transparent `#1a1a19` (dropping `#8a8880` altitude/tick contrast from `4.90:1` to **`4.38:1`**, failing AA) and omits the `Distance (m)` x-axis title/unit completely.

### M5. Animation controls lack `prefers-reduced-motion` handling and keyboard stop
- **Where:** `dashboard/track_charts.py:146-174`.
- **Good:** Animation does **not** auto-play on page load, and a `❚❚ Pause` button exists.
- **Gap:** Once started, playback runs at ~9 fps (`duration=110, redraw=True`) with no keyboard stop mechanism (see C2), no `prefers-reduced-motion` check or discrete-step mode, and no reset-to-start button.

---

## Low Findings

### L1. Heading hierarchy skips `<h2>` on all pages and duplicates `<h1>` on report pages
- **Where:** All 10 views use `st.title()` (`<h1>`) followed immediately by `st.subheader()` (`<h3>`) or `st.markdown("### ...")` (`7_Sizing.py:54`, `8_Track_Map.py:36`), skipping `<h2>` everywhere. Sidebar `st.sidebar.subheader()` (`layout.py:245`, `1_Overview.py:75`, `3_Trace_Explorer.py:47,57`, `4_Compare.py:44`) emits `<h3>` before the page's `<h1>`.
- `9_CO2_Sensitivity.py:195` and `10_Cornering_Speed.py:108` render markdown files containing `# Study B…` / `# Study C…`, producing a second `<h1>` inside the page.

### L2. Orphaned sidebar headings on `Trace Explorer` and `Compare`
- **Where:** `dashboard/views/3_Trace_Explorer.py:47-48`, `dashboard/views/4_Compare.py:44-46`, and `dashboard/layout.py:261-271`.
- Both pages call `st.sidebar.subheader("Run")` / `st.sidebar.subheader("Runs")` and then call `run_picker(...)`, which renders `st.selectbox(...)` in the **main column** instead of `st.sidebar`. Screen-reader users navigating by headings encounter an empty `"Run"`/`"Runs"` section in the sidebar.

### L3. Static report PNGs flash white backgrounds on dark theme and carry terse alt text
- **Where:** `dashboard/views/9_CO2_Sensitivity.py:57` (`docs/study-b-*.png`), `dashboard/views/10_Cornering_Speed.py:48` (`docs/study-c-*.png`).
- Pure-white raster charts sit directly on `#1a1a19` (high glare for low-vision/photophobic dark-mode users), shrink unreadably at 390 px (`width="stretch"`), and use minimal captions/alt text (e.g. `"Combustion comparison"`, `docs/study-b-sensitivity.md:49`).

---

## Recommendation

Fix these three items first—they resolve the worst mobile breakage, keyboard blockers, and WCAG AA failures without altering any workbook figure:

1. **Rebuild `lap_map()` framing and move playback controls to native Streamlit widgets (`dashboard/track_charts.py:20, 83-174, 204-230`; `dashboard/layout.py:155`) — Medium (~3–4 hours).**
   - Centre the map on `(min+max)/2` lat/lon and adjust zoom/bounds so the full Spa circuit (including La Source and Bruxelles) fits at 1920, 1366, and 390 px.
   - Replace Plotly's SVG `updatemenus` and `sliders` with keyboard-accessible Streamlit controls (e.g., `st.slider` / corner-step selector below the map) so controls never overlap the map or each other and satisfy WCAG 2.1.1/4.1.2.
   - Update the speed strip below to plot the *selected painted metric* (not only speed), eliminating colour-only encoding on the map, and switch `initial_sidebar_state="auto"` in `layout.py:155` so mobile pages aren't covered by the sidebar.

2. **Fix WCAG AA contrast failures and CVD collisions across theme and charts (`.streamlit/config.toml:5`, `dashboard/charts.py:114-137, 211-237, 277-291`, `dashboard/sensitivity_charts.py:187`, `dashboard/track_charts.py:21, 23`, `dashboard/sizing_charts.py:16-17, 85`, `dashboard/views/8_Track_Map.py:57-59`) — Small–Medium (~2–3 hours).**
   - Fix `primaryColor` text/chip contrast (≥4.5:1 on active segmented controls and multiselect tags) and avoid dimmed links inside `st.caption`.
   - Raise tornado bar opacity above 0.8 (≥3:1 contrast), brighten the dark stops of `SEQUENTIAL`/`DIVERGING`/`_RAMP`, add dark halos behind white map labels, and call `style_axes(fig, pal, x_title="Distance (m)")` in `8_Track_Map.py:57`.
   - Pass `DASH_CYCLE` (and distinct marker shapes) in `compare_traces()`, `trace_lines()`, and `force_breakdown()` so same-powertrain comparisons and BEV-vs-PHEV pairs remain distinguishable under deuteranopia/protanopia; regenerate Study C's embedded PNGs with `theme.py`'s palette + line/marker redundancy.

3. **Fix mobile chart readability and cold-start loading feedback (`dashboard/sensitivity_charts.py:73-123`, `dashboard/sizing_charts.py:66-108`, `dashboard/charts.py:96-101`, `dashboard/views/6_Model.py:161-170`, `dashboard/views/7_Sizing.py:45-56`, `dashboard/views/8_Track_Map.py:40-44`) — Medium (~3 hours).**
   - Make `elasticity_panels()` single-column or facet-selectable so it does not smash labels at 390 px; shorten/relocate `GAP_LABEL` on narrow bars (`†` + legend/caption) so `"electricity not counted"` never shrinks to 2 px; fix `sizing_charts.py` margins/ranges so `"-26 %"` and `"Level with petrol"` never clip, and show a colorbar on both heatmaps.
   - Move `st.title()` and intro prose above `sizes()`/`storage()` in `7_Sizing.py`, and gate `laps()` in `6_Model.py:168` behind `st.toggle` (instead of running 5.3 s of hidden compute inside a collapsed expander).
   - Widen the `Lap` column ratio in `8_Track_Map.py:40` (or stack above `Powertrain`) so `"Francorchamps — eco"` is not clipped at 1366 px.
