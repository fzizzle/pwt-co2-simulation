# PWT CO2 Simulation

Group project for PWT — Powertrains (MESISI471226, Marc Nelis), ESILV 2026-Autumn.

The course's spreadsheet CO2 model, ported to Python and extended: petrol, battery-electric,
full hybrid and plug-in hybrid over NEDC, Spa-Francorchamps (eco and sport) and WLTC Class 3.

## Layout

| Path | Contents |
|---|---|
| `data/course-files/` | The 22 files Nelis supplied at L3, unchanged. Read-only: never edit these. |
| `docs/` | Snapshot of the brief and plan. The live copies are in the vault, `40 Projects/PWT CO2 Simulation/`. |
| `pwt/` | Reader for the supplied workbooks. No Streamlit import — a plain library. |
| `dashboard/` | Streamlit app for exploring what the workbooks contain. |
| `tests/` | Golden tests: the reader must reproduce each workbook's totals before anything changes. |

## The dashboard

**Hosted:** <https://pwt-co2-simulation-iihscdva9b3woycsyuk7dp.streamlit.app>

Deployed from this repo on Streamlit Community Cloud. Because the repo is private the app is
invite-only — teammates need their email added under *Settings → Sharing* before the link
works for them. It sleeps after extended inactivity; the next visitor waits ~30 s for it to
wake, so open it once before any session where you need it immediately.

An **internal viewer, not a project deliverable**. It shows the supplied figures exactly as the
workbooks report them — no unit conversion, no recomputation, no corrections, no conclusions.
Analysis belongs to the Python model phase, which is separate work.

Run it locally with:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run dashboard/Overview.py
```

Three pages: **Overview** (all twelve runs, one table and one chart), **Trace Explorer**
(per-step data for one run), **Compare** (two runs, with their differing inputs listed first).
Every table has a CSV download.

`python -m pwt.build` writes `data/processed/*.parquet` to speed startup. It is optional and
gitignored — the app reads the workbooks directly when the parquet is absent.

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
- Each trace ends with a cumulative summary row and a unit-annotation row. Real steps fill
  50-100% of their columns and these artifacts 22-29%, so a density threshold separates them.
- Three titles contradict their filename, so run identity comes from `pwt/catalog.py`.

Spa laps are **32 variable-length segments**, not per-second traces; NEDC runs are ~105 steps.

## Golden numbers

Petrol, Francorchamps eco (`07 SPA Franco PETROL car ECO Driving.xlsx`):
**10.273 l/100 km** and **245.7 g CO2/km**. Locked in `tests/test_extract_golden.py`, along
with the BEV, hybrid and PHEV headline figures.

```sh
.venv/bin/python -m pytest
```
