# Category View Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear the findings from the whole-branch review of `category-view` so the branch can merge.

**Architecture:** Four tasks. Task 1 closes the two findings that let a reader misread a number on screen — it is the merge gate on its own. Task 2 fixes a count that is stated wrongly and the table that displays it. Task 3 removes the duplicate "inputs that differ" implementation the original plan meant to eliminate. Task 4 sweeps the cosmetic minors. Tasks are independent and can be reviewed separately.

**Tech Stack:** Python 3.14.7, Streamlit 1.64, Plotly 7.1, pandas 3.0, pytest 9.1. Run everything through `.venv/bin/`.

**Spec:** No separate spec. Findings are recorded verbatim in `.superpowers/sdd/2026-09-25-category-view/progress.md` under "Final whole-branch review".

**Branch:** `category-view`, currently 6 commits ahead of `main`, 90 tests green, working tree clean.

## Global Constraints

- **Pass-through only.** No unit conversion, no recomputation, no correcting the supplied data, no conclusions. Marking a known gap is annotation and is allowed; changing a value is not.
- **New code lives in `dashboard/`, never `pwt/`.** Community Cloud hot-reloads the app folder but keeps `pwt/` cached from process boot, so a name added to `pwt/` raises `ImportError` on the deployed app until it is rebooted.
- **Charts:** one y-axis per figure; adjacent-pairlist forms only; colour follows the powertrain, never rank; identity never carried by colour alone; render with `st.plotly_chart(fig, width="stretch", theme=None)` and call `style_axes`.
- `width="stretch"`, never the removed `use_container_width`.
- **Tests:** `.venv/bin/python -m pytest`. Green at 90 before this plan starts.
- **Verified facts this plan depends on** (re-checked against live data, not taken from the review):
  - `energy_wh_per_100km` for the petrol category is dtype `float64` holding `[nan, nan, nan]`. `pd.to_numeric(..., errors="coerce")` is therefore a **no-op** here — the Compare-page fix does not transfer. Only a Styler with `na_rep` produces the blank the caption promises.
  - `varying_parameters` reports `Distinct values = 4` for NEDC `effective mass gear 1 [kg]`, which holds 3 distinct present values and 1 missing.
  - `dashboard/pages/3_Compare.py` still builds its own diff at lines 94-101 using `np.isclose(a, b, rtol=1e-9, atol=0)`.
  - Page files are `2_Trace_Explorer.py`, `3_Compare.py`, `4_Data.py`, `5_Category_View.py`, so Category view currently sorts **last** in the sidebar.

---

### Task 1: Make the figures table honest (findings 1 and 2)

Two problems in one table. `Electrical energy (Wh/100 km)` prints the literal `None` for every petrol run while the caption beneath promises a blank; and the plug-in hybrid's NEDC row shows a bare `0.000`, which the Overview marks `0.000 — to be filled` because the lecturer confirmed that data is missing rather than measured. The figures table is the one remaining surface where a reader can copy that zero out as a result.

**Files:**
- Modify: `dashboard/layout.py` (add `mark_gap_value`)
- Modify: `dashboard/Overview.py` (use it instead of its local `mark_gaps`)
- Modify: `dashboard/pages/5_Category_View.py` (format the figures table)
- Test: `tests/test_category_view.py`

**Interfaces:**
- Produces: `layout.mark_gap_value(value: float | None, powertrain: str | None, cycle: str | None, *, decimals: int = 3) -> str` — formats a figure for display, returning `"—"` when absent and appending `" — to be filled"` when `run_notice` flags that run.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_category_view.py`:

```python
def test_figures_table_shows_a_dash_not_none_for_an_unreported_figure():
    """Petrol runs report no electrical energy; the cell must be blank, not the word None."""
    app = run("Powertrain", "petrol")
    table = app.dataframe[0].value
    column = "Electrical energy (Wh/100 km)"
    values = set(table[column].astype(str))
    assert "None" not in values
    assert values == {"—"}


def test_figures_table_marks_the_known_gap():
    """The NEDC plug-in hybrid has no fuel data; its zeros must not read as results."""
    app = run("Cycle", "nedc")
    table = app.dataframe[0].value.set_index("Run")
    assert table.loc["Plug-in hybrid", "CO₂ per km (g CO₂/km)"] == "0.000 — to be filled"
    # a complete run in the same table is untouched
    assert table.loc["Petrol", "CO₂ per km (g CO₂/km)"] == "158.288"


