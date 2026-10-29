---
type: project
tags: [project]
status: active
course: MESISI471226
repo: https://github.com/fzizzle/pwt-co2-simulation
dashboard: https://pwt-co2-simulation-iihscdva9b3woycsyuk7dp.streamlit.app
---

# PWT CO2 Simulation — Brief

**Course:** [[PWT MOC|PWT — Powertrains]] · Marc Nelis · **Format:** group of 3, 20-minute presentation
**Plan:** [[PWT CO2 Simulation — Plan]] · **Log:** [[PWT CO2 Simulation Log]] · **Findings:** [[PWT CO2 Simulation — Findings]]

## What the project is

A spreadsheet model computes the fuel, energy and CO2 of a car driven over a speed trace. Each row is one step of the trace. The model resolves rolling, grade and aerodynamic resistance plus inertia (with a per-gear rotating-mass factor), turns the result into wheel power, then into engine or motor power through a drivetrain efficiency and an efficiency curve, and finally into litres, Wh and g CO2/km.

Nelis supplies the model for four powertrains — petrol, battery-electric, full hybrid, plug-in hybrid — on two cycles: a 7 km lap of Spa-Francorchamps (eco and sport driving) and NEDC. The group takes this model, extends it, and presents its own analysis.

## Goals

1. **Understand the model** well enough to explain every column: forces → power → energy → fuel → CO2.
2. **Compare technologies on the same cycle** — urban (NEDC), rural eco and sport (Francorchamps), and **highway, which the brief marks "must be done"**. No highway file exists yet; the WLTC Class 3 trace supplied has one.
3. **Run 2–3 short analyses, or one complete one**, on how a parameter or modelling choice moves the result.
4. **Present it:** 3–4 slides introducing the simulation, 10–15 slides of analysis, 20 minutes.
5. **One personal study per student.** The assignment sheet says the group writes the introduction together and each student adds a study of one parameter's influence, graded as their personal contribution. So three separate studies, not one shared headline.

## What the brief suggests analysing

| Strand | Suggested analyses |
|---|---|
| Petrol | driving cycle; engine efficiency (BSFC); tyres, drag, mass, gear ratios; vehicle class |
| Electric | driving cycle; battery energy, energy density, cooling; vehicle parameters |
| Hybrid / PHEV | build the missing NEDC files; size of motor and battery; **charge-sustaining full hybrid**; **separate engine energy from grid energy** in the PHEV |
| Comparison | all technologies on urban, rural and highway cycles |
| Vehicle dynamics | tyre stiffness and downforce vs cornering speed; Jeantaud steering; understeer gradient |
| Technology | hydrogen, bio- and e-fuels, compressed air — description, pros and cons |

> [!tip] Intuition — the lecturer's own verdict
> Nelis calls it "a calculation model, not a simulation model" and says a programming language is "mandatory … to introduce decisions in the model". The hybrid strand is where Excel runs out. That gap is the obvious place to earn marks.

> [!warning] Things in the supplied files to get right before quoting any number
> - **PHEV CO2 leaves out grid electricity.** The eco lap ends at 88 % charge and reports 34 g/km; the electricity used counts as zero.
> - **The hybrid "Energy to move the car" row nets regenerated energy against engine energy.** On the PHEV eco lap it goes negative (−5 285 Wh/100 km). The fuel figures are unaffected.
> - **Hybrid vs petrol changes two things at once:** a different efficiency curve (Atkinson vs "modern") and extra mass. A like-for-like comparison has to separate them.
> - **Three titles are wrong:** petrol SPORT reads "ECO", hybrid SPORT reads "ECO DRIVING", NEDC PHEV reads "FRANCORCHAMPS".
> - **NEDC PHEV returns 0 l/100 km, and that is what its formulas compute.** The 40 kW motor covers every demand on NEDC and the battery ends at 78 %, above the 23 % engine threshold, so the run is all-electric. What is missing is the electricity: battery energy and its CO2. Nelis's reference table expects ~3 l/100 km, which needs a charge-sustaining run as well.
> - **Fuel energy uses 0.0909 g/Wh** — the assignment sheet's own "1 kg ≈ 40 MJ or 11 kWh" (1/11 kWh/kg). Quote it as the course assumption. Typical petrol heating values are higher (~43 MJ/kg; inference, needs a source), so the model likely overstates fuel by up to ~8 %.
> - **The grid factor is not the same across files:** Francorchamps EV uses 220 g/kWh, NEDC EV 440 g/kWh. The assignment sheet gives 250 (EU average) and 73 (France), from the EEA.
> - **The workbooks are not one model.** Effective mass is $m_\text{total}\,k_i$ in NEDC petrol but $m_\text{driver} + m_\text{veh}\,k_i$ everywhere else; shift speeds are 18/38/50/70 km/h in NEDC petrol, 35/57/82/115 elsewhere; battery mass is $2E/80$, $2E/150$ or $2E/160$ depending on the file. Any cross-file comparison inherits these.

## What the assignment sheet adds

`1 Simulation of cars on driving cycles.pdf` is the original statement of the TD, inspired by Prof. P. Duysinx's ULiège project.

- **Two Spa cases.** Eco: 0–100 km/h in 20 s, braking ~0.4 g, 90 km/h cap, corners limited by tyre friction, corners 16–17 taken as straights. Sport: acceleration limited by the engine, braking ~0.6 g, top speed limited by engine power — "iterations needed to find the max speed point and braking point".
- **Ask:** criticise and improve the model, and say what the next step is.
- **Conversions:** petrol 0.75 kg/l, 2392 g CO2/l (diesel 2640, LPG 1665, CNG 2536 g/kg); electricity 250 g/kWh EU, 73 g/kWh France.

The sheet's vehicle data does not match the workbooks in five places:

| Parameter | Assignment sheet | Workbooks |
|---|---|---|
| Petrol vehicle mass | 1280 kg | 1300 kg (Francorchamps), 1280 kg (NEDC) |
| Engine maximum power | 74 kW at 6000 rpm | 85 000 W in the efficiency curve |
| Fuel density | 0.75 kg/l | 720 kg/m³ |
| Battery specific energy | 150 Wh/kg | 80, 150 or 160 Wh/kg, doubled for pack mass |
| Electric car battery and mass | 22 kWh, 1460 kg | 50 kWh, 1777 kg (battery 497 kg) |

## Open questions for Nelis

- Presentation date, and whether the TD3 exam (Fri 4 Dec) is separate from the project.
- Weighting of project vs exam.
- Are the groups assigned, and can we choose our analysis freely?
- Which grid CO2 factor he expects — his sheet gives 250 (EU) and 73 (France), but the EV files use 220 and 440 g/kWh.
- Which vehicle data is authoritative where the sheet and the workbooks disagree (mass, engine power, fuel density).

## Sources

| Source | Checked |
|---|---|
| `1 Simulation of cars on driving cycles.pdf` — assignment sheet: task, cases, vehicle data, formulas | Read in full |
| `30 Examples of personal analysis.docx` — rules and analysis list | Read in full |
| `08 Hybrid vehicle Organigram and results.pptx` — hybrid model logic, reference results | Read in full |
| `06`–`15`, `31`–`36` workbooks | Formulas read; totals taken from cached values, not recomputed |
| `11 Good trajectory speed.pdf` — cornering speed on the ideal line | 52 → 67 km/h recomputed ✓ |
| [[PWT MOC]] — dates, TD structure | Vault |
