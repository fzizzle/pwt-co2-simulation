# PWT CO2 Simulation

Group project for PWT — Powertrains (MESISI471226, Marc Nelis), ESILV 2026-Autumn.

The course's spreadsheet CO2 model, ported to Python and extended: petrol, battery-electric,
full hybrid and plug-in hybrid over NEDC, Spa-Francorchamps (eco and sport) and WLTC Class 3.

## Layout

| Path | Contents |
|---|---|
| `data/course-files/` | The 22 files Nelis supplied at L3, unchanged. Read-only: never edit these. |
| `docs/` | Snapshot of the brief and plan. The live copies are in the vault, `40 Projects/PWT CO2 Simulation/`. |
| `tests/` | Golden tests: the Python model must reproduce each workbook's totals before anything changes. |

## First test to write

Petrol, Francorchamps eco (`07 SPA Franco PETROL car ECO Driving.xlsx`):
**10.273 l/100 km** and **245.7 g CO2/km**.
