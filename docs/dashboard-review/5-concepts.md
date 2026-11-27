# Dashboard Visual Design Concepts

Three distinct visual concept directions for the PWT CO₂ Simulation Streamlit dashboard (`dashboard/`), all staying inside the agreed group-deck visual language (`docs/superpowers/specs/2026-11-23-group-deck-design.md`, `pwt/deck/art.py`, `pwt/deck/track.py`, `pwt/deck/data.py`).

All nine mockups are standalone, interactive HTML files (plus 1280 px PNG renders in `5-concepts/png/`) built directly from live repo data (`pwt.deck.data.baseline()`, `pwt.phase2.result_for()`, `pwt.deck.track`, `pwt.sweep.cycles()`, and `dashboard.loaders.load_runs()`).

- **Gallery switcher:** [`5-concepts/index.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/index.html) ([PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/index.png))

---

## Shared Problems Solved Across All Three Directions

1. **Deck alignment (surfaces, type, and car palette):** Replaces the current warm-grey `#1a1a19` theme and old 4-colour series (`#3987e5` / `#d95926` / `#199e70` / `#c98500`) with the deck's Inter typography, neutral Apple dark (`#000000` / `#1c1c1e` / `#2c2c2e`) or light (`#ffffff` / `#f5f5f7` / `#e5e5ea`) surfaces, and fixed muted car palette: Petrol `#d09539`, Full hybrid `#4fb267`, Plug-in hybrid `#b677d5`, Battery electric `#3984d0`.
2. **Track map never cropped (`1 : 1.62` portrait geometry):** Measuring `pwt.deck.track.lap().xy` shows Spa-Francorchamps north-up has a **width : height ratio of `1.0 : 1.619`**. The current `dashboard/track_charts.py` drops it into a wide, short `Scattermap` (~2.6 : 1) at hardcoded `zoom=13.2`, cropping La Source at the top and Bruxelles at the bottom (as in `user-screenshot-map-cutoff.png`). Every concept switches the circuit to a **portrait-aspect column** paired with telemetry beside it, rendered as an equal-aspect Cartesian Plotly figure (`scaleanchor="x", scaleratio=1`) over the deck's interpolated altitude relief contours (373–470 m, explicitly labelled as an impression, not survey data), with outward non-overlapping corner labels and zero tile/OSM clutter.
3. **AGENTS.md boundaries preserved:** Supplied workbook runs stay verbatim (`34 NEDC PHYBRID engine.xlsx` remains `0 g CO₂/km — electricity not counted`; Petrol Spa eco stays `245.7 g CO₂/km`), model outputs are explicitly tagged (`Model output · storage losses · EU 250 g/kWh`), and all three infeasible baseline runs (`short_steps > 0`: Petrol WLTC `145.1* g CO₂/km` [15 steps, −9.2 kW], Plug-in hybrid NEDC `67.9* g CO₂/km` [1 step, −2.3 kW], Plug-in hybrid WLTC `73.6* g CO₂/km` [34 steps, −13.1 kW]) are visibly marked with hollow/outlined shapes, `*`, and explicit deficit readouts.

---

## Direction A — Keynote Darkroom

Closest to the dark slide deck (`24-first-slide-v5.png` & `31-main-slides-v7.png`): pitch-black `#000000` stage, `#1c1c1e` elevated cards, persistent sidebar navigation matching `dashboard/Overview.py`, and the Slide-1 Spa-Francorchamps hero.

- **Files:**
  - Home: [`5-concepts/concept-a-home.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/concept-a-home.html) · [PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/concept-a-home.png)
  - Track map: [`5-concepts/concept-a-track.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/concept-a-track.html) · [PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/concept-a-track.png)
  - CO₂ comparison: [`5-concepts/concept-a-compare.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/concept-a-compare.html) · [PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/concept-a-compare.png)

### What it improves
- **Home:** Gives the app an unmistakable front door — a Slide-1-faithful north-up Spa circuit fading behind *"Four cars. Four cycles."*, a live WLTC Class 3 baseline strip (with hollow swatches for the two infeasible WLTC runs), and three cleanly separated navigation bands (**01 The workbooks**, **02 The model**, **03 The reports**) tagged by provenance and lap corner. Decouples the landing page from the raw 12-workbook table.
- **Track map:** 42 / 58 side-by-side split puts the complete 7.00 km circuit in a portrait frame on the left and keeps KPIs, Play/Pause + distance scrubber, and the synchronised Speed & Elevation chart visible without scrolling on a 1280 × 900 screen. Supports all five paint channels (Speed, Power, CO₂ here, Altitude, SoC) with graceful fallback when a car has no battery channel.
- **CO₂ comparison:** Matches Slide 7 & Slide 8 directly — axisless grouped bars, 4 px top-rounded corners, direct value labels, hollow outlined bars + `*` for `short_steps > 0`, a feasibility summary strip underneath, EU (250 g/kWh) vs French (50 g/kWh) grid toggle, and an isolated **Supplied workbooks (12 · verbatim)** tab with the PHEV NEDC warning banner.

### Trade-offs
- **Vertical hero height:** The Slide-1 hero pushes Section 03 (*The reports*) below the fold on smaller laptop screens (1366 × 768).
- **Dark-only contrast in bright rooms:** Pure `#000000` looks dramatic on laptops and OLED displays, but can wash out slightly under harsh classroom projectors unless paired with a light theme option.
- **Cross-cycle magnitude spread:** Grouped bars on a single 0–400 g CO₂/km scale still make BEV NEDC (`38.0 g CO₂/km`) look short next to Full hybrid Spa sport (`395.2 g CO₂/km`), though direct value labels and the WLTC-focus tab mitigate this.

### Streamlit buildability
- **100% native Streamlit 1.66 + Plotly 7.1 + CSS — zero custom components needed.**
  - `config.toml`: `[theme]` / `[theme.dark]` sets `#000000`, `#1c1c1e`, `#f5f5f7`, `#2c2c2e`, `font = "Inter"`, `baseRadius = "0.75rem"`.
  - Home hero: pre-rendered SVG/HTML via `st.html(...)` (reusing `pwt.deck.track`) + clickable `st.page_link(...)` cards inside `st.container(border=True)`.
  - Track map: `st.columns([0.43, 0.57])` with one `go.Figure` (`go.Scatter` relief lines + colour-mapped track + `scaleanchor="x", scaleratio=1`, `frames` + `sliders`/`updatemenus` for Play/Pause). Note: in pure Plotly without a custom component, driving *both* the map car dot and the right-column speed/elevation cursor from one Play button requires either putting both in a 2-column `make_subplots` Plotly figure (`column_widths=[0.43, 0.57]`, which is 100% native!) or keeping the speed cursor inside the map figure.
  - Grouped bars: native `go.Bar` with `marker=dict(color="rgba(0,0,0,0)", line=dict(color=car_color, width=2.5), cornerradius=4)` for hollow infeasible bars.

---

## Direction B — Editorial Light Atlas

Mirrors the deck's light theme (`#ffffff` paper, `#f5f5f7` trays, `#e5e5ea` hairlines) and section-opener layouts. Built for daytime reading, classroom projection, and rapid corner-by-corner inspection.

- **Files:**
  - Home: [`5-concepts/concept-b-home.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/concept-b-home.html) · [PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/concept-b-home.png)
  - Track map: [`5-concepts/concept-b-track.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/concept-b-track.html) · [PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/concept-b-track.png)
  - CO₂ comparison: [`5-concepts/concept-b-compare.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/concept-b-compare.html) · [PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/concept-b-compare.png)

### What it improves
- **Home:** Uses the deck's asymmetric **section-opener composition** (bold left typography + zoomed Eau Rouge speed/relief vignette fading into white on the right + top-right little lap), followed by a compact 3-column hairline workspace index and a Slide-4 **Four driving cycles** sparkline strip using the real speed traces (`11.2 km` NEDC, `23.3 km` WLTC Class 3, `7.0 km` eco & sport). All three page groups sit above the fold.
- **Track map:** Pairs the aspect-locked portrait circuit (with a *Relief contours / Clean paper* backdrop toggle) beside a **clickable 10-corner Spa landmark dossier** showing exact distance, speed, altitude, power demand (kW), and local CO₂ (g/km) at each corner. Clicking a corner highlights it on the track and moves the playhead there; full-width Speed & Elevation runs underneath.
- **CO₂ comparison:** Replaces 16 vertical bars with a **Cleveland dot-and-spread chart** (4 horizontal cycle rows on one 0–420 g CO₂/km axis). Connecting range bars make the electrification spread (`−72%` NEDC, `−68%` WLTC, `−74%` Spa eco, `−66%` Spa sport) immediately legible without visual bar-height clutter, and hollow rings cleanly mark `short_steps > 0`. Paired directly with a structured numeric + feasibility table underneath.

### Trade-offs
- **Light-mode contrast watch-out:** Muted petrol amber (`#d09539`) and green (`#4fb267`) have lower contrast on `#ffffff` than on `#000000` (borderline ~2.6:1 for small text), so they must be used only for dots/bars/swatches with dark `#1d1d1f` value labels — never as body text.
- **More vertical scroll on Track map:** Putting the full-width Speed & Elevation strip below the portrait map + corner table pushes the strip partially below the fold (~1300 px total height).
- **Less immediate visual "wow" for slides:** The Cleveland dot plot is more analytical than grouped bars, so it differs slightly from Slide 7's bar visual during a live Q&A transition.

### Streamlit buildability
- **95% native Streamlit + Plotly + CSS.**
  - `config.toml`: `[theme.light]` natively supported in Streamlit 1.66 (`backgroundColor = "#ffffff"`, `secondaryBackgroundColor = "#f5f5f7"`, `textColor = "#1d1d1f"`, `borderColor = "#e5e5ea"`).
  - Clickable 10-corner table: native `st.dataframe(..., on_select="rerun", selection_mode="single-row")` in Streamlit 1.66! Clicking a row updates `st.session_state` and highlights the selected corner on the Plotly track map (causes a clean fast rerun, no custom component needed).
  - Cleveland dot plot: native `go.Scatter` (grey segment traces + solid marker traces + hollow white-filled marker traces with `line=dict(width=3)`).

---

## Direction C — Pit-Wall Workbench

Designed for active engineering comparison and the Slide-23 live demo: deep graphite `#0b0b0d`, Streamlit 1.66 **top navigation bar** (`st.navigation(MENU, position="top")`), freeing 100% of screen width for side-by-side telemetry and 4-panel small multiples.

- **Files:**
  - Home: [`5-concepts/concept-c-home.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/concept-c-home.html) · [PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/concept-c-home.png)
  - Track map: [`5-concepts/concept-c-track.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/concept-c-track.html) · [PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/concept-c-track.png)
  - CO₂ comparison: [`5-concepts/concept-c-compare.html`](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/concept-c-compare.html) · [PNG](/tmp/claude-1000/-home-phred-Projects-pwt-co2-simulation/55bca25c-431b-4298-a085-a0249351c033/scratchpad/dashboard-review/5-concepts/png/concept-c-compare.png)

### What it improves
- **Home:** Fits the entire command header, live 4-car WLTC/Sport preview strip, and all 10 page links across three swimlanes **completely above the fold** (~928 px height). Dropping the permanent 250 px sidebar gives every chart and track page ~25% more horizontal canvas.
- **Track map:** Adds **Car A vs Car B head-to-head comparison** (e.g., Petrol vs BEV on Spa sport) with a **Power Δ (A − B)** paint mode directly on the uncropped portrait circuit, plus a **3-channel synchronised telemetry stack** (Speed, Drivetrain Power with a dashed `74 kW` petrol engine cap line, and Elevation) and one-click corner jump chips.
- **CO₂ comparison:** Uses **4-panel small multiples** (switchable between *By Cycle* and *By Powertrain*, and *Shared 0–420* vs *Panel-local* scale) with **Tailpipe fuel CO₂ vs EU-grid electricity CO₂ stacked fills** (solid car colour + hatched grid cap). This immediately reveals *why* PHEV sits between Hybrid and BEV (e.g. Spa eco `113 g CO₂/km` = `40.4` fuel + `72.6` grid) and why BEV is non-zero under the EU 250 g/kWh grid, while keeping hollow outlined bars + a dedicated **Feasibility register** for the three `short_steps > 0` runs.

### Trade-offs
- **Higher visual density:** More controls per screen (Car A, Car B, Lap, Paint) can feel busier for a casual visitor than Direction A's clean keynote restraint.
- **Sidebar filter migration:** Pages that currently put filters in `st.sidebar` (`1_Overview.py`, `2_Category_View.py`, `3_Trace_Explorer.py`) would need their controls moved into a compact top popover/expander bar if top navigation replaces the sidebar.
- **Top-bar overflow with 10 pages:** `st.navigation(MENU, position="top")` groups the 3 sections into 3 dropdown menus cleanly, rather than showing all 10 pages inline simultaneously (slightly more clicks to switch between two workbook pages than an always-open sidebar).

### Streamlit buildability
- **95% native Streamlit 1.66 + Plotly 7.1 + CSS.**
  - Top navigation: native `st.navigation(MENU, position="top")` in Streamlit 1.66.
  - 3-channel synchronised track + telemetry: native single Plotly `make_subplots` with `column_widths=[0.41, 0.59]` and `rowspan=3` on column 1 (portrait track on left, 3 stacked XY channels on right), so one Play button and one slider animate all 4 subplots smoothly with **zero custom component**.
  - Hatched grid CO₂ bar segment: native Plotly `marker=dict(pattern=dict(shape="/", bgcolor=..., fgcolor=...))` supported in Plotly 7.1!
  - Only **corner jump chips** smoothly animating an in-flight Plotly Play cursor without a Streamlit rerun would require a tiny custom component; otherwise `st.pills` sets the initial frame via rerun (completely acceptable in Streamlit).

---

## Side-by-Side Comparison

| Dimension | A · Keynote Darkroom | B · Editorial Light Atlas | C · Pit-Wall Workbench |
|---|---|---|---|
| **Visual match to deck** | Exact match to dark slides (Slide 1 + Slide 7) | Exact match to light slides + section openers | Extended dark telemetry sibling of deck |
| **Navigation** | Sidebar (keeps existing `Overview.py` structure) | Sidebar (keeps existing `Overview.py` structure) | Top nav (`position="top"`, +25% chart width) |
| **Home above-the-fold** | Dramatic hero; Study cards below fold | Opener + all 3 sections + 4 cycles visible | Ultra-compact; everything visible at 930 px |
| **Track map solution** | 42/58 portrait relief + Speed/Altitude | 46/54 portrait + clickable 10-corner table | 41/59 portrait + Car A/B delta + 3-channel |
| **CO₂ chart clarity** | Direct deck continuity (grouped bars + `*`) | Best for reading electrification spread (dots) | Best for explaining fuel vs grid physics |
| **Classroom projector** | Needs dark room (unless paired with light theme) | Best under bright projector lighting | Same as A |
| **Migration effort** | **Lowest** (drop-in theme + Home + Track refactor) | Low–Medium | Medium (moves sidebar filters inline) |
| **Custom components** | None | None | None (optional only for zero-rerun corner jump) |

---

## Recommendation

**Pick Direction A (*Keynote Darkroom*) as the primary foundation, and selectively adopt two high-leverage ideas from B and C:**

1. **Why Direction A wins as the core:**
   - **Zero visual seam between presentation and live demo:** When the group switches from the dark PowerPoint deck (Slide 23) to the live Streamlit app, Direction A feels like the *exact same artefact come alive* — identical `#000000` / `#1c1c1e` surfaces, identical four-car colours, identical hollow-bar + `*` feasibility grammar, and identical north-up Spa-Francorchamps speed ribbon over altitude relief.
   - **Lowest implementation risk:** It keeps the existing 3-group sidebar (`dashboard/Overview.py`) and existing sidebar filters intact across all 10 pages, so the team doesn't have to rewrite every workbook page's control layout.
   - **Solves both owner pain points cleanly:** The home page gains genuine deck-matched craft (and stops conflating the app front door with the raw 12-workbook matrix), and the portrait 42/58 Cartesian track layout permanently eliminates the map cropping shown in `user-screenshot-map-cutoff.png`.
2. **Two targeted borrowings worth folding in:**
   - **From Direction B:** Configure `[theme.light]` alongside `[theme.dark]` in `.streamlit/config.toml` (native in Streamlit 1.66) so the group can flip to the Light deck palette in Settings if the classroom projector washes out dark slides.
   - **From Direction C:** Add a *"Split tailpipe vs grid CO₂"* toggle (native Plotly `marker.pattern`) on the Model comparison chart so anyone asking *"why isn't the BEV zero?"* or *"where does the PHEV's CO₂ come from?"* gets an instant visual answer during Q&A.

### First three build steps

1. **Unify the design tokens and dual theme (`.streamlit/config.toml` + `dashboard/theme.py`):**
   - Switch `.streamlit/config.toml` to Streamlit 1.66 `[theme.dark]` (`#000000` / `#1c1c1e` / `#f5f5f7` / `#2c2c2e`) and `[theme.light]` (`#ffffff` / `#f5f5f7` / `#1d1d1f` / `#e5e5ea`) with `font = "Inter"`.
   - Update `dashboard/theme.py` so `POWERTRAIN_ORDER` and `Palette.series` adopt the deck's agreed car colours (`#d09539`, `#4fb267`, `#b677d5`, `#3984d0`) and add a tiny shared `inject_css()` helper in `dashboard/layout.py` for card borders, tabular numerals, and provenance badges (`Workbook · verbatim` vs `Model output` vs `Study draft`).
2. **Rebuild `dashboard/track_charts.py` around the portrait equal-aspect circuit (`1 : 1.62`):**
   - Replace the wide, short `go.Scattermap` (hardcoded `zoom=13.2`) with a 2-column Plotly `make_subplots` (`column_widths=[0.43, 0.57]`) using Cartesian `go.Scatter` with `scaleanchor="x", scaleratio=1`, `pwt.deck.track.lap()` north-up coordinates, `pwt.deck.track.relief()` contours (with the altitude-impression caption), non-overlapping outward landmark labels, and the synchronised Speed & Elevation subplot + Play/Pause slider in column 2. Because `lap_section()` is shared, this fixes `8_Track_Map.py`, `6_Model.py`, `1_Overview.py`, and `3_Trace_Explorer.py` in one move.
3. **Add a dedicated `Home` landing page and upgrade the Model CO₂ chart (`dashboard/Overview.py`, `dashboard/views/0_Home.py`, `dashboard/views/6_Model.py`):**
   - Register `0_Home.py` as `default=True` in `dashboard/Overview.py` (keeping `1_Overview.py` untouched as the verbatim 12-workbook matrix), rendering the Slide-1 Spa-Francorchamps SVG hero, the WLTC baseline preview (with `short_steps` marks), and `st.page_link` entry cards for the three menu groups.
   - Add the deck-style grouped CO₂ bar chart (hollow outlined bars + `*` + feasibility summary strip for `short_steps > 0`, plus optional tailpipe-vs-grid split and EU/FR grid toggle) at the top of `6_Model.py`.
