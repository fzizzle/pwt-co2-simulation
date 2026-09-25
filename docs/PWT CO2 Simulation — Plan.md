---
type: project
tags: [project]
status: active
course: MESISI471226
repo: https://github.com/fzizzle/pwt-co2-simulation
dashboard: https://pwt-co2-simulation-iihscdva9b3woycsyuk7dp.streamlit.app
---

# PWT CO2 Simulation — Plan

**Goal:** Present a 20-minute group analysis that compares four powertrains on urban, rural and highway cycles and goes further than the supplied spreadsheets in one area.
**Brief:** [[PWT CO2 Simulation — Brief]] · **Log:** [[PWT CO2 Simulation Log]]

> [!info] Dates this plan works back from
> - **Presentation date: unknown.** TD2 (Mon 30 Nov) is "answers to questions before submission of projects", so the plan freezes results by then.
> - **w48 is taken:** Engineering Ethics and Probabilistic Methods exams on 25–26 Nov. Slides must exist before then.
> - **w49 is taken:** BSA, PWT exam (Fri 4 Dec 17:00) and SUSI all land 3–4 Dec.
> - **No PWT teaching between today (L3) and TD1 on Wed 4 Nov.** That gap is the working window.

---

## Directions

Ranked. The first is compulsory; pick one of 2–4 as the group's headline analysis, and optionally one of 5–6 as a short second.

| # | Direction | What it adds | Effort (group) | Marks ceiling |
|---|---|---|---|---|
| 1 | **Highway cycle for all four powertrains** (WLTC Class 3, extra-high phase) | The comparison the brief says must be done | 6–8 h | Required |
| 2 | **Port the model to Python and give the hybrids real decisions** — charge-sustaining full hybrid, PHEV with grid and fuel energy separated, well-to-wheel CO2 | Fixes the three hybrid flaws in the brief; answers Nelis's own "a programming language is mandatory" | 20–25 h | Highest |
| 3 | **Size the hybrid**: sweep battery kWh and motor kW, including the mass each adds | A clear optimum curve per cycle; a strong single figure | 10–12 h (≈4 h on top of 2) | High |
| 4 | **Sensitivity (tornado) study**: mass, SCx, rolling resistance, gear ratios, engine efficiency curve (NA vs Atkinson vs EcoBoost) | Ranks which parameter matters most per technology and cycle | 8–10 h (≈3 h on top of 2) | Medium–high |
| 5 | **Cornering speed → sport lap**: tyre grip and spoiler downforce raise corner speed; feed that back into the Francorchamps sport trace | Links vehicle dynamics (L4) to CO2; uses the trajectory sheet | 8 h | Medium |
| 6 | **Technology review**: hydrogen, e-fuels, bio-fuels | Low risk, no modelling; L6 (H2) is only on 30 Nov | 5 h | Low |

> [!tip] Recommendation
> **1 + 2, with 3 or 4 as the finished analysis.** Once the model runs in Python, 3 and 4 are loops over parameters, not new spreadsheets. With three people: one builds the highway files (1), one ports and extends the model (2), one owns the sweep and the figures (3 or 4). Direction 2 suits you — it is a programming job with a mechanics check on every line.

---

## Phase 0 — set up (by Fri 2 Oct)

- [ ] **Form the group of three** and agree the directions above. *20 min*
- [ ] **Email Nelis the four open questions** in the brief. *15 min*
- [ ] **Copy the 22 simulation files** into a project folder outside the vault; put its path in `repo:`. *5 min*

## Phase 1 — reproduce and audit (by Fri 16 Oct)

- [ ] **Walk the petrol ECO workbook column by column** and write each formula as an equation in the log. *60 min*
- [ ] **Check the corrections in the brief** against the files and note each one's effect on the headline figure. *45 min*
- [ ] **Recompute the rotating-mass factor** $m_\text{eff} = m_\text{driver} + m_\text{veh}(1.04 + 0.0025\,i^2)$ for one gear by hand. *10 min*
- [ ] **Build the highway workbooks** (direction 1): paste the WLTC Class 3 trace into the four model sheets, split results by phase (low/medium/high/extra-high). *6–8 h, split four ways*
- [ ] **Finish the NEDC PHEV file,** which returns 0 l/100 km. *60–90 min*

