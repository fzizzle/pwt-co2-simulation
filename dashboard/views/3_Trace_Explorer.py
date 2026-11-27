"""Trace Explorer — the per-step data for one run, instead of scrolling a spreadsheet."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard import charts
from dashboard.layout import (
    show_chart,
    WB_TRACE_RUN_KEY,
    X_LABELS,
    configure,
    download,
    render_run_notices,
    run_label,
    run_picker,
    sidebar_reset_button,
    source_caption,
)
from dashboard.labels import column as column_label
from dashboard.labels import readable
from dashboard.loaders import (
    axis_columns,
    axis_exclusion_reason,
    load_runs,
    numeric_trace_columns,
    trace_for,
)
from dashboard.theme import style_axes
from dashboard.track_charts import is_lap, lap_section, mark_corners

pal = configure("Trace explorer")
runs = load_runs()

st.title("Trace explorer")

# --- controls -------------------------------------------------------------------------------

row = run_picker(runs, "Run", key="trace_run", index=0, persist_key=WB_TRACE_RUN_KEY)
sidebar_reset_button()
trace = trace_for(row["powertrain"], row["cycle"])

if trace.empty:
    st.warning("This workbook has no trace data.")
    st.stop()

available = numeric_trace_columns(trace)
x_options = axis_columns(trace)
x_column = st.sidebar.selectbox(
    "X-axis", options=x_options, format_func=lambda c: X_LABELS[c]
)
x_label = X_LABELS[x_column]

for excluded in ("distance_m", "time_s"):
    reason = axis_exclusion_reason(trace, excluded)
    if reason:
        st.sidebar.caption(reason)
if x_column == "step":
    trace = trace.assign(step=range(len(trace)))

source_caption(row)
render_run_notices(row)
on_lap = is_lap(row["cycle"]) and "distance_m" in x_options

# --- the three standing views ---------------------------------------------------------------

st.subheader("Speed and altitude")
fig = charts.speed_and_altitude(trace, x_column, pal, colour=pal.for_powertrain(row["powertrain"]))
style_axes(fig, pal, x_title=x_label)
fig.update_layout(height=420)
if on_lap:
    mark_corners(fig, trace, x_column, pal)
show_chart(fig, toolbar=True)

if on_lap:
    st.subheader("Circuit map")
    lap_section({run_label(row["powertrain"], row["cycle"]): trace}, "trace", pal, source="workbook",
                colour=pal.for_powertrain(row["powertrain"]))

left, right = st.columns(2)

with left:
    if "gear" in trace.columns and trace["gear"].notna().any():
        st.subheader("Gear")
        fig = charts.gear_steps(trace, x_column, pal, colour=pal.for_powertrain(row["powertrain"]))
        style_axes(fig, pal, x_title=x_label, y_title="Gear")
        fig.update_layout(height=300)
        if on_lap:
            mark_corners(fig, trace, x_column, pal, labels=False)
        show_chart(fig)
    else:
        st.subheader("Gear")
        st.caption("This workbook has no gear data.")

with right:
    st.subheader("Forces")
    fig = charts.force_breakdown(trace, x_column, pal)
    style_axes(fig, pal, x_title=x_label, y_title="Force (N)")
    fig.update_layout(height=300)
    if on_lap:
        mark_corners(fig, trace, x_column, pal, labels=False)
    show_chart(fig)
    st.caption(
        "Acceleration force can be negative during braking. "
        "Resistive force can be negative on descents."
    )

# --- free-form column picker ----------------------------------------------------------------

st.subheader("Trace columns")
default = [c for c in ("engine_power_w",) if c in available] or available[:1]
columns = st.multiselect(
    "Columns to plot", options=available, default=default, label_visibility="collapsed",
    format_func=column_label,
)
if columns:
    fig = charts.trace_lines(trace, columns, x_column, pal)
    style_axes(fig, pal, x_title=x_label,
               y_title=column_label(columns[0]) if len(columns) == 1 else "")
    fig.update_layout(height=380)
    if on_lap:
        mark_corners(fig, trace, x_column, pal)
    show_chart(fig, toolbar=True)
    if len(columns) > 1:
        st.caption(
            "Selected columns share one scale. Plot columns with different units separately."
        )
else:
    st.caption("Select at least one column.")

# --- the table ------------------------------------------------------------------------------

with st.expander(f"Trace table ({len(trace)} steps)"):
    st.dataframe(readable(trace), width="stretch", hide_index=True)
    download(trace, f"trace-{row['powertrain']}-{row['cycle']}.csv", "Download trace (CSV)")
