# Group Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python -m pwt.deck --theme dark|light` builds the 23-slide first-draft group deck as a `.pptx`. It takes the words from `docs/deck/slides.md` and every number, chart and track graphic from the model, in the agreed look.

**Architecture:** A new package, `pwt/deck/`, has one module per job:
- the model numbers and text tags (`data.py`)
- the lap geometry: outline, relief, opener framing, label placement (`track.py`)
- the fixed running order and the content-file parser (`structure.py`, `content.py`)
- the track pictures, rendered by matplotlib as full-slide PNGs (`art.py`)
- the slide assembly in python-pptx (`render.py`)

Text, charts, the flow diagram and the little lap are native PowerPoint shapes, so the group can edit them later. The road, relief and fades are images.

**Tech Stack:** Python, numpy, pandas, matplotlib, contourpy (ships with matplotlib), python-pptx 1.0, pytest. Run everything through `.venv/bin/`.

**Spec:** `docs/superpowers/specs/2026-11-23-group-deck-design.md`. The reference for the look is `docs/superpowers/specs/deck-mockups/` (`mock16.py` and the scripts it execs). Its geometry code (smoothing, placement search, label search, contour masking) is the starting point to port.

**Status:** In progress. Tasks 1–4 done (b23d88d, a5e593c, f95e191, c49f4dc); Task 5 complete (336 tests passed). Task 6 in progress.

## Global Constraints

- **Words:** Claude writes no headlines, findings or conclusions. Every text field that `docs/deck/slides.md` leaves empty renders as a grey italic placeholder naming the field. Structural labels are fixed by code:
  - section numbers `01`–`06`
  - corner names and distances
  - cycle and car names
  - chart footnotes
  - "model output · first draft"
- **Baseline:** assignment vehicles (`pwt.model.fleet.petrol/electric/hybrid/plugin`) through `pwt.sweep.sweep` (the "storage losses" default), on `pwt.sweep.cycles()`. EU grid, 250 g/kWh. No changes to `pwt/model/`, `pwt/sweep.py` or `data/course-files/`.
- **Names:** cycles come from `pwt.sweep.CYCLES` keys, and display names are "NEDC", "WLTC Class 3", "Francorchamps eco" and "Francorchamps sport". Powertrain names come from `pwt.catalog.POWERTRAIN_NAMES`.
- **Numbers:** they reach slide text only through tags. Values are formatted to one decimal.
- **Feasibility:** a bar whose `short_steps > 0` is drawn outlined, with no fill, and gets an asterisk on its value. The chart's footnote reads "* outlined: engine short of the trace on some steps".
- **Colours:**
  - cars: petrol `#d09539`, full hybrid `#4fb267`, plug-in hybrid `#b677d5`, battery electric `#3984d0`
  - speed ramp from 40 to 150 km/h, with stops at 0 `#0a84ff`, 0.45 `#30d158`, 0.75 `#ffd60a` and 1 `#ff453a`
- **Themes:**
  - dark: bg `#000000`, fg `#f5f5f7`, muted `#86868b`, soft `#1c1c1e`, line `#2c2c2e`
  - light: bg `#ffffff`, fg `#1d1d1f`, muted `#86868b`, soft `#f5f5f7`, line `#e5e5ea`
  - relief opacity: 0.14 on dark, 0.20 on light (×1.8 on every fifth line)
- **Geometry:**
  - slide 16:9, 13.333 × 7.5 in. Design units are 1600 × 900, at 120 units per inch.
  - track north up, smoothed by a closed moving average (±4 points, two passes)
  - relief contours every 2 m, over 370–476 m
  - little-lap box at x 1452, y 44, max 62 wide by 100 tall, in design units
  - bar corner radius 3 units on the grouped chart and 5 on the single chart
- **Font:** Inter for every text run.
- **Output:** written only to `docs/deck/build/`, which is gitignored. `pwt/` must not import Streamlit.
- **Dependencies:** `requirements-deck.txt` holds `-r requirements.txt`, `matplotlib>=3.8` and `python-pptx>=1.0`.

## Review Focus

