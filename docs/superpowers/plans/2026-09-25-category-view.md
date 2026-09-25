# Category View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Category view page that shows every run in one category together — all the petrols, all the NEDC runs, all the sport runs — with their totals, their traces overlaid, and the parameters that differ across them.

**Architecture:** One new page, `dashboard/pages/5_Category_View.py`, plus two pure helpers: `charts.overlay_traces` (N runs on one axis, generalising the existing two-run `compare_traces`) and `layout.varying_parameters` (an N-way version of the pairwise diff already on the Compare page). Everything else is reused: loaders, palette, run notices, downloads. A category is a slice of the 4×3 grid along one field — `powertrain` (4 categories of 3) or `cycle` (3 categories of 4).

**Tech Stack:** Python 3.14.7, Streamlit 1.64, Plotly 7.1, pandas 3.0, pytest 9.1. Run everything through `.venv/bin/`.

**Spec:** No separate spec document. The request was "one way to view each category together, with graphs tables and stuff — for example all the petrols, all the NEDC, all the sport." Requirements are captured in Global Constraints below and in each task.

## Global Constraints

Every task's requirements implicitly include these.

- **Pass-through only.** No unit conversion, no recomputation, no correcting the supplied data, no conclusions. This tool is an internal viewer, not a project deliverable. Annotations about the data are allowed; changes to it are not.
- **`style` is not a category axis.** It maps 1:1 onto `cycle` today: `eco`↔`franco_eco`, `sport`↔`franco_sport`, `regulatory`↔`nedc`. Choosing the cycle category already delivers "all the sport". Do not add a third selector.
- **New UI copy and annotations go in `dashboard/`, never `pwt/`.** Streamlit Community Cloud hot-reloads the app folder but keeps `pwt/` cached from process boot, so a name added to `pwt/` raises `ImportError` on the deployed app until it is rebooted.
- **Chart rules** (from the data-viz method, already encoded in `dashboard/theme.py` and `dashboard/charts.py`):
  - Adjacent-pairlist forms only — grouped bars and fixed-order lines. **Never a four-series scatter**: no set of four categorical colours clears the all-pairs colourblind gates in both light and dark.
  - Colour follows the powertrain via `theme.Palette.for_powertrain`, never the series' rank, so filtering never repaints the survivors.
  - One y-axis per figure. Two measures of different scale get two charts.
  - Value labels and a table view are mandatory relief, not decoration — aqua and yellow sit below 3:1 on the light surface.
  - Render with `st.plotly_chart(fig, theme=None)` and call `theme.style_axes`, which pins `template="none"` and enables `automargin`.
- **Known gaps** are declared in `layout.RUN_NOTICES`, keyed by `(powertrain, cycle)`, and surfaced with `layout.render_run_notices`. Currently one entry: `("phev", "nedc")`.
- **Widths** use `width="stretch"`, never the removed `use_container_width`.
- **Tests:** `.venv/bin/python -m pytest`. Page behaviour is tested with `streamlit.testing.v1.AppTest`; chart and helper behaviour is tested directly without the Streamlit runtime. The suite is green at 69 tests before this plan starts.

---

### Task 1: Correct the excluded-axis caption

`loaders.axis_columns` drops any column that does not run forward. The Trace Explorer caption explaining the exclusion currently says the workbook "records it per step rather than cumulatively" for every excluded case. That is true of `33 NEDC PETROL Car.xlsx` but wrong for `32 NEDC ELECTRIC.xlsx`, whose `distance_m` column exists but is entirely empty. Distance semantics are per-workbook, not per-cycle: all eight Francorchamps files and NEDC hybrid/PHEV are cumulative; only NEDC petrol is per-step.

