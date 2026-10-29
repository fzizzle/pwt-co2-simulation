# Python Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port Nelis's spreadsheet model to Python so that it reproduces every supplied and derived workbook exactly (stage A). Then change its behaviour one tested step at a time (stage B): engine capability, a charge-sustaining full hybrid, cited constants, and the assignment sheet's vehicles.

**Architecture:** A new subpackage, `pwt/model/`, that never imports from `dashboard/`. One vectorised road-load function shared by every powertrain. One step function per powertrain family (petrol, electric, hybrid, the last covering the plug-in too). Everything the twelve workbooks disagree on lives in a `Conventions` record, so "reproduce file X" and "harmonise" are the same code with different records. The existing reader (`pwt.workbook`) and the derived workbooks (`pwt.derived`) are the test oracle: each model run is compared with its workbook's totals and per-step columns.

**Tech Stack:** Python 3.14, numpy 2, pandas 3, pytest 9. Run everything through `.venv/bin/`. LibreOffice is needed only to rebuild `data/derived/`, not to run the model.

**Spec:** The Plan's Phase 2 section (`docs/PWT CO2 Simulation — Plan.md`), the equations in `docs/model-equations.md`, and the baseline in `docs/phase-1-results.md`.

**Deadline:** stage A by Sun 1 Nov, stage B by Tue 3 Nov, checkpoint at TD1, Wed 4 Nov.

**Status (Thu 29 Oct):** Tasks 1–10 done; the stretch is open. Where the build departed from this plan:

- **Hard-coded zeros** (the table below): they are not repeated timestamps. Most equal what the formula gives anyway. The one exception is sheet row 24's engine torque in the six Francorchamps engine files, a dead cell the golden test skips.
- **Task 7:** the harmonised convention keeps a 120 kW regeneration cap. Without it, the electric car's sport lap recovers braking power no motor could absorb. A conventional petrol engine idles at standstill; a hybrid's is off.
- **Task 8:** capability is reported as a shortfall beside the figures, not used to cut them.
- **Task 9:** the strategy receives the engine speed, so charging is capped at the full-load curve. `NelisStrategy(efficiency_at="engine")` was added to separate the sheets' efficiency shortcut from the strategy change.
- **Task 10:** the scenarios live in `pwt/phase2.py`, not `fleet.py`.

## Global Constraints

- **Reproduce before changing.** No stage B task starts until all 19 golden runs pass. Every stage B change is a new `Conventions` or `Vehicle` value, or a new strategy, reached by a flag. The workbook-exact path stays available and tested.
- **Golden tolerance:** totals and per-step columns to `rel=1e-6, abs=1e-9`. The derived workbooks match their templates to 1e-9, so a looser tolerance would hide porting errors.
- **Per-step results use the reader's column names** (`pwt.workbook.TRACE_ALIASES`: `total_force_n`, `engine_power_drivetrain_w`, `qfuel_l`, `batt_soc`, …), so a model frame and `Run.trace` compare column by column.
- **`data/course-files/` is read-only.** Never write there.
- **No conclusions in code comments.** Comments say what the sheet does and why the code mirrors it; findings go in `docs/`.
- **`pwt/` changes need an app reboot on Streamlit Cloud** (README). The dashboard does not import `pwt.model`, so this only matters if a task touches `pwt/workbook.py`.
- **Tests:** `.venv/bin/python -m pytest`. The suite is green at 113 tests before this plan starts.

## The golden runs

| Family | Runs |
|---|---|
| Petrol | `07` Franco eco, `13` Franco sport, `33` NEDC, `WLTC3 PETROL` |
| Electric | `06` Franco eco, `12` Franco sport, `32` NEDC, `WLTC3 ELECTRIC` |
| Full hybrid | `10` Franco eco, `15` Franco sport, `35` NEDC, `WLTC3 HYBRID` |
| Plug-in hybrid | `09` Franco eco, `14` Franco sport, `34` NEDC, `NEDC PHYBRID CD`/`CS`, `WLTC3 PHYBRID CD`/`CS` |

## What differs between the workbooks

This is what `Conventions` must encode. Source: `docs/model-equations.md`, plus `pwt.derived` for the derived files.

