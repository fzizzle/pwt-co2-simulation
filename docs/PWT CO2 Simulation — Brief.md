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
**Plan:** [[PWT CO2 Simulation — Plan]] · **Log:** [[PWT CO2 Simulation Log]]

## What the project is

A spreadsheet model computes the fuel, energy and CO2 of a car driven over a speed trace. Each row is one step of the trace. The model resolves rolling, grade and aerodynamic resistance plus inertia (with a per-gear rotating-mass factor), turns the result into wheel power, then into engine or motor power through a drivetrain efficiency and an efficiency curve, and finally into litres, Wh and g CO2/km.

Nelis supplies the model for four powertrains — petrol, battery-electric, full hybrid, plug-in hybrid — on two cycles: a 7 km lap of Spa-Francorchamps (eco and sport driving) and NEDC. The group takes this model, extends it, and presents its own analysis.

## Goals

1. **Understand the model** well enough to explain every column: forces → power → energy → fuel → CO2.
2. **Compare technologies on the same cycle** — urban (NEDC), rural eco and sport (Francorchamps), and **highway, which the brief marks "must be done"**. No highway file exists yet; the WLTC Class 3 trace supplied has one.
3. **Run 2–3 short analyses, or one complete one**, on how a parameter or modelling choice moves the result.
4. **Present it:** 3–4 slides introducing the simulation, 10–15 slides of analysis, 20 minutes.

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
> - **Three titles are wrong:** petrol SPORT reads "ECO", hybrid SPORT reads "ECO DRIVING", NEDC PHEV reads "FRANCORCHAMPS". NEDC PHEV returns 0 l/100 km — unfinished.
> - **Fuel energy uses 0.0909 g/Wh,** which implies a heating value of 39.6 MJ/kg. Typical petrol values are higher (inference; needs a source), so the model likely overstates fuel slightly.

## Open questions for Nelis

- Presentation date, and whether the TD3 exam (Fri 4 Dec) is separate from the project.
- Weighting of project vs exam.
- Are the groups assigned, and can we choose our analysis freely?
- Which grid CO2 factor he expects — the EV files use 220 g/kWh.

## Sources

| Source | Checked |
|---|---|
| `30 Examples of personal analysis.docx` — rules and analysis list | Read in full |
| `08 Hybrid vehicle Organigram and results.pptx` — hybrid model logic, reference results | Read in full |
| `06`–`15`, `31`–`36` workbooks | Formulas read; totals taken from cached values, not recomputed |
| `11 Good trajectory speed.pdf` — cornering speed on the ideal line | 52 → 67 km/h recomputed ✓ |
| [[PWT MOC]] — dates, TD structure | Vault |