**Files:**
- Modify: `dashboard/loaders.py` (add `axis_exclusion_reason`)
- Modify: `dashboard/pages/2_Trace_Explorer.py` (use it)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `loaders.axis_columns(trace) -> list[str]` (exists)
- Produces: `loaders.axis_exclusion_reason(trace: pd.DataFrame, column: str) -> str | None` — returns a sentence explaining why `column` is not offered as an axis, or `None` if it is offered or absent entirely.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_app.py`:

```python
def test_axis_exclusion_reason_distinguishes_empty_from_per_step():
    """Distance is per-step in NEDC petrol but simply empty in NEDC electric."""
    from dashboard.loaders import axis_exclusion_reason, trace_for

    petrol = trace_for.__wrapped__("petrol", "nedc")
    reason = axis_exclusion_reason(petrol, "distance_m")
    assert reason is not None and "per step" in reason

    bev = trace_for.__wrapped__("bev", "nedc")
    reason = axis_exclusion_reason(bev, "distance_m")
    assert reason is not None and "empty" in reason
    assert "per step" not in reason


def test_axis_exclusion_reason_is_none_when_the_column_works():
    """Francorchamps distance is cumulative, so there is nothing to explain."""
    from dashboard.loaders import axis_exclusion_reason, trace_for

    lap = trace_for.__wrapped__("petrol", "franco_eco")
    assert axis_exclusion_reason(lap, "distance_m") is None
    assert axis_exclusion_reason(lap, "not_a_column") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_app.py -k axis_exclusion -v`
Expected: FAIL with `ImportError: cannot import name 'axis_exclusion_reason'`

- [ ] **Step 3: Implement**

In `dashboard/loaders.py`, directly below `axis_columns`:

```python
def axis_exclusion_reason(trace: pd.DataFrame, column: str) -> str | None:
    """Why `column` is not offered as an x-axis, or None if it is offered or absent.

    Distance semantics are per-workbook, not per-cycle: the eight Francorchamps files and the
    NEDC hybrid and plug-in hybrid store it cumulatively, `33 NEDC PETROL Car.xlsx` stores it
    per step, and `32 NEDC ELECTRIC.xlsx` has the column but never fills it.
    """
    if column not in trace.columns or column in axis_columns(trace):
        return None
    values = trace[column].dropna()
    if values.empty:
        return f"`{column}` is empty in this workbook, so there is nothing to plot against."
    if not values.is_monotonic_increasing:
        return (
            f"`{column}` is recorded per step in this workbook rather than cumulatively, so it "
            "does not run forward and would scramble the chart."
        )
    return f"`{column}` does not increase across the run, so it cannot be an axis."
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_app.py -k axis_exclusion -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Use it in the Trace Explorer**

In `dashboard/pages/2_Trace_Explorer.py`, replace the hardcoded caption block:

```python
if "distance_m" in trace.columns and "distance_m" not in x_options:
    st.sidebar.caption(
        "Distance is not offered for this run: the workbook records it per step rather than "
        "cumulatively, so it does not run forward."
    )
```

with:

```python
for excluded in ("distance_m", "time_s"):
    reason = axis_exclusion_reason(trace, excluded)
    if reason:
        st.sidebar.caption(f"Not offered as an axis: {reason}")
```

and extend the import at the top of the file:

```python
from dashboard.loaders import (
    axis_columns,
    axis_exclusion_reason,
    load_runs,
    numeric_trace_columns,
    trace_for,
)
```

- [ ] **Step 6: Update the existing caption assertion**

In `tests/test_app.py`, inside `test_nedc_distance_is_not_offered_as_an_axis`, replace:

```python
    assert "per step rather than cumulatively" in captions
```

with:

```python
    assert "recorded per step in this workbook rather than cumulatively" in captions
```

- [ ] **Step 7: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 71 passed

- [ ] **Step 8: Commit**

```bash
git add dashboard/loaders.py dashboard/pages/2_Trace_Explorer.py tests/test_app.py
git commit -m "Explain axis exclusion per workbook, not per cycle"
```

---

### Task 2: N-way parameter diff