| Field | Values | Where |
|---|---|---|
| `trace_kind` | `"distance"`: points by distance, $\Delta t = \Delta s / \bar v$ · `"time"`: points by time, $\Delta s = v_i \Delta t$ | Franco · NEDC, WLTC |
| `shift_kph` | `(35, 57, 82, 115)` · `(18, 38, 50, 70)` · `None` (single ratio) | most · `33` only · EVs |
| `eff_mass` | `"outside"`: $m_d (+ m_\text{EM} + m_\text{batt}) + m_v k$ · `"total"`: $m\,k$ | most · `33` only |
| `idle_l_per_h` | 0.8 at standstill · `None` (engine off) | petrol, Franco hybrids · NEDC/WLTC hybrids |
| `regen` | `False` (negative power discarded) · `True` ($P_e = \eta_t P_w$) | petrol · hybrids, EVs |
| `regen_cap_w` | `-120_000` · `None` | Franco EVs · others |
| `soc_min` | 0.3 · 0.23 | full hybrids · plug-ins |
| `fictive_recharge` | `True` · `False` | `10`, `15`, `35`, `WLTC3 HYBRID` · plug-ins |
| `fuel_g_per_wh`, `co2_g_per_l` | 0.0909, 2392 | all |
| `grid_g_per_kwh` | 220 · 440 · `None` | Franco EVs · NEDC/WLTC EVs · hybrids |
| hard-coded cells | zeros equal to the formula's value; row 24 engine torque (dead cell) | all NEDC files; Francorchamps engine files |

---

### Task 1: Stop the reader keeping the NEDC electric summary row

`32 NEDC ELECTRIC.xlsx` ends its trace with a sums row that fills exactly 11 of 22 columns. `_STEP_FILL_THRESHOLD` keeps any row at 50 % or more, so this row survives as a 106th "step" at 1240 s with an 11.2 km step distance. `WLTC3 ELECTRIC.xlsx` inherits it. The dashboard plots it today.

**Files:**
- Modify: `pwt/workbook.py` (`_read_trace`)
- Modify: `README.md` (the `Traces (677 steps)` count, and the density-threshold bullet)
- Test: `tests/test_extract_golden.py`, `tests/test_derived.py`

- [ ] **Step 1: Measure before choosing the rule.** For all 12 supplied and 7 derived workbooks, list each kept row's fill fraction. If no real step sits at exactly 0.5, tightening to `filled <= 0.5 * len(values)` is enough. If one does, drop trailing rows whose `Time (s)` does not advance and whose distance is not a step's instead.
- [ ] **Step 2: Write the failing tests.** `read_run(course_file("32 NEDC ELECTRIC.xlsx")).trace` has 105 rows and `summary_rows_skipped == 1`; same for `WLTC3 ELECTRIC.xlsx` with 1801 rows.
- [ ] **Step 3: Implement, run the full suite,** and update any dashboard test that counted 677 trace steps (the new total is 676).
- [ ] **Step 4: Commit.**

### Task 2: Cycles, vehicles and conventions

**Files:**
- Create: `pwt/model/__init__.py`, `pwt/model/cycle.py`, `pwt/model/vehicle.py`, `pwt/model/conventions.py`
- Test: `tests/test_model_inputs.py`

**Interfaces:**
- `Cycle(t: np.ndarray | None, s: np.ndarray | None, v_kph: np.ndarray, z: np.ndarray, phase: np.ndarray | None)`, plus `Cycle.from_run(run: Run, kind: str) -> Cycle` and `Cycle.wltc_class3() -> Cycle`. A distance cycle carries `s`, a time cycle carries `t`.
- `Vehicle` (frozen dataclass): `wheel_diameter_m, ratios: tuple[float, ...], m_vehicle, m_driver, m_machine, m_battery, g, frontal_area, cx, rho_air, f_roll, eta_drivetrain, eta_max, a1, a2, a3, p_max_w, fuel_density, battery_wh, p_motor_w, motor_eff: tuple[float, float, float] | None, soc0`. Plus `Vehicle.from_run(run: Run) -> Vehicle`, reading `run.params` by `(label, unit)` key.
- `Conventions` (frozen dataclass) with the fields in the table above. `conventions_for(source_file: str) -> Conventions` holds the per-file table. `HARMONISED: Conventions` is added in Task 7.

- [ ] **Step 1: Write the failing tests.**
  - `Vehicle.from_run` on `07` gives `m_vehicle == 1300` and `ratios[0] == 12.526`.
  - `Vehicle.from_run` on `10` takes the efficiency curve from column C ("atkinson"), not B. The reader already keys on C.
  - `Cycle.from_run` on `33` has 105 points ending at 1240 s; `Cycle.wltc_class3()` has 1801 points.
  - `conventions_for` returns `shift_kph == (18, 38, 50, 70)` for `33` and `fictive_recharge` for `35`.
