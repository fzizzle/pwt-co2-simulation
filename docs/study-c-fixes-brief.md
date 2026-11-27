# Brief: Study C second-pass fixes

This brief is for a coding agent. It covers four fixes to the Study C draft in
[PR #10](https://github.com/fzizzle/pwt-co2-simulation/pull/10), branch `study-c-fixes`.

## Step 0: pull the latest version of the repo

Do this before anything else, so you work on the current code and not an old copy:

```sh
git fetch origin --prune
git checkout study-c-fixes
git pull origin study-c-fixes
```

If you have uncommitted changes, stop and ask before overwriting them. If `study-c-fixes`
doesn't exist locally yet, `git checkout study-c-fixes` creates it from `origin/study-c-fixes`.

## Before you start

Read these first. They are binding.

- `AGENTS.md`: the repo rules. Study C is graded coursework, and the analysis belongs to its owner. Write plumbing, tests and wording fixes only. Write no conclusions and no slides.
- `README.md`.
- The plan, `docs/superpowers/plans/2026-11-02-study-c-cornering.md`. Its *Global Constraints* and *Baseline to check against* sections are binding: the sport lap is 235.1 s, petrol is 385.2 g CO2/km, and the lap has 12 corners with a set speed.
- The draft, `docs/study-c-cornering.md`, and the code in `pwt/cornering.py`, `pwt/trackmap.py`, `tests/test_cornering.py` and `tests/test_cornering_report.py`.

Hard rules:

- Never edit `data/course-files/`.
- Never change `pwt/model/`.
- The golden tests must keep passing.
- Run every tool through `.venv/bin/`. If `.venv` is missing, run `python3 -m venv .venv` and then `.venv/bin/pip install -r requirements.txt`.
- Every number quoted in the doc is either formatted from data or checked by a test. Never type a number from a run into prose.

## Branch

Work on the existing branch `study-c-fixes` that Step 0 checked out, and don't create a new
one. Don't commit to `main`.

## Fix 1: a better estimate of the outline radii

**The problem.** `_outline_corner_matches` in `pwt/cornering.py` takes the smallest
circumradius through 3 neighbouring points, anywhere within ±120 m of each corner. The points
on the outline are 8 to 377 m apart. A minimum keeps any noisy kink, so the radii come out too
small: La Source reads 13.3 m, against the plan's rough 35 m. The spread of implied grip,
μ = 0.41 to 0.94, may therefore come from the method rather than from the circuit.

**The change:**

1. Resample the outline at an even spacing of 5 m before measuring anything.
2. For each corner, fit one circle by least squares to the resampled points within about
   ±40 m of its apex, and take that circle's radius. Make the half-window a named constant.
   Remove the minimum-of-3-points rule, or keep it only as a documented comparison.
3. Add a second radius for the driver's line: the fitted radius plus half a track width. Use
   `TRACK_HALF_WIDTH_M = 5.0`, labelled as an ASSUMPTION in the code, in the doc and in
   `docs/sources.md`.
4. Check the method on La Source. Find a published radius for it if you can, and add that to
   `docs/sources.md`. If you can't, compare with the plan's rough 35 m. Report what the method
   gives in either case.
5. Keep `radius_method="inferred"` as the default. The plan's baseline must reproduce
   unchanged.

**Tests first:**

- There is one radius per corner with a set speed, 12 in all, with no gaps.
- On a synthetic circle of known radius, sampled coarsely, the fitted radius comes back
  within 2 %.
- The driver's-line radius is never smaller than the fitted radius.
- The baseline is unchanged: 235.1 s and 385.2 g CO2/km for petrol.

**Rewrite the claim** in the Choices table of `docs/study-c-cornering.md`. It currently says
"so the template speeds are not at one uniform grip limit". Replace it with a sentence like
this, with X and Y formatted from `docs/study-c-corners.csv` and checked in
`tests/test_cornering_report.py`:

> On this coarse outline, the implied grip ranges from X to Y. This spread is within the
> method's uncertainty, so it can't show whether the template speeds sit at one grip limit.

If the new method still shows a large and consistent spread, describe it as evidence for the
owner to weigh in Task 2. Don't present it as a finding.

## Fix 2: the draft label

In `docs/study-c-cornering.md`, change the status line to:

> **Status: DRAFT (second pass by Gemini 4 Neon, first pass by Claude), for the owner to review.**

If your own pass changes the content, add your model's name to the label as a third pass.
Use the same wording in the PR description.

## Fix 3: the like-for-like rule

Under the spoiler-against-tyres comparison in `docs/study-c-cornering.md`, add:

> Matched on lap time, a provisional rule. Matching on the average corner speed or on one
> reference corner could change the result; the owner to choose.

Leave the code alone. `MATCH_RULES` already allows other rules to be added.

## Fix 4: check the sources

Open every link added to the Study C section of `docs/sources.md` and confirm that the quoted
figure is on the page:

- the Porsche 718 Cayman GT4: 122 kg of rear downforce;
- the Porsche 911 GT3 RS: 409 kg at 200 km/h;
- the Verus UCW wing: 500 lbf at 140 mph, 6.8 kg;
- the APR GTC-200, GTC-300 and GT-250 CFD pages;
- Kheirkhah et al., *Scientific Reports*, 2025.

If a link is dead or the figure isn't there, remove the claim or mark it as unverified. Don't
look for a replacement figure and quote it as if it were the original. List what you found in
the PR description.

## Finish

1. Regenerate the outputs with `.venv/bin/python -m pwt.cornering`, and then with
   `.venv/bin/python -m pwt.cornering --radius-method outline` if that writes separate files.
2. Run the full suite with `.venv/bin/python -m pytest tests`. Everything must pass. A test
   that needs LibreOffice may be skipped.
3. Tick any plan steps you complete in the plan file. Leave the Task 2 choice boxes unticked:
   they are the owner's.
4. Commit with clear messages, then **push to the branch**:

   ```sh
   git push origin study-c-fixes
   ```

   This updates PR #10. Don't merge it.
5. Update the PR #10 description. Include:
   - what changed in each fix;
   - the new range of radii and of implied grip, and how La Source compares with its
     reference value;
   - the result of checking each source;
   - the test result;
   - a reminder that the Streamlit Cloud app needs a reboot after merging, because
     `pwt/cornering.py` changed.

Report back with the PR URL, the head commit SHA, the test result, and anything you couldn't do
and why.
