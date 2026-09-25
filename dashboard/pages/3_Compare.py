"""Compare — two runs side by side: their inputs, their totals, and one trace column."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import streamlit as st

from dashboard import charts
from dashboard.layout import (
    CANONICAL_QUANTITIES,
    configure,
    download,
    run_label,
    run_picker,
    source_caption,
)
from dashboard.loaders import axis_columns, load_runs, numeric_trace_columns, trace_for
from dashboard.theme import style_axes

pal = configure("Compare")
runs = load_runs()

st.title("Compare two runs")
st.markdown(
    "Pick any two workbooks. Differing inputs are listed first, so it is clear what changed "
    "between them before any figure is compared."
)

# --- controls -------------------------------------------------------------------------------

st.sidebar.subheader("Runs")
left_row = run_picker(runs, "Left", key="cmp_left", index=0)
right_row = run_picker(runs, "Right", key="cmp_right", index=2)

left_name = run_label(left_row["powertrain"], left_row["cycle"])
right_name = run_label(right_row["powertrain"], right_row["cycle"])
left_colour = pal.for_powertrain(left_row["powertrain"])
right_colour = pal.for_powertrain(right_row["powertrain"])

if left_row["source_file"] == right_row["source_file"]:
    st.info("Both sides are the same run. Pick a different run on one side.")
    st.stop()

source_caption(left_row, right_row)

# --- reported figures -----------------------------------------------------------------------

st.subheader("Reported figures")
records = []
for column, (display, unit) in CANONICAL_QUANTITIES.items():
    a, b = left_row.get(column), right_row.get(column)
    if pd.isna(a) and pd.isna(b):
        continue
    if pd.isna(a) or pd.isna(b):
        change = "—"
    elif a == 0:
        change = "—"  # a percentage change from zero says nothing
    else:
        change = f"{(b - a) / abs(a) * 100:+.1f}%"
    records.append(
        {
            "Figure": f"{display} ({unit})",
            left_name: a,
            right_name: b,
            "Difference": None if pd.isna(a) or pd.isna(b) else b - a,
            "Change": change,
        }
    )
figures = pd.DataFrame(records)
st.dataframe(
    figures.style.format({left_name: "{:,.3f}", right_name: "{:,.3f}", "Difference": "{:+,.3f}"},
                         na_rep="—"),
    width="stretch",
    hide_index=True,
)
st.caption(
    "A dash means the figure is absent from one workbook, or the left value is zero so a "
    "percentage change carries no information."
)

# --- inputs that differ ---------------------------------------------------------------------

st.subheader("Inputs that differ")
param_columns = [c for c in runs.columns if c.startswith("param:")]
rows = []
for column in param_columns:
    a, b = left_row.get(column), right_row.get(column)
    if pd.isna(a) and pd.isna(b):
        continue
    same = pd.notna(a) and pd.notna(b) and np.isclose(a, b, rtol=1e-9, atol=0)
    if same:
        continue
    rows.append({"Parameter": column.removeprefix("param:"), left_name: a, right_name: b})

differences = pd.DataFrame(rows)
if not differences.empty:
    # Absent parameters arrive as Python None in an object column, which a Styler prints
    # literally as "None"; as NaN they honour na_rep instead.
    for side in (left_name, right_name):
        differences[side] = pd.to_numeric(differences[side], errors="coerce")
if differences.empty:
    st.caption("Every parameter these two workbooks share holds the same value.")
else:
    st.dataframe(
        differences.style.format({left_name: "{:,.4g}", right_name: "{:,.4g}"}, na_rep="—"),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        f"{len(differences)} of {len(param_columns)} parameters differ, or appear in only one "
        "of the two workbooks."
    )
    download(differences, "parameter-differences.csv")

# --- one trace column, overlaid --------------------------------------------------------------

st.subheader("A column from both runs")
left_trace = trace_for(left_row["powertrain"], left_row["cycle"])
right_trace = trace_for(right_row["powertrain"], right_row["cycle"])

shared = sorted(set(numeric_trace_columns(left_trace)) & set(numeric_trace_columns(right_trace)))
if not shared:
    st.caption("These two workbooks share no per-step column.")
    st.stop()

shared_axes = [c for c in axis_columns(left_trace) if c in axis_columns(right_trace)]
x_candidates = [c for c in shared_axes if c == "step" or c in shared] or ["step"]
picker, axis = st.columns([3, 1])
with picker:
    column = st.selectbox(
        "Column",
        options=[c for c in shared if c not in ("step",)],
        index=max(0, next((i for i, c in enumerate(shared) if c == "speed_kph"), 0)),
    )
with axis:
    x_column = st.selectbox("Against", options=x_candidates)

if x_column == "step":
    left_trace = left_trace.assign(step=range(len(left_trace)))
    right_trace = right_trace.assign(step=range(len(right_trace)))

fig = charts.compare_traces(
    left_trace, right_trace, column, x_column, (left_name, right_name),
    (left_colour, right_colour), pal,
)
style_axes(fig, pal, x_title=x_column, y_title=column)
fig.update_layout(height=420)
st.plotly_chart(fig, width="stretch", theme=None)

if left_row["cycle"] != right_row["cycle"]:
    st.caption(
        "These runs are on different cycles, so the x-axes cover different ground: the "
        "Francorchamps lap is 7 km, NEDC is about 11 km."
    )
elif (
    len(left_trace) == len(right_trace)
    and left_trace[column].round(9).equals(right_trace[column].round(9))
):
    st.caption(
        f"Both runs report the same {column} at every step, so the two lines coincide — "
        "these workbooks drive the identical cycle."
    )
