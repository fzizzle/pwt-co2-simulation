# Agent instructions

These instructions are for coding agents working in this repo. Read `README.md` first: it covers the layout, the model and how the workbooks are read. This file adds the rules the README leaves implicit.

## This is graded coursework

This is a group project for PWT (ESILV, Marc Nelis), and each study is one student's personal graded work.

- **The analysis is the owner's.** You may write plumbing (variants, sweeps, tables, tests, figure code), check numbers and point out problems. Don't write a study's choices, interpretation, conclusions or slides unless the owner asks for that specifically. Even then, label the output as a draft for the owner to rewrite.
- **Follow the study's plan.** Plans are in `docs/superpowers/plans/`. Each plan's *Global Constraints* and *Baseline to check against* sections are binding. Tick off steps as they're done and update the plan's **Status** line.
- **Don't pick between options on the owner's behalf.** When a plan asks the owner to decide something (for example, how to define mass in Study B), ask them.

## Never change

- **`data/course-files/`:** the supplied files are read-only. Don't edit, rename or re-save them.
- **The shared baseline.** Use the assignment vehicles (`pwt.model.fleet`) in the `"storage losses"` scenario, the default for `pwt.sweep.sweep`. Don't change shared values in `pwt/model/` (constants, conventions, fleet, strategies) or any model step without the group agreeing. A new study goes in its own module (`pwt/<study>.py`) and builds variants with `dataclasses.replace`.
- **The golden numbers.** `tests/test_extract_golden.py` and `tests/test_model_golden.py` lock in the workbooks' totals. A change that moves them is a bug, unless the group has agreed to the change.

## Environment

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests
```

- Always run tools through `.venv/bin/`.
- You may install packages without asking. Add runtime dependencies to `requirements.txt`, which Streamlit Cloud installs. Dependencies used only for reports go in a separate file, such as `requirements-study-b.txt`.
- `python -m pwt.derived` and `tests/test_derived.py` need LibreOffice (`soffice`). Without it, that test is skipped. That's expected and doesn't count as a failure.

## Working practice

- **Work on a branch** named after the study (`study-b`, `study-c`, …) and open a pull request into `main`. Don't commit to `main` directly.
- **Write tests first.** At a minimum, test that the baseline in the plan reproduces (to one decimal), that expected rows are present with no gaps in CO2, and that the response has the expected physical direction.
- **Generate every figure and table from code** with a `python -m pwt.<module>` entry point, so they can be rebuilt if Nelis changes an assumption. Don't type numbers from a run into prose: format them from the data, or test the quoted values.
- **Label assumptions as assumptions.** Add any new external constant to `docs/sources.md` along with its source.
- **Respect feasibility.** `sweep` reports `short_steps` and `short_kw` when the engine can't deliver the power the trace demands. CO2 on an infeasible trace is a conditional result. Flag it rather than ranking on it silently.
- **Lookups go by label, never by cell address.** The workbooks don't share a layout (see "What the reader has to work around" in the README).

## The dashboard

The `dashboard/` folder is a Streamlit app for exploring the data internally. It is **not a deliverable**.

- Pages that show supplied workbooks show the figures exactly as reported: no unit conversion, recomputation, corrections or conclusions.
- The **Model**, **Track map**, **Hybrid sizing**, **CO₂ sensitivity** and **Cornering speed** pages show what `pwt.model` computes. A study may have its own page, provided it says it shows model output, reads the study's saved results instead of rerunning sweeps, and keeps the study's draft and provisional labels. Don't add model results or conclusions to the workbook pages.
- `pwt/` must not import Streamlit.
- After any change to `pwt/`, remind the user to reboot the Cloud app, because it doesn't re-import `pwt/` on push.

## Writing

- Follow the style of the existing docs: plain, short sentences, with units on every number (g CO2/km, l/100 km, kWh/100 km).
- Name cycles and powertrains with the keys in `pwt.sweep.CYCLES` and `pwt.catalog.POWERTRAIN_NAMES`.