- [ ] **Step 2: Implement.** Battery mass is a formula in the sheets (`2*(C45/160)`, …). Read its cached value from `params`; don't re-derive it.
- [ ] **Step 3: Run, commit.**

### Task 3: Road load and the petrol chain

**Files:**
- Create: `pwt/model/road_load.py`, `pwt/model/petrol.py`, `pwt/model/totals.py`
- Create: `tests/test_model_golden.py` (the harness the next two tasks extend)

**Interfaces:**
- `road_load(cycle, vehicle, conv) -> pd.DataFrame` with columns `delta_time_s, delta_distance_m, speed_ms, gear, acceleration_ms2, wheel_speed_rads, engine_speed_rads, slope_rad, resistive_force_n, acceleration_force_n, total_force_n`. Row 0 is the initial state, as sheet row 3.
- `petrol(cycle, vehicle, conv) -> pd.DataFrame`: road load plus `engine_power_w, engine_power_drivetrain_w, engine_torque_nm, energy_wh, engine_efficiency, qfuel_g, qfuel_l, emission_g_co2`.
- `totals(frame, conv) -> dict[Key, float]`, keyed like `Run.totals`.

- [ ] **Step 1: Write the golden harness.** Parametrise over the golden runs. For each run: model frame vs `run.trace` on every shared column, and model totals vs `run.totals`, at the tolerance above. Start with the petrol four; mark the rest `xfail(strict=True)` so they flip to failures when they start passing.
- [ ] **Step 2: Implement the road load** from `docs/model-equations.md`, numpy throughout. The traps:
  - Wheel power uses the **mean** of $v_{i-1}$ and $v_i$; aero force uses $v_i$ alone.
  - Rolling resistance is $m g f_r$, not $m g f_r \cos\theta$.
  - At gear 0 the engine speed is idle: $800 \cdot 2\pi/60$ rad/s.
  - Where $\Delta t = 0$ the sheet hard-codes 0 instead of dividing.
- [ ] **Step 3: Implement the petrol chain** until `07`, `13`, `33` and `WLTC3 PETROL` pass. Idle fuel replaces the computed fuel at gear 0; it isn't added to it.
- [ ] **Step 4: Commit.**

### Task 4: Electric

**Files:** Create `pwt/model/electric.py`; extend the harness.

- [ ] **Step 1:** Remove the `xfail` marks on `06`, `12`, `32` and `WLTC3 ELECTRIC`.
- [ ] **Step 2: Implement.**
  - Motor efficiency $aN^2 + bN + c$ (%) uses this step's rpm in traction and the **previous** step's in regeneration.
  - Franco EVs cap regenerative power at −120 kW.
  - Torque in regeneration divides by the mean of two engine speeds (`06` column U).
  - CO2 uses the file's grid factor.
- [ ] **Step 3: Commit.**

### Task 5: Hybrid and plug-in hybrid

**Files:** Create `pwt/model/hybrid.py`; extend the harness.

- [ ] **Step 1:** Remove the `xfail` marks on the eleven hybrid runs.
- [ ] **Step 2: Implement the step loop.** It's sequential because each step's motor share depends on the previous state of charge. See *Hybrid columns* in `docs/model-equations.md`:
  - The 0.9 derate applies in traction only.
  - The regeneration branch tests `SOC <= 1`, not `< 1`.
  - Fuel exists only where engine energy is positive.
  - The fictive recharge row prices fuel at `eta_max`, and its energy uses `/11`, which equals the other rows' `0.0909`.
- [ ] **Step 3: Report the battery side,** as `pwt.derived` adds it: final SOC, battery Wh, Wh/100 km, and grid g/km at a given factor.
- [ ] **Step 4: Commit.** Stage A is done when the harness has no `xfail` left.

### Task 6: One entry point and the checkpoint from Python

**Files:** Modify `pwt/model/__init__.py`, `pwt/checkpoint.py`. Test: `tests/test_model_golden.py`.

**Interfaces:** `simulate(vehicle, cycle, conv) -> Result`, where `Result` holds `steps: pd.DataFrame`, `totals: dict`, `phases: dict[str, dict] | None` and `battery: dict | None`.

- [ ] **Step 1:** Test that `pwt.checkpoint.cells(source="model")` returns the same figures as `source="workbooks"` for all 16 headline cells.
- [ ] **Step 2: Implement** the `source` switch. The R101 weighting stays in `checkpoint.py`.
- [ ] **Step 3: Commit.**

### Task 7: Cited constants and a harmonised convention (stage B)

**Files:** Create `pwt/model/constants.py`, `docs/sources.md`; add `HARMONISED` to `conventions.py`.