The Compare page diffs two runs inline. The Category view needs the same idea across three or four. Extract it as a reusable helper that both can use.

**Files:**
- Modify: `dashboard/layout.py` (add `varying_parameters`)
- Test: `tests/test_charts.py`

**Interfaces:**
- Consumes: `layout.run_label(powertrain, cycle) -> str` (exists)
- Produces: `layout.varying_parameters(runs: pd.DataFrame) -> pd.DataFrame` — one row per parameter that is not identical across every run, one column per run named by `run_label`, plus a `Distinct values` column. Sorted with the most-varied parameters first. Returns an empty DataFrame when nothing varies.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_charts.py`:

```python
def test_varying_parameters_lists_only_what_differs(runs):
    from dashboard.layout import varying_parameters

    petrols = runs[runs["powertrain"] == "petrol"]
    varying = varying_parameters(petrols)

    assert not varying.empty
    assert "Parameter" in varying.columns
    assert "Distinct values" in varying.columns
    # One column per run, named the way every other page names them.
    assert "Petrol · NEDC" in varying.columns

    names = set(varying["Parameter"])
    # Mass differs between the NEDC car and the Spa car; the wheel is the same everywhere.
    assert any(n.startswith("total mass") for n in names)
    assert not any(n.startswith("wheel diameter") for n in names)

    # Most-varied first.
    counts = varying["Distinct values"].tolist()
    assert counts == sorted(counts, reverse=True)


def test_varying_parameters_flags_a_parameter_present_in_only_some_runs(runs):
    """A parameter only some workbooks carry is a difference, not a match."""
    from dashboard.layout import varying_parameters

    nedc = runs[runs["cycle"] == "nedc"]
    names = set(varying_parameters(nedc)["Parameter"])
    # Only the hybrids carry an electric machine; petrol and BEV do not.
    assert any(n.startswith("electric machine mass") for n in names)


def test_varying_parameters_is_empty_for_a_single_run(runs):
    from dashboard.layout import varying_parameters

    one = runs[(runs["powertrain"] == "petrol") & (runs["cycle"] == "nedc")]
    assert varying_parameters(one).empty
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_charts.py -k varying_parameters -v`
Expected: FAIL with `ImportError: cannot import name 'varying_parameters'`

- [ ] **Step 3: Implement**

In `dashboard/layout.py`, below `run_label`:

```python
def varying_parameters(runs: pd.DataFrame) -> pd.DataFrame:
    """Parameters that are not identical across every run given.

    A parameter counts as varying when the runs disagree on its value, or when some runs carry
    it and others do not — a plug-in hybrid has a battery mass that a petrol car has no row
    for, and that absence is a real difference, not a match. Values are compared as the
    workbooks report them; nothing is rounded to force agreement beyond float noise.
    """
    if len(runs) < 2:
        return pd.DataFrame()

    labels = [run_label(row["powertrain"], row["cycle"]) for _, row in runs.iterrows()]
    records = []
    for column in (c for c in runs.columns if c.startswith("param:")):
        values = [runs.iloc[i][column] for i in range(len(runs))]
        present = [v for v in values if pd.notna(v)]
        if not present:
            continue
        distinct = {round(float(v), 9) for v in present}
        if len(distinct) == 1 and len(present) == len(values):
            continue  # every run agrees and none is missing it
        record = {"Parameter": column.removeprefix("param:")}
        record.update(dict(zip(labels, values)))
        record["Distinct values"] = len(distinct) + (len(values) != len(present))
        records.append(record)

    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return frame.sort_values(
        ["Distinct values", "Parameter"], ascending=[False, True]
    ).reset_index(drop=True)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_charts.py -k varying_parameters -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add dashboard/layout.py tests/test_charts.py
