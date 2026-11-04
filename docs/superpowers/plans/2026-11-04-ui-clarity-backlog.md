# UI and clarity improvements — backlog

Status: items 1, 2, 5 and 6 built on branch `ui-clarity` (2026-11-04, uncommitted). Items 3 and 4
still need decisions. Original note: suggestions from a review of all eight pages; items 3 and 4
need decisions on wording and on which pages go. Suggested order: 1, 2, 5, 3, 4, then 6.

## 1. Fix first: the same run shows two CO₂ figures

Overview: battery electric, Francorchamps eco = 47.1 g/km. Model, column "1 · As in the
workbooks" = 51.2. Plug-in hybrid: 34.2 vs 75.4. The gap is real (the Model page counts
electricity at 250 g/kWh for every car), but the label claims workbook figures.

- Rename the column, e.g. "1 · Workbook vehicles, 250 g/kWh grid" (`SCENARIO_LABELS` in
  `dashboard/pages/6_Model.py`).
- Add one line saying why it differs from Overview.

## 2. Two labelled groups in the sidebar menu

- "The workbooks": Overview, Category View, Trace Explorer, Compare, Data — figures as reported.
- "The model": Model, Sizing, Track Map — what `pwt.model` computes.
- Use `st.navigation` with sections.

## 3. Lead with the answer

The landing page opens with "PWT workbook explorer" and a warning box. Follow Sizing's pattern
(headings that state a finding): open Overview with 3–4 headline findings, each linking to the
page that shows it.

## 4. Fewer overlapping pages (8 → about 6)

- Category View, Trace Explorer and Compare all overlay traces. Let Compare take two or more
  runs and absorb Category View.
- Track Map duplicates the map on Model; consider making it a mode of Model.

## 5. Plain names and sensible precision everywhere

One shared lookup of display names, units and formats, used by every page.

- Raw names shown: `speed_kph`, `distance_m`, `a1`/`a2`/`a3`, `title_cell`,
  `summary_rows_skipped`, lowercase `powertrain`/`cycle` headers.
- "None" next to "—" for missing values.
- Too many digits: 245.730 → 245.7; 1,720.109 → 1,720; `8.5e+04` W → 85 kW.
- Mixed units: kph vs km/h; Wh/100 km vs kWh/100 km.
- Lap names: "Francorchamps — sport", "Spa sport lap", "Sport lap" → pick one.

## 6. Smaller UI fixes

- Plug-in hybrid NEDC warning box: about seven lines, repeated on Overview and Data → one
  sentence plus a "why" link.
- Category View overlay defaults to all three cycles against time (reads as noise) → default to
  distance on the laps.
- Map slider shows only a "0" tick → label it with corner names.
- Corner labels are written vertically over the speed line → place them above the plot area.
- Model metric tiles show "From the battery —" for petrol → hide tiles that don't apply.
- Map is 800 px tall and pushes everything below it down → about 550 px.
