# Study C: Cornering Speed Plan

**Goal:** Find how tyre grip and spoiler downforce change corner speed, and what that does to lap time and CO2 on the Spa sport lap, including the spoiler's drag.

**Architecture:** A new module, `pwt/cornering.py`, turns grip and downforce into corner speeds. These go into the existing lap generator through `generate(corner_speed=...)`, and `pwt.sweep.sweep` runs the cars on each new lap. No model code changes.

**Tech Stack:** Python, numpy, pandas and pytest, run through `.venv/bin/`. No spreadsheet software needed.

**Spec:** The study guide tab of the shared brief, `data/course-files/11 Good trajectory speed.pdf`, and `pwt/model/profile.py`.

**Deadline:** results by Fri 20 Nov, slide draft by Sun 22 Nov, numbers frozen at TD2, Mon 30 Nov.

**Status:** Not started. Owner to be agreed.

## Global Constraints

- **This is personal, graded work.** The code below is starter plumbing. The choices, analysis, conclusions and slides are the owner's.
- **Leave the baseline alone.** Use the assignment vehicles in the "storage losses" scenario, which `sweep` runs by default. Tell the group before changing a shared value or model step.
- **Use the sport lap.** The eco lap's 90 km/h cap hides many speed gains.
- **`data/course-files/` is read-only.**
- **Generate every figure from code,** so results can be refreshed if Nelis changes an assumption.
- **Label assumptions as assumptions.** Add any new sources to `docs/sources.md`.
- **Work on your own branch** and open a pull request into `main`.

## Baseline to check against

| Check | Value |
|---|---|
| Sport lap time | 235.1 s |
| Petrol on the sport lap | 385.2 g CO2/km |
| Corners with a set speed on the lap | 12 |

## Task 1: Set up

- [ ] Clone the repo, then create the environment and run the tests:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
```

Every test should pass.

- [ ] Create your branch:

```sh
git checkout -b study-c
```

## Task 2: Record your choices

Read `data/course-files/11 Good trajectory speed.pdf`. Then create `docs/study-c-cornering.md` and write down these choices before running anything:

- [ ] **What do the template corner speeds mean?** La Source is about 35 m in radius on the circuit outline and the sport template takes it at 40 km/h, which implies a grip of only about μ = 0.36. So the speeds may not be at the grip limit.
- [ ] **Reference grip μ₀:** which value will you assume, and why?
- [ ] **Corner radii:** infer them from each corner speed with R = v² / (μ₀ g), or estimate them from the coarse outline in `data/track/` using `pwt/trackmap.py`.
- [ ] **The spoiler:** which downforce area (SCz), added drag and added mass will you assume? Find a source for each if you can.

## Task 3: The grip rule

**Files:** create `pwt/cornering.py`.

Corner speed follows v = √(μ g R), so a change in grip scales speed by its square root.

- [ ] Start from this. It is tested.

```python
"""Study C: corner speeds from tyre grip and spoiler downforce."""

import math


def grip_speed(factor: float):
    """Scale every corner speed for `factor` times the grip."""
    return lambda s, v: v * math.sqrt(factor)
```

`generate` calls this with each corner's distance `s` (m) and template speed `v` (m/s), and uses the speed it returns.

- [ ] **Files:** create `tests/test_cornering.py`. Test that a factor of 1 reproduces the lap exactly:

```python
import numpy as np

from pwt.cornering import grip_speed
from pwt.model import fleet
from pwt.model.profile import generate


def test_unchanged_grip_reproduces_the_lap():
    car = fleet.petrol()
    lap = generate("sport", car, corner_speed=grip_speed(1))
    assert np.array_equal(lap.v_kph, generate("sport", car).v_kph)
```

## Task 4: Sweep grip

- [ ] Run a range of grip values, recording lap time and CO2:

```python
from pwt.model import fleet
from pwt.model.profile import generate, lap_time_s
from pwt.sweep import sweep

car = fleet.petrol()
lap = generate("sport", car, corner_speed=grip_speed(1.1))
print(lap_time_s(lap))
table = sweep({("petrol", "grip +10%"): car}, {"franco_sport_generated": lap})
print(table["co2_eu"])
```

- [ ] Plot lap time and CO2 against grip, as two charts rather than two scales on one.

## Task 5: The downforce rule

**Files:** modify `pwt/cornering.py` and `tests/test_cornering.py`.

Balancing cornering force against grip, with air pressing the car down, gives:

$$v^2 = \frac{\mu g R}{1 - \dfrac{\mu \rho \, SC_z \, R}{2m}}$$

- [ ] Add this starter. It infers R from the template speed, so replace that line if you chose another way in Task 2.

```python
G = 9.81


def downforce_speed(mu0: float, scz: float, mass: float, rho: float = 1.2):
    def corner(s, v):
        radius = v * v / (mu0 * G)
        spare = 1 - mu0 * rho * scz * radius / (2 * mass)
        if spare <= 0:
            return float("inf")  # downforce alone holds the car: no corner limit
        return math.sqrt(mu0 * G * radius / spare)
    return corner
```

- [ ] Test that `scz=0` reproduces the lap exactly. This holds with the starter code.
- [ ] Test that more downforce never makes a corner slower.

## Task 6: Add the spoiler's cost

- [ ] Change the car with `dataclasses.replace`: raise `cx` for the drag, and add any mass to `m_vehicle`.
- [ ] Use the changed car in **both** `generate` and `sweep`. Using it in only one overstates the benefit.

```python
from dataclasses import replace

spoiler = replace(car, cx=car.cx * DRAG_FACTOR, m_vehicle=car.m_vehicle + ADDED_KG)
lap = generate("sport", spoiler,
               corner_speed=downforce_speed(MU0, SCZ, spoiler.m_total))
table = sweep({("petrol", "spoiler"): spoiler}, {"franco_sport_generated": lap})
```

`DRAG_FACTOR`, `ADDED_KG`, `MU0` and `SCZ` are your choices from Task 2.

- [ ] Sweep several spoiler sizes, and compare with the same grip gain from tyres.

## Task 7: Compare the cars and explain

**Files:** modify `docs/study-c-cornering.md`.

- [ ] Run the other powertrains on the same laps with `fleet.electric()`, `fleet.hybrid(0.6)` and `fleet.plugin(0.98)`.
- [ ] Explain each main result through the trade-off: less braking and rebuilding of speed, against higher speeds and added drag.
- [ ] Check `short_steps` in the table for any step the engine cannot deliver.
- [ ] State these limits:
  - **Radii:** they are inferred or estimated from a coarse outline.
  - **One line:** the model has one line through each corner.
  - **Fixed braking:** the sport lap brakes at 0.6 g, and more grip may also allow harder braking.
  - **Fixed speeds elsewhere:** only the listed corners change.

The dashboard's **Track map** page shows where the car brakes on the real circuit.

## Task 8: Slides

- [ ] Make about 3 to 5 slides, with one clear claim on each.
- [ ] Close with the study's limits and the next step.