def test_figures_table_formats_to_three_decimals():
    app = run("Powertrain", "petrol")
    table = app.dataframe[0].value.set_index("Run")
    assert table.loc["Francorchamps — eco", "CO₂ per km (g CO₂/km)"] == "245.730"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_category_view.py -k "figures_table" -v`
Expected: FAIL — the cells currently hold raw floats and `None`.

- [ ] **Step 3: Add the shared formatter to `dashboard/layout.py`**

Place it directly below `run_notice`:

```python
def mark_gap_value(
    value: float | None,
    powertrain: str | None,
    cycle: str | None,
    *,
    decimals: int = 3,
) -> str:
    """Format a reported figure for display, labelling a known gap in place.

    A figure the workbook does not report becomes an em dash. A figure from a run whose
    workbook is flagged in RUN_NOTICES keeps its value but carries "to be filled", so a zero
    that exists only because the data is missing cannot be read as a measurement.
    """
    if value is None or pd.isna(value):
        return "—"
    formatted = f"{value:,.{decimals}f}"
    return f"{formatted} — to be filled" if run_notice(powertrain, cycle) else formatted
```

- [ ] **Step 4: Use it in the Category view**

In `dashboard/pages/5_Category_View.py`, extend the layout import to include `mark_gap_value`, then replace the loop that builds `records` so every canonical figure goes through the formatter:

```python
records = []
for name, (_, row) in zip(member_names, members.iterrows()):
    record = {"Run": name}
    for column, (display, unit) in CANONICAL_QUANTITIES.items():
        record[f"{display} ({unit})"] = mark_gap_value(
            row.get(column), row["powertrain"], row["cycle"]
        )
    record["Workbook"] = row["source_file"]
    records.append(record)
figures = pd.DataFrame(records)
```

Then change the caption under that table from:

```python
st.caption(
    "A blank cell means that workbook does not report the figure. Values are as reported — "
    "nothing here is converted or recomputed."
)
```

to:

```python
st.caption(
    "A dash means that workbook does not report the figure; “to be filled” marks a known gap "
    "in the supplied file. Values are as reported — nothing here is converted or recomputed."
)
```

- [ ] **Step 5: Switch Overview to the shared formatter**

In `dashboard/Overview.py`, delete the local `mark_gaps` function and the loop that calls it, and build `display` with the shared one instead:

```python
display = matrix.copy().astype(object)
for powertrain in matrix.index:
    for cycle in matrix.columns:
        code_p = next(k for k, v in POWERTRAIN_NAMES.items() if v == powertrain)
        code_c = next(k for k, v in CYCLE_NAMES.items() if v == cycle)
        display.loc[powertrain, cycle] = mark_gap_value(
            matrix.loc[powertrain, cycle], code_p, code_c
        )
```

Add `mark_gap_value` to the `dashboard.layout` import list at the top of the file.

- [ ] **Step 6: Run the tests**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 93 passed. The existing Overview assertions (`"245.730"`, `"0.000 — to be filled"`, `"—"`) must still hold — they are the regression check that the shared formatter behaves exactly as Overview's local one did.

- [ ] **Step 7: Commit**

```bash
git add dashboard/layout.py dashboard/Overview.py dashboard/pages/5_Category_View.py tests/test_category_view.py
git commit -m "Mark gaps and blanks in the Category view figures table"
```

---

### Task 2: Stop over-counting distinct values (findings 3 and 4)

`varying_parameters` reports `Distinct values = len(distinct) + (1 if any run is missing it)`. For NEDC `effective mass gear 1 [kg]` that yields **4** against 3 distinct present values and one blank — the column name states something the number does not mean. Sorting must still put "differs and is missing somewhere" above "differs only", so the presence signal moves into the sort key rather than the displayed count.

**Files:**
- Modify: `dashboard/layout.py` (`varying_parameters`)
- Modify: `dashboard/pages/5_Category_View.py` (caption + blanks in the varying table)
- Test: `tests/test_charts.py`, `tests/test_category_view.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_charts.py`:

```python
def test_distinct_values_counts_only_distinct_present_values(runs):
    """The column says "Distinct values", so it must not also count absence."""
    from dashboard.layout import varying_parameters

    nedc = runs[runs["cycle"] == "nedc"]
    varying = varying_parameters(nedc)
    row = varying[varying["Parameter"].str.startswith("effective mass gear 1")].iloc[0]

    run_columns = [c for c in varying.columns if c not in ("Parameter", "Distinct values")]
    values = [row[c] for c in run_columns]
    present = [v for v in values if pd.notna(v)]

    assert len(present) == 3
    assert len(values) - len(present) == 1
    assert row["Distinct values"] == len(set(present)) == 3