1. **A content file with a typo in a slide id or tag** must fail loudly, naming the bad id or tag, never drop the text silently. Tests: Task 3 (`test_unknown_slide_id_fails`) and Task 1 (`test_unknown_tag_fails`).
2. **A slide number of two digits next to a tight part of the outline** must not touch it. Test: Task 2 (`test_label_clear_for_every_slide`).
3. **The zoomed road crossing the title or the little lap** on any of the 7 openers. Test: Task 2 (`test_opener_frames_clear`).
4. **Rebuilding while a hand-edited copy exists** must never overwrite anything outside `docs/deck/build/`. Test: Task 5 (`test_writes_only_build_dir`).
5. **A missing or empty `slides.md`** must still build, with every field shown as a placeholder. Test: Task 5 (`test_builds_without_content`).

---

### Task 1: Model numbers and tags

**Files:**
- Create: `pwt/deck/__init__.py` (empty docstring module), `pwt/deck/data.py`
- Test: `tests/test_deck_data.py`

**Interfaces:**
- Produces:
  - `POWERTRAINS = ("petrol", "hybrid", "phev", "bev")`, the chart order
  - `CYCLE_KEYS = ("nedc", "wltc", "franco_eco_generated", "franco_sport_generated")`
  - `CYCLE_LABELS: dict[str, str]`
  - `CAR_COLOURS: dict[str, str]`
  - `baseline() -> pd.DataFrame`. It's cached with `functools.cache`, and its columns are those of `pwt.sweep.sweep` with `v1` dropped.
  - `cell(pt: str, cycle: str) -> pd.Series`
  - `tags() -> dict[str, str]`
  - `fill(text: str) -> str`, which raises `KeyError` naming the tag
- Tag grammar: `{co2.<pt>.<cycle>}` gives `"145.1 g CO2/km"`, `{fuel.<pt>.<cycle>}` gives `"x.x l/100 km"`, and `{elec.<pt>.<cycle>}` gives `"x.x kWh/100 km"`. `<pt>` and `<cycle>` take the keys above, and the short cycle aliases `eco` and `sport` are also accepted.

- [x] **Step 1: Write the failing tests**

```python
EXPECTED = {  # g CO2/km, EU grid; spec baseline, to one decimal
    ("petrol","nedc"):134.1, ("petrol","wltc"):145.1, ("petrol","franco_eco_generated"):217.5, ("petrol","franco_sport_generated"):385.2,
    ("bev","nedc"):38.0, ("bev","wltc"):45.8, ("bev","franco_eco_generated"):56.5, ("bev","franco_sport_generated"):132.2,
    ("hybrid","nedc"):123.7, ("hybrid","wltc"):128.8, ("hybrid","franco_eco_generated"):218.8, ("hybrid","franco_sport_generated"):395.2,
    ("phev","nedc"):67.9, ("phev","wltc"):73.6, ("phev","franco_eco_generated"):113.0, ("phev","franco_sport_generated"):293.0,
}
def test_baseline_reproduces():        # every pair, round(co2_eu,1) == EXPECTED; 16 rows, no NaN in co2_eu
def test_short_steps_flags():          # short_steps > 0 exactly for petrol/wltc, phev/nedc, phev/wltc
def test_fill_formats_tags():          # fill("{co2.petrol.wltc}") == "145.1 g CO2/km"; fill("{co2.bev.sport}") == "132.2 g CO2/km"
def test_unknown_tag_fails():          # fill("{co2.diesel.wltc}") raises KeyError whose message contains "co2.diesel.wltc"
def test_text_without_tags_unchanged():# fill("plain {not a tag") == "plain {not a tag"
```

- [x] **Step 2: Run** `.venv/bin/python -m pytest tests/test_deck_data.py -q`. Expected: it FAILS on the import.
- [x] **Step 3: Implement `data.py`.** `fill` matches `\{(co2|fuel|elec)\.[a-z_]+\.[a-z_]+\}` only, so other braces pass through.
- [x] **Step 4: Run the tests.** Expected: they PASS.
- [x] **Step 5: Commit:** `git add pwt/deck tests/test_deck_data.py && git commit -m "Deck: baseline numbers and text tags"`

### Task 2: Lap geometry

**Files:**
- Create: `pwt/deck/track.py`
- Test: `tests/test_deck_track.py`