git commit -m "Add an N-way parameter diff"
```

---

### Task 3: Overlay N traces on one axis

`charts.compare_traces` draws exactly two runs. Generalise to any number, then reimplement the two-run function on top of it so there is one code path.

**Files:**
- Modify: `dashboard/charts.py`
- Test: `tests/test_charts.py`

**Interfaces:**
- Consumes: `theme.Palette` (exists), `charts.LINE_WIDTH`, `charts.MARKER_SIZE` (exist)
- Produces: `charts.overlay_traces(frames: list[pd.DataFrame], labels: list[str], colours: list[str], column: str, x_column: str, pal: Palette) -> go.Figure`. `compare_traces` keeps its current signature and delegates.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_charts.py`:

```python
def test_overlay_traces_draws_one_line_per_run(lap):
    frames = [lap, lap, lap]
    labels = ["a", "b", "c"]
    colours = [DARK.series[0], DARK.series[1], DARK.series[2]]
    fig = charts.overlay_traces(frames, labels, colours, "speed_kph", "distance_m", DARK)

    assert len(fig.data) == 3
    assert [t.name for t in fig.data] == labels
    assert [t.line.color for t in fig.data] == colours
    for trace in fig.data:
        assert trace.line.width == charts.LINE_WIDTH
        assert getattr(trace, "yaxis", None) in (None, "y")  # single axis


def test_overlay_traces_skips_a_run_missing_the_column(lap):
    """A BEV has no gear column; it drops out rather than raising."""
    without = lap.drop(columns=["gear"])
    fig = charts.overlay_traces(
        [lap, without], ["has gear", "no gear"], [DARK.series[0], DARK.series[1]],
        "gear", "distance_m", DARK,
    )
    assert [t.name for t in fig.data] == ["has gear"]


def test_compare_traces_still_works_through_the_shared_path(lap):
    fig = charts.compare_traces(
        lap, lap, "speed_kph", "distance_m", ("left", "right"),
        (DARK.series[0], DARK.series[1]), DARK,
    )
    assert [t.name for t in fig.data] == ["left", "right"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_charts.py -k "overlay_traces or shared_path" -v`
Expected: FAIL with `AttributeError: module 'dashboard.charts' has no attribute 'overlay_traces'`

- [ ] **Step 3: Implement**

In `dashboard/charts.py`, replace the whole `compare_traces` function with:

```python
def overlay_traces(
    frames: list[pd.DataFrame],
    labels: list[str],
    colours: list[str],
    column: str,
    x_column: str,
    pal: Palette,
) -> go.Figure:
    """One per-step column from several runs on a single axis.

    A run that does not carry the column is skipped rather than drawn as a gap — the electric
    workbooks have no gear column at all, and an empty series in the legend would suggest the
    data is missing when the concept simply does not apply.
    """
    fig = go.Figure()
    for frame, label, colour in zip(frames, labels, colours):
        if column not in frame.columns or frame[column].isna().all():
            continue
        fig.add_scatter(
            name=label,
            x=frame[x_column],
            y=frame[column],
            mode="lines+markers",
            line=dict(color=colour, width=LINE_WIDTH),
            marker=dict(size=MARKER_SIZE, color=colour, line=dict(color=pal.surface, width=2)),
            hovertemplate=f"<b>{label}</b><br>%{{y:.4g}}<extra></extra>",
        )
    fig.update_layout(showlegend=len(fig.data) > 1, hovermode="x unified")
    return fig


def compare_traces(
    left: pd.DataFrame,
    right: pd.DataFrame,
    column: str,
    x_column: str,
    labels: tuple[str, str],
    colours: tuple[str, str],
    pal: Palette,
) -> go.Figure:
    """One per-step column from two runs on a single axis."""
    fig = overlay_traces(
        [left, right], list(labels), list(colours), column, x_column, pal
    )
    fig.update_layout(showlegend=True)
    return fig
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_charts.py -q`
Expected: PASS

- [ ] **Step 5: Run the full suite to confirm Compare still behaves**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 77 passed

- [ ] **Step 6: Commit**