def test_a_parameter_missing_somewhere_still_sorts_above_a_plain_difference(runs):
    """Absence still matters for ordering, it just is not counted as a value."""
    from dashboard.layout import varying_parameters

    nedc = varying_parameters(runs[runs["cycle"] == "nedc"])
    run_columns = [c for c in nedc.columns if c not in ("Parameter", "Distinct values")]

    def missing(row):
        return sum(pd.isna(row[c]) for c in run_columns)

    keys = [(row["Distinct values"], missing(row)) for _, row in nedc.iterrows()]
    assert keys == sorted(keys, key=lambda k: (k[0], k[1]), reverse=True)
```

Append to `tests/test_category_view.py`:

```python
def test_varying_table_explains_its_blanks():
    app = run("Cycle", "nedc")
    captions = " ".join(c.value for c in app.caption)
    assert "absent from" in captions
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_charts.py tests/test_category_view.py -k "distinct_values or sorts_above or explains_its_blanks" -v`
Expected: FAIL — the count is currently 4, and no such caption exists.

- [ ] **Step 3: Fix the count in `dashboard/layout.py`**

Inside `varying_parameters`, replace the record-building and sort. The `Distinct values` column now holds only distinct present values; absence moves to a private sort column that is dropped before returning:

```python
        record = {"Parameter": column.removeprefix("param:")}
        record.update(dict(zip(labels, values)))
        record["Distinct values"] = len(distinct)
        record["_missing"] = len(values) - len(present)
        records.append(record)

    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return (
        frame.sort_values(
            ["Distinct values", "_missing", "Parameter"], ascending=[False, False, True]
        )
        .drop(columns="_missing")
        .reset_index(drop=True)
    )
```

- [ ] **Step 4: Show the varying table's blanks and explain them**

In `dashboard/pages/5_Category_View.py`, where the varying table is rendered, replace the bare `st.dataframe(varying, ...)` call with a formatted one, and add the caption sentence. The run columns are everything except `Parameter` and `Distinct values`:

```python
    run_columns = [c for c in varying.columns if c not in ("Parameter", "Distinct values")]
    st.dataframe(
        varying.style.format({c: "{:,.4g}" for c in run_columns}, na_rep="—"),
        width="stretch",
        hide_index=True,
        height=min(len(varying), 18) * 35 + 38,
    )
    st.caption(
        f"{len(varying)} parameters differ across the category, or are absent from some of its "
        "workbooks — a dash means that workbook has no row for it at all. Most-varied first."
    )
```

Note the existing `hide_index=True` must be kept; a Styler still honours it.

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 96 passed.

- [ ] **Step 6: Commit**

```bash
git add dashboard/layout.py dashboard/pages/5_Category_View.py tests/test_charts.py tests/test_category_view.py
git commit -m "Count only distinct present values, and show the varying table's blanks"
```

---

### Task 3: One implementation of "inputs that differ" (finding 5)

Task 2 of the original plan said to extract the diff "as a reusable helper that both can use", but the Compare page was never switched. Two implementations now coexist with different equality rules — `np.isclose(rtol=1e-9)` in Compare against `round(..., 9)` in `varying_parameters`. The review verified they agree on all 66 run pairs, so this is a safe consolidation, not a behaviour change.

**Files:**
- Modify: `dashboard/pages/3_Compare.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_app.py`:

```python
def test_compare_and_category_view_agree_on_what_differs():
    """Both pages must answer "what differs" identically — one implementation, not two."""
    from dashboard.layout import varying_parameters
    from dashboard.loaders import load_runs

    runs = load_runs.__wrapped__()
    pair = runs[
        ((runs["powertrain"] == "petrol") | (runs["powertrain"] == "hybrid"))
        & (runs["cycle"] == "franco_eco")
    ]
    expected = set(varying_parameters(pair)["Parameter"])

    app = run(COMPARE)
    app.selectbox(key="cmp_left").set_value(run_index("petrol", "franco_eco")).run()
    app.selectbox(key="cmp_right").set_value(run_index("hybrid", "franco_eco")).run()
    shown = set(app.dataframe[1].value["Parameter"])

    assert shown == expected
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app.py -k agree_on_what_differs -v`
Expected: FAIL — Compare's column header is `Parameter` but its row set is built by the inline loop, and its labels are `run_label` form rather than matching.

- [ ] **Step 3: Replace the inline diff in `dashboard/pages/3_Compare.py`**

Delete the whole block from `param_columns = [c for c in runs.columns if c.startswith("param:")]` through the construction of `differences` (the `rows` loop, the `np.isclose` comparison, and the `pd.to_numeric` coercion that followed it), and replace it with:

```python
pair = pd.concat([left_row.to_frame().T, right_row.to_frame().T], ignore_index=True)
differences = varying_parameters(pair)
if not differences.empty:
    differences = differences.drop(columns="Distinct values")
