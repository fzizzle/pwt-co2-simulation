# Study B: Sensitivity (Tornado) Plan

**Goal:** Find which vehicle factor moves CO2 most for each powertrain and cycle, and explain why. Change one factor by ±10 % at a time and rank the factors by how far CO2 swings.

**Architecture:** A new module, `pwt/sensitivity.py`, builds the vehicle variants and passes them to the existing `pwt.sweep.sweep`. No model code changes. Charts and the write-up sit on top of the table it returns.

**Tech Stack:** Python, pandas and pytest, run through `.venv/bin/`. No spreadsheet software needed.

**Spec:** The study guide tab of the shared brief, `docs/model-equations.md`, and `docs/phase-3-sizing.md` as an example of a finished study.

**Deadline:** results by Fri 20 Nov, slide draft by Sun 22 Nov, numbers frozen at TD2, Mon 30 Nov.

**Status:** Implemented on `study-b` using the owner's approved starter assumptions (3 November 2026). Results and five-slide draft are in `docs/study-b-sensitivity.md`; interpretation and slides await the owner's review.

Review follow-up is on the canonical `study-b-sensitivity` branch. The owner requested all
research extensions: these are separate from the approved fixed-trace study. See
`docs/study-b-review-response.md` for the feedback mapping and remaining model limitations.

## Global Constraints

- **This is personal, graded work.** The code below is starter plumbing. The choices, analysis, conclusions and slides are the owner's.
- **Leave the baseline alone.** Use the assignment vehicles in the "storage losses" scenario, which `sweep` runs by default. Tell the group before changing a shared value or model step.
- **`data/course-files/` is read-only.**
- **Generate every figure from code,** so results can be refreshed if Nelis changes an assumption.
- **Label assumptions as assumptions.** Add any new sources to `docs/sources.md`.
- **Work on your own branch** and open a pull request into `main`.

## Baseline to check against

g CO2/km with electricity at 250 g/kWh:

| Powertrain | NEDC | WLTC | Eco lap | Sport lap |
|---|---:|---:|---:|---:|
| `petrol` | 134.1 | 145.1 | 217.5 | 385.2 |
| `bev` | 38.0 | 45.8 | 56.5 | 132.2 |
| `hybrid` | 123.7 | 128.8 | 218.8 | 395.2 |
| `phev` | 67.9 | 73.6 | 113.0 | 293.0 |

## Task 1: Set up

- [x] Clone the repo, then create the environment and run the tests:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
```

Every test should pass.

- [x] Create your branch:

```sh
git checkout -b study-b
```

## Task 2: Record your choices

Create `docs/study-b-sensitivity.md` and write down these choices before running anything:

- [x] **Mass:** does ±10 % apply to the car alone (`m_vehicle`) or to total mass, including driver and battery?
- [x] **Engine efficiency:** will you scale its peak (`eta_max`), change the curve's shape (`a1`, `a2`, `a3`), or both? Workbooks `10`, `15` and `35` hold other curves.
- [x] **Laps:** keep the generated lap fixed, or regenerate it for each changed car? `cycles()` builds it once for the baseline petrol car. Regenerating means calling `generate` with the changed vehicle.

## Task 3: Build the variants

**Files:** create `pwt/sensitivity.py`.

- [x] Start from this. It is tested, and uses the simplest option for each choice in Task 2, so replace anything you decided differently.

```python
"""Study B: change one factor at a time and measure the CO2 swing."""

from dataclasses import replace

from pwt.model import fleet
from pwt.sweep import START_SOC

BASE = {
    "petrol": fleet.petrol(),
    "bev": fleet.electric(),
    "hybrid": fleet.hybrid(START_SOC["hybrid"]),
    "phev": fleet.plugin(START_SOC["phev"]),
}
FACTORS = {
    "mass": lambda v, k: replace(v, m_vehicle=v.m_vehicle * k),
    "drag": lambda v, k: replace(v, cx=v.cx * k),
    "rolling": lambda v, k: replace(v, f_roll=v.f_roll * k),
    "gears": lambda v, k: replace(v, ratios=tuple(r * k for r in v.ratios)),
    "engine": lambda v, k: replace(v, eta_max=v.eta_max * k),
}


def variants() -> dict:
    out = {}
    for powertrain, vehicle in BASE.items():
        out[(powertrain, "baseline", 1.0)] = vehicle
        for name, change in FACTORS.items():
            if name == "engine" and powertrain == "bev":
                continue  # an electric car has no engine
            for k in (0.9, 1.1):
                out[(powertrain, name, k)] = change(vehicle, k)
    return out
```

There should be 42 variants, which is 168 rows over the four cycles.

## Task 4: Run the sweep and compute the swings

**Files:** modify `pwt/sensitivity.py`.

- [x] Run the variants:

```python
from pwt.sweep import cycles, sweep

table = sweep(variants(), cycles()).rename(columns={"v1": "factor", "v2": "scale"})
```

- [x] Add a function that returns, for each powertrain, cycle and factor, CO2 at 0.9, CO2 at 1.1 and the swing between them.
- [x] Check the `baseline` rows against the table above. If they differ, stop and find out why.

## Task 5: Test it

**Files:** create `tests/test_sensitivity.py`.

- [x] Test that the `baseline` rows match the table above, to one decimal place.
- [x] Test that more mass gives more CO2 for every powertrain and cycle. This already holds with the starter code.
- [x] Test that every expected row is present and `co2_eu` has no gaps.
- [x] Run the tests:

```sh
.venv/bin/python -m pytest tests/test_sensitivity.py
```

## Task 6: Draw the tornado charts

- [x] Sort the factors by swing, largest on top, and draw a bar from the 0.9 result to the 1.1 result around the baseline.
- [x] Pick the most telling combinations. Do not show all of them.
- [x] Use the powertrain colours in `dashboard/theme.py`, name the axes in words, and state the cycle and car on each chart.

## Task 7: Explain the results

**Files:** modify `docs/study-b-sensitivity.md`.

- [x] For each main finding, explain the ranking through the forces and the energy chain. Numbers without a reason are not the finding.
- [x] Compare the rankings between powertrains and between cycles.
- [x] State these limits:
  - **Gear ratios:** engine efficiency depends only on power, not rpm, so ratios act mainly through rotating mass and the full-load limit.
  - **±10 % is not equally plausible** for every factor. Say where a realistic range would differ.
  - **Interactions:** changing one factor at a time misses combined effects.
  - **Feasibility:** check `short_steps` and `short_kw`, which show when a variant asks for more than the engine can give.

## Task 8: Slides

- [x] Make about 3 to 5 slides, with one clear claim on each.
- [x] Close with the study's limits and the next step.