```bash
git add dashboard/charts.py tests/test_charts.py
git commit -m "Generalise trace overlay to any number of runs"
```

---

### Task 4: The Category view page

**Files:**
- Create: `dashboard/pages/5_Category_View.py`
- Test: `tests/test_category_view.py`

**Interfaces:**
- Consumes: `layout.configure`, `layout.render_run_notices`, `layout.run_notice`, `layout.run_label`, `layout.download`, `layout.CANONICAL_QUANTITIES`, `layout.varying_parameters` (Task 2); `loaders.load_runs`, `loaders.trace_for`, `loaders.axis_columns`, `loaders.numeric_trace_columns`; `charts.grouped_totals`, `charts.overlay_traces` (Task 3); `theme.style_axes`, `theme.POWERTRAIN_ORDER`; `pwt.catalog.POWERTRAIN_NAMES`, `pwt.catalog.CYCLE_NAMES`
- Produces: nothing other modules import.

- [ ] **Step 1: Write the failing test**

Create `tests/test_category_view.py`:

```python
"""The Category view page shows every run in one category together."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

CATEGORY_VIEW = str(ROOT / "dashboard" / "pages" / "5_Category_View.py")


def run(axis_name: str | None = None, choice: str | None = None) -> AppTest:
    app = AppTest.from_file(CATEGORY_VIEW, default_timeout=180).run()
    assert not app.exception, [e.value for e in app.exception]
    if axis_name is not None:
        app.radio[0].set_value(axis_name).run()
        assert not app.exception, [e.value for e in app.exception]
    if choice is not None:
        app.selectbox[0].set_value(choice).run()
        assert not app.exception, [e.value for e in app.exception]
    return app


def test_page_renders():
    app = run()
    assert app.title[0].value == "Category view"


def test_powertrain_category_shows_three_runs():
    app = run("Powertrain", "petrol")
    text = " ".join(m.value for m in app.markdown) + " ".join(c.value for c in app.caption)
    assert "3 runs" in text


def test_cycle_category_shows_four_runs():
    app = run("Cycle", "nedc")
    text = " ".join(m.value for m in app.markdown) + " ".join(c.value for c in app.caption)
    assert "4 runs" in text


def test_all_sport_is_reachable_through_the_cycle_category():
    """"All the sport" is the Francorchamps sport cycle category."""
    app = run("Cycle", "franco_sport")
    table = app.dataframe[0].value
    assert len(table) == 4
    assert "Petrol" in set(table["Run"])
    assert "Plug-in hybrid" in set(table["Run"])


def test_totals_table_carries_every_canonical_figure():
    app = run("Powertrain", "petrol")
    table = app.dataframe[0].value
    for heading in ("CO₂ per km (g CO₂/km)", "Fuel consumption (l/100 km)"):
        assert heading in table.columns


def test_petrol_category_shows_the_workbook_figures():
    app = run("Powertrain", "petrol")
    table = app.dataframe[0].value.set_index("Run")
    assert table.loc["Francorchamps — eco", "CO₂ per km (g CO₂/km)"] == pytest.approx(
        245.7298, rel=1e-4
    )
    assert table.loc["NEDC", "CO₂ per km (g CO₂/km)"] == pytest.approx(158.2885, rel=1e-4)


def test_incomplete_run_is_flagged_in_its_categories():
    """The NEDC plug-in hybrid gap must show in both categories that contain it."""
    for axis_name, choice in (("Cycle", "nedc"), ("Powertrain", "phev")):
        app = run(axis_name, choice)
        warnings = " ".join(w.value for w in app.warning)
        assert "to be filled" in warnings, f"{axis_name}={choice}"


def test_varying_parameters_are_listed():
    app = run("Powertrain", "petrol")
    names = set(app.dataframe[1].value["Parameter"])
    assert any(n.startswith("total mass") for n in names)


def test_axis_falls_back_when_the_category_shares_no_distance():
    """The BEV category shares no usable distance or time column, so it plots against step."""
    app = run("Powertrain", "bev")
    assert not app.exception, [e.value for e in app.exception]
    axis = app.selectbox[2]
    assert axis.options == ["Step"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_category_view.py -q`
