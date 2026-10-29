# Phase 1 results — the 4 × 4 checkpoint

Every powertrain on every cycle, computed by Nelis's own spreadsheet model. Nothing is corrected yet: these are the baseline the Python model must reproduce before Phase 2 changes anything. Regenerate with `python -m pwt.checkpoint` (needs LibreOffice for the last table).

**Where the figures come from**

- **NEDC and Francorchamps:** the supplied workbooks' cached values, except the plug-in hybrid on NEDC.
- **WLTC Class 3:** `data/derived/WLTC3 *.xlsx`. Each one is a supplied NEDC workbook (`33`, `32`, `35`, `34`) with WLTC's 1801-second trace in place of NEDC's. Rebuilding each template on its own trace reproduces its supplied totals to 1e-9 (`tests/test_derived.py`), so the fill-down is faithful.
- **Plug-in hybrid on NEDC and WLTC:** a charge-depleting run (start at 98 %, as `34`) and a charge-sustaining run (start at the 23 % engine threshold), combined as UN ECE R101 does for NEDC: $C = (D_e C_1 + 25\,C_2)/(D_e + 25)$, where $D_e$ is the electric range on the 75 % usable charge. The same weighting is applied to WLTC for comparability; real WLTP uses utility factors instead.

## The tables

### Fuel (l/100 km)

|                  | NEDC   | Francorchamps — eco   | Francorchamps — sport   | WLTC Class 3   |
|:-----------------|:-------|:----------------------|:------------------------|:---------------|
| Petrol           | 6.62   | 10.27                 | 15.60                   | 7.43           |
| Battery electric | —      | —                     | —                       | —              |
| Full hybrid      | 5.40   | 7.58                  | 13.87                   | 6.58           |
| Plug-in hybrid   | 2.22   | 1.43                  | 6.34                    | 2.32           |

### Electricity from the battery (kWh/100 km)

|                  | NEDC   | Francorchamps — eco   | Francorchamps — sport   | WLTC Class 3   |
|:-----------------|:-------|:----------------------|:------------------------|:---------------|
| Petrol           | —      | —                     | —                       | —              |
| Battery electric | 14.9   | 20.5                  | 38.4                    | 17.8           |
| Full hybrid      | —      | —                     | —                       | —              |
| Plug-in hybrid   | 9.0    | 16.5                  | 18.7                    | 8.8            |

### CO2 as the sheets report it (g/km)

|                  |   NEDC |   Francorchamps — eco |   Francorchamps — sport |   WLTC Class 3 |
|:-----------------|-------:|----------------------:|------------------------:|---------------:|
| Petrol           |  158.3 |                 245.7 |                   373.1 |          177.8 |
| Battery electric |   65.6 |                  47.1 |                    87.1 |           78.3 |
| Full hybrid      |  129.1 |                 181.2 |                   331.9 |          157.5 |
| Plug-in hybrid   |   53.2 |                  34.2 |                   151.5 |           55.6 |

### CO2 with grid electricity at the EU average, 250 g/kWh (g/km)

|                  |   NEDC |   Francorchamps — eco |   Francorchamps — sport |   WLTC Class 3 |
|:-----------------|-------:|----------------------:|------------------------:|---------------:|
| Petrol           |  158.3 |                 245.7 |                   373.1 |          177.8 |
| Battery electric |   37.3 |                  51.2 |                    95.9 |           44.5 |
| Full hybrid      |  129.1 |                 181.2 |                   331.9 |          157.5 |
| Plug-in hybrid   |   75.7 |                  75.4 |                   198.3 |           77.5 |

### Plug-in hybrid detail

| cycle        | run           |   l/100 km |   kWh/100 km |   g CO2/km (fuel) |   g CO2/km (+ EU grid) | source                                                                          |
|:-------------|:--------------|-----------:|-------------:|------------------:|-----------------------:|:--------------------------------------------------------------------------------|
| NEDC         | R101 weighted |       2.22 |          9   |              53.2 |                   75.7 | R101 weighting of NEDC PHYBRID CD.xlsx and NEDC PHYBRID CS.xlsx, De = 42.0 km   |
| NEDC         | cd            |       0    |         14.3 |               0   |                   35.7 | NEDC PHYBRID CD.xlsx                                                            |
| NEDC         | cs            |       5.96 |          0.1 |             142.7 |                  142.9 | NEDC PHYBRID CS.xlsx                                                            |
| WLTC Class 3 | R101 weighted |       2.32 |          8.8 |              55.6 |                   77.5 | R101 weighting of WLTC3 PHYBRID CD.xlsx and WLTC3 PHYBRID CS.xlsx, De = 42.4 km |
| WLTC Class 3 | cd            |       0.14 |         14.1 |               3.3 |                   38.6 | WLTC3 PHYBRID CD.xlsx                                                           |
| WLTC Class 3 | cs            |       6.04 |         -0.4 |             144.4 |                  143.5 | WLTC3 PHYBRID CS.xlsx                                                           |

### What each inconsistency is worth