```

Add `varying_parameters` to the `dashboard.layout` import list. Remove `import numpy as np` from the top of the file if nothing else in the file uses it — check with `grep -n "np\." dashboard/pages/3_Compare.py` before deleting the import.

The caption below the table counts parameters; keep it, but it now reads from `differences` alone:

```python
    st.caption(
        f"{len(differences)} parameters differ, or appear in only one of the two workbooks."
    )
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 97 passed. The existing Compare tests (`test_compare_lists_differing_inputs`, `test_compare_renders_absent_parameters_as_a_dash_not_none`) are the regression check.

If `test_compare_renders_absent_parameters_as_a_dash_not_none` fails because the columns are no longer numeric dtype, that is expected — `varying_parameters` returns raw values. Fix it by rendering through a Styler exactly as Task 2 Step 4 does for the Category view, then update that test to assert `"—"` appears rather than asserting dtype.

- [ ] **Step 5: Commit**

```bash
git add dashboard/pages/3_Compare.py tests/test_app.py
git commit -m "Give Compare and the Category view one diff implementation"
```

---

### Task 4: Minor sweep (findings 6-13)

Eight small, independent corrections. Do them in one commit.

**Files:**
- Modify: `dashboard/layout.py`, `dashboard/pages/5_Category_View.py`, `dashboard/pages/2_Trace_Explorer.py`, `dashboard/pages/3_Compare.py`, and four page filenames
- Test: `tests/test_app.py`, `tests/test_category_view.py`, `tests/test_data_page.py`

- [ ] **Step 1: Hoist the axis labels into `dashboard/layout.py`**

Three pages need them and two disagree today. Add near `CANONICAL_QUANTITIES`:

```python
#: Display names for the columns a chart can be plotted against.
X_LABELS: dict[str, str] = {
    "distance_m": "Distance (m)",
    "time_s": "Time (s)",
    "step": "Step",
}
```

Then in `2_Trace_Explorer.py` and `5_Category_View.py`, delete the local `X_LABELS` definitions and import the shared one. In `5_Category_View.py` change `format_func=X_LABELS.get` to `format_func=lambda c: X_LABELS[c]`, so an unmapped code raises instead of silently rendering `None`.

In `3_Compare.py`, the x-axis title currently passes the raw column code. Change `style_axes(fig, pal, x_title=x_column, y_title=column)` to `style_axes(fig, pal, x_title=X_LABELS.get(x_column, x_column), y_title=column)` and import `X_LABELS`.

- [ ] **Step 2: Gate the distance caption on the axis**

In `5_Category_View.py`, the "Francorchamps lap is 7 km, NEDC about 11 km" caption prints regardless of which axis is selected, so it appears under a chart plotted against step number. Change its condition from `if field == "powertrain":` to:

```python
    if field == "powertrain" and x_column == "distance_m":
```

- [ ] **Step 3: Reorder the sidebar**

Category view currently sorts last, after Data, though the README lists it second. Rename so the nav order matches how the pages are used. URLs are derived from the name without the numeric prefix, so no link changes:

```bash
git mv dashboard/pages/5_Category_View.py dashboard/pages/2_Category_View.py
git mv dashboard/pages/2_Trace_Explorer.py dashboard/pages/3_Trace_Explorer.py
git mv dashboard/pages/3_Compare.py dashboard/pages/4_Compare.py
git mv dashboard/pages/4_Data.py dashboard/pages/5_Data.py
```