**Checkpoint:** a 4 × 4 table — petrol, EV, HEV, PHEV × NEDC, Francorchamps eco, sport, WLTC — in l/100 km, kWh/100 km and g CO2/km. Compare with Nelis's reference table (slide 14–15).

## Phase 2 — Python model (direction 2, by Tue 3 Nov)

Repo outside the vault. Python 3, `numpy`, `pandas`, `matplotlib`, `pytest`.

| File | Responsibility |
|---|---|
| `cycles.py` | Load a trace (time or distance, speed, altitude) from each workbook into a DataFrame |
| `vehicle.py` | Vehicle parameters as a dataclass, one instance per supplied workbook |
| `road_load.py` | Forces, wheel power, per-gear effective mass, gear choice |
| `powertrains.py` | `petrol()`, `electric()`, `hybrid()`, `plugin()` — each returns per-step and total energy, fuel, CO2 |
| `tests/test_against_excel.py` | Golden tests: each function must reproduce its workbook's totals |

- [ ] **Write the golden test first:** petrol ECO must return 10.273 l/100 km and 245.7 g/km (workbook `07`, cached values). Run it; it fails. *20 min*
- [ ] **Port road load and the petrol chain** until the test passes to 0.1 %. *2–3 h*
- [ ] **Add golden tests and ports for EV (`06`: 20 477 Wh/100 km), HEV (`10`: 7.575 l/100 km) and PHEV (`09`: 1.430 l/100 km).** *3–4 h*
- [ ] **Only now change behaviour,** one test per change:
  - full hybrid holds charge within a band (e.g. 50–70 %) by loading the engine towards its best-efficiency point, instead of the end-of-lap "fictive line" recharge; *3 h*
  - PHEV reports fuel and grid energy separately, and CO2 from both with a stated grid factor (the files use 220 g/kWh; give France and EU values with sources); *2 h*
  - fuel heating value and CO2 per litre taken from a cited source. *1 h*

**Checkpoint (bring to TD1, Wed 4 Nov):** the 4 × 4 table from Python matching Excel, plus the corrected hybrid rows beside the originals.

## Phase 3 — headline analysis (by Fri 20 Nov)

- [ ] **Direction 3:** sweep battery 1–20 kWh and motor 20–80 kW on each cycle; battery mass from the workbooks' own rule (160 Wh/kg plus fixed mass). Plot g CO2/km against battery size. *4 h*
- [ ] *or* **Direction 4:** ±10 % on each parameter, one at a time, per technology and cycle; tornado chart. *3 h*
- [ ] **Write the "influence of modelling" slide:** what each correction from Phase 1 changed. *1 h*

## Phase 4 — presentation (draft by Sun 22 Nov, rehearse Fri 27 Nov)

- [ ] **Slides 1–4:** the model — forces → power → energy → CO2, one diagram. *90 min*
- [ ] **Slides 5–7:** the 4 × 4 comparison, highway included. *90 min*
- [ ] **Slides 8–15:** the headline analysis, one claim per slide. *3 h*
- [ ] **Timed rehearsal,** 20 minutes, one speaker per section. *45 min*
- [ ] **TD2 (Mon 30 Nov):** last questions; freeze numbers.

---

## Self-check against the brief

| Brief requirement | Covered by |
|---|---|
| Group of 3, 20 min, 3–4 intro + 10–15 analysis slides | Phase 4 |
| 2–3 short analyses or one complete | Phase 3 plus the modelling slide |
| Highway "must be done" | Phase 1, direction 1 |
| Create NEDC hybrid files | Phase 1 |
| Recharge battery during the cycle; separate engine and grid energy | Phase 2 |
| Powertrain size | Direction 3 |