- [ ] **Step 1: Write `docs/sources.md`.** For each constant, give its value and a source a reader can open: petrol heating value, density, CO2 per kg of fuel, EU and France grid factors (the assignment sheet cites the EEA for 250 and 73), and charger efficiency. Where no source is found, say so.
- [ ] **Step 2: Define `HARMONISED`.** Shift speeds 35/57/82/115, `eff_mass="outside"`, idle at standstill for every engine, regeneration with no cap, one grid factor. CO2 is computed per kg of fuel, not per litre, so density no longer moves CO2.
- [ ] **Step 3: Test** that the harmonised run of `07` differs from the workbook run only by the documented changes. Pin each delta.
- [ ] **Step 4: Commit.**

### Task 8: Engine capability (stage B)

**Files:** Modify `pwt/model/petrol.py`, `pwt/model/hybrid.py`; add a `capability: bool` flag to `Conventions`.

- [ ] **Step 1: Write the full-load curve.** Per the assignment sheet: power linear from 0 to 5000 rpm, plateau to 6000 rpm, 74 kW. Torque follows as $P/\omega$. Write it as a function of $\omega_e$.
- [ ] **Step 2: Write the failing tests.**
  - With `capability=True`, `07` and `13` report a positive `shortfall_w` on every step that exceeds the curve. Against the flat 74 kW limit alone, that is 1 step on the eco lap and 7 on the sport lap. The rpm-dependent curve can only add steps.
  - Delivered power never exceeds the curve.
- [ ] **Step 3: Implement** clipping and a `shortfall_w` column. For hybrids, clip only the engine's share. A shortfall means the imposed speed trace is infeasible: report it, don't hide it.
- [ ] **Step 4: Commit.**

### Task 9: Charge-sustaining full hybrid (stage B)

**Files:** Create `pwt/model/strategy.py`; modify `pwt/model/hybrid.py`.

**Interfaces:** `Strategy` protocol: `motor_share(state, demand_w, dt) -> float`. Implement `NelisStrategy`, today's rule (the default, so stage A stays green), and `SocBandStrategy(low=0.5, high=0.7)`.

- [ ] **Step 1: Write the failing tests.** With `SocBandStrategy` on `WLTC3 HYBRID`:
  - final SOC ends within ±2 % of the starting SOC, with no fictive recharge line;
  - SOC stays inside [0.45, 0.75] throughout;
  - fuel is reported beside the Nelis-strategy figure.
- [ ] **Step 2: Implement.** Below the band, the engine carries extra load towards its best-efficiency point, $x^* = -A_2 / 2A_1$ of $P_\text{max}$, and the surplus charges the battery. Above the band, the motor takes the demand up to its rating. Inside the band, use Nelis's rule.
- [ ] **Step 3: Commit.**

### Task 10: Assignment-sheet vehicles and the TD1 checkpoint

**Files:** Create `pwt/model/fleet.py`; write `docs/phase-2-results.md`.

- [ ] **Step 1: Define two vehicle sets.** The workbooks' set uses `Vehicle.from_run` on each file. The assignment-sheet set uses 1280 kg, 74 kW, 0.75 kg/l, 150 Wh/kg battery, EV 22 kWh and 1460 kg, HEV 20–30 kW, PHEV 40–50 kW / 10–20 kWh. Take the midpoint of each range, and note that choice in the doc.
- [ ] **Step 2: Generate the 4 × 4 table three ways.**
  - workbook-exact (must equal `docs/phase-1-results.md`);
  - harmonised;
  - harmonised + capability + charge-sustaining hybrid.
  
  Also show the sport lap's shortfall per step.
- [ ] **Step 3: Write `docs/phase-2-results.md`:** one paragraph per change, giving what it moved and by how much.
- [ ] **Step 4: Commit.**

### Stretch: generate the Francorchamps speed profiles

Only after Task 10, and only if no teammate has taken direction 5. Inputs: `02 Distances acceleration et freinage.xlsx`, `03`/`04` (empty lap templates with corner radii), `11 Good trajectory speed.pdf`.

- Corner speed $v = \sqrt{\mu g R}$.
- Eco: 0–100 km/h in 20 s, braking at 0.4 g, 90 km/h cap.
- Sport: acceleration from the full-load curve and gear, braking at 0.6 g. Iterate each straight: accelerate forward from the corner exit, brake backward from the next corner entry, and take the minimum. That is the "iterations needed" in the assignment.

Test it against `03`/`04`'s point layout and the supplied speeds where the supplied profile is feasible.