| change                                             | run                                          | l/100 km        | g CO2/km      | effect   | note                                           |
|:---------------------------------------------------|:---------------------------------------------|:----------------|:--------------|:---------|:-----------------------------------------------|
| Vehicle mass 1300 → 1280 kg (sheet value)          | 07 SPA Franco PETROL car ECO Driving.xlsx    | 10.273 → 10.174 | 245.7 → 243.4 | -1.0 %   |                                                |
| Engine max power 85 → 74 kW (sheet value)          | 07 SPA Franco PETROL car ECO Driving.xlsx    | 10.273 → 10.126 | 245.7 → 242.2 | -1.4 %   | Only rescales the efficiency curve's load axis |
| Fuel density 720 → 750 kg/m³ (sheet value)         | 07 SPA Franco PETROL car ECO Driving.xlsx    | 10.273 → 9.862  | 245.7 → 235.9 | -4.0 %   | CO2 is per litre, so it moves too              |
| Hybrid's efficiency curve → petrol's               | 10 SPA Franco HYBRID engine ECO Driving.xlsx | 7.575 → 7.464   | 181.2 → 178.5 | -1.5 %   | Atkinson curve costs the hybrid this much      |
| Petrol + 87.5 kg (hybrid's extra mass)             | 07 SPA Franco PETROL car ECO Driving.xlsx    | 10.273 → 10.690 | 245.7 → 255.7 | +4.1 %   | Extra mass costs the hybrid this much          |
| NEDC petrol effective mass → Francorchamps formula | 33 NEDC PETROL Car.xlsx                      | 6.617 → 6.607   | 158.3 → 158.0 | -0.2 %   |                                                |
| NEDC petrol shift speeds → 35/57/82/115 km/h       | 33 NEDC PETROL Car.xlsx                      | 6.617 → 6.745   | 158.3 → 161.3 | +1.9 %   |                                                |

## Reading the tables

- **The supplied NEDC plug-in hybrid was not missing data.** Its 0 l/100 km is the charge-depleting result: the 40 kW motor covers every NEDC demand and the battery ends at 78 %. What the file lacked was the electricity, 14.3 kWh/100 km, and a charge-sustaining run (5.96 l/100 km). Weighted, 2.22 l/100 km and 53 g/km, close to Nelis's ~3.0 l/100 km and ~70 g/km.
- **The WLTC electric car has a 50 kWh battery and weighs 1777 kg,** as every supplied EV file does. The assignment sheet's EV is 22 kWh and 1460 kg.
- **The WLTC petrol car shifts at 35/57/82/115 km/h,** the assignment sheet's calibration, not NEDC petrol's 18/38/50/70. That alone is worth +1.9 % on NEDC (last table), so NEDC → WLTC for petrol mixes the cycle with the shift strategy.
- **The full hybrid's WLTC phase figures exclude the end-of-cycle recharge.** The battery starts full, so the Low phase uses no fuel; the recharge line at the end buys the charge back at the engine's best efficiency and lands only in the total.
- **The sheets' own CO2 row uses different grid factors** (220 g/kWh Francorchamps EV, 440 NEDC EV, none for the plug-in hybrid). The EU-grid table puts every electric kWh at the assignment sheet's 250 g/kWh, without charger losses.

### Against Nelis's reference table (slides 14–15 of `08`)

| | Nelis NEDC | Ours NEDC | Nelis Francorchamps | Ours eco / sport |
|---|---|---|---|---|
| Petrol, l/100 km | ~9.0 ("old" engine) | 6.62 ("downsized") | ~15 | 10.27 / 15.60 |
| Electric, kWh/100 km | ~14 | 14.9 | ~30 | 20.5 / 38.4 |
| Full hybrid, l/100 km | ~8.0 | 5.40 | ~10.0 | 7.58 / 13.87 |
| Plug-in hybrid, l/100 km | ~3.0 | 2.22 (R101) | ~5.5 | 1.43 / 6.34 |

His Francorchamps column sits between our eco and sport laps, and his NEDC petrol figure is for the "old" efficiency curve that `33` keeps in column D. He calls these "examples of typical consumptions", so the match is order-of-magnitude, not exact.

## What each finding in the brief is worth

From the last table, measured in Nelis's sheets by changing one cell and recalculating:

- **Hybrid vs petrol is not confounded the way the brief feared.** Both differences cost the hybrid fuel. The Atkinson curve is worth +1.5 % and the extra 87.5 kg +4.1 %, yet the hybrid still uses 26 % less than petrol on the eco lap. The whole saving comes from electric drive and regenerative braking.
- **Fuel density is the largest sheet-vs-assignment difference: −4.0 %** on fuel and CO2 together, because CO2 is computed per litre. At 720 kg/m³ the sheets emit 3.32 g CO2 per gram of petrol, against 3.19 at 750.
- **The 0.0909 g/Wh fuel energy** (39.6 MJ/kg) scales fuel linearly. At a typical 43 MJ/kg (needs a source) every fuel figure would fall by about 8 %.
- **PHEV grid electricity** adds 41 g/km on the eco lap at 250 g/kWh, doubling its reported 34 g/km. At France's 73 g/kWh it adds 12 g/km.
- **Engine capability is not checked.** On the sport lap the petrol car is asked for up to 127 kW and 480 Nm from a 74 kW, 146 Nm engine. The sport speed profile has to be rebuilt from engine power before sport figures mean anything (Phase 2).
- **Effective-mass formula (−0.2 %) and mass 1300 vs 1280 kg (−1.0 %)** are small.

