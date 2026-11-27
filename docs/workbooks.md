# The workbooks

How the supplied workbooks are read, what `pwt.derived` builds from them, and where their figures leave something out.

## What the reader has to work around

The twelve result workbooks share a shape but not a layout. Found by inspecting all of them:

- Totals sit at different rows in each file (`C47` petrol-Franco, `C48` hybrid, `C45` NEDC-petrol), so lookups are by label, never by cell address.
- Petrol rows 48 and 49 are both labelled `Total emission:` and differ only in unit, so values are keyed by `(label, unit)`.
- Column B is a unit *or* a value: files `10`/`15`/`35` lay out a menu of engine efficiency curves across B/C/D, with row 30 naming them (`downsized` / `atkinson` / `old`). Column C is the active value everywhere.
- Only 12 of 37 trace headers are universal. `Time (s)`, `Distance (m)` and `Gear` are each missing from some workbooks, and `Energy (Wh)` is spelled `Engergy (Wh)` in six of them.
- `Distance (m)` is per-workbook, not per-cycle: the eight Francorchamps files and NEDC hybrid/plug-in hybrid store it cumulatively, `33 NEDC PETROL Car.xlsx` stores it per step, and `32 NEDC ELECTRIC.xlsx` has the column but never fills it. A column is offered as a chart axis only when it actually runs forward.
- Each trace ends with a cumulative summary row and a unit-annotation row. Real steps fill 96-100 % of their columns and these artifacts 22-50 %, so a density threshold separates them.
- Three titles contradict their filename, so run identity comes from `pwt/catalog.py`.

Spa laps are **32 variable-length segments**, not per-second traces. NEDC runs are about 105 steps.

## Derived workbooks

`python -m pwt.derived` builds `data/derived/` from the supplied NEDC workbooks. It needs LibreOffice (`soffice`) to recalculate. Each derived file keeps its template's parameter block and formulas, and changes only the trace, the starting state of charge or the shift speeds. Rebuilding a template on its own trace reproduces its supplied totals exactly, which `tests/test_derived.py` checks whenever LibreOffice is present.

| File | Template | What changed |
|---|---|---|
| `WLTC3 PETROL.xlsx` | `33` | WLTC Class 3 trace; shift speeds 35/57/82/115 km/h |
| `WLTC3 ELECTRIC.xlsx` | `32` | WLTC Class 3 trace |
| `WLTC3 HYBRID.xlsx` | `35` | WLTC Class 3 trace |
| `WLTC3 PHYBRID CD.xlsx` / `CS.xlsx` | `34` | WLTC Class 3 trace; CS starts at the 23 % engine threshold |
| `NEDC PHYBRID CD.xlsx` / `CS.xlsx` | `34` | CD as supplied; CS starts at 23 % |

Each adds rows below the parameter block: WLTC phase distance, consumption and emission, plus battery energy used and grid CO2 for the hybrids. `python -m pwt.checkpoint` prints the 4 × 4 table in [phase-1-results.md](phase-1-results.md). The dashboard does not show derived runs yet.

## Runs whose figures leave something out

`34 NEDC PHYBRID engine.xlsx` reports 0 l/100 km and 0 g CO2/km, and that zero is what its formulas compute. The 40 kW motor covers every NEDC demand, so the motor's share of power (`FACT`) stays at 1 and the battery only falls from 98 % to 78 %, never reaching the 23 % that brings the engine in. What the sheet leaves out is the electricity: the energy drawn from the battery and its CO2. The dashboard marks the run "electricity not counted" wherever its figures appear, and `data/derived/` adds the electricity and a charge-sustaining run.

Record further gaps in `RUN_NOTICES` in `dashboard/layout.py`, keyed by `(powertrain, cycle)`. Every page picks them up automatically.