**Interfaces:**
- Consumes: `pwt.trackmap.place`, `pwt.sweep.cycles()["franco_sport_generated"]` (its `s`, `v_kph` and `z`).
- Produces:
  - `@dataclass(frozen=True) class Lap: xy: np.ndarray (n,2, unit width, y down, north up), s: np.ndarray, v: np.ndarray, z: np.ndarray`
  - `lap() -> Lap`, cached
  - `index_at(s_m: float) -> int`
  - `CORNERS = {"start": 0, "la_source": 220, "eau_rouge": 1010, "les_combes": 2200, "pouhon": 3600, "stavelot": 4740, "bus_stop": 6540, "finish": 6990}`
  - `CORNER_NAMES: dict[str, str]`, from key to display name, with "Start / finish" for both start and finish
  - `zoomed(s_m: float, zoom: float, fx: float, fy: float) -> np.ndarray`, the lap in design units with the point `s_m` placed at `(fx, fy)`; lap width = 1600·zoom
  - `relief() -> list[tuple[float, list[np.ndarray]]]`, giving (level, lines in unit coords). The field is interpolated by IDW (power 3 on distance, every 4th point), then 12 passes of a 5-point box blur, then contourpy.
  - `opener_frame(s_m: float, zoom: float) -> tuple[float, float]`
  - `KEEP_OUT = [(1400, 20, 1600, 180), (60, 300, 900, 580)]`
  - `minimap_points() -> np.ndarray`, the lap fitted in the little-lap box (design units)
  - `label_spot(points: np.ndarray, dot: tuple[float, float], text: str) -> tuple[float, float]`
- Algorithms to port from `deck-mockups/mock16.py`:
  - `opener_frame` searches fx 950–1300 and fy 300–700 in steps of 25. Its score is `5·(points in KEEP_OUT[0], padded 30) + 3·(points in KEEP_OUT[1]) + |fx−1100|/50 + |fy−450|/50`.
  - `label_spot` tries angles 0–345° in steps of 15 and radii (16, 20, 26, 32). The box is 10.5·len(text) wide by 14 tall, padded 3. It prefers a clear box (more than 2 units from every point), then the smallest radius, then the furthest from the centroid.

- [x] **Step 1: Write the failing tests**

```python
def test_north_up_and_clockwise():   # La Source (index_at(220)) has smaller y than start; signed area of xy (y up) is negative
def test_relief_levels():            # levels run 370..474 step 2; at least one line near the lap at 380 and at 460
def test_opener_frames_clear():      # for each opener corner (all of CORNERS except "start") with its zoom
                                     # (la_source 3.2, eau_rouge 2.8, les_combes 3.0, pouhon 2.6, stavelot 3.0, bus_stop 3.4, finish 2.4):
                                     # no point of zoomed(...) inside KEEP_OUT[0] padded by 10, and fewer than 5% inside KEEP_OUT[1]
def test_label_clear_for_every_slide():  # for slide numbers "2".."23" at the lap positions from structure.lap_position (Task 3):
                                     # the label box at label_spot is > 2 units from every minimap point
def test_minimap_fits_box():         # all minimap_points inside the box x 1452..1514, y 44..144
```

`test_label_clear_for_every_slide` imports `structure` from Task 3. Write it in this task, mark it `xfail` until Task 3 lands, and remove the mark in Task 3.

- [x] **Step 2: Run** `.venv/bin/python -m pytest tests/test_deck_track.py -q`. Expected: FAIL.
- [x] **Step 3: Implement `track.py`.**
- [x] **Step 4: Run the tests.** Expected: they PASS, with the one xfail.
- [x] **Step 5: Commit:** `git commit -m "Deck: lap geometry, relief, opener framing, label placement"`

### Task 3: Running order and content file