Expected: FAIL with `FileNotFoundError` — the page does not exist yet.

- [ ] **Step 3: Create the page**

Create `dashboard/pages/5_Category_View.py`:

```python
"""Category view — every run in one category together.

A category is a slice of the 4x3 grid along one field: all four powertrains on one cycle, or
one powertrain across all three cycles. Driving style is not a third axis — it maps 1:1 onto
cycle today (eco/sport/regulatory to the two Francorchamps laps and NEDC), so "all the sport"
is the Francorchamps sport category.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard import charts
from dashboard.layout import (
    CANONICAL_QUANTITIES,
    configure,
    download,
    render_run_notices,
    run_label,
    run_notice,
    varying_parameters,
)
from dashboard.loaders import axis_columns, load_runs, numeric_trace_columns, trace_for
from dashboard.theme import POWERTRAIN_ORDER, style_axes
from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES

pal = configure("Category view")
runs = load_runs()

st.title("Category view")
st.markdown(
    "Every run in one category, side by side. Choose powertrain to see one technology across "
    "the cycles, or by cycle to see the four technologies on the same drive."
)

# --- pick the category -----------------------------------------------------------------------

CATEGORY_AXES = {
    "Powertrain": ("powertrain", POWERTRAIN_NAMES, list(POWERTRAIN_ORDER)),
    "Cycle": ("cycle", CYCLE_NAMES, list(CYCLE_NAMES)),
}

axis = st.radio(
    "Category", options=list(CATEGORY_AXES), horizontal=True, label_visibility="collapsed"
)
field, names, order = CATEGORY_AXES[axis]
available = [code for code in order if code in set(runs[field])]
choice = st.selectbox(axis, options=available, format_func=lambda c: names[c])

members = runs[runs[field] == choice].copy()
# Order members the way the rest of the app orders runs, so colour and sequence stay stable.
sort_field = "cycle" if field == "powertrain" else "powertrain"
sort_order = list(CYCLE_NAMES) if sort_field == "cycle" else list(POWERTRAIN_ORDER)
members["_sort"] = members[sort_field].map({c: i for i, c in enumerate(sort_order)})
members = members.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)

#: Each member's short name: the field that varies within the category.
member_names = [
    (CYCLE_NAMES if sort_field == "cycle" else POWERTRAIN_NAMES)[row[sort_field]]
    for _, row in members.iterrows()
]
#: Colour always follows the powertrain, even when the powertrain is what the category has in
#: common — that keeps a technology the same colour on every page.
member_colours = [pal.for_powertrain(row["powertrain"]) for _, row in members.iterrows()]

st.caption(
    f"{names[choice]} — {len(members)} runs: "
    + " · ".join(f"`{row['source_file']}`" for _, row in members.iterrows())
)

render_run_notices(*(row for _, row in members.iterrows()))

# --- the figures, as a table -------------------------------------------------------------------

st.subheader("Reported figures")

records = []
for name, (_, row) in zip(member_names, members.iterrows()):
    record = {"Run": name}
    for column, (display, unit) in CANONICAL_QUANTITIES.items():
        record[f"{display} ({unit})"] = row.get(column)
    record["Workbook"] = row["source_file"]
    records.append(record)
figures = pd.DataFrame(records)

st.dataframe(
    figures, width="stretch", hide_index=True, height=len(figures) * 35 + 38
)
st.caption(
    "A blank cell means that workbook does not report the figure. Values are as reported — "
    "nothing here is converted or recomputed."
)
download(figures, f"pwt-category-{choice}.csv", "Download these figures as CSV")

# --- one measure, charted ----------------------------------------------------------------------

st.subheader("Compare one measure")
quantity = st.selectbox(
    "Measure",
    options=list(CANONICAL_QUANTITIES),
    format_func=lambda q: CANONICAL_QUANTITIES[q][0],
)
display_name, unit = CANONICAL_QUANTITIES[quantity]

gaps = {
    (row["powertrain"], row["cycle"])
    for _, row in members.iterrows()
    if run_notice(row["powertrain"], row["cycle"])
}
fig = charts.grouped_totals(members, quantity, pal, unit=unit, gaps=gaps)
style_axes(fig, pal, y_title=unit)
fig.update_layout(height=400)
st.plotly_chart(fig, width="stretch", theme=None)

if members[quantity].isna().all():
    st.caption(f"No run in this category reports {display_name.lower()}.")

# --- traces overlaid ---------------------------------------------------------------------------

st.subheader("Traces overlaid")

traces = [trace_for(row["powertrain"], row["cycle"]) for _, row in members.iterrows()]

shared_axes = set.intersection(*(set(axis_columns(t)) for t in traces))
X_LABELS = {"distance_m": "Distance (m)", "time_s": "Time (s)", "step": "Step"}
axis_options = [c for c in ("distance_m", "time_s", "step") if c in shared_axes]

shared_columns = sorted(set.intersection(*(set(numeric_trace_columns(t)) for t in traces)))
plottable = [c for c in shared_columns if c not in ("step",)]

if not plottable:
    st.caption("These runs share no per-step column, so there is nothing to overlay.")
else:
    picker, axis_picker = st.columns([3, 1])
    with picker:
        default = next((i for i, c in enumerate(plottable) if c == "speed_kph"), 0)
        column = st.selectbox("Column", options=plottable, index=default)
    with axis_picker:
        x_column = st.selectbox("Against", options=axis_options, format_func=X_LABELS.get)

    if x_column == "step":
        traces = [t.assign(step=range(len(t))) for t in traces]

    fig = charts.overlay_traces(
        traces, member_names, member_colours, column, x_column, pal
    )
    style_axes(fig, pal, x_title=X_LABELS[x_column], y_title=column)
    fig.update_layout(height=420)
    st.plotly_chart(fig, width="stretch", theme=None)

    if axis_options == ["Step"] or axis_options == ["step"]:
        st.caption(
            "Plotted against step number: these workbooks share no distance or time column "
            "that runs forward across all of them."
        )
    if field == "powertrain":
        st.caption(
            "These runs are on different cycles, so the x-axes cover different ground: the "
            "Francorchamps lap is 7 km, NEDC about 11 km."
        )

# --- what differs ------------------------------------------------------------------------------

st.subheader("Inputs that differ across the category")

varying = varying_parameters(members)
if varying.empty:
    st.caption("Every parameter these workbooks share holds the same value.")
else:
    # Rename the run columns to the short names used above.
    rename = {
        run_label(row["powertrain"], row["cycle"]): name
        for name, (_, row) in zip(member_names, members.iterrows())
    }
    varying = varying.rename(columns=rename)
    st.dataframe(
        varying, width="stretch", hide_index=True,
        height=min(len(varying), 18) * 35 + 38,
    )
    st.caption(
        f"{len(varying)} parameters differ across the category, or appear in only some of its "
        "workbooks. Most-varied first."
    )
    download(varying, f"pwt-category-{choice}-parameters.csv", "Download these parameters as CSV")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_category_view.py -q`
