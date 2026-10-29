# Phase 2 results — the Python model

`pwt/model/` reproduces all twelve supplied workbooks and the seven derived ones: every total to about 1e-15, and every per-step column (`tests/test_model_golden.py`). From there the model changes one tested step at a time. Regenerate everything below with `python -m pwt.phase2`; no LibreOffice needed.

## The four scenarios

1. **exact**: each workbook as supplied. Equal to `docs/phase-1-results.md`.
2. **harmonised**: the same vehicles, on one convention with cited constants:
   - shift speeds 35/57/82/115 km/h;
   - one effective-mass formula;
   - idle only for the conventional petrol car;
   - electric regeneration capped at 120 kW;
   - petrol at 44.3 MJ/kg and 3.07 g CO2 per g (IPCC 2006 defaults);
   - grid electricity at 250 g/kWh.
   
   See `docs/sources.md`.
3. **stage B**: harmonised, plus two corrections to the hybrids:
   - engine efficiency is read at the power the engine delivers, not at the whole demand;
   - the full hybrid holds its battery in a 50–70 % band.
4. **assignment**: stage B with the assignment sheet's vehicles in place of the workbooks':
   - petrol: 1280 kg, 74 kW, 0.75 kg/l;
   - electric: 22 kWh, 1460 kg;
   - full hybrid: +100 kg, 1.5 kWh, 25 kW;
   - plug-in hybrid: +100 kg, 15 kWh, 45 kW;
   - batteries at 150 Wh/kg.
   
   Where the sheet gives a range, the midpoint is used.

CO2 below always includes electricity at 250 g/kWh, so all four powertrains compare on one footing. The plug-in hybrid on NEDC and WLTC is the UN R101 weighting of a charge-depleting and a charge-sustaining run, as in Phase 1.

## All four, CO2 with electricity at 250 g/kWh (g/km)

|                                               |   exact |   harmonised |   stage B |   assignment |
|:----------------------------------------------|--------:|-------------:|----------:|-------------:|
| ('Petrol', 'NEDC')                            |   158.3 |        134.8 |     134.8 |        134.1 |
| ('Petrol', 'Francorchamps — eco')             |   245.7 |        203   |     203   |        198.1 |
| ('Petrol', 'Francorchamps — sport')           |   373.1 |        308.3 |     308.3 |        308.2 |
| ('Petrol', 'WLTC Class 3')                    |   177.8 |        146.9 |     146.9 |        145.1 |
| ('Battery electric', 'NEDC')                  |    37.3 |         37.3 |      37.3 |         34.2 |
| ('Battery electric', 'Francorchamps — eco')   |    51.2 |         51.2 |      51.2 |         46.3 |
| ('Battery electric', 'Francorchamps — sport') |    95.9 |         95.9 |      95.9 |         86.1 |
| ('Battery electric', 'WLTC Class 3')          |    44.5 |         44.5 |      44.5 |         41.2 |
| ('Full hybrid', 'NEDC')                       |   129.1 |        106.7 |     105.7 |         98.7 |
| ('Full hybrid', 'Francorchamps — eco')        |   181.2 |        149.7 |     174.4 |        160.7 |
| ('Full hybrid', 'Francorchamps — sport')      |   331.9 |        274.2 |     304.6 |        276.8 |
| ('Full hybrid', 'WLTC Class 3')               |   157.5 |        130.1 |     110.8 |        104.7 |
| ('Plug-in hybrid', 'NEDC')                    |    75.7 |         66.4 |      66.4 |         55.7 |
| ('Plug-in hybrid', 'Francorchamps — eco')     |    75.4 |         69.5 |      72.2 |         63.7 |
| ('Plug-in hybrid', 'Francorchamps — sport')   |   198.3 |        171.9 |     182.2 |        185.5 |
| ('Plug-in hybrid', 'WLTC Class 3')            |    77.5 |         67.8 |      68.2 |         56.7 |

## The full hybrid's change, step by step (l/100 km)

|                                                |   NEDC |   Francorchamps — eco |   Francorchamps — sport |   WLTC Class 3 |
|:-----------------------------------------------|-------:|----------------------:|------------------------:|---------------:|
| sheets' rule, efficiency at the whole demand   |   4.83 |                  6.77 |                   12.4  |           5.89 |
| sheets' rule, efficiency at the engine's share |   4.83 |                  7.89 |                   14.07 |           5.93 |
| same, starting at 60 %                         |   6.37 |                  8.6  |                   13.8  |           6.48 |
| charge-sustaining band 50-70 %, from 60 %      |   4.78 |                  7.89 |                   13.78 |           5.01 |

## exact

### Fuel (l/100 km)

|                  | NEDC   | Francorchamps — eco   | Francorchamps — sport   | WLTC Class 3   |
|:-----------------|:-------|:----------------------|:------------------------|:---------------|
| Petrol           | 6.62   | 10.27                 | 15.60                   | 7.43           |
| Battery electric | —      | —                     | —                       | —              |
| Full hybrid      | 5.40   | 7.58                  | 13.87                   | 6.58           |
| Plug-in hybrid   | 2.22   | 1.43                  | 6.34                    | 2.32           |