**Files:**
- Create: `pwt/deck/structure.py`, `pwt/deck/content.py`, `docs/deck/slides.md`
- Test: `tests/test_deck_content.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class SlideSpec: id: str; layout: str; section: str; fields: tuple[str, ...]`
  - `SLIDES: tuple[SlideSpec, ...]` (23 slides)
  - `SECTIONS: dict[str, tuple[str, str, float]]`, mapping a section to (corner key, number, zoom), as in `sim → ("la_source","01",3.2)`, `cmp → ("eau_rouge","02",2.8)`, `A → ("les_combes","03 · Study A",3.0)`, `B → ("pouhon","04 · Study B",2.6)`, `C → ("stavelot","05 · Study C",3.0)`, `lim → ("bus_stop","06",3.4)`
  - `lap_position(i: int) -> float | None`, for a 0-based slide index. It returns None for the title. An opener sits at its corner. Content slide j of n in a section sits at corner + (next corner − corner)·j/n, where the section after `lim` ends at `finish`. "questions" sits at `finish`.
  - `parse(text: str) -> dict[str, dict[str, str]]`
  - `load(path: Path) -> dict[str, dict[str, str]]`, which returns `{}` when the file is missing
- The slide ids and layouts, in order:

| id | layout | fields |
|---|---|---|
| `title` | `title` | title, subtitle, byline, notes |
| `sim` | `opener` | title, notes |
| `sim-model` | `flow` | label, headline, step1…step6 (`Name \| detail`), notes |
| `sim-cars` | `cars` | label, headline, spec.petrol, spec.hybrid, spec.phev, spec.bev, notes |
| `sim-changed` | `tiles` | label, headline, tile1…tile4 (`number \| line`), notes |
| `cmp` | `opener` | title, notes |
| `cmp-all` | `grouped` | label, headline, notes |
| `cmp-wltc` | `single` | label, headline, notes |
| `A` | `opener` | title, notes |
| `A-1`, `A-2`, `A-3` | `slot` | label, headline, figure (repo-relative image path), notes |
| `B` | `opener` | title, notes |
| `B-1`, `B-2`, `B-3` | `slot` | label, headline, figure, notes |
| `C` | `opener` | title, notes |
| `C-1`, `C-2`, `C-3` | `slot` | label, headline, figure, notes |
| `lim` | `opener` | title, notes |
| `lim-rows` | `rows` | label, headline, row1…row3 (`limit \| why \| next`), notes |
| `questions` | `closing` | title, subtitle, notes |

- File format: `## <id>` starts a slide. `key: value` lines set fields. Any later lines that don't start with `key:` continue the previous field, joined with a newline, which is how multi-line notes work. Lines before the first `##` and lines starting with `>` are comments.

- [x] **Step 1: Write the failing tests**

```python
def test_order_and_count():          # [s.id for s in SLIDES] equals the table's id column; len == 23
def test_parse_fields_and_notes():   # "## cmp-all\nheadline: Hi\nnotes: a\nb\n" -> {"cmp-all": {"headline": "Hi", "notes": "a\nb"}}
def test_unknown_slide_id_fails():   # parse("## cmp-al\nheadline: x") raises ValueError naming "cmp-al"
def test_unknown_field_fails():      # parse("## cmp-all\nheadlin: x") raises ValueError naming "headlin" and "cmp-all"
def test_lap_positions():            # lap_position(0) is None; strictly increasing from 1 to 22; opener values equal CORNERS
def test_starter_file_parses():      # load(Path("docs/deck/slides.md")) parses, every SLIDES id present, all values ""
```

- [x] **Step 2: Run** the tests. Expected: FAIL.
- [x] **Step 3: Implement `structure.py` and `content.py`.** Then write the starter `docs/deck/slides.md`:
  - a `> how to write this file` comment of 5 lines: the format, the tags with one example, "empty fields show as placeholders", and the rebuild command
  - every slide id from the table, with each of its fields present and empty. **No words in any field.**
- [x] **Step 4: Remove the xfail** from `test_label_clear_for_every_slide`, then run `tests/test_deck_content.py` and `tests/test_deck_track.py`. Expected: they PASS.
- [x] **Step 5: Commit:** `git commit -m "Deck: running order, content file format, empty starter file"`

### Task 4: Track pictures

**Files:**
- Create: `pwt/deck/art.py`, `requirements-deck.txt`
- Test: `tests/test_deck_art.py`