Expected: PASS (9 passed)

If `test_axis_falls_back_when_the_category_shares_no_distance` fails on the selectbox index, print what is on the page and adjust the index — the axis picker is the third selectbox (category choice, measure, column, axis), so confirm with:

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from streamlit.testing.v1 import AppTest
at=AppTest.from_file('dashboard/pages/5_Category_View.py', default_timeout=180).run()
for i,s in enumerate(at.selectbox): print(i, s.label, s.options)
"
```

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 86 passed

- [ ] **Step 6: Look at the page**

```bash
.venv/bin/streamlit run dashboard/Overview.py --server.port 8560 --server.headless true &
sleep 9
```

Open `http://localhost:8560/Category_View`. Check by eye, then stop the server:
- choosing Powertrain → petrol shows three runs, one bar per cycle;
- choosing Cycle → NEDC shows four runs and the "to be filled" banner;
- the trace overlay draws one line per run in the category's colours;
- no axis label is clipped and nothing overflows horizontally.

- [ ] **Step 7: Commit**

```bash
git add dashboard/pages/5_Category_View.py tests/test_category_view.py
git commit -m "Add a Category view page"
```

---

### Task 5: Document it

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the page list**

In `README.md`, replace the paragraph beginning "Four pages:" with:

```markdown
Five pages: **Overview** (all twelve runs, one table and one chart), **Category view** (every run in
one category together — all the petrols, all the NEDC runs, all the sport runs), **Trace
Explorer** (per-step data for one run), **Compare** (two runs, with their differing inputs
listed first), and **Data** (the raw datasets as plain tables). Every table has a CSV download.

A category is a slice of the 4×3 grid along one field: powertrain (4 categories of 3) or cycle
(3 categories of 4). Driving style is not a third axis — it maps 1:1 onto cycle today, so "all the
sport" is the Francorchamps sport category. That changes when the WLTC highway cycle is added,
at which point `regulatory` will cover both NEDC and WLTC.
```