### CO2 with electricity at 250 g/kWh (g/km)

|                  |   NEDC |   Francorchamps — eco |   Francorchamps — sport |   WLTC Class 3 |
|:-----------------|-------:|----------------------:|------------------------:|---------------:|
| Petrol           |  158.3 |                 245.7 |                   373.1 |          177.8 |
| Battery electric |   37.3 |                  51.2 |                    95.9 |           44.5 |
| Full hybrid      |  129.1 |                 181.2 |                   331.9 |          157.5 |
| Plug-in hybrid   |   75.7 |                  75.4 |                   198.3 |           77.5 |

## harmonised

### Fuel (l/100 km)

|                  | NEDC   | Francorchamps — eco   | Francorchamps — sport   | WLTC Class 3   |
|:-----------------|:-------|:----------------------|:------------------------|:---------------|
| Petrol           | 6.10   | 9.18                  | 13.95                   | 6.65           |
| Battery electric | —      | —                     | —                       | —              |
| Full hybrid      | 4.83   | 6.77                  | 12.40                   | 5.89           |
| Plug-in hybrid   | 1.99   | 1.28                  | 5.66                    | 2.08           |

### CO2 with electricity at 250 g/kWh (g/km)

|                  |   NEDC |   Francorchamps — eco |   Francorchamps — sport |   WLTC Class 3 |
|:-----------------|-------:|----------------------:|------------------------:|---------------:|
| Petrol           |  134.8 |                 203   |                   308.3 |          146.9 |
| Battery electric |   37.3 |                  51.2 |                    95.9 |           44.5 |
| Full hybrid      |  106.7 |                 149.7 |                   274.2 |          130.1 |
| Plug-in hybrid   |   66.4 |                  69.5 |                   171.9 |           67.8 |

### Steps the engine cannot deliver (74 kW full-load curve)

|                | NEDC                 | Francorchamps — eco   | Francorchamps — sport   | WLTC Class 3            |
|:---------------|:---------------------|:----------------------|:------------------------|:------------------------|
| Petrol         | —                    | 5 of 31, up to 38 kW  | 16 of 31, up to 90 kW   | 16 of 1800, up to 9 kW  |
| Full hybrid    | 1 of 104, up to 1 kW | 2 of 31, up to 15 kW  | 8 of 31, up to 70 kW    | 27 of 1800, up to 11 kW |
| Plug-in hybrid | 1 of 104, up to 2 kW | 2 of 31, up to 12 kW  | 6 of 31, up to 61 kW    | 32 of 1800, up to 13 kW |

## stage B

### Fuel (l/100 km)

|                  | NEDC   | Francorchamps — eco   | Francorchamps — sport   | WLTC Class 3   |
|:-----------------|:-------|:----------------------|:------------------------|:---------------|
| Petrol           | 6.10   | 9.18                  | 13.95                   | 6.65           |
| Battery electric | —      | —                     | —                       | —              |
| Full hybrid      | 4.78   | 7.89                  | 13.78                   | 5.01           |
| Plug-in hybrid   | 1.99   | 1.40                  | 6.13                    | 2.09           |

### CO2 with electricity at 250 g/kWh (g/km)

|                  |   NEDC |   Francorchamps — eco |   Francorchamps — sport |   WLTC Class 3 |
|:-----------------|-------:|----------------------:|------------------------:|---------------:|
| Petrol           |  134.8 |                 203   |                   308.3 |          146.9 |
| Battery electric |   37.3 |                  51.2 |                    95.9 |           44.5 |
| Full hybrid      |  105.7 |                 174.4 |                   304.6 |          110.8 |
| Plug-in hybrid   |   66.4 |                  72.2 |                   182.2 |           68.2 |

### Steps the engine cannot deliver (74 kW full-load curve)

|                | NEDC                 | Francorchamps — eco   | Francorchamps — sport   | WLTC Class 3            |
|:---------------|:---------------------|:----------------------|:------------------------|:------------------------|
| Petrol         | —                    | 5 of 31, up to 38 kW  | 16 of 31, up to 90 kW   | 16 of 1800, up to 9 kW  |
| Full hybrid    | —                    | 2 of 31, up to 15 kW  | 13 of 31, up to 70 kW   | 26 of 1800, up to 11 kW |
| Plug-in hybrid | 1 of 104, up to 2 kW | 2 of 31, up to 12 kW  | 6 of 31, up to 61 kW    | 32 of 1800, up to 13 kW |

## assignment

### Fuel (l/100 km)

|                  | NEDC   | Francorchamps — eco   | Francorchamps — sport   | WLTC Class 3   |
|:-----------------|:-------|:----------------------|:------------------------|:---------------|
| Petrol           | 5.82   | 8.60                  | 13.39                   | 6.30           |
| Battery electric | —      | —                     | —                       | —              |
| Full hybrid      | 4.29   | 6.98                  | 12.02                   | 4.55           |
| Plug-in hybrid   | 1.23   | 0.95                  | 6.22                    | 1.28           |