Then update the path constants in the tests:

```bash
grep -rn '5_Category_View.py\|2_Trace_Explorer.py\|3_Compare.py\|4_Data.py' tests/
```

and edit each to the new filename. The constants are `CATEGORY_VIEW` in `tests/test_category_view.py`, `TRACE` and `COMPARE` in `tests/test_app.py`, and `DATA` in `tests/test_data_page.py`.

- [ ] **Step 4: Fix the stale docstring**

`dashboard/layout.py` line 3 says the module serves "all three pages". Change it to "every page".

- [ ] **Step 5: Add the missing dash test**

No test pins that the Category view actually passes `dashes=` — deleting the argument keeps the suite green. `AppTest` cannot inspect a Plotly figure, so assert it at the seam instead. Append to `tests/test_category_view.py`:

```python
def test_page_requests_dashes_only_for_a_powertrain_category(monkeypatch):
    """Guards the call site: AppTest cannot see a figure, so capture the argument."""
    from dashboard import charts

    captured: list[object] = []
    original = charts.overlay_traces

    def spy(*args, **kwargs):
        captured.append(kwargs.get("dashes"))
        return original(*args, **kwargs)

    monkeypatch.setattr(charts, "overlay_traces", spy)

    run("Powertrain", "petrol")
    assert captured and captured[-1] is not None, "a powertrain category needs dashes"
    assert len(set(captured[-1])) == 3

    captured.clear()
    run("Cycle", "nedc")
    assert captured and captured[-1] is None, "a cycle category is separated by colour"
```

- [ ] **Step 6: Run the tests**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 98 passed.

- [ ] **Step 7: Commit**

```bash
git add -A -- dashboard tests
git commit -m "Sweep the review's minor findings"
```

---

### Task 5: Verify in the running app, then update the README

- [ ] **Step 1: Look at every page**

```bash
.venv/bin/streamlit run dashboard/Overview.py --server.port 8580 --server.headless true &
sleep 9
```

Walk all five pages. Confirm by eye:
- Category view → Powertrain → Petrol: the Electrical energy column shows dashes, not `None`; figures read to three decimals.
- Category view → Cycle → NEDC: the plug-in hybrid row reads `0.000 — to be filled`, and the warning banner is present.
- The sidebar order is Overview, Category view, Trace Explorer, Compare, Data.
- Compare still lists differing inputs and shows dashes for absent parameters.
- No axis label is clipped and nothing overflows horizontally.

Stop the server when done.

- [ ] **Step 2: Correct the README's page order**

The "Five pages:" paragraph lists Category view second, which now matches the sidebar. Re-read it and confirm no other sentence contradicts the new order.

- [ ] **Step 3: Commit anything the walk-through changed**

```bash
git add -A
git commit -m "Verify the pages after the review fixes"
```

---

## Self-Review

**Finding coverage.** 1 and 2 → Task 1. 3 and 4 → Task 2. 5 → Task 3. 6 (distance caption), 7 (sidebar order), 8 (`X_LABELS` duplication and Compare's raw x title), 11 (`format_func` returning `None`), 12 (no dash test), 13 (stale docstring) → Task 4. Findings 9 and 10 are unreachable branches the review confirmed cannot be hit from the live pages; they are **deliberately not fixed** — deleting a guard that costs nothing and would matter if a future caller bypasses `numeric_trace_columns` trades safety for tidiness.

**Placeholders.** None. Every code step carries its code; every test step carries the command and its expected result.

**Type consistency.** `mark_gap_value(value, powertrain, cycle, *, decimals=3) -> str` is defined in Task 1 and consumed in Task 1 only. `varying_parameters(runs) -> DataFrame` keeps its signature through Task 2 and gains a consumer in Task 3; its `Distinct values` column is dropped by Compare, which does not display it. `X_LABELS` is defined in Task 4 Step 1 and imported by three pages in the same task.

**Risks.**
- Task 1 changes the Overview's rendering path. Its three existing assertions are the regression check and must pass unchanged.
- Task 3 changes Compare's dtypes from coerced-numeric to raw. Step 4 names the test most likely to need updating and says what to do.
- Task 4 Step 3 renames four files; every test path constant must move with them or the suite fails loudly, which is the desired failure mode.