- [ ] **Step 2: Record the distance quirk**

In `README.md`, in the "What the reader has to work around" list, replace the bullet beginning "Only 12 of 37 trace headers" by appending a new bullet after it:

```markdown
- `Distance (m)` is per-workbook, not per-cycle: the eight Francorchamps files and NEDC
  hybrid/plug-in hybrid store it cumulatively, `33 NEDC PETROL Car.xlsx` stores it per step,
  and `32 NEDC ELECTRIC.xlsx` has the column but never fills it. A column is offered as a
  chart axis only when it actually runs forward.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Document the Category view and the distance quirk"
```

---

## Self-Review

**Spec coverage.** The request named three examples. "All the petrols" is the Powertrain category (Task 4). "All the NEDC" and "all the sport" are both the Cycle category, since style is 1:1 with cycle — covered by Task 4 and asserted by `test_all_sport_is_reachable_through_the_cycle_grouping`. "Graphs tables and stuff" is the figures table, the measure chart, the trace overlay, and the varying-parameters table, each with a CSV download.

**Placeholders.** None. Every code step carries the code; every test step carries the assertions and the exact command with its expected result.

**Type consistency.** `varying_parameters(runs: pd.DataFrame) -> pd.DataFrame` is defined in Task 2 and consumed in Task 4 under that name, with the `Parameter` and `Distinct values` columns the page renames around. `overlay_traces(frames, labels, colours, column, x_column, pal)` is defined in Task 3 and called with that argument order in Task 4. `axis_exclusion_reason(trace, column)` is defined in Task 1 and used only there. `run_notice`, `render_run_notices`, `run_label`, `download`, `CANONICAL_QUANTITIES`, `axis_columns`, `numeric_trace_columns`, `grouped_totals(..., gaps=...)` and `style_axes` all exist today with the signatures used here.

**Risks.**
- The BEV category shares only `step` as an axis, because the Francorchamps EV files have no `Time (s)` column and NEDC electric has no usable distance. The page handles it and says so; `test_axis_falls_back_when_the_category_shares_no_distance` pins it.
- Overlaying runs from different cycles puts a 7 km lap and an 11 km cycle on one axis. The page captions this rather than rescaling, which would be a recomputation.
- Task 3 changes `compare_traces` internals. The existing Compare tests are the regression check; run the full suite at Task 3 Step 5 before moving on.