**Interfaces:**
- Consumes: Task 2 (`lap`, `zoomed`, `relief`, `opener_frame`, `CORNERS`) and Task 3 (`SECTIONS`).
- Produces:
  - `THEMES: dict[str, dict[str, str]]`, as listed in Global Constraints
  - `speed_colour(v_kph: float) -> str`
  - `title_art(theme: str, path: Path) -> Path`
  - `opener_art(theme: str, corner: str, zoom: float, path: Path) -> Path`
  - Both write a 3200 × 1800 PNG with no text, in the theme's background colour.
- How each picture is drawn, with the mockup functions to port from `mock16.py` and its execs:
  - **Road:** drawn with `LineCollection` in speed bands. The speed is smoothed over ±3 points and quantised to 48 bands. Each band is a polyline overlapping its neighbours by one point, with butt caps, laid over a single underlay in the band-0.5 colour. Width 30 units on openers, 13 on the title.
  - **Relief:** drawn under the road. On openers it is unmasked; on the title it is masked with a 170-unit-wide stroke of the lap blurred by σ = 45.
  - **Openers:** a left-to-right fade over x 0–0.72 of the width, from opaque bg to 0.8 at 0.6 to transparent.
  - **Title:** the lap is centred at (800, 375) and 610 units tall. A bottom-up fade runs from opaque at y = 900, to 0.82 at 22 %, to transparent at 42 %.

- [x] **Step 1: Write the failing tests**

```python
def test_speed_colour_ends():        # speed_colour(40) == "#0a84ff"; speed_colour(150) == "#ff453a"; clamps below 40 and above 150
def test_opener_png(tmp_path):       # opener_art("dark","stavelot",3.0,tmp_path/"o.png"): PIL size (3200,1800); pixel (40,40) == (0,0,0);
                                     # mean of the left 20% strip within 8 of the bg; some pixel in the right half is saturated (max-min channel > 120)
def test_title_png_light(tmp_path):  # title_art("light", ...): size (3200,1800); corner pixel == (255,255,255)
```

- [x] **Step 2: Run** the tests. Expected: FAIL.
- [x] **Step 3: Implement `art.py`.** Use `figure(figsize=(16, 9), dpi=200)`, axes covering the whole figure with limits 0–1600 × 900–0, and the axis turned off. Write `requirements-deck.txt`.
- [x] **Step 4: Run the tests.** Expected: they PASS.
- [x] **Step 5: Commit:** `git commit -m "Deck: title and opener track pictures"`

### Task 5: Slide assembly and entry point

**Files:**
- Create: `pwt/deck/render.py`, `pwt/deck/__main__.py`
- Modify: `.gitignore` (add `docs/deck/build/`) and `README.md` (one paragraph after the Study B paragraph: what `python -m pwt.deck` does, the install line and the content file)
- Test: `tests/test_deck_build.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `build(theme: str, content: dict[str, dict[str, str]], out_dir: Path) -> Path`, which returns the `.pptx` path `out_dir/f"group-deck-{theme}.pptx"`
  - the CLI `python -m pwt.deck [--theme dark|light|both] [--content PATH] [--out DIR]`, defaulting to `both`, `docs/deck/slides.md` and `docs/deck/build`. It prints each path written.
- **Shape names** (the tests rely on these):
  - every bar is named `bar:<pt>:<cycle>`, with `.fill.background()` when outlined
  - the little lap is named `lap-outline`, its dot `lap-dot` and its label `lap-label`
  - placeholders are named `placeholder:<field>`
- **Layout,** in design units ×(1/120 in):
  - label at (110, 70), 24 pt muted; headline at (110, 105), 44 pt bold fg
  - placeholder text: muted, italic, at 0.75 transparency where supported, otherwise plain muted
  - **placeholder wording** matches the mockup, so Task 6 can compare like with like. It's defined once, as `PLACEHOLDERS` in `render.py`:

| Field | Placeholder text |
|---|---|
| headline | `Your headline` on group slides, `Owner's headline` on study slots |
| spec.* | `key specs` |
| tileN | `number` (big) and `one line` (small) |
| rowN | `limit`, `why it matters`, `next step` |
| figure | `chart or figure from the study`, with a second line `Study A owner's slides` (or B, C) |
| questions.subtitle | `then, if time allows: the live demo` |
| any other field | the field name |

  - **The title slide** puts `subtitle` and `byline` on one line, joined with ` · `, as in the mockup.
  - **Flow step details** (`Name | detail`) wrap as in `mock16.chain`. The detail is split at `, `. With fewer than three parts, each part gets its own line; with three or more, the first two parts share line 1 and the rest share line 2.
  - footer "model output · first draft" at (110, 845), 17 pt muted
  - the chart geometry follows `mock16.grouped`, `single`, `chain`, `carscycles`, `tiles`, `rows` and `study_slot`
  - the little lap is a freeform from `minimap_points()`, muted, 2.5 units at 70 % opacity. The dot has an 8-unit radius in fg, and the label sits at `label_spot`, 18 pt bold. It appears on every slide but `title`.
  - every slide's notes are the `notes` field, then a blank line, then "Source: …", naming the module behind its numbers or figure. On the title and opener slides the source line also reads: "Contour lines are an impression, interpolated from the generated lap's altitude (373–470 m), not survey data."
  - a slot's `figure` image is fitted inside (250, 240)–(1350, 760). With no figure, a dashed rounded frame holds `placeholder:figure`.
  - pixel sizes in the mockups are on the 1600-unit canvas, and 1 pt = 1.667 units, so convert font sizes as px × 0.6 = pt (for example the 44 px headline becomes 26.4 pt). Use this rule throughout.