### CO2 with electricity at 250 g/kWh (g/km)

|                  |   NEDC |   Francorchamps — eco |   Francorchamps — sport |   WLTC Class 3 |
|:-----------------|-------:|----------------------:|------------------------:|---------------:|
| Petrol           |  134.1 |                 198.1 |                   308.2 |          145.1 |
| Battery electric |   34.2 |                  46.3 |                    86.1 |           41.2 |
| Full hybrid      |   98.7 |                 160.7 |                   276.8 |          104.7 |
| Plug-in hybrid   |   55.7 |                  63.7 |                   185.5 |           56.7 |

### Steps the engine cannot deliver (74 kW full-load curve)

|                | NEDC                 | Francorchamps — eco   | Francorchamps — sport   | WLTC Class 3            |
|:---------------|:---------------------|:----------------------|:------------------------|:------------------------|
| Petrol         | —                    | 5 of 31, up to 37 kW  | 15 of 31, up to 88 kW   | 16 of 1800, up to 9 kW  |
| Full hybrid    | 1 of 104, up to 1 kW | 4 of 31, up to 19 kW  | 12 of 31, up to 74 kW   | 25 of 1800, up to 11 kW |
| Plug-in hybrid | 1 of 104, up to 2 kW | 1 of 31, up to 6 kW   | 6 of 31, up to 63 kW    | 35 of 1800, up to 13 kW |

## What each change moved

- **Cited constants: about −17 % CO2 for every engine.** Petrol at 44.3 MJ/kg instead of the sheets' 39.6 cuts fuel 10.6 %. CO2 at 3.07 g per g of fuel, instead of the sheets' 3.32 (2392 g/l at 720 kg/m³), cuts a further 7.6 %. NEDC petrol moves less (−14.8 %) because it also changes from NEDC's prescribed shift speeds to the common ones, worth +1.9 %.
- **The electric car does not move until the vehicle changes.** The regen cap stays (removing it would credit braking power far beyond any motor), and the 250 g/kWh grid factor was already applied in the comparison table.
- **The sheets' hybrid efficiency shortcut hides fuel on Spa.** The sheets read the engine's efficiency at the whole demand, even when the motor supplies most of it, and a high reading flatters the engine. Reading it at the engine's own share adds 16.5 % fuel on the eco lap and 13.5 % on the sport lap. NEDC and WLTC barely move: there, the motor either covers the demand entirely or the engine covers most of it.
- **Charge-sustaining pays on WLTC, not on Spa.** Compared with the sheets' rule with the efficiency read honestly, holding the battery in its band:
  - saves 15.5 % on WLTC (5.93 → 5.01 l/100 km) and 1 % on NEDC;
  - is level on the eco lap and saves 2 % on the sport lap.
  
  Against the sheets' rule as supplied, the eco lap is +16.5 %, but that is the efficiency shortcut above, not the strategy. On WLTC the band loads the engine towards its best point and stores the surplus for the urban phases. A 7 km lap of corners and climbs has little light-load driving for the stored energy to replace. Against the same rule starting at 60 % (the fair start), the band saves 25 % on NEDC, 23 % on WLTC and 8 % on the eco lap.
- **The assignment sheet's vehicles favour the electric car and the plug-in hybrid.** The electric car is 237 kg lighter (22 kWh instead of 50) and emits 7–10 % less. The plug-in hybrid's 15 kWh battery nearly doubles its electric range on NEDC and WLTC, which cuts its weighted CO2 by 16 %. The petrol car barely changes: its 74 kW rating only rescales the efficiency curve.

## Feasibility

No supplied sheet checks whether the engine can deliver what the trace asks. The model does, against the assignment sheet's full-load curve: power rising linearly to 5000 rpm, then 74 kW to 6000 rpm. This check does not change the figures above. Clipping the power would only make an infeasible lap look frugal, so the shortfall is reported instead.

- **The sport lap is not the assignment's sport case.** The petrol car falls short on 16 of 31 steps, by up to 90 kW. The assignment wants the sport speed profile limited by engine power, with the braking points found by iteration. That needs the profile generator (the Phase 2 stretch, or direction 5).
- **Even the eco lap is infeasible on 5 of 31 steps,** by up to 38 kW. The sheets choose the gear from speed alone, so the car accelerates in 4th at 2580 rpm, where the curve allows only ~38 kW. A driver would shift down, so this is the shift rule as much as the engine.
- **WLTC is nearly feasible:** 16 of 1800 steps, by up to 9 kW, all low-rpm pulls in a high gear.

## What is still a modelling choice

- **The hybrids' battery has no losses,** in either direction. Neither does the motor in the hybrid sheets; only the electric car has a motor map.
- **Grid CO2 is per kWh drawn from the battery,** with no charger loss (no source yet; `docs/sources.md`).
- **Gear choice is by speed alone,** which is behind the eco lap's infeasibility above.
- **The assignment sheet gives no rolling resistance and no efficiency-curve shape.** The workbooks' values are kept (`pwt/model/fleet.py`).
