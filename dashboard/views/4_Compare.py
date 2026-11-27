"""Compare — two runs side by side: their inputs, their totals, and one trace column."""

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
    show_chart,
    CANONICAL_QUANTITIES,
    WB_CMP_LEFT_KEY,
    WB_CMP_RIGHT_KEY,
    X_LABELS,
    configure,
    download,
    render_run_notices,
    run_label,
    run_picker,
    sidebar_reset_button,
    source_caption,
    varying_parameters,
)
from dashboard.labels import column as column_label
from dashboard.labels import figure, number
from dashboard.loaders import axis_columns, load_runs, numeric_trace_columns, trace_for
from dashboard.theme import style_axes
from dashboard.track_charts import is_lap, lap_section, mark_corners

pal = configure("Compare")
runs = load_runs()

st.title("Compare two runs")

# --- controls -------------------------------------------------------------------------------

pick_left, pick_right = st.columns(2)
with pick_left:
    left_row = run_picker(runs, "Left run", key="cmp_left", index=0, persist_key=WB_CMP_LEFT_KEY)
with pick_right:
    right_row = run_picker(runs, "Right run", key="cmp_right", index=2, persist_key=WB_CMP_RIGHT_KEY)
sidebar_reset_button()

left_name = run_label(left_row["powertrain"], left_row["cycle"])
right_name = run_label(right_row["powertrain"], right_row["cycle"])
left_colour = pal.for_powertrain(left_row["powertrain"])
right_colour = pal.for_powertrain(right_row["powertrain"])

if left_row["source_file"] == right_row["source_file"]:
    st.info("Both sides are the same run. Select two different runs.")
    st.stop()

source_caption(left_row, right_row)
render_run_notices(left_row, right_row)

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
            "Difference (right minus left)": None if pd.isna(a) or pd.isna(b) else b - a,
            "Change from left (%)": change,
        }
    )
figures = pd.DataFrame(records)
st.dataframe(
    figures.style.format({left_name: figure, right_name: figure,
                          "Difference (right minus left)": lambda d: ("+" if d > 0 else "") + figure(d)},
                         na_rep="—"),
    width="stretch",
    hide_index=True,
)
st.caption(
    "A dash marks a missing figure. Percentage change is undefined when the left value is zero."
)

# --- inputs that differ ---------------------------------------------------------------------

st.subheader("Parameter differences")
pair = pd.concat([left_row.to_frame().T, right_row.to_frame().T], ignore_index=True)
differences = varying_parameters(pair)
if not differences.empty:
    differences = differences.drop(columns="Distinct values")

if differences.empty:
    st.caption("The workbooks report the same parameters and values.")
else:
    st.dataframe(
        differences.style.format({left_name: number, right_name: number}, na_rep="—"),
        width="stretch",
        hide_index=True,
    )
    st.caption("A dash marks a parameter the workbook does not report.")
    download(differences, "parameter-differences.csv", "Download parameter differences (CSV)")

# --- one trace column, overlaid --------------------------------------------------------------

st.subheader("Trace comparison")
left_trace = trace_for(left_row["powertrain"], left_row["cycle"])
right_trace = trace_for(right_row["powertrain"], right_row["cycle"])

shared = sorted(set(numeric_trace_columns(left_trace)) & set(numeric_trace_columns(right_trace)))
if not shared:
    st.caption("These runs share no numeric trace column.")
    st.stop()

shared_axes = [c for c in axis_columns(left_trace) if c in axis_columns(right_trace)]
x_candidates = [c for c in shared_axes if c == "step" or c in shared] or ["step"]
picker, axis = st.columns([3, 1])
with picker:
    column = st.selectbox(
        "Trace column",
        options=[c for c in shared if c not in ("step",)],
        index=max(0, next((i for i, c in enumerate(shared) if c == "speed_kph"), 0)),
        format_func=column_label,
    )
with axis:
    x_column = st.selectbox("X-axis", options=x_candidates, format_func=column_label)

if x_column == "step":
    left_trace = left_trace.assign(step=range(len(left_trace)))
    right_trace = right_trace.assign(step=range(len(right_trace)))

fig = charts.compare_traces(
    left_trace, right_trace, column, x_column, (left_name, right_name),
    (left_colour, right_colour), pal,
)
style_axes(fig, pal, x_title=X_LABELS.get(x_column, x_column), y_title=column_label(column))
fig.update_layout(height=420)
both_laps = is_lap(left_row["cycle"]) and is_lap(right_row["cycle"])
# Eco and sport reach a corner at different times, so only distance suits both.
if both_laps and (x_column == "distance_m" or left_row["cycle"] == right_row["cycle"]):
    mark_corners(fig, left_trace, x_column, pal)
show_chart(fig, toolbar=True)

if left_row["cycle"] != right_row["cycle"] and x_column == "step":
    st.caption("Step numbers refer to each workbook's own trace.")
elif (
    len(left_trace) == len(right_trace)
    and left_trace[column].round(9).equals(right_trace[column].round(9))
):
    col_lower = column_label(column, with_unit=False).lower()
    same_x = left_trace[x_column].round(9).equals(right_trace[x_column].round(9))
    if same_x:
        st.caption(
            f"Both workbooks report the same {col_lower} values at matching {X_LABELS.get(x_column, x_column).lower()}, "
            "so the two lines coincide."
        )
    else:
        st.caption(f"Both workbooks report the same {col_lower} values.")

laps = {name: t for name, t, r in ((left_name, left_trace, left_row),
                                   (right_name, right_trace, right_row)) if is_lap(r["cycle"])}
if laps:
    st.subheader("Circuit map")
    lap_section(laps, "compare", pal, source="workbook")