- Every text field passes through `data.fill` before it's placed.

- [x] **Step 1: Write the failing tests** (build once per module with a fixture)

```python
def test_builds_without_content(tmp_path):   # build("dark", {}, tmp_path): file exists; 23 slides; slide 7 has placeholder:headline
def test_bars_and_flags(tmp_path):           # slide 7: 16 shapes named bar:*; outlined ones (fill.type is None / background) are exactly
                                             # bar:petrol:wltc, bar:phev:nedc, bar:phev:wltc; slide 8: 4 bars, petrol and phev outlined
def test_tags_filled(tmp_path):              # content {"cmp-wltc": {"headline": "Petrol {co2.petrol.wltc}"}} -> slide 8 text contains "Petrol 145.1 g CO2/km"
def test_lap_label_is_slide_number(tmp_path):# for slides 2..23 the shape lap-label has text str(n); slide 1 has no lap-label
def test_writes_only_build_dir(tmp_path):    # CLI with --out tmp_path/build and --theme light: files created only under tmp_path/build
def test_both_themes(tmp_path):              # CLI default theme writes group-deck-dark.pptx and group-deck-light.pptx
```

- [x] **Step 2: Run** the tests. Expected: FAIL.
- [x] **Step 3: Implement `render.py` and `__main__.py`.** Then update `.gitignore` and `README.md`.
- [x] **Step 4: Run the full suite:** `.venv/bin/python -m pytest -q`. Expected: all tests pass. The LibreOffice test may be skipped.
- [x] **Step 5: Build and look.** Run `.venv/bin/python -m pwt.deck`. Render both decks to images and compare them with `deck-mockups/png/31-main-slides-v7.png`:
  - with LibreOffice: `soffice --headless --convert-to pdf` and `pdftoppm`
  - without it: open the `.pptx` in PowerPoint or Keynote, or upload it to Google Slides

  Fix any visible drift from the mockups before committing.
- [x] **Step 6: Commit,** and update this plan's **Status:** `git commit -m "Deck: assemble the 23-slide first draft; python -m pwt.deck"`

### Task 6: Fidelity to the mockups, at least 99 %

Phred's requirement: the built slides must match the approved mockups to at least 99 %. This task makes that a measured, repeatable check, then fixes `render.py` and `art.py` until every slide passes.

**Files:**
- Create:
  - `tests/fixtures/deck-mockup.md`, a content file that reproduces the mockup's filled-in text
  - `docs/superpowers/specs/deck-mockups/reference.py`, which writes one reference PNG per slide and theme
  - `pwt/deck/fidelity.py`
  - `tests/test_deck_fidelity.py`
- Modify: `pwt/deck/render.py` and `pwt/deck/art.py`, to fix any drift.

