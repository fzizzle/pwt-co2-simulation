# PWT CO2 Simulation

Group project for PWT — Powertrains (MESISI471226, Marc Nelis), ESILV 2026-Autumn.

The course's spreadsheet CO2 model, ported to Python and extended: petrol, battery-electric,
full hybrid and plug-in hybrid over NEDC, Spa-Francorchamps (eco and sport) and WLTC Class 3.

## Layout

| Path | Contents |
|---|---|
| `data/course-files/` | The 23 files Nelis supplied, unchanged — the 22 handed out at L3 plus the assignment sheet, `1 Simulation of cars on driving cycles.pdf`. Read-only: never edit these. |
| `data/derived/` | Workbooks built from the supplied ones by `python -m pwt.derived`: WLTC for all four powertrains, and the plug-in hybrid's charge-depleting and charge-sustaining runs. |
| `data/track/` | The Spa-Francorchamps outline from [bacinger/f1-circuits](https://github.com/bacinger/f1-circuits), with its MIT licence. |
| `docs/` | Snapshot of the brief and plan, plus `model-equations.md` (every column as an equation) and `phase-1-results.md` (the 4 × 4 table). The live brief and plan are in the vault, `40 Projects/PWT CO2 Simulation/`. |
| `pwt/` | Reader for the supplied workbooks, the derived-workbook builder, the checkpoint tables and the sweeps. No Streamlit import — a plain library. |
| `pwt/model/` | The spreadsheet model in Python (see below). |
| `dashboard/` | Streamlit app for exploring the workbooks and the model. |
| `tests/` | Golden tests: the reader and the model must reproduce each workbook's totals before anything changes. |

## The dashboard

**Hosted:** <https://pwt-co2-simulation-iihscdva9b3woycsyuk7dp.streamlit.app>

> [!important]
> **Reboot the app after any change to `pwt/`.** Community Cloud pulls new files on push and
> re-runs the page scripts, but it only re-imports modules inside the app folder
> (`dashboard/`). The `pwt/` package sits outside that tree and stays in memory from boot, so
> a page calling a newly added function hits `ImportError: cannot import name …` even though
> the function is on disk. Manage app → ⋮ → Reboot app. Changes confined to `dashboard/`
> hot-reload on their own.

Deployed from this repo on Streamlit Community Cloud. Because the repo is private the app is
invite-only — teammates need their email added under *Settings → Sharing* before the link
works for them. It sleeps after extended inactivity; the next visitor waits ~30 s for it to
wake, so open it once before any session where you need it immediately.

An **internal viewer, not a project deliverable**. Five of its eight pages show the supplied figures
exactly as the workbooks report them — no unit conversion, no recomputation, no corrections, no
conclusions. The **Model**, **Sizing** and **Track map** pages are the exceptions: they show what `pwt.model` computes.

Run it locally with:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run dashboard/Overview.py
```

Eight pages: **Overview** (all twelve runs, one table and one chart), **Category view** (every run in
one category together — all the petrols, all the NEDC runs, all the sport runs), **Trace
Explorer** (per-step data for one run), **Compare** (two runs, with their differing inputs
listed first), **Data** (the raw datasets as plain tables), **Model** (what `pwt.model` computes), **Sizing** (the hybrid sizing findings, one chart each), and **Track map** (a generated lap on the real circuit, animated). Every table has a CSV download.

A category is a slice of the 4×3 grid along one field: powertrain (4 categories of 3) or cycle
(3 categories of 4). Driving style is not a third axis — it maps 1:1 onto cycle today, so "all the
sport" is the Francorchamps sport category. That changes when the WLTC highway cycle is added,
at which point `regulatory` will cover both NEDC and WLTC.

The Data page carries five datasets: `Runs` (12 × 74), `Totals` and `Parameters` in long form,
`Traces` (676 steps), and `Workbook cells` — one workbook's labelled block exactly as the
sheet holds it, with the original label and unit text, the row number, and how the reader
classified each row. That last one is where to look when a figure elsewhere seems wrong.

`python -m pwt.build` writes `data/processed/*.parquet` to speed startup. It is optional and
gitignored — the app reads the workbooks directly when the parquet is absent.

## Derived workbooks

`python -m pwt.derived` builds `data/derived/` from the supplied NEDC workbooks. It needs
LibreOffice (`soffice`) to recalculate. Each derived file keeps its template's parameter block
and formulas and changes only the trace, the starting state of charge or the shift speeds.
Rebuilding a template on its own trace reproduces its supplied totals exactly, which
`tests/test_derived.py` checks whenever LibreOffice is present.

| File | Template | What changed |
|---|---|---|
| `WLTC3 PETROL.xlsx` | `33` | WLTC Class 3 trace; shift speeds 35/57/82/115 km/h |
| `WLTC3 ELECTRIC.xlsx` | `32` | WLTC Class 3 trace |
| `WLTC3 HYBRID.xlsx` | `35` | WLTC Class 3 trace |
| `WLTC3 PHYBRID CD.xlsx` / `CS.xlsx` | `34` | WLTC Class 3 trace; CS starts at the 23 % engine threshold |
| `NEDC PHYBRID CD.xlsx` / `CS.xlsx` | `34` | CD as supplied; CS starts at 23 % |

Each adds rows below the parameter block: WLTC phase distance, consumption and emission, plus
battery energy used and grid CO2 for the hybrids. `python -m pwt.checkpoint` prints the
4 × 4 table in `docs/phase-1-results.md`. The dashboard does not show derived runs yet.

## The Python model

`pwt/model/` is the spreadsheet model ported to Python. `from_workbook(run)` reproduces any
supplied or derived workbook exactly, totals and every per-step column
(`tests/test_model_golden.py`). `simulate(vehicle, cycle, conventions, strategy)` takes
them separately, which is how anything gets changed:

| Module | Holds |
|---|---|
| `conventions.py` | Everything the workbooks disagree on, one record per file, and `harmonised()` |
| `vehicle.py`, `cycle.py` | Inputs, read from a workbook's block and trace |
| `road_load.py`, `powertrains.py` | Forces, then petrol, electric and hybrid chains |
| `strategy.py` | The sheets' motor-share rule and a charge-sustaining band |
| `constants.py`, `fleet.py` | Cited constants (`docs/sources.md`) and the assignment sheet's vehicles |
| `profile.py` | Francorchamps laps generated from the assignment's eco and sport rules |

`python -m pwt.sweep` runs the hybrid sizing study in `docs/phase-3-sizing.md`. Its `sweep()`
takes any set of `Vehicle` variants, for other parameter studies. `generate(...,
corner_speed=...)` replaces the template corner speeds, for tyre and downforce studies.

`python -m pwt.phase2` prints the five-scenario comparison in `docs/phase-2-results.md`; the
dashboard's **Model** page shows it, the generated laps, and any single run. Reboot the
Cloud app after deploying this — the page imports `pwt.model`, which a running app has not
loaded.

## Runs whose figures leave something out

`34 NEDC PHYBRID engine.xlsx` reports 0 l/100 km and 0 g CO₂/km, and that zero is what its
formulas compute. The 40 kW motor covers every NEDC demand, so the motor's share of power
(`FACT`) stays at 1 and the battery only falls from 98 % to 78 %, never reaching the 23 % that
brings the engine in. What the sheet leaves out is the electricity: the energy drawn from the
battery and its CO₂. The app marks the run "electricity not counted" wherever its figures
appear. `data/derived/` adds the electricity and a charge-sustaining run (see above).

Record further gaps in `RUN_NOTICES` in `dashboard/layout.py`, keyed by `(powertrain, cycle)`;
every page picks them up automatically.

## What the reader has to work around

The twelve result workbooks share a shape but not a layout. Found by inspecting all of them:

- Totals sit at different rows in each file (`C47` petrol-Franco, `C48` hybrid, `C45`
  NEDC-petrol), so lookups are by label, never by cell address.
- Petrol rows 48 and 49 are both labelled `Total emission:` and differ only in unit, so values
  are keyed by `(label, unit)`.
- Column B is a unit *or* a value: files `10`/`15`/`35` lay out a menu of engine efficiency
  curves across B/C/D with row 30 naming them (`downsized` / `atkinson` / `old`). Column C is
  the active value everywhere.
- Only 12 of 37 trace headers are universal. `Time (s)`, `Distance (m)` and `Gear` are each
  missing from some workbooks, and `Energy (Wh)` is spelled `Engergy (Wh)` in six of them.
- `Distance (m)` is per-workbook, not per-cycle: the eight Francorchamps files and NEDC
  hybrid/plug-in hybrid store it cumulatively, `33 NEDC PETROL Car.xlsx` stores it per step,
  and `32 NEDC ELECTRIC.xlsx` has the column but never fills it. A column is offered as a
  chart axis only when it actually runs forward.
- Each trace ends with a cumulative summary row and a unit-annotation row. Real steps fill
  96-100% of their columns and these artifacts 22-50%, so a density threshold separates them.
- Three titles contradict their filename, so run identity comes from `pwt/catalog.py`.

Spa laps are **32 variable-length segments**, not per-second traces; NEDC runs are ~105 steps.

## Golden numbers

Petrol, Francorchamps eco (`07 SPA Franco PETROL car ECO Driving.xlsx`):
**10.273 l/100 km** and **245.7 g CO2/km**. Locked in `tests/test_extract_golden.py`, along
with the BEV, hybrid and PHEV headline figures.

```sh
.venv/bin/python -m pytest
```