**The fixture** `tests/fixtures/deck-mockup.md` fills exactly the fields that the mockup (`mock16.py`) shows as normal text, and leaves the rest empty so they render as placeholders. It's a test fixture, not deck content: it never goes in `docs/deck/slides.md`.
- **title:** title `Four cars. Four cycles.`, subtitle `Simulating the CO2 of four powertrains`, byline `Group of three · PWT Powertrains · ESILV 2026`
- **opener titles:**
  - sim `The simulation`
  - cmp `Four cars compared`
  - A `Hybrid sizing`
  - B `Sensitivity`
  - C `Cornering speed`
  - lim `Limits and next step`
- **labels:**
  - sim-model, sim-cars and sim-changed: `The simulation`
  - cmp-all: `Four cars on four cycles · g CO2/km`
  - cmp-wltc: `WLTC Class 3 · g CO2/km`
  - A-1 to A-3: `Hybrid sizing`
  - B-1 to B-3: `Sensitivity`
  - C-1 to C-3: `Cornering speed`
  - lim-rows: `Limits and next step`
- **sim-model steps:**
  - `Speed trace | v(t) or v(s)`
  - `Forces | rolling, aero, grade, inertia`
  - `Wheel power | F · v`
  - `Engine / motor | ÷ transmission η, capability`
  - `Energy | engine η(P), heating value`
  - `CO2 | fuel + grid, g/km`
- **questions:** title `Questions?`
- everything else is empty

**Reference images:** `reference.py --out DIR --theme dark|light` reuses the mockup chain (`mock16.py` and its execs, with the data JSONs in that folder). It writes each of the 23 slides as its own 1600 × 900 PNG, `DIR/<theme>/NN.png`, by rendering that slide's SVG in headless Chromium (`chromium --headless=new --window-size=1600,900 --screenshot`). The mockup is the specification; change it only to remove a difference that exists only in the mockup (a page frame, shadow or rounded slide corners). Record any such change in a comment.

**Interfaces:**
- `render_deck(pptx: Path, out_dir: Path) -> list[Path]` uses `soffice --headless --convert-to pdf`, then `pdftoppm -png -scale-to-x 1600 -scale-to-y 900`, and returns 23 PNGs.
- `similarity(a: Path, b: Path) -> float` compares the two images at 1600 × 900, RGB, each blurred with a Gaussian of radius 1.5 (PIL). It returns the fraction of pixels whose largest per-channel absolute difference is at most 16.
- `report(theme: str, out_dir: Path) -> list[tuple[int, float]]` builds the deck from the fixture, renders both sides, and returns `(slide number, similarity)` for all 23 slides.
- CLI: `python -m pwt.deck.fidelity [--theme dark|light|both]` prints a table and exits non-zero if any slide scores below 0.99. It also writes side-by-side diff images (reference | deck | difference) to `docs/deck/build/fidelity/`.

- [ ] **Step 1: Write the failing test.** `test_every_slide_matches_mockup` is parametrised over both themes. It asserts that every one of the 23 slides scores at least 0.99, and lists the failing slides with their scores in the message. It's skipped if `soffice`, `pdftoppm` or `chromium` is missing.
- [ ] **Step 2: Run it.** Expected: FAIL, with per-slide scores.
- [ ] **Step 3: Close the gaps.** Read the diff images worst-first and fix `render.py` and `art.py` until every slide scores at least 0.99 in both themes. Expect to calibrate text box offsets: an SVG `y` is the baseline, while a PowerPoint text box is placed from its top. Also expect to calibrate font sizes, chart geometry and the opener fade. Don't lower the threshold or change the metric. If one slide can't reach 0.99 for a reason outside the renderer (for example font hinting), stop and report it with its score and the diff image.
- [ ] **Step 4: Run** `.venv/bin/python -m pytest -q`. Expected: everything passes.
- [ ] **Step 5: Commit:** `git commit -m "Deck: measured fidelity to the mockups, every slide >= 99 %"`

---

**After the plan:** remind Phred that the deck builds from `docs/deck/slides.md`, and that every field is empty until they write it. `pwt/` gains a package, but the dashboard doesn't import it, so the Cloud app needs no reboot. Mention it anyway, per AGENTS.md.
